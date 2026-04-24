"""
1_taste_profile.py

This is the taste profile page, which contains:
- The taste profile quiz for first time users
- A tab to view and update their taste profile for returning users.
"""

import streamlit as st
from api import get_profile, create_profile, update_profile, health_check, load_filter_options
import json

### Global Variables
OPTIONS = load_filter_options()
COUNTRY_LIST = OPTIONS.get("countries", [])

REGION_LIST = OPTIONS.get("regions", [])

VARIETAL_LIST = OPTIONS.get("varietals", [])

WINE_TYPES = ["Red", "White", "Rosé", "Sparkling", "Dessert", "Fortified"]
 
# Slider value maps — displayed as labels, stored as strings
SWEETNESS_OPTIONS = ["Bone Dry", "Dry", "Off-Dry", "Semi-Sweet", "Sweet"]
BODY_OPTIONS      = ["Light", "Light-Medium", "Medium", "Medium-Full", "Full"]
TANNIN_OPTIONS    = ["Very Low", "Low", "Medium", "High", "Very High"]
ACIDITY_OPTIONS   = ["Very Low", "Low", "Medium", "High", "Very High"]

### Styling
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
        font-size: 3rem;
        font-weight: 300;
        color: var(--burgundy);
        letter-spacing: 0.04em;
        margin-bottom: 0.1rem;
    }
    .page-subtitle {
        font-family: 'Cormorant Garamond', serif;
        font-style: italic;
        font-size: 1.1rem;
        color: var(--muted);
        margin-bottom: 2rem;
    }
 
    /* Section headers */
    .section-label {
        font-family: 'Jost', sans-serif;
        font-size: 0.7rem;
        font-weight: 500;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 0.5rem;
        margin-top: 1.8rem;
    }
 
    /* Gold divider */
    .gold-divider {
        height: 1px;
        background: linear-gradient(to right, transparent, var(--gold), transparent);
        margin: 1.5rem auto;
        width: 80%;
    }
 
    /* Slider label override */
    .stSlider label {
        font-family: 'Jost', sans-serif !important;
        font-size: 0.85rem !important;
        color: var(--charcoal) !important;
    }
 
    /* Multiselect styling */
    .stMultiSelect label {
        font-family: 'Jost', sans-serif !important;
        font-size: 0.85rem !important;
    }
 
    /* Primary button */
    .stButton > button[kind="primary"],
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
        transition: background-color 0.2s ease;
    }
    .stButton > button:hover {
        background-color: var(--burgundy-dk);
    }
 
    /* Secondary / outline button */
    .stButton > button[kind="secondary"] {
        background-color: transparent;
        color: var(--burgundy);
        border: 1px solid var(--burgundy);
    }
    .stButton > button[kind="secondary"]:hover {
        background-color: var(--burgundy);
        color: white;
    }
 
    /* Number inputs */
    .stNumberInput input {
        border: 1px solid #DDD5C8;
        border-radius: 2px;
        font-family: 'Jost', sans-serif;
        background: #FDFAF7;
    }
 
    /* Profile summary card */
    .profile-card {
        background: white;
        border: 1px solid #E8E0D5;
        border-left: 3px solid var(--burgundy);
        border-radius: 2px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 0.75rem;
    }
    .profile-card-label {
        font-size: 0.7rem;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 0.2rem;
    }
    .profile-card-value {
        font-family: 'Cormorant Garamond', serif;
        font-size: 1.2rem;
        color: var(--charcoal);
    }
 
    /* Info text */
    .info-text {
        font-size: 0.8rem;
        color: var(--muted);
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

### Get session state from url (test for user login)
if "user_id" not in st.session_state or st.session_state["user_id"] is None:
    st.warning("Please log in first.")
    st.switch_page("app.py")
 
user_id = st.session_state["user_id"]
display_name = st.session_state.get("display_name", "")


### Load Profile

@st.cache_data(ttl=30)
def fetch_profile(uid: int) -> dict:
    return get_profile(uid)

existing = fetch_profile(user_id)
has_profile = "error" not in existing
 
### JSON loader

def safe_loads(val, fallback=None):
    if fallback is None:
        fallback = []
    if not val:
        return fallback
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return fallback
    
### Page Header

name_display = f", {display_name}" if display_name else ""
 
if has_profile:
    st.markdown(
        f'<div class="page-title">Your Taste Profile{name_display}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="page-subtitle">Review and refine your preferences below.</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f'<div class="page-title">Tell Us Your Tastes{name_display}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="page-subtitle">'
        'Answer a few questions so we can tailor recommendations to your tastes.'
        '</div>',
        unsafe_allow_html=True,
    )
 
st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)

### View Mode Settings

if has_profile:
    view_mode = st.radio(
        "Mode",
        ["View Profile", "Edit Profile"],
        horizontal=True,
        label_visibility="collapsed",
    )
else:
    view_mode = "Edit Profile"

### View Mode: Summary of Profile if you have one

if view_mode == "View Profile" and has_profile:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f'<div class="profile-card">'
            f'<div class="profile-card-label">Sweetness</div>'
            f'<div class="profile-card-value">{existing.get("sweetness", "—")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="profile-card">'
            f'<div class="profile-card-label">Acidity</div>'
            f'<div class="profile-card-value">{existing.get("acidity", "—")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="profile-card">'
            f'<div class="profile-card-label">Tannins</div>'
            f'<div class="profile-card-value">{existing.get("tannins", "—")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="profile-card">'
            f'<div class="profile-card-label">Body</div>'
            f'<div class="profile-card-value">{existing.get("body", "—")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col2:
        price_str = (
            f"${existing.get('price_min', 0):.0f} – ${existing.get('price_max', 100):.0f}"
        )
        st.markdown(
            f'<div class="profile-card">'
            f'<div class="profile-card-label">Price Range</div>'
            f'<div class="profile-card-value">{price_str}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
 
        types_list = safe_loads(existing.get("types"))
        st.markdown(
            f'<div class="profile-card">'
            f'<div class="profile-card-label">Wine Types</div>'
            f'<div class="profile-card-value">'
            f'{", ".join(types_list) if types_list else "Any"}'
            f'</div></div>',
            unsafe_allow_html=True,
        )
 
        regions_list = safe_loads(existing.get("regions"))
        st.markdown(
            f'<div class="profile-card">'
            f'<div class="profile-card-label">Preferred Regions</div>'
            f'<div class="profile-card-value">'
            f'{", ".join(regions_list) if regions_list else "Any"}'
            f'</div></div>',
            unsafe_allow_html=True,
        )
 
        countries_list = safe_loads(existing.get("countries"))
        st.markdown(
            f'<div class="profile-card">'
            f'<div class="profile-card-label">Preferred Countries</div>'
            f'<div class="profile-card-value">'
            f'{", ".join(countries_list) if countries_list else "Any"}'
            f'</div></div>',
            unsafe_allow_html=True,
        )
 
    flavors_list = safe_loads(existing.get("flavors"))
    if flavors_list:
        st.markdown('<div class="section-label">Favourite Flavours</div>', unsafe_allow_html=True)
        st.write(", ".join(flavors_list))
 
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Go to Recommendations →"):
        st.switch_page("pages/2_recommendations.py")

### Edit Mode

else:
    # Pre-populate with existing values if editing
    default_sweetness = (
        SWEETNESS_OPTIONS.index(existing.get("sweetness", "Dry"))
        if has_profile and existing.get("sweetness") in SWEETNESS_OPTIONS
        else 1
    )
    default_body = (
        BODY_OPTIONS.index(existing.get("body", "Medium"))
        if has_profile and existing.get("body") in BODY_OPTIONS
        else 2
    )
    default_tannins = (
        TANNIN_OPTIONS.index(existing.get("tannins", "Medium"))
        if has_profile and existing.get("tannins") in TANNIN_OPTIONS
        else 2
    )
    default_acidity = (
        ACIDITY_OPTIONS.index(existing.get("acidity", "Medium"))
        if has_profile and existing.get("acidity") in ACIDITY_OPTIONS
        else 2
    )
 
    # --- Structural preferences ---
    st.markdown('<div class="section-label">Structure &amp; Style</div>', unsafe_allow_html=True)
    st.caption("Use the sliders to describe your ideal wine's character.")
 
    sweetness_idx = st.select_slider(
        "Sweetness",
        options=SWEETNESS_OPTIONS,
        value=SWEETNESS_OPTIONS[default_sweetness],
    )
    body_idx = st.select_slider(
        "Body",
        options=BODY_OPTIONS,
        value=BODY_OPTIONS[default_body],
    )
    tannins_idx = st.select_slider(
        "Tannins",
        options=TANNIN_OPTIONS,
        value=TANNIN_OPTIONS[default_tannins],
    )
    acidity_idx = st.select_slider(
        "Acidity",
        options=ACIDITY_OPTIONS,
        value=ACIDITY_OPTIONS[default_acidity],
    )
 
    st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)
 
    # --- Wine types ---
    st.markdown('<div class="section-label">Wine Types</div>', unsafe_allow_html=True)
    st.caption("Select all types you tend to enjoy.")
 
    default_types = safe_loads(existing.get("types")) if has_profile else []
    selected_types = st.multiselect(
        "Wine types",
        options=WINE_TYPES,
        default=[t for t in default_types if t in WINE_TYPES],
        label_visibility="collapsed",
    )
 
    st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)
 
    # --- Flavour notes ---
    st.markdown('<div class="section-label">Flavour Notes</div>', unsafe_allow_html=True)
    st.caption("Input the flavours you enjoy finding in a wine, seperated by commas.")
 
    default_flavors = safe_loads(existing.get("flavors")) if has_profile else []
    flavor_input = st.text_input(
        "Flavours",
        value = ",".join(default_flavors),
        placeholder="e.g. dark cherry, oak, vanilla, tobacco, mineral",
        label_visibility="collapsed",
    )

    selected_flavors = [
    f.strip() for f in flavor_input.split(",")
    if f.strip()
]
 
    st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)
 
    # --- Region and country preferences ---
    st.markdown('<div class="section-label">Origins</div>', unsafe_allow_html=True)
    st.caption(
        "Select your preferred wine regions and countries. "
        "Leave blank for no preference — these inform recommendations "
        "but don't hard-filter results."
    )
 
    default_regions   = safe_loads(existing.get("regions"))   if has_profile else []
    default_countries = safe_loads(existing.get("countries")) if has_profile else []
 
    selected_regions = st.multiselect(
        "Preferred regions",
        options=REGION_LIST,
        default=[r for r in default_regions if r in REGION_LIST],
    )
    selected_countries = st.multiselect(
        "Preferred countries",
        options=COUNTRY_LIST,
        default=[c for c in default_countries if c in COUNTRY_LIST],
    )
 
    st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)
 
    # --- Price range ---
    st.markdown('<div class="section-label">Price Range</div>', unsafe_allow_html=True)
    st.caption("Your typical budget per bottle.")
 
    default_min = float(existing.get("price_min", 0.0))  if has_profile else 0.0
    default_max = float(existing.get("price_max", 50.0)) if has_profile else 50.0
 
    price_col1, price_col2 = st.columns(2)
    with price_col1:
        price_min = st.number_input(
            "Minimum ($)",
            min_value=0.0,
            max_value=999.0,
            value=default_min,
            step=5.0,
        )
    with price_col2:
        price_max = st.number_input(
            "Maximum ($)",
            min_value=0.0,
            max_value=999.0,
            value=default_max,
            step=5.0,
        )
 
    if price_min > price_max:
        st.warning("Minimum price cannot exceed maximum price.")
 
    st.markdown("<br>", unsafe_allow_html=True)
 
    # --- Submit button ---
    btn_label = "Update Profile" if has_profile else "Save My Taste Profile"
 
    if st.button(btn_label, disabled=(price_min > price_max)):
        with st.spinner("Saving your preferences..."):
 
            if has_profile:
                # only send changed fields if updating
                result = update_profile(user_id, {
                    "sweetness": sweetness_idx,
                    "body":      body_idx,
                    "tannins":   tannins_idx,
                    "acidity":   acidity_idx,
                    "flavors":   json.dumps(selected_flavors),
                    "types":     json.dumps(selected_types),
                    "regions":   json.dumps(selected_regions),
                    "countries": json.dumps(selected_countries),
                    "price_min": price_min,
                    "price_max": price_max,
                })
            else:
                # create new profile
                result = create_profile(
                    user_id=user_id,
                    sweetness=sweetness_idx,
                    body=body_idx,
                    tannins=tannins_idx,
                    acidity=acidity_idx,
                    flavors=selected_flavors,
                    types=selected_types,
                    regions=selected_regions,
                    countries=selected_countries,
                    price_min=price_min,
                    price_max=price_max,
                )
 
        if "error" in result:
            st.error(f"Could not save profile: {result['error']}")
        else:
            st.session_state["has_profile"] = True
            # Clear the profile cache so view mode shows fresh data
            fetch_profile.clear()
            st.success("Profile saved!" if has_profile else "Taste Profile saved. Let's find your wines!")
            st.switch_page("pages/2_recommendations.py")
        
# ---------------------------------------------------------------------------
# Navigation footer
# ---------------------------------------------------------------------------
 
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)
 
nav_col1, nav_col2 = st.columns(2)
with nav_col1:
    if st.button("← Back to Login", key="nav_login"):
        st.switch_page("app.py")
with nav_col2:
    if has_profile:
        if st.button("Recommendations →", key="nav_rec"):
            st.switch_page("pages/2_recommendations.py")






