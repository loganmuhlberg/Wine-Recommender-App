"""
app.py

Entry point for the Wine Recommender Streamlit frontend.
 
This is the login / account page. It handles:
- New user creation (first visit)
- Returning user login via stored user_id
- Session state initialization
- Backend health check on load
 
Run with:
    streamlit run app.py
 
Make sure the FastAPI backend is running first:
    uvicorn main:app --reload --port 8000
"""

import streamlit as st
from api import health_check, create_user, get_user

### Page Configuration

st.set_page_config(
    page_title="Vinny: Your Personal AI Sommelier",
    page_icon="🍷",
    layout="centered",
    initial_sidebar_state="auto",
)

### Custom Styling? Not sure If I want this yet.

st.markdown("""
<style>
    /* Import elegant serif + clean sans pairing */
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=Jost:wght@300;400;500&display=swap');
 
    /* Root color palette — deep burgundy and cream */
    :root {
        --burgundy:     #6B1D2E;
        --burgundy-dk:  #4A1020;
        --gold:         #C9A84C;
        --cream:        #F7F3ED;
        --charcoal:     #2C2C2C;
        --muted:        #8A7F78;
    }
 
    /* Global font overrides */
    html, body, [class*="css"] {
        font-family: 'Jost', sans-serif;
        color: var(--charcoal);
    }
 
    /* Hide default Streamlit header and footer */
    #MainMenu, footer, header { visibility: hidden; }
 
    /* Page background */
    .stApp {
        background-color: var(--cream);
    }
 
    /* Hero title */
    .hero-title {
        font-family: 'Cormorant Garamond', serif;
        font-size: 5rem;
        font-weight: 300;
        color: var(--burgundy);
        text-align: center;
        letter-spacing: 0.05em;
        line-height: 1.1;
        margin-bottom: 0.25rem;
    }
 
    .hero-subtitle {
        font-family: 'Cormorant Garamond', serif;
        font-style: italic;
        font-size: 1.3rem;
        color: var(--muted);
        text-align: center;
        letter-spacing: 0.1em;
        margin-bottom: 3rem;
    }
 
    /* Divider line */
    .gold-divider {
        height: 1px;
        background: linear-gradient(to right, transparent, var(--gold), transparent);
        margin: 2rem auto;
        width: 60%;
    }
 
    /* Card container */
    .login-card {
        background: white;
        border: 1px solid #E8E0D5;
        border-radius: 2px;
        padding: 2.5rem;
        box-shadow: 0 4px 24px rgba(107, 29, 46, 0.06);
    }
 
    .card-title {
        font-family: 'Cormorant Garamond', serif;
        font-size: 1.6rem;
        font-weight: 400;
        color: var(--burgundy);
        margin-bottom: 0.25rem;
    }
 
    .card-subtitle {
        font-size: 0.85rem;
        color: var(--muted);
        letter-spacing: 0.05em;
        margin-bottom: 1.5rem;
    }
 
    /* Input styling */
    .stTextInput > div > div > input {
        border: 1px solid #DDD5C8;
        border-radius: 2px;
        font-family: 'Jost', sans-serif;
        font-size: 0.9rem;
        padding: 0.6rem 0.9rem;
        background: #FDFAF7;
    }
    .stTextInput > div > div > input:focus {
        border-color: var(--burgundy);
        box-shadow: 0 0 0 1px var(--burgundy);
    }
 
    /* Button styling */
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
 
    /* Status badge */
    .status-ok {
        display: inline-block;
        background: #E8F5E9;
        color: #2E7D32;
        font-size: 0.75rem;
        padding: 0.2rem 0.7rem;
        border-radius: 20px;
        letter-spacing: 0.05em;
    }
    .status-err {
        display: inline-block;
        background: #FFEBEE;
        color: #C62828;
        font-size: 0.75rem;
        padding: 0.2rem 0.7rem;
        border-radius: 20px;
        letter-spacing: 0.05em;
    }
 
    /* Info text */
    .info-text {
        font-size: 0.8rem;
        color: var(--muted);
        text-align: center;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

### Session State Defaults

def init_session_state():
    defaults = {
        "user_id":               None,
        "display_name":          None,
        "has_profile":           False,
        "current_rec":           None,
        "current_rec_id":        None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val
 
init_session_state()

### Restore Session from URL parameters

def restore_from_url():
    """
    If user_id is in the URL query params, verify it with the backend
    and restore the session. This allows users to bookmark their URL
    and return without re-entering their name.
    """
    if st.session_state["user_id"] is not None:
        return
 
    params = st.query_params
    if "user_id" in params:
        try:
            uid = int(params["user_id"])
            result = get_user(uid)
            if "error" not in result:
                st.session_state["user_id"]      = result["id"]
                st.session_state["display_name"] = result.get("display_name", "")
                st.session_state["has_profile"]  = True
 
        except (ValueError, KeyError):
            # Invalid user_id in URL
            st.query_params.clear()
 
restore_from_url()

# If already logged in, redirect to recommendations page
if st.session_state["user_id"] is not None:
    st.switch_page("pages/2_recommendations.py")

# Backend health check
backend_ok = health_check()

# Page layout:

# Hero section
st.markdown('<div class="hero-title">Vinny</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-subtitle">Your personal sommelier, powered by memory.</div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)
 
# Backend status
if backend_ok:
    st.markdown(
        '<div style="text-align:center"><span class="status-ok">● cellar connected</span></div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<div style="text-align:center"><span class="status-err">● cellar offline — start the backend server</span></div>',
        unsafe_allow_html=True,
    )
 
st.markdown("<br>", unsafe_allow_html=True)

### User Login/Create Tabs

tab_new, tab_return = st.tabs(["New Guest", "Returning Guest"])

# New User Tab
with tab_new:
    st.markdown('<div class="card-title">Start Getting Personalized Wine Recommendations!</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-subtitle">Create an account to save your preferences and recommendations.</div>',
        unsafe_allow_html=True,
    )

    new_name = st.text_input(
        label = "Enter Your Name",
        placeholder = "e.g. Alex or Winelover07",
        key = "new_name_input",
        label_visibility = "collapsed"
    )

    if st.button("Create Account", key="create_btn", disabled=not backend_ok):
        if not new_name.strip():
            st.error("Please enter your name to continue.")
        else:
            with st.spinner("Creating Account..."):
                result = create_user(new_name.strip())

            if "error" in result:
                st.error(f"Could not create account: {result['error']}")
            else:
                st.session_state["user_id"] = result["id"]
                st.session_state["display_name"] = result.get("display_name", new_name)
                st.session_state["has_profile"] = False

                # Persist user_id in URL so they can return
                st.query_params["user_id"] = str(result["id"])
 
                st.success(f"Welcome, {new_name}!")
                st.info(
                    f"**Your Guest ID is: {result['id']}**  \n"
                    f"Save this number — you'll need it to log back in on future visits.",
                    icon="🔑"
                )
                st.caption("Continuing to your taste profile in a moment...")
    
                import time
                time.sleep(3)
                st.switch_page("pages/1_taste_profile.py")

    st.markdown(
      '<div class="info-text">We remember you by your guest ID. Make sure to bookmark the page once you are onto the recommendations page!</div>',
       unsafe_allow_html=True,
   )

# Returning User Tab
with tab_return:
    st.markdown('<div class="card-title">Welcome Back!</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-subtitle">Enter your guest ID to restore your profile and history.</div>',
        unsafe_allow_html=True,
    )

    returning_id = st.text_input(
        label = "Returning Guest ID",
        placeholder = "e.g. 10",
        key = "returning_id_input",
        label_visibility = "collapsed"
    )

    if st.button("Continue", key="return_btn", disabled=not backend_ok):
        if not returning_id.strip():
            st.error("Please enter your guest ID.")
        else:
            try:
                uid = int(returning_id.strip())
            except ValueError:
                st.error("Guest ID should be a number.")
                uid = None
            if uid is not None:
                with st.spinner("Logging you in..."):
                    result = get_user(uid)
                
                if "error" in result:
                    st.error("Guest ID not found. Please check your number or create a new account.")
                else:
                    st.session_state["user_id"] = result["id"]
                    st.session_state["display_name"] = result.get("display_name", "")
                    st.session_state["has_profile"]  = True
 
                    # Restore user_id in URL
                    st.query_params["user_id"] = str(result["id"])
 
                    st.success(f"Welcome back, {result.get('display_name', '')}!")
                    st.switch_page("pages/2_recommendations.py")
 
    st.markdown(
        '<div class="info-text">Your guest ID was shown when you first created your account.</div>',
        unsafe_allow_html=True,
    )

### Footer

 
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="info-text">Recommendations powered by 170,000 Wine Enthusiast reviews '
    'and Gemini 2.5 Flash.</div>',
    unsafe_allow_html=True,
)
 
 


 

