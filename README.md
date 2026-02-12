# AniMatch — MyAnimeList Recommender

AniMatch est une application Data Engineering en Python (Streamlit) qui transforme des pages MyAnimeList en un produit complet de découverte d'anime:

- scraping web (liste Top + pages détails),
- cache MongoDB,
- indexation et scoring Elasticsearch,
- interface web avec navigation Top, Search, Recommender et page Anime Details.

Ce README regroupe volontairement **la documentation technique, fonctionnelle et la checklist de soutenance** dans un seul fichier.

## 1) Objectif du projet

Le projet répond aux exigences du module:

1. scraper des données depuis un site web réel,
2. stocker ces données en base(s),
3. construire une application web Python pour les exploiter,
4. dockeriser tous les services,
5. documenter clairement l'architecture, le lancement, les choix techniques,
6. viser les bonus (auto-bootstrap, docker-compose, Elasticsearch).

## 2) Fonctionnalités utilisateur

### Top

L'onglet `Top` affiche les animes classés depuis le cache Mongo, avec pagination contrôlée:

- `Load Top 50`,
- `Load Next 50`,
- `Load Next 500`,
- `Previous 50`.

Chaque carte anime affiche image, titre, score, métadonnées et bouton `Details`.

### Search

L'onglet `Search` utilise Elasticsearch pour une recherche full-text sur les champs texte (titre/synopsis). L'utilisateur contrôle:

- la requête,
- le nombre de résultats,
- un score minimum.

Les résultats sont enrichis avec les données Mongo (image, type, URL) et sont cliquables vers la page détails.

### Recommender

L'onglet `Recommender` applique une logique de scoring basée sur les préférences:

- genres,
- thèmes,
- studios,
- mot-clé optionnel,
- score minimum.

Le filtrage interne exclut `Music`, `PV`, `CM` sans exposer ce réglage à l'utilisateur.

### Anime Details

La page `Anime_Details` affiche une fiche complète d'un anime:

- titres,
- image,
- score/épisodes/source/rating,
- genres/thèmes/studios,
- synopsis,
- métadonnées de diffusion et popularité,
- lien vers MyAnimeList.

Elle utilise un cache-first: si la fiche existe et est fraîche en base, elle est réutilisée; sinon elle est re-scrapée puis mise en cache.

## 3) Architecture technique

Flux global:

```text
MyAnimeList HTML -> scraper/scraper.py -> MongoDB (anime_list + anime_details)
                  -> Elasticsearch (anime_index)
                  -> Streamlit UI (Top/Search/Recommender/Details)
```

Composants principaux:

- `scraper/scraper.py`: scraping, parsing, upsert Mongo, hydration détails, indexation/query Elasticsearch.
- `app/app.py`: page principale Streamlit (tabs Top/Search/Recommender + contrôles de données).
- `app/pages/Anime_Details.py`: page dédiée à un anime.
- `docker-compose.yml`: orchestration complète des services.

## 4) Modèle de données

### Collection Mongo `animedb.anime_list` (cache léger)

Champs principaux:

- `mal_id`, `rank`, `title`, `url`, `score`, `image_url`, `type`, `episodes`.

### Collection Mongo `animedb.anime_details` (cache riche)

Champs principaux:

- identifiants et titres,
- `synopsis`,
- `score`, `scored_by`, `rank`, `popularity`, `members`,
- `genres`, `themes`, `studios`, `source`,
- infos de diffusion (`status`, `aired`, `duration`, `rating`, etc.),
- `details_fetched_at` pour la fraîcheur du cache.

### Index Elasticsearch `anime_index`

Utilisé pour:

- recherche textuelle multi-champs,
- scoring de pertinence,
- recommandations par préférences.

## 5) Lancement du projet (procédure complète)

Depuis la racine du repo:

```bash
docker compose up -d --build
```

Endpoints:

- App Streamlit: `http://localhost:8501`
- Mongo Express: `http://localhost:8081`
- Elasticsearch: `http://localhost:9200`

Arrêt:

```bash
docker compose down
```

Vérification des containers:

```bash
docker compose ps
```

Services attendus:

- `myanimelist-app`
- `myanimelist-mongo`
- `myanimelist-elasticsearch`
- `myanimelist-mongo-express`

## 6) Auto-bootstrap (mode démo rapide)

Au démarrage, l'app peut se préparer automatiquement:

1. charger le top si nécessaire,
2. hydrater les fiches détails,
3. indexer Elasticsearch.

Variables utiles dans `docker-compose.yml`:

- `AUTO_BOOTSTRAP`
- `AUTO_BOOTSTRAP_TOP`
- `AUTO_BOOTSTRAP_DETAILS`
- `AUTO_BOOTSTRAP_ES`
- `HTTP_SLEEP_SECONDS`
- `HYDRATE_MAX_WORKERS`

## 7) Guide de démonstration (2 à 4 min)

1. Ouvrir `localhost:8501` et montrer le statut de bootstrap.
2. Dans `Top`, charger/naviguer et ouvrir un anime via `Details`.
3. Dans `Search`, lancer une requête texte et ouvrir un résultat.
4. Dans `Recommender`, sélectionner préférences et lancer la recommandation.
5. Montrer rapidement `localhost:8081` (Mongo Express) et `localhost:9200` (ES).

## 8) Choix techniques

- **MongoDB**: schéma souple pour données scrapées et mise à jour incrémentale.
- **Elasticsearch**: scoring/boost et recherche full-text performante.
- **Streamlit**: développement rapide, rendu lisible pour soutenance.
- **Docker Compose**: exécution reproductible sur machine évaluateur.

## 9) Performance et robustesse

Le projet réduit le temps de démo grâce à:

- cache Mongo (évite re-scrape systématique),
- hydration parallèle des détails,
- synchronisation ES conditionnelle,
- auto-bootstrap au démarrage.

Limites connues:

- dépendance à la latence réseau et au site source,
- fragilité possible si MyAnimeList change son HTML,
- premier run plus lent qu'un run avec cache chaud.

## 10) Dépannage

Si l'app ne répond pas:

```bash
docker compose ps
docker compose logs app
```

Si Search/Recommender renvoie peu de résultats:

- lancer `Quick Demo Prep`,
- puis `Index All Details -> ES`.

Si Mongo est inaccessible:

- vérifier que `mongo` est `Up`,
- vérifier les ports déjà utilisés localement.

## 11) Checklist de soutenance (intégrée)

### Exigences obligatoires

- [ ] Travail en binôme présenté clairement.
- [ ] Données scrapées depuis MyAnimeList.
- [ ] Données stockées en base (Mongo + index Elasticsearch).
- [ ] Application web Python fonctionnelle (Streamlit).
- [ ] Affichage pertinent des données (cartes, détails, graphes, recherche/reco).
- [ ] Services exécutés dans des containers Docker.
- [ ] Documentation technique + fonctionnelle disponible (ce README).
- [ ] Repository GitHub public accessible.

### Bonus

- [ ] Auto-bootstrap de données au lancement.
- [ ] Orchestration complète via docker-compose.
- [ ] Moteur de recherche/recommandation avec Elasticsearch.

### Vérification finale avant rendu

- [ ] `docker compose up -d --build` fonctionne sur clone propre.
- [ ] Aucun secret local dans le repo.
- [ ] README à jour avec procédures, architecture, fonctionnalités.
- [ ] Dernier code poussé sur GitHub public.
