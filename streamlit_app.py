import streamlit as st
import os
import re
from src import utils

# --- CONFIGURATION & SESSION STATE ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(PROJECT_ROOT, "fonts")

# Initialize session state
if 'user_input' not in st.session_state:
    st.session_state.user_input = ""
if 'songs' not in st.session_state:
    st.session_state.songs = None
if 'pdf_data' not in st.session_state:
    st.session_state.pdf_data = None

def set_example_links():
    st.session_state.user_input = (
        "https://open.spotify.com/track/4PTG3Z6ehGkBFwjybzWkR8?si=44d4b8822cac4dc8\n"
        "https://open.spotify.com/track/0Bo5fjMtTfCD8vHGebivqc?si=5bc94c4aadf84bca\n"
        "https://open.spotify.com/track/6Sy9BUbgFse0n0LPA5lwy5?si=ac74b629e3834310"
    )

def set_example_playlist():
    st.session_state.user_input = (
        "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
    )

def reset_generation():
    """Clear generated data when input changes."""
    st.session_state.songs = None
    st.session_state.pdf_data = None

db = {
    "fonts_dict": {
        'year': os.path.join(FONT_DIR, "Montserrat-Bold.ttf"),
        'artist': os.path.join(FONT_DIR, "Montserrat-SemiBold.ttf"),
        'song': os.path.join(FONT_DIR, "Montserrat-MediumItalic.ttf")
    },
    "color_gradient": ["#7030A0", "#E31C79", "#FF6B9D", "#FFA500", "#FFD700", "#87CEEB", "#4169E1"],
    "card_size": 2000, 
    "neon_colors": [(255, 0, 100), (0, 200, 255), (255, 255, 0), (0, 255, 120)],
    "ink_saving_mode": False,
    "card_draw_border": False,
    "card_background_color": "black",
    "card_border_color": "white",
    "card_label": None,
}
utils.db = db

# --- HELPER: detect input type ---
def parse_input(text):
    """Parse user input and return (input_type, data).
    
    Returns:
        ('tracks', [list of track URLs])
        ('playlist', playlist_url)
        ('empty', None)
    """
    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
    if not lines:
        return 'empty', None
    
    # Check if any line is a playlist URL
    playlist_lines = [l for l in lines if '/playlist/' in l]
    if playlist_lines:
        return 'playlist', playlist_lines[0]
    
    # Otherwise, gather track links
    track_lines = [l for l in lines if '/track/' in l]
    if track_lines:
        return 'tracks', track_lines
    
    return 'empty', None


# --- UI INTERFACE ---
st.set_page_config(page_title="Hitster Generator", page_icon="🎵", layout="wide")

with st.sidebar:
    st.header("⚙️ Settings")
    st.caption("Customize your print layout")
    
    ink_mode = st.toggle("Ink Saving Mode", value=False, 
                        help="Use white background and black text to save ink.")
    border_mode = st.toggle("Draw Cutting Borders", value=False,
                           help="Draw a line around each card for easier cutting.")
    card_label = st.text_input("Card Label (optional)", value="",
                               help="Add a small label to each card (e.g., event name).",
                               placeholder="Game Night 2026")

    db["ink_saving_mode"] = ink_mode
    db["card_draw_border"] = border_mode
    db["card_background_color"] = "white" if ink_mode else "black"
    db["card_border_color"] = "black" if ink_mode else "white"
    db["card_label"] = card_label if card_label.strip() else None
    
    st.divider()

    # --- SPOTIFY API CREDENTIALS (optional, for playlist fetching) ---
    with st.expander("🔑 Spotify API Credentials (optional)"):
        st.caption("Only needed when pasting a playlist URL. "
                   "Without credentials, playlist URLs are limited to ~100 tracks. "
                   "Pasting individual track links works without limits.")
        spotify_client_id = st.text_input("Client ID", type="password")
        spotify_client_secret = st.text_input("Client Secret", type="password")
    
    st.divider()

    st.header("Feedback")
    st.write("Found a bug or have a feature idea? Let me know on GitHub!")
    st.link_button(
        label="Open GitHub Issues", 
        url="https://github.com/WhiteShunpo/hitster-cards-generator/issues",
        type="secondary",
    )

    st.divider()

    st.markdown("### ☕ Support the Project")
    st.write("If this tool made your game night special, feel free to support the developer!")
    button_html = """
    <a href="https://www.buymeacoffee.com/WhiteShunpo" target="_blank">
        <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" 
        alt="Buy Me A Coffee" style="height: 50px !important;width: 181px !important;" >
    </a>
    """
    st.markdown(button_html, unsafe_allow_html=True)


st.divider()

with st.expander("Disclaimer, Accuracy & Support"):
    st.info("""
    **Why are some years wrong?**
    Metadata providers often list the date a song was added to a digital album (like a 'Greatest Hits' or 'Remaster') rather than the original single release date.
    You can now **manually correct years** in the table below after scraping!
    
    **📱 Mobile User Note:**
    If the download button doesn't respond on your phone, please try a desktop browser. Mobile browsers sometimes struggle with large in-memory PDF streams.
    """)

# --- MAIN PAGE ---
col1, col2 = st.columns([2, 1])
with col1:
    st.title("🎵 Hitster Card Generator")
    st.markdown("Generate custom music game cards from any Spotify playlist or track links.")
with col2:
    pass

st.divider()

# Instructions and Preview Columns
info_col, preview_col = st.columns([1, 1])

with info_col:
    with st.expander("How do I get links?", expanded=True):
        st.write("**Option A — Individual Tracks:**")
        st.write("1. Open **Spotify Desktop**.")
        st.write("2. Go to your playlist.")
        st.write("3. Select songs (**Ctrl+A**).")
        st.write("4. Copy (**Ctrl+C**).")
        st.write("5. Paste below!")
        st.write("")
        st.write("**Option B — Playlist URL:**")
        st.write("1. Right-click your playlist → **Share** → **Copy link**.")
        st.write("2. Paste the playlist URL below!")

with preview_col:
    st.info("**Supported formats:**\n"
            "- Track links: `https://open.spotify.com/track/...`\n"
            "- Playlist links: `https://open.spotify.com/playlist/...`")

# Input Area
st.subheader("Input")

btn_col1, btn_col2 = st.columns(2)
with btn_col1:
    st.button("✨ Load Example Tracks", on_click=set_example_links)
with btn_col2:
    st.button("📋 Load Example Playlist", on_click=set_example_playlist)

user_input = st.text_area(
    "Paste Spotify links here:", 
    height=200, 
    key="user_input",
    placeholder="https://open.spotify.com/track/...\nor\nhttps://open.spotify.com/playlist/...",
    on_change=reset_generation,
)

# Detect input type
input_type, input_data = parse_input(user_input)

if input_type == 'playlist':
    st.success("🎶 Spotify **playlist** URL detected!")
elif input_type == 'tracks':
    st.success(f"🎵 {len(input_data)} Spotify **track link(s)** detected.")
else:
    st.warning("No valid Spotify links detected yet.")


# --- STEP 1: SCRAPE / FETCH METADATA ---
if st.button("🔍 Fetch Song Metadata", type="primary"):
    if input_type == 'empty':
        st.error("Please paste some valid Spotify links first!")
    else:
        with st.status("Fetching metadata...", expanded=True) as status:
            progress_bar = st.progress(0, text="Starting...")

            if input_type == 'playlist':
                playlist_url = input_data
                # If user provided API credentials, use the API
                if spotify_client_id and spotify_client_secret:
                    st.write("Using Spotify API to fetch playlist...")
                    playlist_data = utils.fetch_spotify_playlist(
                        playlist_url, spotify_client_id, spotify_client_secret
                    )
                    songs = utils.parse_playlist_data(playlist_data)
                    progress_bar.progress(1.0, text="Done!")
                else:
                    # Scrape playlist page for track links, then scrape each track
                    st.write("Scraping playlist page for track links (no API key)...")
                    track_links = utils.scrape_playlist_track_links(playlist_url)
                    if not track_links:
                        st.error("Could not extract tracks from the playlist page. "
                                 "Try adding Spotify API credentials in the sidebar, "
                                 "or paste individual track links instead.")
                        st.stop()
                    st.write(f"Found {len(track_links)} tracks. Scraping metadata...")
                    songs = utils.fetch_no_api_data_from_list(track_links, progress_bar)
            else:
                st.write("Scraping track metadata...")
                songs = utils.fetch_no_api_data_from_list(input_data, progress_bar)

            status.update(label=f"✅ Fetched {len(songs)} songs!", state="complete")
            progress_bar.empty()

        st.session_state.songs = songs
        st.session_state.pdf_data = None  # reset PDF when songs change


# --- STEP 2: REVIEW & EDIT SONGS TABLE ---
songs = st.session_state.songs

if songs:
    st.divider()
    st.subheader("📝 Review & Edit Songs")
    st.caption("Fix any incorrect years before generating cards. "
               "Songs with unknown years show as empty — fill them in!")

    # Build an editable dataframe
    import pandas as pd
    
    df = pd.DataFrame([
        {
            "Artist": s['artist'],
            "Song": s['name'],
            "Year": s['year'] if s['year'] is not None else None,
            "Source": s.get('year_source', ''),
            "Link": s['link'],
        }
        for s in songs
    ])

    edited_df = st.data_editor(
        df,
        column_config={
            "Artist": st.column_config.TextColumn("Artist", disabled=True),
            "Song": st.column_config.TextColumn("Song", disabled=True),
            "Year": st.column_config.NumberColumn("Year", min_value=1900, max_value=2030, step=1,
                                                   help="Edit this to fix incorrect years!"),
            "Source": st.column_config.TextColumn("Source", disabled=True, 
                                                   help="Where the year came from"),
            "Link": st.column_config.LinkColumn("Link", display_text="Open"),
        },
        use_container_width=True,
        num_rows="fixed",
        hide_index=True,
    )

    # Count problems
    unknown_count = edited_df['Year'].isna().sum()
    if unknown_count > 0:
        st.warning(f"⚠️ {unknown_count} song(s) have no year. Please fill them in above, "
                   "or they will show as '????' on the cards.")

    # --- CARD PREVIEW ---
    st.divider()
    st.subheader("👀 Card Preview")
    
    # Pick a sample song for preview
    preview_idx = st.selectbox(
        "Preview card for:", 
        range(len(edited_df)),
        format_func=lambda i: f"{edited_df.iloc[i]['Artist']} — {edited_df.iloc[i]['Song']}",
    )
    
    preview_song = edited_df.iloc[preview_idx]
    preview_year = int(preview_song['Year']) if pd.notna(preview_song['Year']) else None
    all_preview_years = [int(y) if pd.notna(y) else None for y in edited_df['Year']]
    valid_preview_years = [y for y in all_preview_years if y is not None]
    if not valid_preview_years:
        valid_preview_years = [2000]

    pcol1, pcol2 = st.columns(2)
    with pcol1:
        st.caption("QR Side")
        qr_img = utils.create_qr_code(preview_song['Link'])
        qr_card = utils.create_qr_with_neon_rings_in_memory(qr_img, seed=hash(preview_song['Link']))
        st.image(qr_card, width=300)
    with pcol2:
        st.caption("Solution Side")
        sol_card = utils.create_solution_side_in_memory(
            preview_song['Song'], preview_song['Artist'], 
            preview_year, valid_preview_years,
            card_label=db.get('card_label'),
        )
        st.image(sol_card, width=300)

    # --- STEP 3: GENERATE PDF ---
    st.divider()
    
    if st.button("🎴 Create My PDF", type="primary"):
        # Apply edited years back to songs
        for i, song in enumerate(songs):
            new_year = edited_df.iloc[i]['Year']
            if pd.notna(new_year):
                song['year'] = int(new_year)
                if int(new_year) != (songs[i].get('year') or 0):
                    song['year_source'] = 'Manual'
            else:
                song['year'] = None

        with st.status("Generating cards...", expanded=True) as status:
            progress_bar = st.progress(0, text="Starting PDF generation...")
            
            pdf_data = utils.create_pdf_in_memory(songs, progress_bar)
            
            status.update(label="✅ All Cards Generated!", state="complete")
            progress_bar.empty()

        st.session_state.pdf_data = pdf_data

    # Show download button if PDF exists
    if st.session_state.pdf_data:
        st.download_button(
            label="💾 Download Printable PDF",
            data=st.session_state.pdf_data,
            file_name="my_hitster_cards.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        st.balloons()