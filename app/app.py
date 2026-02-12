import os
import re
import sys
from datetime import datetime
from html import escape

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scraper import scraper as mal

st.set_page_config(page_title="AniMatch", layout="wide")

HIDDEN_EXCLUDED_TYPES = tuple(sorted(mal.DEFAULT_EXCLUDED_TYPES))

# Fallback catalogs so users can see a complete genre/theme list
# even before all detail pages are hydrated.
GENRE_CATALOG = [
    "Action",
    "Adventure",
    "Avant Garde",
    "Award Winning",
    "Boys Love",
    "Comedy",
    "Drama",
    "Fantasy",
    "Girls Love",
    "Gourmet",
    "Horror",
    "Mystery",
    "Romance",
    "Sci-Fi",
    "Slice of Life",
    "Sports",
    "Supernatural",
    "Suspense",
]

THEME_CATALOG = [
    "Adult Cast",
    "Anthropomorphic",
    "CGDCT",
    "Childcare",
    "Combat Sports",
    "Crossdressing",
    "Delinquents",
    "Detective",
    "Educational",
    "Gag Humor",
    "Gore",
    "Harem",
    "High Stakes Game",
    "Historical",
    "Idols (Female)",
    "Idols (Male)",
    "Isekai",
    "Iyashikei",
    "Love Polygon",
    "Magical Sex Shift",
    "Mahou Shoujo",
    "Martial Arts",
    "Mecha",
    "Medical",
    "Military",
    "Music",
    "Mythology",
    "Organized Crime",
    "Otaku Culture",
    "Parody",
    "Performing Arts",
    "Pets",
    "Psychological",
    "Racing",
    "Reincarnation",
    "Reverse Harem",
    "Romantic Subtext",
    "Samurai",
    "School",
    "Showbiz",
    "Space",
    "Strategy Game",
    "Super Power",
    "Survival",
    "Team Sports",
    "Time Travel",
    "Vampire",
    "Video Game",
    "Visual Arts",
    "Workplace",
]


def _env_bool(name, default=False):
    raw = os.getenv(name, "1" if default else "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _env_int(name, default, minimum=0):
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        value = default
    return max(minimum, value)


A_AUTO_BOOTSTRAP_ENABLED = _env_bool("AUTO_BOOTSTRAP", default=True)
A_AUTO_BOOTSTRAP_TOP = _env_int("AUTO_BOOTSTRAP_TOP", default=50, minimum=0)
A_AUTO_BOOTSTRAP_DETAILS = _env_int("AUTO_BOOTSTRAP_DETAILS", default=50, minimum=0)
A_AUTO_BOOTSTRAP_ES = _env_bool("AUTO_BOOTSTRAP_ES", default=True)


def hard_stop():
    st.stop()
    raise SystemExit


def improve_image_quality(url):
    if not url:
        return url
    return re.sub(r"/r/\d+x\d+/", "/", url)


def inject_global_styles():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=Space+Grotesk:wght@400;500;700&display=swap');

        :root {
            --am-bg-1: #071923;
            --am-bg-2: #0f2d3d;
            --am-bg-3: #143f53;
            --am-card: rgba(8, 25, 36, 0.84);
            --am-text: #e8f8ff;
            --am-muted: #99b8c9;
            --am-accent: #2ad6c2;
            --am-accent-2: #ffb84d;
            --am-border: rgba(131, 192, 214, 0.28);
        }

        .stApp {
            color: var(--am-text);
            background:
                radial-gradient(1200px 600px at 95% -10%, rgba(42, 214, 194, 0.16), transparent 62%),
                radial-gradient(1200px 680px at -10% 110%, rgba(255, 184, 77, 0.12), transparent 62%),
                linear-gradient(145deg, var(--am-bg-1), var(--am-bg-2) 45%, var(--am-bg-3));
        }

        html, body, [class*="css"] {
            font-family: 'Space Grotesk', sans-serif;
        }

        h1, h2, h3 {
            font-family: 'Sora', sans-serif;
            letter-spacing: 0.2px;
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(4, 18, 27, 0.96), rgba(9, 31, 45, 0.92));
            border-right: 1px solid var(--am-border);
        }

        [data-testid="stSidebar"] .stButton>button,
        [data-testid="stSidebar"] .stNumberInput,
        [data-testid="stSidebar"] [data-baseweb="select"] {
            animation: amRise 0.35s ease both;
        }

        .stButton>button {
            border-radius: 12px;
            border: 1px solid var(--am-border);
            background: linear-gradient(140deg, rgba(32, 81, 103, 0.8), rgba(17, 55, 74, 0.92));
            color: var(--am-text);
            font-weight: 600;
            transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
        }

        .stButton>button:hover {
            transform: translateY(-1px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.28);
            border-color: rgba(42, 214, 194, 0.85);
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 16px;
            border: 1px solid var(--am-border);
            background: linear-gradient(155deg, rgba(9, 32, 45, 0.9), rgba(7, 23, 34, 0.95));
            box-shadow: 0 14px 30px rgba(3, 13, 20, 0.35);
            animation: amRise 0.35s ease both;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color: rgba(42, 214, 194, 0.75);
        }

        [data-testid="stTabs"] button[role="tab"] {
            border-radius: 999px;
            border: 1px solid var(--am-border);
            padding: 8px 16px;
            margin-right: 8px;
            background: rgba(7, 26, 38, 0.7);
            color: var(--am-muted);
            font-weight: 600;
        }

        [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            color: #001219;
            border-color: rgba(42, 214, 194, 0.9);
            background: linear-gradient(120deg, var(--am-accent), #7df9df);
        }

        [data-testid="metric-container"] {
            border: 1px solid var(--am-border);
            border-radius: 16px;
            background: linear-gradient(150deg, rgba(10, 35, 48, 0.9), rgba(8, 24, 35, 0.94));
            padding: 10px 14px;
            box-shadow: 0 10px 20px rgba(3, 12, 19, 0.28);
        }

        .am-hero {
            border: 1px solid var(--am-border);
            border-radius: 20px;
            padding: 26px 28px;
            margin-bottom: 14px;
            background: linear-gradient(135deg, rgba(10, 34, 47, 0.9), rgba(9, 26, 38, 0.95));
            box-shadow: 0 18px 36px rgba(1, 9, 16, 0.36);
            animation: amFadeIn 0.45s ease both;
        }

        .am-hero-kicker {
            color: var(--am-accent-2);
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            font-size: 0.78rem;
            margin-bottom: 8px;
            font-family: 'Sora', sans-serif;
        }

        .am-hero-title {
            margin: 0;
            font-size: clamp(2rem, 3vw, 3.1rem);
            line-height: 1.05;
            font-family: 'Sora', sans-serif;
            letter-spacing: -0.01em;
            background: linear-gradient(120deg, #dffbff, #7ef2e5 40%, #ffd394);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }

        .am-hero-sub {
            margin: 10px 0 0;
            color: var(--am-muted);
            font-size: 1.03rem;
            max-width: 850px;
        }

        .am-meta {
            color: var(--am-muted);
            font-size: 0.92rem;
            margin-bottom: 6px;
        }

        .am-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 8px;
            align-items: center;
        }

        .am-chip {
            border-radius: 999px;
            border: 1px solid rgba(126, 242, 229, 0.45);
            padding: 2px 10px;
            background: rgba(18, 56, 74, 0.74);
            font-size: 0.8rem;
            color: #dffbff;
        }

        .am-chip-label {
            color: var(--am-accent-2);
            font-weight: 700;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-right: 4px;
        }

        .am-image-placeholder {
            border-radius: 12px;
            border: 1px dashed rgba(153, 184, 201, 0.45);
            padding: 24px 10px;
            text-align: center;
            color: var(--am-muted);
            font-size: 0.86rem;
        }

        @keyframes amFadeIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes amRise {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero():
    st.markdown(
        """
        <section class="am-hero">
            <div class="am-hero-kicker">Elastic Relevance Engine</div>
            <h1 class="am-hero-title">AniMatch</h1>
            <p class="am-hero-sub">
                Production-ready anime discovery with live scraping, Mongo cache, and
                Elasticsearch scoring for search and recommendations.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _chips_html(label, items, max_items=8):
    safe_items = [escape(str(item)) for item in (items or []) if str(item).strip()]
    if not safe_items:
        return ""
    chips = "".join([f"<span class='am-chip'>{item}</span>" for item in safe_items[:max_items]])
    return f"<div class='am-chip-row'><span class='am-chip-label'>{escape(label)}</span>{chips}</div>"


def enrich_results_with_top_metadata(rows, max_lookup=600):
    if not rows:
        return []
    resolved_ids = []
    for row in rows[:max_lookup]:
        mal_id = row.get("mal_id")
        if mal_id is None and row.get("url"):
            mal_id = mal.extract_mal_id(row.get("url"))
        if mal_id is None:
            continue
        resolved_ids.append(int(mal_id))

    basics = mal.get_anime_list_by_ids(sorted(set(resolved_ids))) if resolved_ids else []
    by_id = {row["mal_id"]: row for row in basics}

    enriched = []
    for row in rows:
        copy = dict(row)
        mal_id = copy.get("mal_id")
        if mal_id is None and copy.get("url"):
            mal_id = mal.extract_mal_id(copy.get("url"))
        if mal_id is not None:
            mal_id = int(mal_id)
            copy["mal_id"] = mal_id
            base = by_id.get(mal_id)
            if base:
                for key in ("image_url", "rank", "type", "episodes", "url"):
                    if copy.get(key) in (None, "", []):
                        copy[key] = base.get(key)
                if copy.get("score") is None:
                    copy["score"] = base.get("score")
        enriched.append(copy)
    return enriched


def open_details_from_row(row):
    mal_id = row.get("mal_id")
    if mal_id is None and row.get("url"):
        mal_id = mal.extract_mal_id(row.get("url"))
    if mal_id is None:
        st.warning("Cannot open details for this result (missing anime id).")
        return
    mal_id = int(mal_id)
    st.session_state.selected_mal_id = mal_id
    st.query_params.clear()
    st.query_params["mal_id"] = str(mal_id)
    st.switch_page("pages/Anime_Details.py")


def render_result_card(row, key_prefix, idx):
    with st.container(border=True):
        left, right = st.columns([1, 3])
        with left:
            image_url = improve_image_quality(row.get("image_url"))
            if image_url:
                st.image(image_url, use_container_width=True)
            else:
                st.markdown("<div class='am-image-placeholder'>No cover available</div>", unsafe_allow_html=True)
        with right:
            st.markdown(f"#### {row.get('title', 'Untitled')}")
            score_value = row.get("score")
            es_score = row.get("es_score")
            es_score_text = f"{float(es_score):.2f}" if isinstance(es_score, (int, float)) else str(es_score or "N/A")
            st.markdown(
                f"<div class='am-meta'>Rank #{row.get('rank', '?')} | "
                f"Type {row.get('type') or 'Unknown'} | "
                f"Score {score_value if score_value is not None else 'N/A'} | "
                f"ES {es_score_text}</div>",
                unsafe_allow_html=True,
            )
            genres_html = _chips_html("Genres", row.get("genres", []))
            if genres_html:
                st.markdown(genres_html, unsafe_allow_html=True)
            themes_html = _chips_html("Themes", row.get("themes", []))
            if themes_html:
                st.markdown(themes_html, unsafe_allow_html=True)
            studios_html = _chips_html("Studios", row.get("studios", []), max_items=4)
            if studios_html:
                st.markdown(studios_html, unsafe_allow_html=True)
            synopsis = row.get("synopsis")
            if synopsis:
                short = synopsis[:380] + ("..." if len(synopsis) > 380 else "")
                st.write(short)
            actions = st.columns([1, 1, 3])
            with actions[0]:
                if st.button("Details", key=f"{key_prefix}_details_{idx}_{row.get('mal_id', 'na')}"):
                    open_details_from_row(row)
            with actions[1]:
                if row.get("url"):
                    st.link_button("Go to site", row["url"], use_container_width=True)


if "limit" not in st.session_state:
    st.session_state.limit = 50
if "page_skip" not in st.session_state:
    st.session_state.page_skip = 0
if "es_sync_state" not in st.session_state:
    st.session_state.es_sync_state = None
if "selected_mal_id" not in st.session_state:
    st.session_state.selected_mal_id = None
if "top_notice" not in st.session_state:
    st.session_state.top_notice = ""
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "reco_results" not in st.session_state:
    st.session_state.reco_results = []


@st.cache_data(ttl=60)
def _get_total_cached():
    return mal.get_anime_list_count()


@st.cache_data(ttl=60)
def _get_total_details():
    return mal.get_mongo_details_count()


@st.cache_data(ttl=60)
def _get_page(skip: int, limit: int):
    return mal.get_top_from_mongo(skip=skip, limit=limit)


@st.cache_data(ttl=300)
def _get_recommender_options():
    genres = set(mal.get_mongo_details_distinct("genres"))
    themes = set(mal.get_mongo_details_distinct("themes"))
    studios = mal.get_mongo_details_distinct("studios")
    genres.update(GENRE_CATALOG)
    themes.update(THEME_CATALOG)
    return sorted(genres), sorted(themes), studios


def sync_es_if_needed(total_cached_count, total_details_count, force=False):
    target_state = (total_cached_count, total_details_count)
    if not force and st.session_state.es_sync_state == target_state:
        return 0, 0, False
    indexed_light = mal.index_mongo_list_to_es(limit=None)
    indexed_details = mal.index_mongo_details_to_es(limit=None)
    st.session_state.es_sync_state = target_state
    return indexed_light, indexed_details, True


def get_es_doc_count(index_name="anime_index"):
    try:
        es = mal.get_es_client()
        if not es.indices.exists(index=index_name):
            return 0
        return int(es.count(index=index_name).get("count", 0))
    except Exception:
        return 0


def auto_bootstrap(total_cached, total_details):
    if not A_AUTO_BOOTSTRAP_ENABLED:
        return total_cached, total_details, "Auto-bootstrap disabled."

    actions = []
    changed = False

    if total_cached < A_AUTO_BOOTSTRAP_TOP and A_AUTO_BOOTSTRAP_TOP > 0:
        fetched_total = 0
        with st.spinner("Auto-bootstrap: loading top pages..."):
            for offset in range(0, A_AUTO_BOOTSTRAP_TOP, 50):
                page = mal.fetch_next_top_page_to_mongo(limit_start=offset)
                if not page:
                    break
                fetched_total += len(page)
        st.cache_data.clear()
        total_cached = mal.get_anime_list_count()
        changed = True
        actions.append(f"top cache +{fetched_total}")

    wanted_details = min(total_cached, A_AUTO_BOOTSTRAP_DETAILS)
    if wanted_details > total_details and wanted_details > 0:
        with st.spinner("Auto-bootstrap: hydrating details..."):
            mal.hydrate_details_from_mongo_top(max_items=wanted_details, max_age_hours=24)
        st.cache_data.clear()
        total_details = mal.get_mongo_details_count()
        changed = True
        actions.append(f"details ready {total_details}")

    if A_AUTO_BOOTSTRAP_ES:
        es_count = get_es_doc_count()
        if changed or es_count == 0:
            with st.spinner("Auto-bootstrap: indexing Elasticsearch..."):
                indexed_light, indexed_details, _ = sync_es_if_needed(
                    total_cached,
                    total_details,
                    force=True,
                )
            actions.append(f"es list={indexed_light}, details={indexed_details}")

    if not actions:
        return total_cached, total_details, "Auto-bootstrap: cache already ready."
    return total_cached, total_details, "Auto-bootstrap: " + " | ".join(actions)


inject_global_styles()
render_hero()

try:
    total_cached = _get_total_cached()
    total_details = _get_total_details()
except Exception as exc:
    st.error("Mongo not reachable. Start docker-compose first.")
    st.code(str(exc))
    hard_stop()

if "auto_bootstrap_done" not in st.session_state:
    st.session_state.auto_bootstrap_done = False
if "auto_bootstrap_status" not in st.session_state:
    st.session_state.auto_bootstrap_status = ""

if not st.session_state.auto_bootstrap_done:
    total_cached, total_details, st.session_state.auto_bootstrap_status = auto_bootstrap(
        total_cached,
        total_details,
    )
    st.session_state.auto_bootstrap_done = True

if st.session_state.auto_bootstrap_status:
    st.caption(st.session_state.auto_bootstrap_status)

st.sidebar.header("Data Controls")

def _load_top_page_and_move(next_skip: int):
    rows = mal.fetch_next_top_page_to_mongo(limit_start=next_skip)
    if rows:
        st.session_state.page_skip = next_skip
        st.session_state.top_notice = ""
    else:
        st.session_state.top_notice = f"No anime found for offset {next_skip}. You may be at the end."
    st.cache_data.clear()
    st.rerun()


if st.sidebar.button("Load Top 50", use_container_width=True):
    st.session_state.limit = 50
    _load_top_page_and_move(0)

if st.sidebar.button("Quick Demo Prep", use_container_width=True):
    with st.spinner("Preparing demo data (top + details + Elasticsearch)..."):
        if total_cached < 50:
            mal.fetch_next_top_page_to_mongo(limit_start=0)
        st.cache_data.clear()
        refreshed_total_cached = mal.get_anime_list_count()
        quick_hydrate_count = min(max(refreshed_total_cached, 1), 50)
        mal.hydrate_details_from_mongo_top(max_items=quick_hydrate_count, max_age_hours=24)
        refreshed_total_details = mal.get_mongo_details_count()
        sync_es_if_needed(refreshed_total_cached, refreshed_total_details, force=True)
    st.cache_data.clear()
    st.sidebar.success("Quick demo prep complete.")
    st.rerun()

if st.sidebar.button("Load Next 50", use_container_width=True):
    next_skip = st.session_state.page_skip + 50
    _load_top_page_and_move(next_skip)

if st.sidebar.button("Load Next 500", use_container_width=True):
    next_skip = st.session_state.page_skip + 500
    _load_top_page_and_move(next_skip)

if st.sidebar.button("Previous 50", use_container_width=True):
    prev_skip = max(0, st.session_state.page_skip - 50)
    _load_top_page_and_move(prev_skip)

hydrate_max = max(total_cached, 1)
hydrate_default = min(max(total_cached, 1), 50)
hydrate_count = st.sidebar.number_input(
    "Details to hydrate",
    min_value=1,
    max_value=hydrate_max,
    value=hydrate_default,
    step=1,
)
st.sidebar.caption("For demo speed, keep this around 50-100.")
if st.sidebar.button("Hydrate Details", use_container_width=True):
    with st.spinner("Hydrating details cache from top list..."):
        hydrated = mal.hydrate_details_from_mongo_top(max_items=int(hydrate_count), max_age_hours=24)
    st.cache_data.clear()
    st.sidebar.success(f"Hydrated {len(hydrated)} anime details.")
    st.rerun()

if st.sidebar.button("Index All Details -> ES", use_container_width=True):
    with st.spinner("Indexing Mongo details into Elasticsearch..."):
        indexed_light, indexed_details, _ = sync_es_if_needed(total_cached, total_details, force=True)
    st.sidebar.success(
        f"Indexed in Elasticsearch: list={indexed_light}, details={indexed_details}."
    )

st.sidebar.markdown("---")
st.sidebar.write(f"Cached in Mongo (top list): {total_cached}")
st.sidebar.write(f"Cached in Mongo (details): {total_details}")

animes = []
try:
    animes = _get_page(skip=st.session_state.page_skip, limit=st.session_state.limit)
except Exception as exc:
    st.error("Failed to read top list from Mongo.")
    st.code(str(exc))
    hard_stop()

if not animes:
    st.info("No cached data yet. Click 'Load Top 50' in the sidebar.")
    hard_stop()

tab_top, tab_search, tab_reco = st.tabs(["Top", "Search", "Recommender"])

with tab_top:
    st.subheader("Top Anime")
    if st.session_state.top_notice:
        st.warning(st.session_state.top_notice)
    page_start = st.session_state.page_skip + 1
    page_end = st.session_state.page_skip + len(animes)
    st.caption(f"Showing rank positions {page_start} to {page_end}")
    cols = st.columns(5)
    for idx, anime in enumerate(animes):
        col = cols[idx % 5]
        with col:
            image_url = improve_image_quality(anime.get("image_url"))
            if image_url:
                st.image(image_url, use_container_width=True)
            st.write(f"**{anime.get('title', '')}**")
            st.write(f"Score: {anime.get('score', 'N/A')}")
            meta = [anime.get("type"), anime.get("episodes")]
            meta = [m for m in meta if m]
            if meta:
                st.caption(" | ".join(meta))
            if st.button("Details", key=f"details_{anime['mal_id']}"):
                open_details_from_row(anime)

    st.subheader("Quick Stats")
    df = pd.DataFrame(animes)
    if "score" in df.columns:
        fig = px.histogram(df, x="score", nbins=20, title="Score distribution (loaded top list)")
        st.plotly_chart(fig, use_container_width=True)
    if "type" in df.columns:
        type_counts = df["type"].value_counts().reset_index()
        type_counts.columns = ["type", "count"]
        fig2 = px.bar(type_counts, x="type", y="count", title="Type distribution (loaded top list)")
        st.plotly_chart(fig2, use_container_width=True)

with tab_search:
    st.subheader("Search")
    query = st.text_input("Query", placeholder="e.g. revenge dark fantasy sword", key="search_query")
    col1, col2 = st.columns(2)
    size = col1.slider("Results", min_value=5, max_value=50, value=20, step=5, key="search_size")
    min_score = col2.slider(
        "Minimum score",
        min_value=0.0,
        max_value=10.0,
        value=0.0,
        step=0.1,
        key="search_min_score",
    )

    if st.button("Run Search", type="primary", use_container_width=True):
        try:
            sync_es_if_needed(total_cached, total_details)
            results = mal.search_anime_in_es(
                query=query,
                size=size,
                min_score=min_score,
                excluded_types=HIDDEN_EXCLUDED_TYPES,
            )
        except Exception as exc:
            st.error("Elasticsearch search failed.")
            st.code(str(exc))
            hard_stop()
        st.session_state.search_results = enrich_results_with_top_metadata(results)

    search_results = st.session_state.search_results
    st.write(f"Results: {len(search_results)}")
    if not search_results:
        st.info("No result yet. Run a query to display results.")
    for idx, row in enumerate(search_results):
        render_result_card(row, "search", idx)

with tab_reco:
    st.subheader("Recommender")

    try:
        genres_options, themes_options, studios_options = _get_recommender_options()
    except Exception as exc:
        st.error("Cannot load recommender options from Mongo.")
        st.code(str(exc))
        hard_stop()

    if total_details < total_cached:
        st.info(
            "Option lists depend on hydrated details. "
            "Use 'Hydrate Details' in sidebar (set it to full cached top) for more genres/themes/studios."
        )

    query_text = st.text_input("Optional keyword", placeholder="e.g. vengeance school magic", key="reco_query")
    reco_min_score = st.slider(
        "Minimum score",
        min_value=0.0,
        max_value=10.0,
        value=0.0,
        step=0.1,
        key="reco_min_score",
    )
    st.caption("Recommender returns all matching anime (up to Elasticsearch max window: 10,000).")
    st.caption("Fast mode: no live scraping during recommendation.")

    preferred_genres = st.multiselect("Preferred genres", options=genres_options, default=[])
    preferred_themes = st.multiselect("Preferred themes", options=themes_options, default=[])
    preferred_studios = st.multiselect("Preferred studios", options=studios_options, default=[])
    manual_studios = st.text_input("Custom studios (comma-separated)", key="manual_studios")
    manual_studios_list = [s.strip() for s in manual_studios.split(",") if s.strip()]
    selected_studios = sorted(set(preferred_studios + manual_studios_list))

    if st.button("Recommend", type="primary", use_container_width=True):
        if not preferred_genres and not preferred_themes and not selected_studios and not query_text:
            st.warning("Select at least one preference or keyword.")
            hard_stop()

        try:
            sync_es_if_needed(total_cached, total_details)
            results = mal.recommend_anime_in_es(
                preferred_genres=preferred_genres,
                preferred_themes=preferred_themes,
                preferred_studios=selected_studios,
                query_text=query_text,
                size=0,
                min_score=reco_min_score,
                excluded_types=HIDDEN_EXCLUDED_TYPES,
            )
        except Exception as exc:
            st.error("Elasticsearch recommendation query failed.")
            st.code(str(exc))
            hard_stop()
        st.session_state.reco_results = enrich_results_with_top_metadata(results)

    reco_results = st.session_state.reco_results
    st.write(f"Results: {len(reco_results)}")
    if not reco_results:
        st.info("No recommendation yet. Pick preferences and click Recommend.")
    for idx, row in enumerate(reco_results):
        render_result_card(row, "reco", idx)

st.caption(f"Refreshed at: {datetime.now().isoformat(timespec='seconds')}")

