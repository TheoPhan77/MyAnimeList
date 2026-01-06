import time
import requests
from bs4 import BeautifulSoup
import re

BASE_URL = "https://myanimelist.net"
TOP_ANIME_URL = f"{BASE_URL}/topanime.php"

HEADERS = {
    # User-Agent pour éviter d'être pris pour un bot low-cost
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}


def fetch_html(url: str) -> str:
    """Télécharge une page HTML et renvoie son contenu texte."""
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    time.sleep(1)  # Toujours garder la pause pour éviter de se faire bloquer
    return resp.text


def parse_top_anime_page(html: str):
    """
    Parse une page du top anime.
    Renvoie une liste de dicts {title, url, score}.
    """
    soup = BeautifulSoup(html, "html.parser")
    animes = []

    # ⚠️ Les sélecteurs ci-dessous dépendent du HTML exact de MyAnimeList.
    # Il faudra peut-être les ajuster après un test avec Inspecter l'élément.
    rows = soup.select(".ranking-list")

    print(f"[DEBUG] Nombre de blocs d'anime trouvés: {len(rows)}")

    for row in rows:
        # Titre + URL
        title_tag = row.select_one("h3.anime_ranking_h3 a")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        url = title_tag["href"]

        # Score
        score_tag = row.select_one("span.score-label")
        score = None
        if score_tag and score_tag.get_text(strip=True) != "N/A":
            try:
                score = float(score_tag.get_text(strip=True))
            except ValueError:
                score = None

        animes.append(
            {
                "title": title,
                "url": url,
                "score": score,
            }
        )

    return animes


def scrap_top_anime(limit_start: int = 0):
    """
    Scrape une page du top anime à partir d'un offset "limit".
    MyAnimeList utilise souvent un paramètre ?limit=0,50,100,...
    """
    url = f"{TOP_ANIME_URL}?limit={limit_start}"
    html = fetch_html(url)
    animes = parse_top_anime_page(html)
    return animes


def extract_mal_id(url: str) -> int | None:
    """Extrait l'ID MyAnimeList à partir de l'URL, ex: /anime/5114/... -> 5114."""
    m = re.search(r"/anime/(\d+)", url)
    if m:
        return int(m.group(1))
    return None


def scrap_anime_detail(url: str) -> dict:
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    # --- TITLE ---
    title_tag = soup.select_one("h1.title-name strong")
    title = title_tag.get_text(strip=True) if title_tag else None

    title_english_tag = soup.select_one("p.title-english")
    title_english = title_english_tag.get_text(strip=True) if title_english_tag else None

    # --- SYNOPSIS ---
    synopsis_tag = soup.select_one("p[itemprop='description']")
    synopsis = synopsis_tag.get_text(" ", strip=True) if synopsis_tag else None

    # --- INFO SECTION ---
    type_ = episodes = status = aired = premiered = broadcast = None
    producers = studios = genres = themes = demographic = []
    source = duration = rating = None

    info_blocks = soup.select("div.spaceit_pad")
    for block in info_blocks:
        text = block.get_text(" ", strip=True)

        if text.startswith("Type:"):
            type_ = text.replace("Type:", "").strip()

        elif text.startswith("Episodes:"):
            episodes = text.replace("Episodes:", "").strip()

        elif text.startswith("Status:"):
            status = text.replace("Status:", "").strip()

        elif text.startswith("Aired:"):
            aired = text.replace("Aired:", "").strip()

        elif text.startswith("Premiered:"):
            premiered = text.replace("Premiered:", "").strip()

        elif text.startswith("Broadcast:"):
            broadcast = text.replace("Broadcast:", "").strip()

        elif text.startswith("Producers:"):
            producers = [a.get_text(strip=True) for a in block.select("a")]

        elif text.startswith("Studios:"):
            studios = [a.get_text(strip=True) for a in block.select("a")]

        elif text.startswith("Source:"):
            source = text.replace("Source:", "").strip()

        elif text.startswith("Genres:"):
            genres = [a.get_text(strip=True) for a in block.select("a")]

        elif text.startswith("Themes:"):
            themes = [a.get_text(strip=True) for a in block.select("a")]

        elif text.startswith("Demographic:"):
            demographic = [a.get_text(strip=True) for a in block.select("a")]

        elif text.startswith("Duration:"):
            duration = text.replace("Duration:", "").strip()

        elif text.startswith("Rating:"):
            rating = text.replace("Rating:", "").strip()

    # --- STATS ---
    score = rank = popularity = members = None

    score_tag = soup.select_one("div.score-label")
    if score_tag:
        score = float(score_tag.get_text(strip=True))

    stats_block = soup.select_one("div.stats-block")
    if stats_block:
        for stat in stats_block.get_text("\n", strip=True).split("\n"):
            if stat.startswith("Ranked"):
                rank = stat.replace("Ranked #", "").strip()
            elif stat.startswith("Popularity"):
                popularity = stat.replace("Popularity #", "").strip()
            elif stat.startswith("Members"):
                members = stat.replace("Members", "").strip()

    return {
        "title": title,
        "title_english": title_english,
        "url": url,
        "score": score,
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


if __name__ == "__main__":
    print("[INFO] Début du scraping complet du Top Anime...")

    dataset = []
    top_animes = scrap_top_anime(limit_start=0)

    # On limite à 50 ici, mais tu peux changer
    to_scrape = top_animes[:50]
    total = len(to_scrape)

    print(f"[INFO] Nombre d'animes trouvés dans le top : {total}")

    bar_length = 30  # taille de la barre de progression

    for i, anime in enumerate(to_scrape, start=1):
        # --- Effacer la ligne précédente ---
        print("\r\033[K", end="")

        # --- Affichage barre de progression ---
        progress = i / total
        filled = int(bar_length * progress)
        bar = "#" * filled + "-" * (bar_length - filled)

        print(
            f"\r[INFO] [{bar}] {i}/{total} - {anime['title']}",
            end="",
            flush=True,
        )

        # --- Scraping des détails ---
        details = scrap_anime_detail(anime["url"])
        dataset.append(details)

    print("\r\033[K", end="")
    print(f"\r[INFO] [{bar}] {i}/{total}")
    print(f"\n[INFO] Scraping terminé : {len(dataset)} animes récupérés.")

    # petit aperçu
    for j, anime in enumerate(dataset[:3], start=1):
        print(f"\n{j:02d}. {anime['title']}")
        print(f"   Genres : {anime['genres']}")
        print(f"   Score  : {anime['score']}")

