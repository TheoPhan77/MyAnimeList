# AniMatch - MyAnimeList Recommender

AniMatch est une application Data Engineering en Python (Streamlit) qui transforme des pages MyAnimeList en produit de recherche et recommandation anime.

Le projet couvre:
- scraping web (top list + fiches details),
- stockage/cache MongoDB,
- indexation et ranking Elasticsearch,
- interface web Streamlit (Top, Search, Recommendations, details en modal).

Ce README fait office de rapport technique et fonctionnel.

## 1) Objectif du projet

Le projet repond aux attendus du module:

1. scraper des donnees depuis un site reel,
2. stocker ces donnees en base,
3. construire une application web Python pour les exploiter,
4. dockeriser l'ensemble des services,
5. documenter l'architecture, l'execution et les choix techniques.

## 2) Fonctionnalites utilisateur (version actuelle)

### 2.1 Hero et navigation

- Landing hero pleine hauteur avec image de fond anime.
- Navigation `Top`, `Search`, `Recommendations` via chips dans la meme fenetre.
- Cartes statistiques stylisees:
  - `Cached top list`
  - `Cached details`
  - `Mode`

### 2.2 Data controls

- Panneau `Data controls` stylise (control center) avec etat cache et fenetre active.
- Actions principales:
  - `Load Top 50`
  - `Previous 50`
  - `Load Next 50`
  - `Load Next 500`
- Bloc `Advanced controls`:
  - `Hydrate Details`
  - `Index All Details -> ES`

### 2.3 Top

- Affichage du top depuis MongoDB.
- Cartes anime encadrees contenant:
  - image (ratio original conserve),
  - titre,
  - rank/score,
  - type/episodes,
  - bouton `Details`.
- Graphiques rapides:
  - distribution des scores,
  - distribution des types.

### 2.4 Search

- Recherche full-text Elasticsearch sur titre/synopsis.
- Controles utilisateur:
  - requete texte,
  - nombre de resultats,
  - score minimum.
- Resultats enrichis avec donnees Mongo (image, rank, type, URL).

### 2.5 Recommendations

- Recommandation par preferences:
  - genres,
  - themes,
  - studios,
  - mot-cle optionnel,
  - score minimum.
- Exclusion interne des types non souhaites (`Music`, `PV`, `CM` par defaut).

### 2.6 Anime details

- Les details s'ouvrent dans un dialog Streamlit (modal) directement depuis la carte.
- Strategie cache-first:
  - lecture Mongo si fraiche,
  - sinon re-scrape puis mise a jour cache.

## 3) Architecture technique

Flux global:

```text
MyAnimeList HTML -> scraper/scraper.py -> MongoDB (anime_list + anime_details)
                  -> Elasticsearch (anime_index)
                  -> Streamlit (app/app.py)
```

Composants:

- `scraper/scraper.py`
  - scraping top et details,
  - normalisation,
  - upsert Mongo,
  - hydration parallele,
  - indexation et requetes Elasticsearch.
- `app/app.py`
  - UI complete Streamlit (hero, top/search/recommendations, controls, details dialog).
- `app/Dockerfile`
  - image applicative Streamlit.
- `docker-compose.yml`
  - orchestration MongoDB, Elasticsearch, App, Mongo Express.

## 4) Modele de donnees

### 4.1 MongoDB `animedb.anime_list` (cache leger)

Champs principaux:
- `_id` (mal_id),
- `rank`,
- `title`,
- `url`,
- `score`,
- `image_url`,
- `type`,
- `episodes`.

### 4.2 MongoDB `animedb.anime_details` (cache riche)

Champs principaux:
- titres (`title`, `title_english`, `title_japanese`),
- `synopsis`,
- `score`, `scored_by`, `rank`, `popularity`, `members`,
- `genres`, `themes`, `studios`, `source`,
- metadonnees diffusion (`status`, `aired`, `broadcast`, `duration`, `rating`...),
- `details_fetched_at`.

### 4.3 Elasticsearch `anime_index`

Usage:
- recherche textuelle multi-champs,
- scoring de pertinence,
- recommandation ponderee (genres/themes/studios/query).

## 5) Execution du projet

Depuis `6Evaluation/MyAnimeList`:

```bash
docker compose up -d --build
```

Endpoints:
- App Streamlit: `http://localhost:8501`
- Mongo Express: `http://localhost:8081`
- Elasticsearch: `http://localhost:9200`

Arret:

```bash
docker compose down
```

Statut services:

```bash
docker compose ps
```

Services attendus:
- `myanimelist-app`
- `myanimelist-mongo`
- `myanimelist-elasticsearch`
- `myanimelist-mongo-express`

## 6) Configuration (variables utiles)

Variables gerees cote `docker-compose.yml`:
- `MONGO_URI`
- `ES_URL`
- `AUTO_BOOTSTRAP`
- `AUTO_BOOTSTRAP_TOP`
- `AUTO_BOOTSTRAP_DETAILS`
- `AUTO_BOOTSTRAP_ES`
- `HTTP_SLEEP_SECONDS`
- `HYDRATE_MAX_WORKERS`

## 7) Auto-bootstrap (mode demo)

Au premier chargement, l'app peut automatiquement:

1. charger des pages top en cache Mongo,
2. hydrater les details,
3. synchroniser Elasticsearch.

Objectif: rendre la demo immediatement utilisable sans preparation manuelle.

## 8) Comportements importants observes

### 8.1 Pourquoi les compteurs ne sont pas toujours "ronds"

Exemple constate:
- `Cached top list = 301`
- `Cached details = 51`

Ce comportement est normal:
- le compteur `top list` compte les documents en cache, pas un "rank max strict",
- le classement MAL peut contenir des ex-aequo/changements dynamiques pendant le scraping pagine,
- le cache details peut contenir des entrees supplementaires deja ouvertes en `Details` lors d'une session precedente (volume Mongo persistant).

### 8.2 Persistance Docker

Les volumes `mongo_data` et `es_data` conservent les donnees entre redemarrages.

## 9) Demo soutenance (2 a 4 minutes)

1. Ouvrir `localhost:8501`.
2. Montrer hero + stats + `Data controls`.
3. Dans `Top`, ouvrir une fiche via `Details`.
4. Dans `Search`, lancer une requete texte.
5. Dans `Recommendations`, selectionner des preferences et executer.
6. Montrer rapidement `localhost:8081` (Mongo Express) et `localhost:9200` (ES).

## 10) Choix techniques

- **MongoDB**: stockage souple et incremental des donnees scrappees.
- **Elasticsearch**: recherche full-text + scoring/boost avance.
- **Streamlit**: rapidite de developpement et demonstration immediate.
- **Docker Compose**: setup reproductible sur poste evaluateur.

## 11) Limites et risques

- dependance a la stabilite HTML de MyAnimeList,
- latence reseau externe (scraping),
- premier run plus long qu'un run avec cache chaud,
- resultats variables si le top MAL evolue pendant le scraping.

## 12) Depannage

Si l'app ne repond pas:

```bash
docker compose ps
docker compose logs app
```

Si Search/Recommendations renvoie peu de resultats:

1. hydrater davantage de details via `Advanced controls`,
2. executer `Index All Details -> ES`.

Si Mongo est inaccessible:

1. verifier que le service `mongo` est `Up`,
2. verifier les ports locaux occupes,
3. verifier la variable `MONGO_URI`.

## 13) Checklist de rendu

### Obligatoire

- [ ] Donnees scrappees depuis MyAnimeList.
- [ ] Donnees stockees en base (Mongo + ES).
- [ ] Application Python fonctionnelle (Streamlit).
- [ ] Dockerisation complete fonctionnelle.
- [ ] README a jour (ce document).
- [ ] Repository GitHub public accessible.

### Bonus

- [ ] Auto-bootstrap.
- [ ] Orchestration complete docker-compose.
- [ ] Recherche/recommandation Elasticsearch.

### Verification finale

- [ ] `docker compose up -d --build` fonctionne sur clone propre.
- [ ] Aucun secret local dans le repo.
- [ ] Dernier code pousse.
