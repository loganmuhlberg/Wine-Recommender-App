"""
3_history.py


Recommendation history page.
Shows all past recommendations for the current user, newest first.
Each recommendation is shown in a collapsible expander with full wine cards.
Users can reload a past recommendation into the active session.
"""
 
import json
import streamlit as st
from pathlib import Path
from api import get_user_recommendations
 
### Shared styling
 
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=Jost:wght@300;400;500&display=swap');
 
    :root {
        --burgundy:    #6B1D2E;
        --burgundy-dk: #4A1020;
        --gold:        #C9A84C;
        --cream:       #F7F3ED;
        --charcoal:    #2C2C2C;
        --muted:       #8A7F78;
    }
 
    html, body, [class*="css"] {
        font-family: 'Jost', sans-serif;
        color: var(--charcoal);
    }
 
    #MainMenu, footer, header { visibility: hidden; }
    .stApp { background-color: var(--cream); }
 
    /* Page header */
    .page-title {
        font-family: 'Cormorant Garamond', serif;
        font-size: 2.8rem;
        font-weight: 300;
        color: var(--burgundy);
        letter-spacing: 0.04em;
        margin-bottom: 0.1rem;
    }
    .page-subtitle {
        font-family: 'Cormorant Garamond', serif;
        font-style: italic;
        font-size: 1rem;
        color: var(--muted);
        margin-bottom: 1.5rem;
    }
 
    /* Gold divider */
    .gold-divider {
        height: 1px;
        background: linear-gradient(to right, transparent, var(--gold), transparent);
        margin: 1.5rem auto;
        width: 80%;
    }
 
    /* History entry header */
    .history-query {
        font-family: 'Cormorant Garamond', serif;
        font-size: 1.2rem;
        color: var(--burgundy);
        font-weight: 400;
    }
    .history-meta {
        font-size: 0.75rem;
        color: var(--muted);
        letter-spacing: 0.05em;
        margin-top: 0.2rem;
    }
 
    /* Sommelier note */
    .sommelier-note {
        background: white;
        border-left: 3px solid var(--gold);
        border-radius: 0 2px 2px 0;
        padding: 1rem 1.5rem;
        margin: 1rem 0;
        font-family: 'Jost', sans-serif;
        font-style: normal;
        font-weight: 300;
        font-size: 0.95rem;
        color: #1A1A1A;
        line-height: 1.8;
        letter-spacing: 0.01em;
    }
 
    /* Wine card */
    .wine-card {
        background: white;
        border: 1px solid #E8E0D5;
        border-radius: 2px;
        padding: 1.2rem;
        height: 100%;
        box-shadow: 0 2px 12px rgba(107, 29, 46, 0.05);
    }
 
    /* Rank badge */
    .rank-badge {
        display: inline-block;
        background: var(--burgundy);
        color: white;
        font-size: 0.65rem;
        font-weight: 500;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        padding: 0.2rem 0.6rem;
        border-radius: 1px;
        margin-bottom: 0.6rem;
    }
 
    /* Wine name */
    .wine-name {
        font-family: 'Cormorant Garamond', serif;
        font-size: 1.2rem;
        font-weight: 600;
        color: var(--burgundy);
        line-height: 1.2;
        margin-bottom: 0.2rem;
    }
 
    /* Wine meta */
    .wine-meta {
        font-size: 0.75rem;
        color: var(--muted);
        letter-spacing: 0.04em;
        margin-bottom: 0.6rem;
    }
 
    /* Stat pills */
    .wine-stats {
        display: flex;
        gap: 0.6rem;
        margin-bottom: 0.6rem;
        flex-wrap: wrap;
    }
    .stat-pill {
        background: var(--cream);
        border: 1px solid #E8E0D5;
        border-radius: 20px;
        font-size: 0.72rem;
        padding: 0.15rem 0.6rem;
        color: var(--charcoal);
    }
 
    /* Card section label */
    .card-section-label {
        font-size: 0.65rem;
        font-weight: 500;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: var(--muted);
        margin-top: 0.8rem;
        margin-bottom: 0.25rem;
    }
 
    /* Rationale */
    .rationale-text {
        font-size: 0.85rem;
        line-height: 1.6;
        color: var(--charcoal);
    }
 
    /* Empty state */
    .empty-state {
        text-align: center;
        padding: 4rem 2rem;
        color: var(--muted);
    }
    .empty-state-title {
        font-family: 'Cormorant Garamond', serif;
        font-size: 1.8rem;
        font-weight: 300;
        color: var(--burgundy);
        margin-bottom: 0.5rem;
    }
    .empty-state-text {
        font-size: 0.9rem;
        line-height: 1.6;
    }
 
    /* Buttons */
    .stButton > button {
        background-color: var(--burgundy);
        color: white;
        border: none;
        border-radius: 2px;
        font-family: 'Jost', sans-serif;
        font-weight: 500;
        letter-spacing: 0.1em;
        font-size: 0.8rem;
        text-transform: uppercase;
        padding: 0.55rem 1.5rem;
        transition: background-color 0.2s ease;
    }
    .stButton > button:hover {
        background-color: var(--burgundy-dk);
    }
 
    /* Link button */
    .stLinkButton > a {
        background-color: transparent !important;
        color: var(--burgundy) !important;
        border: 1px solid var(--burgundy) !important;
        border-radius: 2px !important;
        font-family: 'Jost', sans-serif !important;
        font-size: 0.72rem !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        padding: 0.35rem 0.8rem !important;
        text-decoration: none !important;
    }
    .stLinkButton > a:hover {
        background-color: var(--burgundy) !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)
 
### Auth guard
 
if "user_id" not in st.session_state or st.session_state["user_id"] is None:
    st.warning("Please log in first.")
    st.switch_page("app.py")
 
user_id      = st.session_state["user_id"]
display_name = st.session_state.get("display_name", "")
 
### Page header
 
st.markdown(
    '<div class="page-title">Your Cellar</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="page-subtitle">A record of every recommendation Vinny has made.</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)
 
### Navigation
 
nav_col1, nav_col2 = st.columns(2)
with nav_col1:
    if st.button("← New Recommendation"):
        st.switch_page("pages/2_recommendations.py")
with nav_col2:
    if st.button("My Profile →"):
        st.switch_page("pages/1_taste_profile.py")
 
st.markdown("<br>", unsafe_allow_html=True)
 
### Load history
 
with st.spinner("Loading your cellar..."):
    history = get_user_recommendations(user_id)
 
### Empty state
 
if not history:
    st.markdown("""
        <div class="empty-state">
            <div class="empty-state-title">Your cellar is empty</div>
            <div class="empty-state-text">
                You haven't received any recommendations yet.<br>
                Head to the recommendations page to find your first wine.
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.stop()
 
### Render history entries
 
st.caption(f"{len(history)} recommendation{'s' if len(history) != 1 else ''} in your cellar.")
 
for i, rec in enumerate(history):
    wines  = rec.get("wines", [])
    n_wines = len(wines)
 
    # Build a short preview of wine names for the expander label
    wine_names = [w.get("wine_name", "").split("(")[0].strip() for w in wines[:3]]
    preview    = " · ".join(wine_names) if wine_names else "No wines"
 
    # Format the query text
    query_display = rec.get("query_text", "Untitled recommendation")
    if len(query_display) > 80:
        query_display = query_display[:80] + "..."
 
    with st.expander(f'"{query_display}"  —  {preview}', expanded=(i == 0)):
 
        # Reload button
        reload_col, spacer = st.columns([1, 3])
        with reload_col:
            if st.button(
                "Refine This →",
                key=f"reload_{rec.get('recommendation_id', i)}",
            ):
                st.session_state["current_rec"]    = rec
                st.session_state["current_rec_id"] = rec.get("recommendation_id")
                st.switch_page("pages/2_recommendations.py")
 
        if rec.get("sommelier_note"):
            st.markdown(
                f'<div class="sommelier-note">{rec["sommelier_note"]}</div>',
                unsafe_allow_html=True,
            )
 
        # Wine cards
        if not wines:
            st.caption("No wine details available for this recommendation.")
        else:
            rank_labels = {1: "Top Pick", 2: "Second Choice", 3: "Third Choice"}
            cols = st.columns(n_wines)
 
            for wine, col in zip(wines, cols):
                with col:
                    # Thumbnail
                    if wine.get("thumbnail"):
                        st.image(wine["thumbnail"], use_column_width=True)
 
                    # Rank + name
                    st.markdown(
                        f'<div class="rank-badge">'
                        f'{rank_labels.get(wine.get("rank", 1), "Pick")}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<div class="wine-name">'
                        f'{wine.get("wine_name", "Unknown Wine")}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
 
                    # Metadata
                    meta_parts = [
                        p for p in [
                            wine.get("winery"),
                            wine.get("variety"),
                            wine.get("region"),
                            wine.get("country"),
                        ] if p
                    ]
                    if meta_parts:
                        st.markdown(
                            f'<div class="wine-meta">'
                            f'{" · ".join(meta_parts)}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
 
                    # Score and price
                    pills = []
                    if wine.get("points"):
                        pills.append(f"★ {wine['points']} pts")
                    if wine.get("price") and wine["price"] > 0:
                        pills.append(f"${wine['price']:.0f}")
                    if pills:
                        pills_html = "".join(
                            f'<span class="stat-pill">{p}</span>'
                            for p in pills
                        )
                        st.markdown(
                            f'<div class="wine-stats">{pills_html}</div>',
                            unsafe_allow_html=True,
                        )
 
                    # Rationale
                    if wine.get("rationale"):
                        st.markdown(
                            '<div class="card-section-label">Why this wine</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f'<div class="rationale-text">'
                            f'{wine["rationale"]}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
 
                    # Buy link
                    if wine.get("buy_link"):
                        source = (wine.get("buy_source") or "").replace("www.", "")
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.link_button(
                            f"Find on {source}" if source else "Find this wine",
                            wine["buy_link"],
                        )
 
        st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)