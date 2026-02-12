import os
import re
import sys
from html import escape

import streamlit as st

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scraper import scraper as mal

st.set_page_config(page_title="Anime Details", layout="wide")


def improve_image_quality(url):
    if not url:
        return url
    return re.sub(r"/r/\d+x\d+/", "/", url)


def hard_stop():
    st.stop()
    raise SystemExit


def inject_details_styles():
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

        section[data-testid="stSidebar"] {
            display: none !important;
        }

        [data-testid="stSidebarCollapsedControl"] {
            display: none !important;
        }

        .block-container {
            max-width: 1220px;
            padding-top: 1.1rem;
        }

        html, body, [class*="css"] {
            font-family: 'Space Grotesk', sans-serif;
        }

        h1, h2, h3, h4 {
            font-family: 'Sora', sans-serif;
            letter-spacing: 0.2px;
        }

        .stButton>button {
            border-radius: 12px;
            border: 1px solid var(--am-border);
            background: linear-gradient(140deg, rgba(32, 81, 103, 0.8), rgba(17, 55, 74, 0.92));
            color: var(--am-text);
            font-weight: 600;
        }

        .stButton>button:hover {
            border-color: rgba(42, 214, 194, 0.85);
        }

        div[data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="metric-container"] {
            border-radius: 16px;
            border: 1px solid var(--am-border);
            background: linear-gradient(155deg, rgba(9, 32, 45, 0.9), rgba(7, 23, 34, 0.95));
            box-shadow: 0 12px 24px rgba(3, 13, 20, 0.3);
        }

        .ad-hero {
            border: 1px solid var(--am-border);
            border-radius: 20px;
            padding: 20px 24px;
            margin-bottom: 14px;
            background: linear-gradient(135deg, rgba(10, 34, 47, 0.9), rgba(9, 26, 38, 0.95));
        }

        .ad-title {
            margin: 0;
            font-size: clamp(1.7rem, 2.3vw, 2.6rem);
            line-height: 1.08;
            background: linear-gradient(120deg, #dffbff, #7ef2e5 40%, #ffd394);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }

        .ad-subtitle {
            margin-top: 8px;
            color: var(--am-muted);
            font-size: 1rem;
        }

        .ad-meta {
            color: var(--am-muted);
            margin-top: 8px;
        }

        .ad-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }

        .ad-chip {
            border-radius: 999px;
            border: 1px solid rgba(126, 242, 229, 0.45);
            padding: 2px 10px;
            background: rgba(18, 56, 74, 0.74);
            font-size: 0.8rem;
            color: #dffbff;
        }

        .ad-nav {
            margin-bottom: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def chips_html(items):
    safe = [escape(str(item)) for item in (items or []) if str(item).strip()]
    if not safe:
        return ""
    return "<div class='ad-chip-row'>" + "".join(f"<span class='ad-chip'>{it}</span>" for it in safe) + "</div>"


inject_details_styles()

top_nav_left, _ = st.columns([1.2, 5.8])
with top_nav_left:
    if st.button("< Back", key="top_back_button", use_container_width=True):
        st.switch_page("app.py")

mal_id_raw = st.session_state.get("selected_mal_id")
if not mal_id_raw:
    mal_id_raw = st.query_params.get("mal_id")
if not mal_id_raw:
    st.info("No anime selected.")
    if st.button("Back to Top", use_container_width=True):
        st.switch_page("app.py")
    hard_stop()

if isinstance(mal_id_raw, list):
    mal_id_raw = mal_id_raw[0] if mal_id_raw else None

try:
    mal_id = int(str(mal_id_raw))
except (TypeError, ValueError):
    st.error("Invalid anime id.")
    if st.button("Back to Top", use_container_width=True):
        st.switch_page("app.py")
    hard_stop()

basic_rows = mal.get_anime_list_by_ids([mal_id])
if not basic_rows:
    st.error("Anime not found in local cache. Load it first from Top.")
    if st.button("Back to Top", use_container_width=True):
        st.switch_page("app.py")
    hard_stop()

basic = basic_rows[0]
details = mal.get_anime_details_cached(mal_id=mal_id, url=basic["url"])

title = details.get("title") or basic.get("title") or "Untitled"
subtitle = details.get("title_english") or details.get("title_japanese")

st.markdown(
    f"""
    <section class="ad-hero">
        <h1 class="ad-title">{escape(title)}</h1>
        <div class="ad-subtitle">{escape(subtitle) if subtitle else ''}</div>
        <div class="ad-meta">{escape(str(details.get('type') or basic.get('type') or 'Unknown'))}</div>
    </section>
    """,
    unsafe_allow_html=True,
)

main_cols = st.columns([1.05, 1.95], gap="large")
with main_cols[0]:
    image_url = improve_image_quality(basic.get("image_url"))
    if image_url:
        st.image(image_url, use_container_width=True)
    if basic.get("url"):
        st.link_button("Open on MyAnimeList", basic["url"], use_container_width=True)

with main_cols[1]:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Score", details.get("score") or basic.get("score") or "N/A")
    m2.metric("Episodes", details.get("episodes") or basic.get("episodes") or "N/A")
    m3.metric("Source", details.get("source") or "N/A")
    m4.metric("Rating", details.get("rating") or "N/A")

    genres = details.get("genres", [])
    themes = details.get("themes", [])
    studios = details.get("studios", [])
    if genres:
        st.markdown("**Genres**")
        st.markdown(chips_html(genres), unsafe_allow_html=True)
    if themes:
        st.markdown("**Themes**")
        st.markdown(chips_html(themes), unsafe_allow_html=True)
    if studios:
        st.markdown("**Studios**")
        st.markdown(chips_html(studios), unsafe_allow_html=True)

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

footer_left, footer_right = st.columns([2, 1])
footer_left.caption(f"Cached at: {details.get('details_fetched_at')}")
with footer_right:
    st.page_link("app.py", label="Back to Top")
