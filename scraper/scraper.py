import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from pymongo import MongoClient, UpdateOne

BASE_URL = "https://myanimelist.net"
TOP_ANIME_URL = f"{BASE_URL}/topanime.php"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

DEFAULT_EXCLUDED_TYPES = {
    value.strip()
    for value in os.getenv("EXCLUDED_TYPES", "Music,PV,CM").split(",")
    if value.strip()
}
HTTP_TIMEOUT_SECONDS = int(os.getenv("HTTP_TIMEOUT_SECONDS", "15"))
HTTP_RETRIES = int(os.getenv("HTTP_RETRIES", "3"))
HTTP_BACKOFF_SECONDS = float(os.getenv("HTTP_BACKOFF_SECONDS", "1.5"))
HTTP_SLEEP_SECONDS = float(os.getenv("HTTP_SLEEP_SECONDS", "1.0"))
HYDRATE_MAX_WORKERS = int(os.getenv("HYDRATE_MAX_WORKERS", "8"))


def _safe_int(value):
    if value is None:
        return None
    cleaned = re.sub(r"[^\d]", "", str(value))
    return int(cleaned) if cleaned else None


def _safe_float(value):
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _normalize_list(values):
    return [v for v in values if v and isinstance(v, str)]


def _upgrade_image_url(image_url):
    if not image_url:
        return image_url
    # MAL ranking pages often expose low-res thumbnails under /r/<w>x<h>/.
    return re.sub(r"/r/\d+x\d+/", "/", image_url)


def fetch_html(
    url: str,
    timeout_seconds: int = HTTP_TIMEOUT_SECONDS,
    retries: int = HTTP_RETRIES,
    backoff_seconds: float = HTTP_BACKOFF_SECONDS,
    sleep_seconds: float = HTTP_SLEEP_SECONDS,
) -> str:
    """
    Fetch HTML with retry/backoff and a short anti-rate-limit pause.
    """
    last_exc = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout_seconds)
            resp.raise_for_status()
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
            return resp.text
        except requests.RequestException as exc:
            last_exc = exc
            if attempt >= retries:
                break
            time.sleep(backoff_seconds * (attempt + 1))
    raise last_exc


def extract_mal_id(url: str):
    match = re.search(r"/anime/(\d+)", url or "")
    return int(match.group(1)) if match else None


def parse_top_anime_page(html: str, excluded_types=None):
    excluded_types = set(excluded_types or DEFAULT_EXCLUDED_TYPES)
    soup = BeautifulSoup(html, "html.parser")
    animes = []

    rows = soup.select(".ranking-list")
    for row in rows:
        rank_tag = row.select_one("td.rank")
        rank = _safe_int(rank_tag.get_text(strip=True)) if rank_tag else None

        title_tag = row.select_one("h3.anime_ranking_h3 a")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        url = title_tag.get("href")
        mal_id = extract_mal_id(url)

        score = None
        score_tag = row.select_one("span.score-label")
        if score_tag:
            txt = score_tag.get_text(strip=True)
            if txt != "N/A":
                score = _safe_float(txt)

        img_tag = row.select_one("img")
        raw_image_url = img_tag.get("data-src") or img_tag.get("src") if img_tag else None
        image_url = _upgrade_image_url(raw_image_url)

        type_ = None
        episodes = None
        info_tag = row.select_one("div.information")
        if info_tag:
            info_text = info_tag.get_text(" ", strip=True)
            # Example: "TV (64 eps)"
            type_match = re.search(r"^(TV|Movie|OVA|ONA|Special|Music|PV|CM)\b", info_text)
            eps_match = re.search(r"\((\d+|\?)\s*eps\)", info_text)
            if type_match:
                type_ = type_match.group(1)
            if eps_match:
                episodes = eps_match.group(1)

        if type_ in excluded_types:
            continue

        animes.append(
            {
                "mal_id": mal_id,
                "rank": rank,
                "title": title,
                "url": url,
                "score": score,
                "image_url": image_url,
                "type": type_,
                "episodes": episodes,
            }
        )
    return animes


def scrap_top_anime(limit_start: int = 0, excluded_types=None):
    url = f"{TOP_ANIME_URL}?limit={limit_start}"
    html = fetch_html(url)
    return parse_top_anime_page(html, excluded_types=excluded_types)


def scrap_anime_detail(url: str):
    mal_id = extract_mal_id(url)
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.select_one("h1.title-name strong")
    title = title_tag.get_text(strip=True) if title_tag else None

    title_english_tag = soup.select_one("p.title-english")
    title_english = title_english_tag.get_text(strip=True) if title_english_tag else None

    title_japanese = None
    synopsis_tag = soup.select_one("p[itemprop='description']")
    synopsis = synopsis_tag.get_text(" ", strip=True) if synopsis_tag else None

    type_ = episodes = status = aired = premiered = broadcast = None
    producers = []
    studios = []
    genres = []
    themes = []
    demographic = []
    source = duration = rating = None

    info_blocks = soup.select("div.spaceit_pad")
    for block in info_blocks:
        text = block.get_text(" ", strip=True)
        if text.startswith("Type:"):
            type_ = text.replace("Type:", "", 1).strip()
        elif text.startswith("Episodes:"):
            episodes = text.replace("Episodes:", "", 1).strip()
        elif text.startswith("Status:"):
            status = text.replace("Status:", "", 1).strip()
        elif text.startswith("Aired:"):
            aired = text.replace("Aired:", "", 1).strip()
        elif text.startswith("Premiered:"):
            premiered = text.replace("Premiered:", "", 1).strip()
        elif text.startswith("Broadcast:"):
            broadcast = text.replace("Broadcast:", "", 1).strip()
        elif text.startswith("Producers:"):
            producers = _normalize_list([a.get_text(strip=True) for a in block.select("a")])
        elif text.startswith("Studios:"):
            studios = _normalize_list([a.get_text(strip=True) for a in block.select("a")])
        elif text.startswith("Source:"):
            source = text.replace("Source:", "", 1).strip()
        elif text.startswith("Genres:"):
            genres = _normalize_list([a.get_text(strip=True) for a in block.select("a")])
        elif text.startswith("Theme:") or text.startswith("Themes:"):
            themes = _normalize_list([a.get_text(strip=True) for a in block.select("a")])
        elif text.startswith("Demographic:"):
            demographic = _normalize_list([a.get_text(strip=True) for a in block.select("a")])
        elif text.startswith("Duration:"):
            duration = text.replace("Duration:", "", 1).strip()
        elif text.startswith("Rating:"):
            rating = text.replace("Rating:", "", 1).strip()
        elif text.startswith("Japanese:"):
            title_japanese = text.replace("Japanese:", "", 1).strip()

    score = None
    score_tag = soup.select_one("div.score-label")
    if score_tag:
        score = _safe_float(score_tag.get_text(strip=True))

    scored_by = None
    scored_by_tag = soup.select_one("span[itemprop='ratingCount']")
    if scored_by_tag:
        scored_by = _safe_int(scored_by_tag.get_text(strip=True))

    rank = popularity = members = None
    stats_block = soup.select_one("div.stats-block")
    if stats_block:
        for stat in stats_block.get_text("\n", strip=True).split("\n"):
            if stat.startswith("Ranked"):
                rank = _safe_int(stat.replace("Ranked #", "", 1).strip())
            elif stat.startswith("Popularity"):
                popularity = _safe_int(stat.replace("Popularity #", "", 1).strip())
            elif stat.startswith("Members"):
                members = _safe_int(stat.replace("Members", "", 1).strip())

    return {
        "mal_id": mal_id,
        "title": title,
        "title_english": title_english,
        "title_japanese": title_japanese,
        "url": url,
        "score": score,
        "scored_by": scored_by,
        "rank": rank,
        "popularity": popularity,
        "members": members,
        "type": type_,
        "episodes": episodes,
        "status": status,
        "aired": aired,
        "premiered": premiered,
        "broadcast": broadcast,
        "producers": producers,
        "studios": studios,
        "source": source,
        "genres": genres,
        "themes": themes,
        "demographic": demographic,
        "duration": duration,
        "rating": rating,
        "synopsis": synopsis,
    }


def scrap_full_top(max_anime: int = 50, excluded_types=None):
    print(f"[INFO] Starting full scrape for top {max_anime} anime...")
    dataset = []
    count = 0
    limit_start = 0

    while count < max_anime:
        page_animes = scrap_top_anime(limit_start=limit_start, excluded_types=excluded_types)
        if not page_animes:
            break

        for anime in page_animes:
            if count >= max_anime:
                break
            count += 1
            print(f"[INFO] ({count}/{max_anime}) {anime['title'][:70]}")
            details = scrap_anime_detail(anime["url"])
            dataset.append(details)

        limit_start += 50

    print(f"[INFO] Scraping complete: {len(dataset)} details rows")
    return dataset


def get_mongo_client():
    uri = os.getenv("MONGO_URI", "mongodb://root:rootpass@localhost:27017/?authSource=admin")
    return MongoClient(uri)


def upsert_anime_list_to_mongo(anime_list, db_name="animedb", collection_name="anime_list"):
    client = get_mongo_client()
    col = client[db_name][collection_name]

    ops = []
    skipped = 0
    for anime in anime_list:
        mal_id = anime.get("mal_id")
        if mal_id is None:
            skipped += 1
            continue
        doc = dict(anime)
        doc["_id"] = mal_id
        doc.pop("mal_id", None)
        ops.append(UpdateOne({"_id": mal_id}, {"$set": doc}, upsert=True))

    if ops:
        res = col.bulk_write(ops, ordered=False)
        print(
            f"[INFO] Mongo upsert OK | matched={res.matched_count} "
            f"modified={res.modified_count} upserted={len(res.upserted_ids)} skipped={skipped}"
        )
    else:
        print(f"[WARN] Nothing to upsert. skipped={skipped}")
    client.close()


def upsert_anime_detail_to_mongo(detail, db_name="animedb", details_col="anime_details"):
    mal_id = detail.get("mal_id")
    if mal_id is None:
        return
    client = get_mongo_client()
    col = client[db_name][details_col]
    doc = dict(detail)
    doc["_id"] = mal_id
    doc["details_fetched_at"] = datetime.now().isoformat(timespec="seconds")
    col.update_one({"_id": mal_id}, {"$set": doc}, upsert=True)
    client.close()


def get_anime_details_cached(
    mal_id: int,
    url: str,
    db_name="animedb",
    details_col="anime_details",
    max_age_hours=24,
):
    client = get_mongo_client()
    col = client[db_name][details_col]
    doc = col.find_one({"_id": mal_id})

    if doc and doc.get("details_fetched_at"):
        try:
            fetched_at = doc["details_fetched_at"]
            if isinstance(fetched_at, str):
                fetched_at = datetime.fromisoformat(fetched_at)
            if datetime.now() - fetched_at < timedelta(hours=max_age_hours):
                client.close()
                return doc
        except Exception:
            pass

    details = scrap_anime_detail(url)
    details["_id"] = mal_id
    details["details_fetched_at"] = datetime.now().isoformat(timespec="seconds")
    col.update_one({"_id": mal_id}, {"$set": details}, upsert=True)

    client.close()
    return details


def get_top_from_mongo(skip=0, limit=50, db_name="animedb", col_name="anime_list"):
    client = get_mongo_client()
    col = client[db_name][col_name]
    projection = {
        "_id": 1,
        "rank": 1,
        "title": 1,
        "score": 1,
        "image_url": 1,
        "type": 1,
        "episodes": 1,
        "url": 1,
    }
    # `skip` is treated as MAL top offset (0, 50, 100...), not as DB cursor offset.
    # This makes paging robust even when Mongo cache is sparse (e.g., only pages 0 and 500 cached).
    start_rank = max(int(skip), 0) + 1
    docs = list(col.find({"rank": {"$gte": start_rank}}, projection).sort("rank", 1).limit(limit))
    for doc in docs:
        doc["mal_id"] = doc.pop("_id")
    client.close()
    return docs


def get_anime_list_count(db_name="animedb", col_name="anime_list"):
    client = get_mongo_client()
    col = client[db_name][col_name]
    count = col.count_documents({})
    client.close()
    return count


def get_anime_list_by_ids(mal_ids, db_name="animedb", col_name="anime_list"):
    if not mal_ids:
        return []
    client = get_mongo_client()
    col = client[db_name][col_name]
    projection = {
        "_id": 1,
        "rank": 1,
        "title": 1,
        "score": 1,
        "image_url": 1,
        "type": 1,
        "episodes": 1,
        "url": 1,
    }
    docs = list(col.find({"_id": {"$in": mal_ids}}, projection))
    by_id = {}
    for doc in docs:
        doc["mal_id"] = doc.pop("_id")
        by_id[doc["mal_id"]] = doc
    client.close()
    return [by_id[mid] for mid in mal_ids if mid in by_id]


def fetch_next_top_page_to_mongo(limit_start: int, db_name="animedb", excluded_types=None):
    page = scrap_top_anime(limit_start=limit_start, excluded_types=excluded_types)
    upsert_anime_list_to_mongo(page, db_name=db_name, collection_name="anime_list")
    return page


def hydrate_details_from_mongo_top(
    max_items=100,
    skip=0,
    db_name="animedb",
    list_col="anime_list",
    details_col="anime_details",
    max_age_hours=24,
):
    top_rows = get_top_from_mongo(skip=skip, limit=max_items, db_name=db_name, col_name=list_col)
    if not top_rows:
        return []

    now = datetime.now()
    max_age = timedelta(hours=max_age_hours)
    top_ids = [row["mal_id"] for row in top_rows]
    by_id = {row["mal_id"]: row for row in top_rows}

    client = get_mongo_client()
    details = client[db_name][details_col]

    existing_docs = list(details.find({"_id": {"$in": top_ids}}, {"details_fetched_at": 1}))
    fresh_ids = set()
    for doc in existing_docs:
        fetched_at = doc.get("details_fetched_at")
        if not fetched_at:
            continue
        try:
            if isinstance(fetched_at, str):
                fetched_at = datetime.fromisoformat(fetched_at)
            if now - fetched_at < max_age:
                fresh_ids.add(doc["_id"])
        except Exception:
            continue

    stale_rows = [by_id[mid] for mid in top_ids if mid not in fresh_ids]

    def _scrape_one(row):
        detail = scrap_anime_detail(row["url"])
        detail["_id"] = row["mal_id"]
        detail["mal_id"] = row["mal_id"]
        detail["details_fetched_at"] = datetime.now().isoformat(timespec="seconds")
        return detail

    if stale_rows:
        workers = max(1, min(HYDRATE_MAX_WORKERS, len(stale_rows)))
        ops = []
        errors = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_to_row = {pool.submit(_scrape_one, row): row for row in stale_rows}
            for future in as_completed(future_to_row):
                row = future_to_row[future]
                try:
                    doc = future.result()
                    ops.append(UpdateOne({"_id": doc["_id"]}, {"$set": doc}, upsert=True))
                except Exception:
                    errors += 1
                    print(f"[WARN] Failed detail scrape for mal_id={row['mal_id']}")
        if ops:
            details.bulk_write(ops, ordered=False)
        if errors:
            print(f"[WARN] Detail scrape errors: {errors}")

    hydrated_docs = list(details.find({"_id": {"$in": top_ids}}))
    hydrated_by_id = {doc["_id"]: doc for doc in hydrated_docs}
    ordered = [hydrated_by_id[mid] for mid in top_ids if mid in hydrated_by_id]
    client.close()
    return ordered


def get_mongo_details_distinct(
    field_name: str,
    db_name="animedb",
    details_col="anime_details",
    max_values=None,
):
    client = get_mongo_client()
    col = client[db_name][details_col]
    raw_values = col.distinct(field_name)
    client.close()

    flattened = []
    for value in raw_values:
        if isinstance(value, list):
            flattened.extend(value)
        else:
            flattened.append(value)
    cleaned = sorted({v for v in flattened if isinstance(v, str) and v.strip()})
    if isinstance(max_values, int) and max_values > 0:
        return cleaned[:max_values]
    return cleaned


def get_mongo_details_count(db_name="animedb", details_col="anime_details"):
    client = get_mongo_client()
    col = client[db_name][details_col]
    count = col.count_documents({})
    client.close()
    return count


def get_es_client():
    es_url = os.getenv("ES_URL", "http://localhost:9200")
    return Elasticsearch(es_url, request_timeout=30)


def ensure_es_index(index_name="anime_index"):
    es = get_es_client()
    if es.indices.exists(index=index_name):
        return

    mappings = {
        "properties": {
            "mal_id": {"type": "integer"},
            "title": {"type": "text"},
            "title_english": {"type": "text"},
            "title_japanese": {"type": "text"},
            "synopsis": {"type": "text"},
            "type": {"type": "keyword"},
            "source": {"type": "keyword"},
            "genres": {"type": "keyword"},
            "themes": {"type": "keyword"},
            "studios": {"type": "keyword"},
            "demographic": {"type": "keyword"},
            "score": {"type": "float"},
            "rank": {"type": "integer"},
            "popularity": {"type": "integer"},
            "members": {"type": "integer"},
            "scored_by": {"type": "integer"},
            "url": {"type": "keyword"},
            "details_fetched_at": {"type": "date"},
        }
    }
    es.indices.create(index=index_name, mappings=mappings)


def _detail_to_es_doc(detail):
    mal_id = detail.get("mal_id") or detail.get("_id")
    return {
        "mal_id": mal_id,
        "title": detail.get("title"),
        "title_english": detail.get("title_english"),
        "title_japanese": detail.get("title_japanese"),
        "synopsis": detail.get("synopsis"),
        "type": detail.get("type"),
        "source": detail.get("source"),
        "genres": _normalize_list(detail.get("genres", [])),
        "themes": _normalize_list(detail.get("themes", [])),
        "studios": _normalize_list(detail.get("studios", [])),
        "demographic": _normalize_list(detail.get("demographic", [])),
        "score": _safe_float(detail.get("score")),
        "rank": _safe_int(detail.get("rank")),
        "popularity": _safe_int(detail.get("popularity")),
        "members": _safe_int(detail.get("members")),
        "scored_by": _safe_int(detail.get("scored_by")),
        "url": detail.get("url"),
        "details_fetched_at": detail.get("details_fetched_at"),
    }


def _list_to_es_doc(row):
    mal_id = row.get("mal_id") or row.get("_id")
    return {
        "mal_id": mal_id,
        "title": row.get("title"),
        "title_english": None,
        "title_japanese": None,
        "synopsis": None,
        "type": row.get("type"),
        "source": None,
        "genres": [],
        "themes": [],
        "studios": [],
        "demographic": [],
        "score": _safe_float(row.get("score")),
        "rank": _safe_int(row.get("rank")),
        "popularity": None,
        "members": None,
        "scored_by": None,
        "url": row.get("url"),
        "details_fetched_at": None,
    }


def index_mongo_list_to_es(
    db_name="animedb",
    list_col="anime_list",
    index_name="anime_index",
    limit=None,
    excluded_types=None,
):
    excluded_types = set(excluded_types or DEFAULT_EXCLUDED_TYPES)
    ensure_es_index(index_name=index_name)

    client = get_mongo_client()
    col = client[db_name][list_col]
    cursor = col.find({})
    if limit:
        cursor = cursor.limit(limit)

    actions = []
    count = 0
    for row in cursor:
        es_doc = _list_to_es_doc(row)
        if es_doc.get("type") in excluded_types:
            continue
        mal_id = es_doc.get("mal_id")
        if mal_id is None:
            continue
        actions.append(
            {
                "_op_type": "index",
                "_index": index_name,
                "_id": mal_id,
                "_source": es_doc,
            }
        )
        count += 1

    if actions:
        bulk(get_es_client(), actions, refresh=True)
    client.close()
    return count


def index_mongo_details_to_es(
    db_name="animedb",
    details_col="anime_details",
    index_name="anime_index",
    limit=None,
    excluded_types=None,
):
    excluded_types = set(excluded_types or DEFAULT_EXCLUDED_TYPES)
    ensure_es_index(index_name=index_name)

    client = get_mongo_client()
    col = client[db_name][details_col]
    cursor = col.find({})
    if limit:
        cursor = cursor.limit(limit)

    actions = []
    count = 0
    for detail in cursor:
        es_doc = _detail_to_es_doc(detail)
        if es_doc.get("type") in excluded_types:
            continue
        mal_id = es_doc.get("mal_id")
        if mal_id is None:
            continue
        actions.append(
            {
                "_op_type": "index",
                "_index": index_name,
                "_id": mal_id,
                "_source": es_doc,
            }
        )
        count += 1

    if actions:
        bulk(get_es_client(), actions, refresh=True)
    client.close()
    return count


def _format_es_hits(resp):
    hits = []
    for hit in resp.get("hits", {}).get("hits", []):
        doc = hit.get("_source", {})
        doc["es_score"] = hit.get("_score")
        hits.append(doc)
    return hits


def search_anime_in_es(
    query: str,
    size=20,
    min_score=0.0,
    excluded_types=None,
    index_name="anime_index",
):
    excluded_types = list(excluded_types or DEFAULT_EXCLUDED_TYPES)
    es = get_es_client()

    filters = []
    if min_score:
        filters.append({"range": {"score": {"gte": float(min_score)}}})

    if query and query.strip():
        strict_body = {
            "size": size,
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["title^5", "title_english^4", "title_japanese^4", "synopsis"],
                                "type": "best_fields",
                                "operator": "and",
                            }
                        }
                    ],
                    "filter": filters,
                    "must_not": [{"terms": {"type": excluded_types}}] if excluded_types else [],
                }
            },
            "sort": ["_score", {"score": {"order": "desc", "missing": "_last"}}],
        }
        strict_resp = es.search(index=index_name, body=strict_body)
        strict_hits = _format_es_hits(strict_resp)
        if strict_hits:
            return strict_hits

        fuzzy_body = {
            "size": size,
            "query": {
                "bool": {
                    "should": [
                        {"match_phrase": {"title": {"query": query, "boost": 10.0}}},
                        {"match_phrase": {"title_english": {"query": query, "boost": 8.0}}},
                        {"match_phrase": {"title_japanese": {"query": query, "boost": 8.0}}},
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["title^4", "title_english^3", "title_japanese^3", "synopsis"],
                                "type": "best_fields",
                                "fuzziness": "AUTO",
                            }
                        },
                    ],
                    "minimum_should_match": 1,
                    "filter": filters,
                    "must_not": [{"terms": {"type": excluded_types}}] if excluded_types else [],
                }
            },
            "sort": ["_score", {"score": {"order": "desc", "missing": "_last"}}],
        }
        resp = es.search(index=index_name, body=fuzzy_body)
        return _format_es_hits(resp)
    else:
        body = {
            "size": size,
            "query": {
                "bool": {
                    "must": [{"match_all": {}}],
                    "filter": filters,
                    "must_not": [{"terms": {"type": excluded_types}}] if excluded_types else [],
                }
            },
            "sort": ["_score", {"score": {"order": "desc", "missing": "_last"}}],
        }
        resp = es.search(index=index_name, body=body)
        return _format_es_hits(resp)


def recommend_anime_in_es(
    preferred_genres=None,
    preferred_themes=None,
    preferred_studios=None,
    query_text=None,
    size=20,
    min_score=0.0,
    excluded_types=None,
    index_name="anime_index",
):
    preferred_genres = preferred_genres or []
    preferred_themes = preferred_themes or []
    preferred_studios = preferred_studios or []
    excluded_types = list(excluded_types or DEFAULT_EXCLUDED_TYPES)
    es = get_es_client()

    should = []
    if query_text and query_text.strip():
        should.append({"match_phrase": {"title": {"query": query_text, "boost": 8.0}}})
        should.append({"match_phrase": {"title_english": {"query": query_text, "boost": 6.0}}})
        should.append(
            {
                "multi_match": {
                    "query": query_text,
                    "fields": ["title^4", "title_english^3", "title_japanese^3", "synopsis"],
                    "type": "best_fields",
                    "operator": "and",
                    "boost": 2.5,
                }
            }
        )
    for genre in preferred_genres:
        should.append({"term": {"genres": {"value": genre, "boost": 2.0}}})
    for theme in preferred_themes:
        should.append({"term": {"themes": {"value": theme, "boost": 3.0}}})
    for studio in preferred_studios:
        should.append({"term": {"studios": {"value": studio, "boost": 1.2}}})

    filters = []
    if min_score:
        filters.append({"range": {"score": {"gte": float(min_score)}}})

    must = []
    if query_text and query_text.strip():
        must.append(
            {
                "multi_match": {
                    "query": query_text,
                    "fields": ["title^5", "title_english^4", "title_japanese^4", "synopsis"],
                    "type": "best_fields",
                    "operator": "and",
                }
            }
        )
    else:
        must.append({"match_all": {}})

    strict_query = {
        "bool": {
            "must": must,
            "should": should,
            "minimum_should_match": 1 if should else 0,
            "filter": filters,
            "must_not": [{"terms": {"type": excluded_types}}] if excluded_types else [],
        }
    }

    strict_size = size if size and int(size) > 0 else 20
    strict_body = {
        "size": strict_size,
        "query": strict_query,
        "sort": ["_score", {"score": {"order": "desc", "missing": "_last"}}],
    }
    strict_resp = es.search(index=index_name, body=strict_body)
    strict_hits = _format_es_hits(strict_resp)

    if strict_hits:
        if not size or int(size) <= 0:
            total = es.count(index=index_name, body={"query": strict_query}).get("count", 0)
            if total > strict_size:
                strict_body["size"] = min(int(total), 10000)
                strict_resp = es.search(index=index_name, body=strict_body)
                strict_hits = _format_es_hits(strict_resp)
        return strict_hits

    if should:
        relaxed_query = {
            "bool": {
                "must": must,
                "should": should,
                "minimum_should_match": 0,
                "filter": filters,
                "must_not": [{"terms": {"type": excluded_types}}] if excluded_types else [],
            }
        }
        relaxed_size = size if size and int(size) > 0 else 20
        relaxed_body = {
            "size": relaxed_size,
            "query": relaxed_query,
            "sort": ["_score", {"score": {"order": "desc", "missing": "_last"}}],
        }
        if not size or int(size) <= 0:
            total = es.count(index=index_name, body={"query": relaxed_query}).get("count", 0)
            if total == 0:
                return []
            relaxed_body["size"] = min(int(total), 10000)
        relaxed_resp = es.search(index=index_name, body=relaxed_body)
        return _format_es_hits(relaxed_resp)

    return []


if __name__ == "__main__":
    rows = []
    for offset in range(0, 300, 50):
        print(f"[INFO] Pulling top page with limit={offset}")
        rows.extend(scrap_top_anime(limit_start=offset))
    print(f"[INFO] Scraped {len(rows)} rows")
    try:
        upsert_anime_list_to_mongo(rows)
    except Exception as exc:
        print("[ERROR] Could not write to MongoDB.")
        print("[ERROR] Start Docker first: docker compose up -d")
        print(f"[ERROR] {exc}")
