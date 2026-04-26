"""
2_recommendations.py
--------------------------
Core recommendation page. Contains:
- Sidebar with price, region, country, and varietal filters
- Main area with natural language query input
- Wine result cards with thumbnail, rationale, food pairing, and buy link
- Refinement UI that appears after results are shown
"""

import json
import streamlit as st
from pathlib import Path
from api import get_recommendation, refine_recommendation, get_profile, load_filter_options

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

    /* Sommelier note block */
    .sommelier-note {
        background: white;
        border-left: 3px solid var(--gold);
        border-radius: 0 2px 2px 0;
        padding: 1rem 1.5rem;
        margin: 1.5rem 0;
        font-family: 'Jost', sans-serif;
        font-style: normal;
        font-weight: 300;
        font-size: 0.95rem;
        color: var(--charcoal);
        line-height: 1.8;
        letter-spacing: 0.01em;
    }

    /* Wine result card */
    .wine-card {
        background: white;
        border: 1px solid #E8E0D5;
        border-radius: 2px;
        padding: 1.5rem;
        height: 100%;
        box-shadow: 0 2px 12px rgba(107, 29, 46, 0.05);
        transition: box-shadow 0.2s ease;
    }
    .wine-card:hover {
        box-shadow: 0 4px 20px rgba(107, 29, 46, 0.1);
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
        margin-bottom: 0.75rem;
    }

    /* Wine name */
    .wine-name {
        font-family: 'Cormorant Garamond', serif;
        font-size: 1.3rem;
        font-weight: 600;
        color: var(--burgundy);
        line-height: 1.2;
        margin-bottom: 0.25rem;
    }

    /* Wine meta — winery, region etc */
    .wine-meta {
        font-size: 0.78rem;
        color: var(--muted);
        letter-spacing: 0.04em;
        margin-bottom: 0.75rem;
    }

    /* Score and price row */
    .wine-stats {
        display: flex;
        gap: 1rem;
        margin-bottom: 0.75rem;
    }
    .stat-pill {
        background: var(--cream);
        border: 1px solid #E8E0D5;
        border-radius: 20px;
        font-size: 0.75rem;
        padding: 0.2rem 0.7rem;
        color: var(--charcoal);
    }

    /* Section labels inside card */
    .card-section-label {
        font-size: 0.65rem;
        font-weight: 500;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: var(--muted);
        margin-top: 0.9rem;
        margin-bottom: 0.3rem;
    }

    /* Rationale text */
    .rationale-text {
        font-size: 0.88rem;
        line-height: 1.6;
        color: var(--charcoal);
    }

    /* Food pairing text */
    .pairing-text {
        font-size: 0.82rem;
        color: var(--muted);
        font-style: italic;
        line-height: 1.5;
    }

    /* Serving suggestion */
    .serving-text {
        font-size: 0.78rem;
        color: var(--muted);
        line-height: 1.5;
    }

    /* Sidebar styling */
    .sidebar-header {
        font-family: 'Cormorant Garamond', serif;
        font-size: 1.4rem;
        color: var(--burgundy);
        margin-bottom: 0.25rem;
    }
    .sidebar-label {
        font-size: 0.68rem;
        font-weight: 500;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 0.3rem;
        margin-top: 1rem;
    }

    /* Primary button */
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
        padding: 0.65rem 2rem;
        width: 100%;
        transition: background-color 0.2s ease;
    }
    .stButton > button:hover {
        background-color: var(--burgundy-dk);
    }

    /* Refinement box */
    .refine-container {
        background: white;
        border: 1px solid #E8E0D5;
        border-top: 3px solid var(--burgundy);
        border-radius: 2px;
        padding: 1.5rem;
        margin-top: 2rem;
    }
    .refine-title {
        font-family: 'Cormorant Garamond', serif;
        font-size: 1.4rem;
        color: var(--burgundy);
        margin-bottom: 0.25rem;
    }
    .refine-subtitle {
        font-size: 0.82rem;
        color: var(--muted);
        margin-bottom: 1rem;
    }

    /* Text area */
    .stTextArea textarea {
        border: 1px solid #DDD5C8;
        border-radius: 2px;
        font-family: 'Jost', sans-serif;
        font-size: 0.9rem;
        background: #FDFAF7;
    }

    /* Link button override */
    .stLinkButton > a {
        background-color: transparent !important;
        color: var(--burgundy) !important;
        border: 1px solid var(--burgundy) !important;
        border-radius: 2px !important;
        font-family: 'Jost', sans-serif !important;
        font-size: 0.75rem !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        padding: 0.4rem 1rem !important;
        text-decoration: none !important;
    }
    .stLinkButton > a:hover {
        background-color: var(--burgundy) !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

### Make Sure user is logged in


if "user_id" not in st.session_state or st.session_state["user_id"] is None:
    st.warning("Please log in first.")
    st.switch_page("app.py")

user_id = st.session_state["user_id"]
display_name = st.session_state.get("display_name", "")

### Load filter options

OPTIONS = load_filter_options()

REGIONS_LIST = OPTIONS.get("regions", [])

COUNTRIES_LIST = OPTIONS.get("countries", [])

VARIETALS_LIST = OPTIONS.get("varietals", [])

### Session state defaults

if "current_rec" not in st.session_state:
    st.session_state["current_rec"] = None
if "current_rec_id" not in st.session_state:
    st.session_state["current_rec_id"] = None

### Sidebar filters


with st.sidebar:
    st.markdown('<div class="sidebar-header">Filters</div>', unsafe_allow_html=True)
    st.caption("Narrow the search pool. Leave blank for no restriction.")

    st.markdown('<div class="sidebar-label">Price Range</div>', unsafe_allow_html=True)
    price_col1, price_col2 = st.columns(2)
    with price_col1:
        price_min = st.number_input(
            "Min $",
            min_value = 0.0,
            max_value = 999.0,
            value = 0.0,
            step = 5.0,
            label_visibility = "collapsed",
        )
    with price_col2:
        price_max = st.number_input(
            "Max $",
            min_value = 0.0,
            max_value = 999.0,
            value = 0.0,
            step = 5.0,
            label_visibility = "collapsed",
        )
    st.caption("$0 / $0 means no price filter.")

    st.markdown('<div class="sidebar-label">Countries</div>', unsafe_allow_html=True)
    selected_countries = st.multiselect(
        "Countries",
        options = COUNTRIES_LIST,
        label_visibility = "collapsed",
    )

    st.markdown('<div class="sidebar-label">Regions</div>', unsafe_allow_html=True)
    selected_regions = st.multiselect(
        "Regions",
        options = REGIONS_LIST,
        label_visibility = "collapsed",
    )

    st.markdown('<div class="sidebar-label">Varietals</div>', unsafe_allow_html=True)
    selected_varietals = st.multiselect(
        "Varietals",
        options = VARIETALS_LIST,
        label_visibility = "collapsed",
    )

    st.markdown("---")

    # Navigation
    if st.button("My Profile", key="nav_profile"):
        st.switch_page("pages/1_taste_profile.py")
    if st.button("History", key="nav_history"):
        st.switch_page("pages/3_history.py")


### Helper functions

def build_filter_kwargs() -> dict:
    """
    Build the filter kwargs to pass to get_recommendation / refine_recommendation.
    Only includes filters the user has explicitly set.
    """
    kwargs = {}
    if price_min > 0:
        kwargs["price_min"] = price_min
    if price_max > 0:
        kwargs["price_max"] = price_max
    if selected_countries:
        kwargs["countries"] = selected_countries
    if selected_regions:
        kwargs["regions"] = selected_regions
    if selected_varietals:
        kwargs["varietals"] = selected_varietals
    return kwargs


def render_wine_card(wine: dict, col):
    """Render a single wine result card into a Streamlit column."""
    with col:
        # Thumbnail
        if wine.get("thumbnail"):
            st.image(wine["thumbnail"], use_column_width=True)

        # Rank badge + wine name
        rank_labels = {1: "Top Pick", 2: "Second Choice", 3: "Third Choice"}
        st.markdown(
            f'<div class="rank-badge">{rank_labels.get(wine.get("rank", 1), "Pick")}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="wine-name">{wine.get("wine_name", "Unknown Wine")}</div>',
            unsafe_allow_html=True,
        )

        # metadata
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
                f'<div class="wine-meta">{" · ".join(meta_parts)}</div>',
                unsafe_allow_html=True,
            )

        # Score and price pills
        pills = []
        if wine.get("points"):
            pills.append(f"★ {wine['points']} pts")
        if wine.get("price") and wine["price"] > 0:
            pills.append(f"${wine['price']:.0f}")
        if pills:
            pills_html = "".join(
                f'<span class="stat-pill">{p}</span>' for p in pills
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
                f'<div class="rationale-text">{wine["rationale"]}</div>',
                unsafe_allow_html=True,
            )

        # Food pairing
        if wine.get("food_pairing"):
            st.markdown(
                '<div class="card-section-label">Food Pairing</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="pairing-text">{wine["food_pairing"]}</div>',
                unsafe_allow_html=True,
            )

        # Serving suggestion
        if wine.get("serving_suggestion"):
            st.markdown(
                '<div class="card-section-label">Serving</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="serving-text">{wine["serving_suggestion"]}</div>',
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


def render_results(rec: dict):
    """Render the full recommendation response, with note, cards, and metadata."""
    # Sommelier note
    if rec.get("sommelier_note"):
        st.markdown(
            f'<div class="sommelier-note">"{rec["sommelier_note"]}"</div>',
            unsafe_allow_html=True,
        )

    # Wine cards: three columns
    wines = rec.get("wines", [])
    if not wines:
        st.warning("No wines were returned. Please try a different query.")
        return

    cols = st.columns(len(wines))
    for wine, col in zip(wines, cols):
        render_wine_card(wine, col)



### Page header

greeting = f", {display_name}" if display_name else ""
st.markdown(
    f'<div class="page-title">Find Your Wine{greeting}</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="page-subtitle">'
    'Describe what you\'re looking for, whether that be occasion, mood, food, or flavor.'
    '</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)


### Query input

query = st.text_area(
    "What are you looking for?",
    placeholder=(
        "e.g. A bold red to pair with a ribeye steak tonight...\n"
        "Something crisp and refreshing for a summer afternoon...\n"
        "A special occasion white wine under $50..."
    ),
    height=100,
    label_visibility="collapsed",
)

search_col, clear_col = st.columns([3, 1])

with search_col:
    search_clicked = st.button(
        "Find My Wines",
        disabled=not query.strip(),
    )

with clear_col:
    if st.button("Clear Results"):
        st.session_state["current_rec"]    = None
        st.session_state["current_rec_id"] = None
        st.rerun()

### Run recommendation

if search_clicked and query.strip():
    filter_kwargs = build_filter_kwargs()

    with st.spinner("Your sommelier is selecting wines..."):
        result = get_recommendation(
            user_id = user_id,
            query_text = query.strip(),
            **filter_kwargs,
        )

    if "error" in result:
        st.error(f"Could not get recommendations: {result['error']}")
    else:
        st.session_state["current_rec"] = result
        st.session_state["current_rec_id"] = result.get("recommendation_id")
        st.rerun()


### Display current recommendation

if st.session_state["current_rec"]:
    st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)
    render_results(st.session_state["current_rec"])

    ### Refinement Calls

    st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="refine-title">Not quite right?</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="refine-subtitle">'
        'Tell your sommelier what to change and they\'ll adjust the selection.'
        '</div>',
        unsafe_allow_html=True,
    )

    feedback = st.text_area(
        "Refinement feedback",
        placeholder=(
            "e.g. These are too tannic, something more elegant...\n"
            "I'd prefer an Old World style...\n"
            "Can you find something under $30?"
        ),
        height=80,
        label_visibility="collapsed",
        key="refinement_input",
    )

    if st.button("Refine Selection", disabled=not feedback.strip()):
        filter_kwargs = build_filter_kwargs()

        with st.spinner("Refining your selection..."):
            result = refine_recommendation(
                user_id=user_id,
                recommendation_id=st.session_state["current_rec_id"],
                feedback=feedback.strip(),
                **filter_kwargs,
            )

        if "error" in result:
            st.error(f"Could not refine recommendations: {result['error']}")
        else:
            st.session_state["current_rec"] = result
            st.session_state["current_rec_id"] = result.get("recommendation_id")
            st.rerun()