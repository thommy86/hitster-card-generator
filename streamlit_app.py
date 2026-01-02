import streamlit as st
import os
import io
from src import utils  # Import your refactored logic

# --- CONFIGURATION & SESSION STATE ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(PROJECT_ROOT, "fonts")

# Initialize session state for user input if it doesn't exist
if 'user_input' not in st.session_state:
    st.session_state.user_input = ""

def set_example_links():
    st.session_state.user_input = (
        "https://open.spotify.com/track/4uLU6YJuEkVx0vY66E7p59\n"
        "https://open.spotify.com/track/2G7S81Y6eJidH57X1E6G8R\n"
        "https://open.spotify.com/track/6Uo9pEskrYvR7C1J6e3C1J"
    )

db = {
    "fonts_dict": {
        'year': os.path.join(FONT_DIR, "Montserrat-Bold.ttf"),
        'artist': os.path.join(FONT_DIR, "Montserrat-SemiBold.ttf"),
        'song': os.path.join(FONT_DIR, "Montserrat-MediumItalic.ttf")
    },
    "color_gradient": ["#7030A0", "#E31C79", "#FF6B9D", "#FFA500", "#FFD700", "#87CEEB", "#4169E1"],
    "card_size": 2000, 
    "neon_colors": [(255, 0, 100), (0, 200, 255), (255, 255, 0), (0, 255, 120)]
}
utils.db = db

# --- UI INTERFACE ---
st.set_page_config(page_title="Hitster Generator", page_icon="🎵", layout="wide")


with st.sidebar:
    st.divider()
    st.markdown("### ☕ Support the Project")
    st.write("If this tool made your game night special, feel free to support the developer!")
    
    # This uses the professional button from Buy Me a Coffee
    # Replace 'WhiteShunpo' if your final username is different
    button_html = """
    <a href="https://www.buymeacoffee.com/WhiteShunpo" target="_blank">
        <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" 
        alt="Buy Me A Coffee" style="height: 50px !important;width: 181px !important;" >
    </a>
    """
    st.markdown(button_html, unsafe_allow_html=True)


# --- MAIN PAGE ---
# Hero Section
col1, col2 = st.columns([2, 1])
with col1:
    st.title("🎵 Hitster Card Generator")
    st.markdown("Generate custom music game cards from any Spotify playlist.")
with col2:
    # Optional: Place a small logo or card preview here
    # st.image("example_pictures/qr_code_side.png", width=150)
    pass

st.divider()

# Instructions and Preview Columns
info_col, preview_col = st.columns([1, 1])

with info_col:
    with st.expander("How do I get links?", expanded=True):
        st.write("1. Open **Spotify Desktop**.")
        st.write("2. Go to your playlist.")
        st.write("3. Select songs (**Ctrl+A**).")
        st.write("4. Copy (**Ctrl+C**).")
        st.write("5. Paste below!")

with preview_col:
    # Example images to show the "end goal"
    st.info("**Tip:** Spotify 'Track Links' usually start with `https://open.spotify.com/track/...`")

# Input Area with Functional Enhancements
st.subheader("Input")

# Sample Links Button
st.button("✨ Load Example Links", on_click=set_example_links)

# Text Area connected to Session State
user_input = st.text_area(
    "Paste Spotify links here:", 
    height=200, 
    key="user_input",
    placeholder="https://open.spotify.com/track/..."
)

# Real-time Link Counter
# Note: Standard Spotify track links usually contain '/track/' and a 22-char ID
valid_links_found = [line for line in user_input.split('\n') if "/track/" in line]
link_count = len(valid_links_found)

if link_count > 0:
    st.success(f"{link_count} valid Spotify track(s) detected.")
else:
    st.warning("No valid track links detected yet.")


# --- GENERATION LOGIC ---
if st.button("Create My PDF", type="primary"):
    if link_count == 0:
        st.error("Please paste some valid Spotify track links first!")
    else:
        links_to_process = [line.strip() for line in valid_links_found]
        
        with st.status("Working on your cards...", expanded=True) as status:
            st.write("Step 1: Scraping metadata...")
            progress_bar = st.progress(0, text="Scraping starting...")
            
            song_names, years, artists, valid_links = utils.fetch_no_api_data_from_list(
                links_to_process, 
                progress_bar
            )
            
            st.write("Step 2: Generating high-res cards...")
            progress_bar.progress(0, text="PDF generation starting...")
            
            # --- THE FIX STARTS HERE ---
            # Generate the data
            pdf_data = utils.create_pdf_in_memory(
                song_names, years, artists, valid_links, 
                progress_bar
            )
            
            status.update(label="All Cards Generated!", state="complete")
            progress_bar.empty()

        # Place the download button INSIDE this block
        # This ensures it only renders once pdf_data exists
        st.download_button(
            label="💾 Download Printable PDF",
            data=pdf_data,
            file_name="my_hitster_cards.pdf",
            mime="application/pdf",
            use_container_width=True
        )