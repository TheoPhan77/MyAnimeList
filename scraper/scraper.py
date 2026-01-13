import time
import requests
from bs4 import BeautifulSoup
import re
from pymongo import MongoClient, UpdateOne
from datetime import datetime, timedelta


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
    """
    Télécharge une page HTML et renvoie le contenu brut (string).

    Pourquoi cette fonction ?
    - Centraliser les requêtes HTTP (headers, timeout, pause anti-bot)
    - Faciliter la maintenance : si MAL change / si on veut ajouter retry, on le fait ici.

    Paramètres
    ----------
    url : str
        URL à télécharger.

    Retour
    ------
    str
        HTML de la page (resp.text)
    """
    # Requête HTTP avec un User-Agent "réaliste" pour limiter les blocages
    resp = requests.get(url, headers=HEADERS, timeout=10)

    # Déclenche une erreur si code HTTP != 200 (403, 404, 500...)
    resp.raise_for_status()

    # Pause volontaire : on évite d'enchaîner trop vite et de se faire rate-limit / bloquer
    time.sleep(1)

    return resp.text


def parse_top_anime_page(html: str):
    """
    Parse une page du Top Anime (topanime.php) et retourne une liste "légère".

    Objectif :
    - Construire un dataset minimal pour la Home / bouton "Plus"
    - Ne pas aller sur les pages détails (trop lent si on veut beaucoup d'animes)

    Champs extraits par anime :
    - mal_id : identifiant stable (extrait de l'URL)
    - rank : position dans le top
    - title, url
    - score
    - image_url (thumbnail)
    - type, episodes (optionnel, selon la page)

    Paramètres
    ----------
    html : str
        HTML d'une page Top Anime.

    Retour
    ------
    list[dict]
        Liste de dicts (un par anime)
    """
    soup = BeautifulSoup(html, "html.parser")
    animes = []

    # Chaque anime du top est dans un bloc <tr class="ranking-list"> ...
    rows = soup.select(".ranking-list")

    for row in rows:
        # --- Rank (position dans le top) ---
        # Exemple dans le HTML : <td class="rank ac">1</td>
        rank_tag = row.select_one("td.rank")
        rank = None
        if rank_tag:
            rank_txt = rank_tag.get_text(strip=True)
            try:
                rank = int(rank_txt)
            except ValueError:
                rank = None

        # --- Titre + URL (lien vers la page détail) ---
        # h3.anime_ranking_h3 contient un lien <a> vers /anime/<id>/<slug>
        title_tag = row.select_one("h3.anime_ranking_h3 a")
        if not title_tag:
            # Si MAL change son HTML, on ignore ce bloc
            continue

        title = title_tag.get_text(strip=True)
        url = title_tag.get("href")

        # --- mal_id (stable) ---
        # On extrait l'ID depuis l'URL, ex : /anime/5114/... -> 5114
        mal_id = extract_mal_id(url) if url else None

        # --- Score ---
        # Sur la page top, le score est souvent dans <span class="score-label">9.29</span>
        score_tag = row.select_one("span.score-label")
        score = None
        if score_tag:
            txt = score_tag.get_text(strip=True)
            if txt != "N/A":
                try:
                    score = float(txt)
                except ValueError:
                    score = None

        # --- Image (thumbnail) ---
        # MAL utilise parfois du lazy loading : src ou data-src
        img_tag = row.select_one("img")
        image_url = None
        if img_tag:
            image_url = img_tag.get("data-src") or img_tag.get("src")

        # --- Type + episodes (optionnel) ---
        # Dans div.information on trouve souvent : "TV (28 eps)" / "Movie (1 eps)" ...
        type_ = None
        episodes = None
        info_tag = row.select_one("div.information")
        if info_tag:
            info_text = info_tag.get_text(" ", strip=True)
            m = re.search(r"^(TV|Movie|OVA|ONA|Special|Music)\s*\((\d+)\s*eps\)", info_text)
            if m:
                type_ = m.group(1)
                episodes = m.group(2)

        # Document "liste légère" (parfait pour stocker dans anime_list)
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


def scrap_top_anime(limit_start: int = 0):
    """
    Scrape UNE page du Top Anime en utilisant le paramètre ?limit=...

    MAL pagine par blocs de 50 :
    - limit=0   -> top 1 à 50
    - limit=50  -> top 51 à 100
    - limit=100 -> top 101 à 150
    etc.

    Paramètres
    ----------
    limit_start : int
        Offset de pagination (0, 50, 100...)

    Retour
    ------
    list[dict]
        Liste d'animes (format "liste légère") parsée depuis la page top.
    """
    url = f"{TOP_ANIME_URL}?limit={limit_start}"
    html = fetch_html(url)
    return parse_top_anime_page(html)


def extract_mal_id(url: str) -> int | None:
    """
    Extrait l'identifiant MAL depuis une URL d'anime.

    Exemple
    -------
    https://myanimelist.net/anime/5114/Fullmetal_Alchemist__Brotherhood -> 5114

    Retourne None si l'URL ne correspond pas au pattern attendu.
    """
    m = re.search(r"/anime/(\d+)", url)
    return int(m.group(1)) if m else None


def scrap_anime_detail(url: str) -> dict:
    """
    Scrape la page "détail" d'un anime (myanimelist.net/anime/<id>/...).

    Objectif :
    - Récupérer les informations avancées (synopsis, studios, producers, genres, etc.)
    - Ces données seront stockées dans une collection séparée (anime_details),
      et récupérées "au clic" dans l'application (live scraping + cache Mongo).

    Paramètres
    ----------
    url : str
        URL de la page anime détail.

    Retour
    ------
    dict
        Document de détails (format riche).
    """
    # Identifiant stable (sera utilisé comme clé Mongo _id)
    mal_id = extract_mal_id(url)

    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    # --- TITLE ---
    title_tag = soup.select_one("h1.title-name strong")
    title = title_tag.get_text(strip=True) if title_tag else None

    # Titre anglais (quand MAL le fournit)
    title_english_tag = soup.select_one("p.title-english")
    title_english = title_english_tag.get_text(strip=True) if title_english_tag else None

    # --- SYNOPSIS ---
    synopsis_tag = soup.select_one("p[itemprop='description']")
    synopsis = synopsis_tag.get_text(" ", strip=True) if synopsis_tag else None

    # --- INFO SECTION (panneau gauche "Information") ---
    # On initialise des valeurs par défaut
    type_ = episodes = status = aired = premiered = broadcast = None
    producers = studios = genres = themes = demographic = []
    source = duration = rating = None

    # Sur MAL, chaque ligne (Type, Episodes, Studios...) est un div.spaceit_pad
    info_blocks = soup.select("div.spaceit_pad")
    for block in info_blocks:
        # On récupère une version texte pour détecter le label (Type:, Episodes:, ...)
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
            # Les valeurs sont des <a> dans le bloc
            producers = [a.get_text(strip=True) for a in block.select("a")]

        elif text.startswith("Studios:"):
            studios = [a.get_text(strip=True) for a in block.select("a")]

        elif text.startswith("Source:"):
            source = text.replace("Source:", "").strip()

        elif text.startswith("Genres:"):
            genres = [a.get_text(strip=True) for a in block.select("a")]

        # MAL peut afficher "Theme:" ou "Themes:" selon les fiches
        elif text.startswith("Theme:") or text.startswith("Themes:"):
            themes = [a.get_text(strip=True) for a in block.select("a")]

        elif text.startswith("Demographic:"):
            demographic = [a.get_text(strip=True) for a in block.select("a")]

        elif text.startswith("Duration:"):
            duration = text.replace("Duration:", "").strip()

        elif text.startswith("Rating:"):
            rating = text.replace("Rating:", "").strip()

    # --- STATS (score/rank/popularity/members) ---
    score = rank = popularity = members = None

    # Score affiché sur la page détail
    score_tag = soup.select_one("div.score-label")
    if score_tag:
        try:
            score = float(score_tag.get_text(strip=True))
        except ValueError:
            score = None

    # Bloc stats : contient Rank, Popularity, Members
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
        "mal_id": mal_id,
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


def scrap_full_top(max_anime: int = 50):
    """
    Scrape un top "complet" (détails inclus) jusqu'à max_anime.

    ⚠️ Attention :
    - Cette fonction est utile pour des tests / génération d'un dataset complet.
    - Mais dans notre architecture finale, on préfère :
      - stocker une liste légère (anime_list)
      - et faire le détail au clic (anime_details) avec cache

    Fonctionnement :
    - pagine automatiquement (limit=0,50,100,...)
    - affiche une barre de progression compacte
    - pour chaque anime : appelle scrap_anime_detail(url)

    Paramètres
    ----------
    max_anime : int
        Nombre d'animes max à scraper (détails inclus)

    Retour
    ------
    list[dict]
        Liste de documents "détails"
    """
    print(f"[INFO] Démarrage du scraping du top {max_anime} animes...")

    dataset = []
    bar_length = 30
    count = 0
    limit_start = 0

    while count < max_anime:
        # 1) Récupérer une page "liste légère"
        page_animes = scrap_top_anime(limit_start=limit_start)
        if not page_animes:
            break  # plus de pages

        # 2) Parcourir les animes de cette page
        for anime in page_animes:
            if count >= max_anime:
                break

            count += 1

            # Barre de progression (compacte, écrasée à chaque itération)
            progress = count / max_anime
            filled = int(progress * bar_length)
            bar = "#" * filled + "-" * (bar_length - filled)

            # Efface la ligne précédente puis ré-écrit la barre
            print("\r\033[K", end="")
            print(f"[INFO] [{bar}] {count}/{max_anime} - {anime['title'][:40]}", end="", flush=True)

            # 3) Scraper la page détail
            details = scrap_anime_detail(anime["url"])
            dataset.append(details)

        # 4) Page suivante
        limit_start += 50

    print("\r\033[K", end="")
    print(f"[INFO] [{bar}] {count}/{max_anime}")
    print(f"[INFO] Scraping terminé : {len(dataset)} animes récupérés.")

    return dataset


def get_mongo_client():
    """
    Crée un client MongoDB pointant vers le container Docker.

    Pourquoi cette fonction ?
    - centraliser l'URI Mongo
    - éviter de dupliquer la chaîne de connexion partout
    """
    uri = "mongodb://root:rootpass@localhost:27017/?authSource=admin"
    return MongoClient(uri)


def upsert_anime_list_to_mongo(anime_list: list[dict], db_name="animedb", collection_name="anime_list"):
    """
    Insère / met à jour une liste d'animes "légers" dans MongoDB.

    Principe :
    - On utilise _id = mal_id (identifiant stable) pour éviter les doublons.
    - L'opération est un upsert :
        - si l'anime existe déjà -> update
        - sinon -> insert

    Pourquoi bulk_write ?
    - plus performant que faire 300 update_one() séparés
    - utile quand on cliquera sur "Plus" et qu'on insert 50 items d'un coup

    Paramètres
    ----------
    anime_list : list[dict]
        Liste de dicts au format "liste légère" (mal_id, title, rank, score, etc.)
    db_name : str
        Nom de la base.
    collection_name : str
        Collection (par défaut anime_list)
    """
    client = get_mongo_client()
    col = client[db_name][collection_name]

    ops = []
    skipped = 0

    for a in anime_list:
        mal_id = a.get("mal_id")
        if mal_id is None:
            skipped += 1
            continue

        # On copie le doc et on convertit mal_id -> _id
        doc = dict(a)
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
        print(f"[WARN] Rien à insérer. skipped={skipped}")

    client.close()


def get_anime_details_cached(
    mal_id: int,
    url: str,
    db_name="animedb",
    details_col="anime_details",
    max_age_hours=24
):
    """
    Cache des détails:
    - si présent et scrapé il y a moins de max_age_hours -> retourne Mongo
    - sinon -> live scrape, stocke, retourne
    """
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
    """
    Récupère une "page" du Top Anime depuis MongoDB (données légères).

    Objectif côté app :
    - afficher la home (Top 50)
    - gérer un bouton "Plus" (skip += 50)

    Paramètres
    ----------
    skip : int
        Nombre de documents à ignorer (pagination). Ex: skip=50 -> page suivante.
    limit : int
        Nombre de documents à retourner.
    db_name : str
        Nom de la base Mongo.
    col_name : str
        Nom de la collection contenant les documents "liste légère" (anime_list).

    Retour
    ------
    list[dict]
        Liste de documents simplifiés (mal_id, title, score, image_url, etc.)
    """
    client = get_mongo_client()
    col = client[db_name][col_name]

    # Projection : on choisit explicitement les champs utiles à l'UI
    # -> évite de ramener des champs inutiles et accélère les requêtes.
    projection = {
        "_id": 1,        # _id = mal_id dans notre modèle
        "rank": 1,
        "title": 1,
        "score": 1,
        "image_url": 1,
        "type": 1,
        "episodes": 1,
        "url": 1,
    }

    # Tri par rank (ordre du top), puis pagination (skip/limit)
    docs = list(
        col.find({}, projection)
           .sort("rank", 1)
           .skip(skip)
           .limit(limit)
    )

    # Pour l'app, c'est plus pratique d'avoir "mal_id" plutôt que "_id"
    for d in docs:
        d["mal_id"] = d.pop("_id")

    client.close()
    return docs


def get_anime_list_count(db_name="animedb", col_name="anime_list"):
    """
    Retourne le nombre total d'animes présents dans la collection anime_list.

    Objectif côté app :
    - afficher un compteur ("300 animes en cache")
    - savoir si on doit encore proposer "Plus"
    """
    client = get_mongo_client()
    col = client[db_name][col_name]

    count = col.count_documents({})

    client.close()
    return count


def get_anime_list_by_ids(mal_ids: list[int], db_name="animedb", col_name="anime_list"):
    """
    Récupère plusieurs animes "liste légère" à partir d'une liste de mal_id.

    Objectif côté recommandation :
    - quand ElasticSearch renverra une liste d'IDs (mal_id),
      on viendra récupérer les infos UI depuis Mongo pour afficher les résultats.

    Paramètres
    ----------
    mal_ids : list[int]
        Liste d'identifiants MAL.

    Retour
    ------
    list[dict]
        Documents correspondants (dans le même format que get_top_from_mongo).
    """
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

    for d in docs:
        d["mal_id"] = d.pop("_id")

    client.close()
    return docs


def fetch_next_top_page_to_mongo(limit_start: int, db_name="animedb"):
    """
    Scrape une page "Top Anime" (50 items via ?limit=...),
    puis upsert dans Mongo (anime_list).

    Objectif côté app :
    - quand l'utilisateur clique sur "Plus", on appelle cette fonction
      avec limit_start=50, 100, 150, etc.
    - l'UI peut ensuite relire Mongo pour afficher la nouvelle page.

    Paramètres
    ----------
    limit_start : int
        Offset MAL (0, 50, 100, ...)

    Retour
    ------
    list[dict]
        La liste "légère" scrapée (au cas où l'app veut l'afficher immédiatement).
    """
    page = scrap_top_anime(limit_start=limit_start)

    # Upsert en base pour garder un cache local (et éviter de re-scraper)
    upsert_anime_list_to_mongo(page, db_name=db_name, collection_name="anime_list")

    return page


if __name__ == "__main__":
    top_300 = []

    for limit in range(0, 300, 50):
        print(f"[INFO] Récupération Top Anime (limit={limit})")
        page = scrap_top_anime(limit_start=limit)
        top_300.extend(page)

    print(f"[INFO] Nombre d'animes récupérés : {len(top_300)}")

    # aperçu
    for anime in top_300[:3]:
        print(anime)

    # Insert/Upsert Mongo (si tu as déjà ajouté les fonctions Mongo)
    upsert_anime_list_to_mongo(top_300)

    # --- TEST "clic": détails live + cache ---
    first = top_300[0]
    mal_id = first["mal_id"]
    url = first["url"]

    print(f"\n[INFO] TEST clic anime: {first['title']} (mal_id={mal_id})")
    details = get_anime_details_cached(mal_id, url)

    print("[INFO] Extrait détails :")
    print("  title:", details.get("title"))
    print("  studios:", details.get("studios"))
    print("  genres:", details.get("genres"))
    print("  fetched_at:", details.get("details_fetched_at"))
