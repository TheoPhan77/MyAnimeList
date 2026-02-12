# AniMatch - MyAnimeList Recommender

AniMatch is a Data Engineering web project built in Python (Streamlit) that:
- scrapes anime data from MyAnimeList,
- stores cache in MongoDB,
- indexes searchable fields in Elasticsearch,
- exposes a single-page app with Top, Search, Recommender, and Details.

This repository is designed for a graded project with Dockerized services and a live demo workflow.

## 1. Functional Scope

- `Top`: browse ranked anime with pagination (`+50`, `+500`, `previous`), open details page.
- `Search`: full-text search over titles/synopsis with relevance ranking and filters.
- `Recommender`: preference-based scoring using genres, themes, studios, optional keyword.
- `Anime Details`: dedicated page with synopsis, metadata, tags, and source link.

## 2. Technical Stack

- `Python 3.11`
- `Streamlit` (frontend/app)
- `MongoDB` (cache + source of truth)
- `Elasticsearch 8` (search + scoring)
- `BeautifulSoup + requests` (scraping)
- `Docker + docker-compose`

## 3. Architecture

```text
MyAnimeList pages
   -> scraper/scraper.py
   -> MongoDB (animedb.anime_list + animedb.anime_details)
   -> Elasticsearch (anime_index)
   -> Streamlit app (Top/Search/Recommender/Details)
```

Core files:
- `scraper/scraper.py`: scraping, Mongo operations, Elasticsearch indexing/querying.
- `app/app.py`: main Streamlit UI (single page with tabs + controls).
- `app/pages/Anime_Details.py`: details page for one anime.
- `docker-compose.yml`: full service orchestration.

## 4. Data Model (simplified)

Top cache (`anime_list`):
- `mal_id`, `rank`, `title`, `url`, `score`, `image_url`, `type`, `episodes`

Detail cache (`anime_details`):
- `mal_id`, titles, synopsis, score/scored_by, rank/popularity/members,
- `genres`, `themes`, `studios`, `source`, `status`, `aired`, `rating`, etc.
- `details_fetched_at` for cache freshness.

## 5. How To Run

From project root:

```bash
docker compose up -d --build
```

Open:
- App: `http://localhost:8501`
- Mongo Express: `http://localhost:8081`
- Elasticsearch: `http://localhost:9200`

Stop:

```bash
docker compose down
```

## 6. Auto-Bootstrap At Startup

At app startup, AniMatch can auto-prepare demo data:
- scrape top pages (if needed),
- hydrate details (if needed),
- index Elasticsearch (if needed).

Configured in `docker-compose.yml`:
- `AUTO_BOOTSTRAP=1`
- `AUTO_BOOTSTRAP_TOP=50`
- `AUTO_BOOTSTRAP_DETAILS=50`
- `AUTO_BOOTSTRAP_ES=1`

Speed controls:
- `HTTP_SLEEP_SECONDS` (scrape pacing),
- `HYDRATE_MAX_WORKERS` (parallel detail hydration workers).

## 7. Live Demo Script (2-4 minutes)

1. Open app (`localhost:8501`), wait bootstrap completion message.
2. `Top`: show pagination and open one anime details page.
3. `Search`: query text (example: `revenge dark fantasy`), open details from result card.
4. `Recommender`: select genres/themes/studios, run, open details from result card.
5. Optional: show Mongo Express and Elasticsearch endpoints to prove backend services.

## 8. Why These Choices

- MongoDB: flexible schema, ideal for scraped JSON and cache updates.
- Elasticsearch: relevance scoring, boosts, multi-field text search.
- Streamlit: fast iteration, clean demo-ready UI for a data project.
- Docker Compose: reproducible environment for evaluators.

## 9. Limits / Risks

- Scraping speed depends on remote website response and rate-limits.
- HTML structure changes on source website can require parser updates.
- First run is slower than warm-cache runs.
- Respect robots/ToS of target websites before large-scale scraping.

## 10. Troubleshooting

- If app is not reachable: `docker compose ps` and `docker compose logs app`.
- If search returns nothing: run `Quick Demo Prep` or `Index All Details -> ES`.
- If Mongo connection fails locally, ensure containers are running and ports are free.

