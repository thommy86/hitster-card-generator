import streamlit as st
import os
import io
from src import utils  # Import your refactored logic

# --- CONFIGURATION ---
# Streamlit Cloud needs to know where the project root is
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(PROJECT_ROOT, "fonts")

# Setup the database dictionary to pass to utils
db = {
    "fonts_dict": {
        'year': os.path.join(FONT_DIR, "Montserrat-Bold.ttf"),
        'artist': os.path.join(FONT_DIR, "Montserrat-SemiBold.ttf"),
        'song': os.path.join(FONT_DIR, "Montserrat-MediumItalic.ttf")
    },
    "color_gradient": ["#7030A0", "#E31C79", "#FF6B9D", "#FFA500", "#FFD700", "#87CEEB", "#4169E1"],
    "card_size": 1500, # Balanced for web performance
    "neon_colors": [(255, 0, 100), (0, 200, 255), (255, 255, 0), (0, 255, 120)]
}
utils.db = db # Inject config into utils

# --- UI INTERFACE ---
st.set_page_config(page_title="Hitster Generator", page_icon="🎵")
st.title("🎵 Hitster Card Generator")
st.markdown("Generate custom music game cards from any Spotify playlist.")

# Help for users
with st.expander("How do I get links?"):
    st.write("1. Open Spotify Desktop.")
    st.write("2. Select songs (Ctrl+A).")
    st.write("3. Copy (Ctrl+C).")
    st.write("4. Paste below!")

# Input Area
user_input = st.text_area("Paste Spotify links here:", height=200, placeholder="https://open.spotify.com/track/...")

if st.button("🚀 Create My PDF"):
    if not user_input:
        st.error("Please paste some links first!")
    else:
        # Filter valid links
        links_to_process = [line.strip() for line in user_input.split('\n') if "spotify.com/track/" in line]
        
        with st.status("Working on your cards...", expanded=True) as status:
            # --- STEP 1: SCRAPING ---
            st.write("Step 1: Scraping metadata...")
            progress_bar = st.progress(0, text="Scraping starting...")
            
            # Pass the progress_bar to the scraping function
            song_names, years, artists, valid_links = utils.fetch_no_api_data_from_list(
                links_to_process, 
                progress_bar
            )
            
            # --- STEP 2: PDF GENERATION ---
            st.write("Step 2: Generating high-res cards...")
            progress_bar.progress(0, text="PDF generation starting...")
            
            # Pass the progress_bar to the PDF function
            pdf_data = utils.create_pdf_in_memory(
                song_names, years, artists, valid_links, 
                progress_bar
            )
            
            status.update(label="All Cards Generated!", state="complete")
            progress_bar.empty() # Remove progress bar when done
            
        st.download_button(
            label=" Download Printable PDF",
            data=pdf_data,
            file_name="my_hitster_cards.pdf",
            mime="application/pdf"
        )