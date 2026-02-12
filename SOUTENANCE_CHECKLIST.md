# Soutenance Checklist

Use this checklist during evaluation to prove each requirement clearly.

## A. Mandatory Requirements

- [ ] Project done as a team of 2 (state team members in oral intro).
- [ ] Data scraped from a website (`MyAnimeList`).
- [ ] Data stored in database(s) (`MongoDB`, plus `Elasticsearch` index).
- [ ] Python web app running (`Streamlit`).
- [ ] Data displayed with useful features (graphs, search, recommender, details page).
- [ ] All services run in Docker containers.
- [ ] Technical + functional documentation available (`README.md`).
- [ ] Public GitHub repository available and accessible.

## B. Bonus Requirements

- [ ] Real-time scraping at startup (auto-bootstrap enabled).
- [ ] `docker-compose` used for full stack orchestration.
- [ ] Search engine with Elasticsearch (with scoring/boosts).

## C. Live Proof Commands

Run in project root:

```bash
docker compose up -d --build
docker compose ps
```

Expected services:
- `myanimelist-app`
- `myanimelist-mongo`
- `myanimelist-elasticsearch`
- `myanimelist-mongo-express`

Verify endpoints:
- `http://localhost:8501` (app)
- `http://localhost:8081` (mongo-express)
- `http://localhost:9200` (elasticsearch info)

## D. Demo Flow (What To Show)

1. Open app and show startup auto-bootstrap status.
2. `Top` tab:
- load pages and navigate (`Load Top 50`, `Load Next 50/500`, `Previous 50`),
- open `Details` page from a card.
3. `Search` tab:
- run query,
- open details from a search result.
4. `Recommender` tab:
- select preferences,
- run recommendation,
- open details from a recommendation.
5. Show one graph section in Top.

## E. Technical Talking Points (Short)

- Cache strategy:
- `anime_list` for fast browsing,
- `anime_details` for rich metadata and freshness (`details_fetched_at`).

- Elasticsearch strategy:
- full text on titles/synopsis,
- boosted terms on genres/themes/studios,
- filtered types internally (`Music/PV/CM` excluded).

- Performance strategy:
- parallel details hydration,
- reduced request sleep,
- startup auto-bootstrap for evaluator convenience.

## F. Final Pre-Submission Checks

- [ ] `README.md` updated and readable.
- [ ] `SOUTENANCE_CHECKLIST.md` included.
- [ ] No local-only secrets in repo.
- [ ] App runs from clean clone with only `docker compose up -d --build`.
- [ ] Latest code pushed to public GitHub repo.

