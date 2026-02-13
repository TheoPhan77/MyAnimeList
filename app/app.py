import os
import re
import sys
from datetime import datetime
from html import escape

import pandas as pd
import plotly.express as px
import streamlit as st
import base64
import textwrap

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
def _asset_b64(*parts) -> str:
    path = os.path.join(ROOT, *parts)
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scraper import scraper as mal

st.set_page_config(page_title="AniMatch", layout="wide")

HIDDEN_EXCLUDED_TYPES = tuple(sorted(mal.DEFAULT_EXCLUDED_TYPES))

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


def sync_view_from_query_params():
    if "active_view" not in st.session_state:
        st.session_state.active_view = "Top"

    view = st.query_params.get("view")
    if isinstance(view, list):
        view = view[0]
    if not view:
        return

    view = str(view).lower().strip()
    mapping = {"top": "Top", "search": "Search", "reco": "Recommendations"}
    if view in mapping:
        st.session_state.active_view = mapping[view]


def _hero_bg_base64() -> str:
    return _asset_b64("background", "anime_background.jpg")


def inject_global_styles():
    bg64 = _hero_bg_base64()
    hero_bg_image = f'url("data:image/jpeg;base64,{bg64}")' if bg64 else "none"

    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=Space+Grotesk:wght@400;500;700&display=swap');

    :root {{
        --am-bg-1: #071923;
        --am-bg-2: #0f2d3d;
        --am-bg-3: #143f53;
        --am-card: rgba(8, 25, 36, 0.78);
        --am-text: #e8f8ff;
        --am-muted: #99b8c9;
        --am-accent: #2ad6c2;
        --am-accent-2: #ffb84d;
        --am-border: rgba(131, 192, 214, 0.28);
    }}

    html, body {{
        height: 100%;
        margin: 0;
        overflow-x: hidden;
        font-family: 'Space Grotesk', sans-serif;
        color: var(--am-text);

        background-image:
            radial-gradient(1200px 600px at 95% -10%, rgba(42, 214, 194, 0.16), transparent 62%),
            radial-gradient(1200px 680px at -10% 110%, rgba(255, 184, 77, 0.12), transparent 62%),
            linear-gradient(145deg, rgba(7, 25, 35, 1), rgba(15, 45, 61, 1) 45%, rgba(20, 63, 83, 1));
        background-repeat: no-repeat, no-repeat, no-repeat;
        background-position: 95% -10%, -10% 110%, center;
        background-size: auto, auto, cover;
        background-attachment: scroll;
    }}

    .stApp {{
        background: transparent !important;
        color: var(--am-text);
    }}

    h1, h2, h3 {{
        font-family: 'Sora', sans-serif;
        letter-spacing: 0.2px;
    }}

    header[data-testid="stHeader"] {{ display: none; }}
    div[data-testid="stToolbar"] {{ display: none; }}
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}

    div.block-container {{
        padding-top: 0rem;
        padding-bottom: 1rem;
    }}
    div[data-testid="stMainBlockContainer"] {{
        padding-top: 0 !important;
    }}

    section[data-testid="stSidebar"],
    div[data-testid="collapsedControl"] {{
        display: none !important;
    }}

    .stButton>button {{
        border-radius: 12px;
        border: 1px solid var(--am-border);
        background: linear-gradient(140deg, rgba(32, 81, 103, 0.8), rgba(17, 55, 74, 0.92));
        color: var(--am-text);
        font-weight: 700;
        transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
    }}
    .stButton>button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.28);
        border-color: rgba(42, 214, 194, 0.85);
    }}

    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 16px;
        border: 1px solid var(--am-border);
        background: linear-gradient(155deg, rgba(9, 32, 45, 0.76), rgba(7, 23, 34, 0.84));
        box-shadow: 0 14px 30px rgba(3, 13, 20, 0.35);
        animation: amRise 0.35s ease both;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {{
        border-color: rgba(42, 214, 194, 0.75);
    }}

    [data-testid="metric-container"] {{
        border: 1px solid var(--am-border);
        border-radius: 16px;
        background: linear-gradient(150deg, rgba(10, 35, 48, 0.76), rgba(8, 24, 35, 0.84));
        padding: 10px 14px;
        box-shadow: 0 10px 20px rgba(3, 12, 19, 0.28);
    }}
    [data-testid="metric-container"] [data-testid="stMetricValue"] {{
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
        max-width: none !important;
        line-height: 1.15 !important;
    }}

    .am-meta {{
        color: rgba(232, 248, 255, 0.78);
        font-size: 0.92rem;
        margin-bottom: 6px;
    }}

    .am-hero {{
        position: relative;
        min-height: 100vh;

        width: 100vw;
        margin-left: calc(50% - 50vw);
        margin-right: calc(50% - 50vw);
        margin-top: 0;

        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;

        padding: 84px 24px 52px;

        background-image:
            radial-gradient(1000px 520px at 90% -5%, rgba(42, 214, 194, 0.16), transparent 60%),
            radial-gradient(1000px 580px at -8% 108%, rgba(255, 184, 77, 0.12), transparent 60%),
            {hero_bg_image};
        background-repeat: no-repeat, no-repeat, no-repeat;
        background-position: 90% -5%, -8% 108%, center;
        background-size: auto, auto, cover;
    }}

    .am-hero::before {{
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(180deg, rgba(4,16,24,0.40), rgba(4,16,24,0.78));
    }}

    .am-hero-inner {{
        position: relative;
        z-index: 1;
        max-width: 980px;
        margin: 0 auto;
        display: flex;
        flex-direction: column;
        gap: 12px;
        align-items: center;
    }}

    .am-hero-kicker {{
        color: var(--am-accent-2);
        font-weight: 800;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        font-size: 0.78rem;
        font-family: 'Sora', sans-serif;
    }}

    .am-hero-title {{
        margin: 0;
        font-size: clamp(2.3rem, 3.8vw, 3.4rem);
        line-height: 1.02;
        font-family: 'Sora', sans-serif;
        letter-spacing: -0.01em;
        background: linear-gradient(120deg, #dffbff, #7ef2e5 40%, #ffd394);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
    }}

    .am-hero-sub {{
        margin: 0;
        color: rgba(232, 248, 255, 0.88);
        font-size: 1.08rem;
        max-width: 860px;
    }}

    .am-mode-row {{
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        justify-content: center;
        margin-top: 12px;
        padding: 14px 16px;
        border: 1px solid rgba(131, 192, 214, 0.22);
        border-radius: 16px;
        background: rgba(8, 25, 36, 0.60);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
    }}

    .am-mode-chip {{
        display: inline-block;
        padding: 8px 14px;
        border-radius: 999px;
        border: 1px solid rgba(131, 192, 214, 0.28);
        background: rgba(18, 56, 74, 0.48);
        color: rgba(232, 248, 255, 0.92);
        text-decoration: none !important;
        font-weight: 800;
        transition: transform 0.15s ease, border-color 0.15s ease, background 0.15s ease;
    }}

    button.am-mode-chip {{
        appearance: none;
        -webkit-appearance: none;
        cursor: pointer;
        font-family: 'Sora', sans-serif;
        font-size: 0.95rem;
    }}

    .am-mode-chip:hover {{
        transform: translateY(-1px);
        border-color: rgba(42, 214, 194, 0.85);
        background: rgba(18, 56, 74, 0.62);
    }}

    .am-mode-chip.active {{
        border-color: rgba(42, 214, 194, 0.95);
        background: rgba(42, 214, 194, 0.12);
    }}

    .am-scroll-cue {{
        margin-top: 22px;
        opacity: 0.75;
        font-size: 1.2rem;
        animation: amBounce 1.4s ease-in-out infinite;
    }}

    .am-stats-grid {{
        position: relative;
        z-index: 2;
        width: min(1200px, 96vw);
        margin: -34px auto 22px;
        padding: 0 12px;
        display: grid;
        grid-template-columns: repeat(3, minmax(200px, 1fr));
        gap: 12px;
    }}

    .am-stat-card {{
        border: 1px solid rgba(131, 192, 214, 0.30);
        border-radius: 18px;
        background: linear-gradient(145deg, rgba(8, 30, 44, 0.92), rgba(12, 43, 60, 0.94));
        box-shadow: 0 12px 26px rgba(3, 13, 20, 0.36);
        padding: 14px 16px 15px;
        overflow: hidden;
    }}

    .am-stat-label {{
        font-family: 'Sora', sans-serif;
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        color: rgba(200, 230, 244, 0.72);
    }}

    .am-stat-value {{
        margin-top: 4px;
        line-height: 1.05;
        font-size: clamp(1.7rem, 2.9vw, 2.35rem);
        font-weight: 800;
        font-family: 'Sora', sans-serif;
        background: linear-gradient(120deg, #e8fbff, #8df9ec 46%, #ffd79e);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
    }}

    .am-stat-note {{
        margin-top: 6px;
        font-size: 0.82rem;
        color: rgba(188, 221, 236, 0.84);
    }}

    @media (max-width: 980px) {{
        .am-stats-grid {{
            grid-template-columns: repeat(2, minmax(180px, 1fr));
        }}
    }}

    @media (max-width: 680px) {{
        .am-stats-grid {{
            margin-top: -24px;
            grid-template-columns: 1fr;
        }}
    }}

    .am-controls-head {{
        margin-bottom: 10px;
    }}

    .am-controls-kicker {{
        font-family: 'Sora', sans-serif;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-size: 0.72rem;
        color: rgba(255, 184, 77, 0.92);
        margin-bottom: 2px;
    }}

    .am-controls-title {{
        margin: 0;
        font-family: 'Sora', sans-serif;
        font-size: clamp(1.3rem, 2.2vw, 1.7rem);
        color: #eaf9ff;
    }}

    .am-controls-sub {{
        margin: 6px 0 10px;
        color: rgba(197, 225, 238, 0.88);
        font-size: 0.92rem;
    }}

    .am-controls-pill-row {{
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
    }}

    .am-controls-pill {{
        border: 1px solid rgba(131, 192, 214, 0.34);
        background: rgba(11, 40, 56, 0.72);
        color: rgba(220, 242, 252, 0.94);
        border-radius: 999px;
        padding: 6px 11px;
        font-size: 0.8rem;
        line-height: 1;
    }}

    .am-controls-footnote {{
        margin-top: 8px;
        color: rgba(184, 216, 230, 0.86);
        font-size: 0.83rem;
    }}

    div[data-testid="stExpander"] {{
        border: 1px solid rgba(131, 192, 214, 0.28) !important;
        border-radius: 14px !important;
        background: linear-gradient(155deg, rgba(10, 35, 49, 0.74), rgba(8, 24, 35, 0.82));
    }}

    div[data-testid="stExpander"] summary p {{
        font-family: 'Sora', sans-serif;
        font-weight: 700;
        letter-spacing: 0.02em;
    }}

    div[data-testid="stNumberInput"] input {{
        border-radius: 10px !important;
        border: 1px solid rgba(131, 192, 214, 0.32) !important;
        background: rgba(9, 32, 44, 0.8) !important;
        color: var(--am-text) !important;
    }}

    @keyframes amBounce {{
        0%, 100% {{ transform: translateY(0); }}
        50% {{ transform: translateY(6px); }}
    }}

    @keyframes amRise {{
        from {{ opacity: 0; transform: translateY(6px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    </style>
    """

    st.markdown(textwrap.dedent(css), unsafe_allow_html=True)


def render_hero(total_cached: int, total_details: int, tagline: str):
    active = st.session_state.get("active_view", "Top")

    def chip(label: str, param: str, is_active: bool):
        cls = "am-mode-chip active" if is_active else "am-mode-chip"
        return f'<button class="{cls}" type="submit" name="view" value="{param}">{label}</button>'

    chips_html = "".join([
        chip("Top", "top", active == "Top"),
        chip("Search", "search", active == "Search"),
        chip("Recommendations", "reco", active == "Recommendations"),
    ])

    safe_tagline = escape(tagline).replace("\n", "<br>")

    hero_html = (
        '<section class="am-hero">'
        '<div class="am-hero-inner">'
        '<div class="am-hero-kicker">Elastic Relevance Engine</div>'
        '<h1 class="am-hero-title">AniMatch</h1>'
        f'<p class="am-hero-sub">{safe_tagline}</p>'
        f'<form class="am-mode-row" method="get">{chips_html}</form>'
        '<div class="am-scroll-cue"><span>↓</span></div>'
        "</div>"
        "</section>"
    )

    st.markdown(hero_html, unsafe_allow_html=True)

    stats_html = f"""
    <section class="am-stats-grid">
      <article class="am-stat-card">
        <div class="am-stat-label">Cached top list</div>
        <div class="am-stat-value">{total_cached:,}</div>
        <div class="am-stat-note">Anime index entries</div>
      </article>
      <article class="am-stat-card">
        <div class="am-stat-label">Cached details</div>
        <div class="am-stat-value">{total_details:,}</div>
        <div class="am-stat-note">Hydrated detail pages</div>
      </article>
      <article class="am-stat-card">
        <div class="am-stat-label">Mode</div>
        <div class="am-stat-value">Live + Cache</div>
        <div class="am-stat-note">MongoDB + Elasticsearch</div>
      </article>
    </section>
    """
    st.markdown(textwrap.dedent(stats_html), unsafe_allow_html=True)


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


def _get_row_mal_id(row):
    mal_id = row.get("mal_id")
    if mal_id is None and row.get("url"):
        mal_id = mal.extract_mal_id(row.get("url"))
    return int(mal_id) if mal_id is not None else None

_DIALOG = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)

def _render_anime_details(mal_id: int):
    basic_rows = mal.get_anime_list_by_ids([mal_id])
    if not basic_rows:
        st.error("Anime not found in local cache. Load it first from Top.")
        return

    basic = basic_rows[0]

    with st.spinner("Loading details..."):
        details = mal.get_anime_details_cached(mal_id=mal_id, url=basic["url"])

    title = details.get("title") or basic.get("title") or "Untitled"
    subtitle = details.get("title_english") or details.get("title_japanese")

    st.markdown(f"## {title}")
    if subtitle:
        st.caption(subtitle)

    left, right = st.columns([1.1, 2.2], gap="large")

    with left:
        image_url = improve_image_quality(basic.get("image_url"))
        if image_url:
            st.image(image_url, use_container_width=True)
        if basic.get("url"):
            st.link_button("Open on MyAnimeList", basic["url"], use_container_width=True)

    with right:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Score", details.get("score") or basic.get("score") or "N/A")
        m2.metric("Episodes", details.get("episodes") or basic.get("episodes") or "N/A")
        m3.metric("Source", details.get("source") or "N/A")
        m4.metric("Rating", details.get("rating") or "N/A")

        genres_html = _chips_html("Genres", details.get("genres", []), max_items=12)
        if genres_html:
            st.markdown(genres_html, unsafe_allow_html=True)

        themes_html = _chips_html("Themes", details.get("themes", []), max_items=12)
        if themes_html:
            st.markdown(themes_html, unsafe_allow_html=True)

        studios_html = _chips_html("Studios", details.get("studios", []), max_items=8)
        if studios_html:
            st.markdown(studios_html, unsafe_allow_html=True)

        synopsis = details.get("synopsis")
        if synopsis:
            with st.container(border=True):
                st.markdown("### Synopsis")
                st.write(synopsis)

        info_left, info_right = st.columns(2)
        with info_left:
            with st.container(border=True):
                st.write(f"**Status:** {details.get('status') or 'N/A'}")
                st.write(f"**Aired:** {details.get('aired') or 'N/A'}")
                st.write(f"**Premiered:** {details.get('premiered') or 'N/A'}")
                st.write(f"**Demographic:** {', '.join(details.get('demographic', [])) or 'N/A'}")
        with info_right:
            with st.container(border=True):
                st.write(f"**Broadcast:** {details.get('broadcast') or 'N/A'}")
                st.write(f"**Duration:** {details.get('duration') or 'N/A'}")
                st.write(f"**Popularity:** {details.get('popularity') or 'N/A'}")
                st.write(f"**Members:** {details.get('members') or 'N/A'}")
                st.write(f"**Scored by:** {details.get('scored_by') or 'N/A'}")

    st.caption(f"Cached at: {details.get('details_fetched_at')}")


if _DIALOG:
    @_DIALOG("Anime details")
    def show_anime_details_dialog(mal_id: int):
        _render_anime_details(mal_id)
else:
    def show_anime_details_dialog(mal_id: int):
        st.warning("Your Streamlit version doesn't support dialogs. Falling back to inline details.")
        _render_anime_details(mal_id)


def open_details_from_row(row):
    mal_id = _get_row_mal_id(row)
    if mal_id is None:
        st.warning("Cannot open details for this result (missing anime id).")
        return
    show_anime_details_dialog(mal_id)


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


def render_top_card(anime, idx):
    with st.container(border=True):
        image_url = improve_image_quality(anime.get("image_url"))
        if image_url:
            st.image(image_url, use_container_width=True)
        else:
            st.caption("No cover available")

        st.markdown(f"**{anime.get('title') or 'Untitled'}**")
        st.markdown(
            f"<div class='am-meta'>Rank #{anime.get('rank', '?')} | "
            f"Score {anime.get('score', 'N/A')}</div>",
            unsafe_allow_html=True,
        )

        type_ = anime.get("type") or "Unknown"
        episodes = anime.get("episodes") or "?"
        st.caption(f"{type_} | {episodes} eps")

        if st.button("Details", key=f"top_details_{idx}_{anime.get('mal_id', 'na')}"):
            open_details_from_row(anime)


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
def _get_recommendations_options():
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
    try:
        indexed_light = mal.index_mongo_list_to_es(limit=None)
        indexed_details = mal.index_mongo_details_to_es(limit=None)
    except Exception as exc:
        st.session_state.es_sync_state = None
        raise RuntimeError(f"Elasticsearch not reachable: {exc}") from exc
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
            try:
                with st.spinner("Auto-bootstrap: indexing Elasticsearch..."):
                    indexed_light, indexed_details, _ = sync_es_if_needed(
                        total_cached,
                        total_details,
                        force=True,
                    )
                actions.append(f"es list={indexed_light}, details={indexed_details}")
            except Exception:
                actions.append("es unavailable (skipped)")

    if not actions:
        return total_cached, total_details, "Auto-bootstrap: cache already ready."
    return total_cached, total_details, "Auto-bootstrap: " + " | ".join(actions)


def _load_top_page_and_move(next_skip: int):
    rows = mal.fetch_next_top_page_to_mongo(limit_start=next_skip)
    if rows:
        st.session_state.page_skip = next_skip
        st.session_state.top_notice = ""
    else:
        st.session_state.top_notice = f"No anime found for offset {next_skip}. You may be at the end."
    st.cache_data.clear()
    st.rerun()


def render_data_controls(total_cached: int, total_details: int):
    page_start = st.session_state.page_skip + 1
    page_end = st.session_state.page_skip + st.session_state.limit
    panel_html = f"""
    <div class="am-controls-head">
      <div class="am-controls-kicker">Control center</div>
      <h3 class="am-controls-title">Data controls</h3>
      <p class="am-controls-sub">Load ranking pages, hydrate detail cache, and keep Elasticsearch in sync.</p>
      <div class="am-controls-pill-row">
        <span class="am-controls-pill">Top cache: {total_cached:,}</span>
        <span class="am-controls-pill">Details cache: {total_details:,}</span>
        <span class="am-controls-pill">Window: {page_start}-{page_end}</span>
      </div>
    </div>
    """

    with st.container(border=True):
        st.markdown(textwrap.dedent(panel_html), unsafe_allow_html=True)

        c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1])

        if c1.button("Load Top 50", use_container_width=True):
            st.session_state.limit = 50
            _load_top_page_and_move(0)

        if c2.button("Previous 50", use_container_width=True):
            prev_skip = max(0, st.session_state.page_skip - 50)
            _load_top_page_and_move(prev_skip)

        if c3.button("Load Next 50", use_container_width=True):
            next_skip = st.session_state.page_skip + 50
            _load_top_page_and_move(next_skip)

        if c4.button("Load Next 500", use_container_width=True):
            next_skip = st.session_state.page_skip + 500
            _load_top_page_and_move(next_skip)

        with c5:
            with st.expander("Advanced controls", expanded=False):
                hydrate_max = max(total_cached, 1)
                hydrate_default = min(max(total_cached, 1), 50)
                hydrate_count = st.number_input(
                    "Details to hydrate",
                    min_value=1,
                    max_value=hydrate_max,
                    value=hydrate_default,
                    step=1,
                )
                st.caption("Tip: keep 50-100 for fast demo.")
                if st.button("Hydrate Details", use_container_width=True):
                    with st.spinner("Hydrating details cache from top list..."):
                        mal.hydrate_details_from_mongo_top(max_items=int(hydrate_count), max_age_hours=24)
                    st.cache_data.clear()
                    st.success("Hydration done.")
                    st.rerun()

                if st.button("Index All Details -> ES", use_container_width=True):
                    try:
                        with st.spinner("Indexing Mongo details into Elasticsearch..."):
                            indexed_light, indexed_details, _ = sync_es_if_needed(total_cached, total_details, force=True)
                        st.success(f"Indexed: list={indexed_light}, details={indexed_details}.")
                    except Exception as exc:
                        st.error("Elasticsearch unavailable.")
                        st.code(str(exc))

        st.markdown(
            f"<div class='am-controls-footnote'>Cached in Mongo: top={total_cached:,} | details={total_details:,}</div>",
            unsafe_allow_html=True,
        )


sync_view_from_query_params()
inject_global_styles()

try:
    total_cached = _get_total_cached()
    total_details = _get_total_details()
except Exception as exc:
    total_cached, total_details = 0, 0
    st.error("Mongo not reachable. Start docker-compose first.")
    st.code(str(exc))
    hard_stop()

render_hero(total_cached, total_details, "Find your next anime to watch!\n-- Powered by MongoDB & Elasticsearch. --")
render_data_controls(total_cached, total_details)

view = st.session_state.active_view


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


animes = []
try:
    animes = _get_page(skip=st.session_state.page_skip, limit=st.session_state.limit)
except Exception as exc:
    st.error("Failed to read top list from Mongo.")
    st.code(str(exc))
    hard_stop()

if not animes:
    st.info("No cached data yet. Click Load Top 50 above.")
    hard_stop()

if view == "Top":
    st.subheader("Top Anime")
    if st.session_state.top_notice:
        st.warning(st.session_state.top_notice)
    page_start = st.session_state.page_skip + 1
    page_end = st.session_state.page_skip + len(animes)
    st.caption(f"Showing rank positions {page_start} to {page_end}")
    for row_start in range(0, len(animes), 5):
        row_items = animes[row_start: row_start + 5]
        cols = st.columns(5)
        for col_idx in range(5):
            with cols[col_idx]:
                if col_idx < len(row_items):
                    render_top_card(row_items[col_idx], row_start + col_idx)
                else:
                    st.empty()

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

elif view == "Search":
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

else:
    st.subheader("Recommendations")

    try:
        genres_options, themes_options, studios_options = _get_recommendations_options()
    except Exception as exc:
        st.error("Cannot load recommendations options from Mongo.")
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
    st.caption("Recommendations returns all matching anime (up to Elasticsearch max window: 10,000).")
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

