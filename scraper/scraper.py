import time
import requests
from bs4 import BeautifulSoup
import re
import json
from pathlib import Path
from datetime import datetime


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
    mal_id = extract_mal_id(url)
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
    Scrape autant d'animes que demandé dans le Top MyAnimeList,
    en parcourant les pages Next 50 automatiquement.
    Affichage : messages INFO + barre de progression compacte.
    """

    print(f"[INFO] Démarrage du scraping du top {max_anime} animes...")

    dataset = []
    bar_length = 30
    count = 0
    limit_start = 0   # commence à la page 1 (top 50)

    while count < max_anime:
        # Récupère une page
        page_animes = scrap_top_anime(limit_start=limit_start)
        if not page_animes:
            break  # plus de pages

        for anime in page_animes:
            if count >= max_anime:
                break

            count += 1

            # Barre de progression
            progress = count / max_anime
            filled = int(progress * bar_length)
            bar = "#" * filled + "-" * (bar_length - filled)

            # Nettoyer la ligne précédente + afficher la nouvelle
            print("\r\033[K", end="")
            print(
                f"[INFO] [{bar}] {count}/{max_anime} - {anime['title'][:40]}",
                end="",
                flush=True
            )

            # Scraping des détails
            details = scrap_anime_detail(anime["url"])
            dataset.append(details)

        # page suivante (Next 50)
        limit_start += 50

    # Fin du scraping
    print("\r\033[K", end="")
    print(f"[INFO] [{bar}] {count}/{max_anime}")
    print(f"[INFO] Scraping terminé : {len(dataset)} animes récupérés.")

    return dataset


def save_dataset_json(dataset: list[dict], filename: str):
    """
    Sauvegarde le dataset JSON dans le dossier /data
    à la racine du projet (indépendamment du dossier de lancement).
    """
    # Chemin absolu vers le fichier scraper.py
    script_dir = Path(__file__).resolve().parent

    # Racine du projet = dossier parent de /scraper
    project_root = script_dir.parent

    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)

    output_path = data_dir / filename

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"[INFO] Dataset JSON sauvegardé : {output_path} ({len(dataset)} animes)")


if __name__ == "__main__":
    MAX = 10  # nombre d'animes total à scraper

    dataset = scrap_full_top(MAX)

    # Sauvegarde JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_dataset_json(dataset, f"anime_dataset_top_{MAX}_{timestamp}.json")

    # Petit aperçu
    for j, anime in enumerate(dataset[:3], start=1):
        print(f"\n{j:02d}. {anime['title']}")
        print(f"   Genres : {anime['genres']}")
        print(f"   Score  : {anime['score']}")

