import streamlit as st
import os
import json
import requests
import qrcode
import io
import textwrap
import numpy as np
from bs4 import BeautifulSoup
from PIL import Image, ImageOps, ImageDraw, ImageFont
import matplotlib.colors as mcolors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import cm

# --- CONFIGURATION (Adapted from original) ---
COLOR_GRADIENT = ["#7030A0", "#E31C79", "#FF6B9D", "#FFA500", "#FFD700", "#87CEEB", "#4169E1"]
NEON_COLORS = [(255, 0, 100), (0, 200, 255), (255, 255, 0), (0, 255, 120)]
CARD_SIZE_PX = 1000  # Reduced for web performance

# Streamlit App UI
st.set_page_config(page_title="Hitster Card Generator", page_icon="🎵")
st.title("🎵 Hitster Card Generator")
st.markdown("Turn your Spotify tracks into physical game cards. No API keys required!")

# --- HELPER FUNCTIONS (Logic from your original script) ---

def get_year_from_itunes(artist, title):
    query = f"{artist} {title}".replace(" ", "+")
    itunes_url = f"https://itunes.apple.com/search?term={query}&entity=song&limit=1"
    try:
        res = requests.get(itunes_url, timeout=5)
        results = res.json().get('results', [])
        if results: return results[0]['releaseDate'].split('-')[0]
    except: pass
    return "0000"

def scrape_metadata(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        title = soup.find("meta", property="og:title")['content']
        desc = soup.find("meta", property="og:description")['content']
        artist = desc.split(" · ")[0]
        year = get_year_from_itunes(artist, title)
        return {"name": title, "artist": artist, "year": int(year) if year != "0000" else 2000, "link": url}
    except:
        return None

# --- WEB-OPTIMIZED RENDERING ---

def create_card_images(song_data, all_years):
    # This replaces saving files to disk. It keeps them in memory.
    qr = qrcode.QRCode(version=1, box_size=10, border=0)
    qr.add_data(song_data['link'])
    qr.make(fit=True)
    qr_img = ImageOps.invert(qr.make_image(fill='black', back_color='white').convert('RGB'))
    
    # Create Front (Neon)
    front = Image.new("RGB", (CARD_SIZE_PX, CARD_SIZE_PX), "black")
    # ... (Simplified neon logic for brevity)
    front.paste(qr_img.resize((400, 400)), (300, 300))
    
    # Create Back (Solution)
    back = Image.new("RGB", (CARD_SIZE_PX, CARD_SIZE_PX), "white")
    draw = ImageDraw.Draw(back)
    # Note: Streamlit needs relative paths to fonts in your repo
    try:
        font = ImageFont.truetype("fonts/Montserrat-Bold.ttf", 100)
        draw.text((500, 500), str(song_data['year']), fill="black", font=font, anchor="mm")
    except:
        draw.text((500, 500), str(song_data['year']), fill="black", anchor="mm")
        
    return front, back

# --- MAIN APP INTERFACE ---

input_text = st.text_area("Paste Spotify Song/Playlist Links (one per line):", height=150)

if st.button("🚀 Generate PDF"):
    links = [line.strip() for line in input_text.split('\n') if "spotify.com" in line]
    
    if not links:
        st.error("No valid Spotify links found!")
    else:
        progress_bar = st.progress(0)
        cards_data = []
        
        # 1. Fetch Data
        for i, link in enumerate(links):
            data = scrape_metadata(link)
            if data: cards_data.append(data)
            progress_bar.progress((i + 1) / len(links))
        
        if cards_data:
            st.success(f"Fetched {len(cards_data)} songs!")
            
            # 2. Create PDF in memory
            pdf_buffer = io.BytesIO()
            c = canvas.Canvas(pdf_buffer, pagesize=A4)
            # (Insert your create_cards_pdf logic here, using the buffers)
            c.drawString(100, 750, f"Hitster Cards for {len(cards_data)} songs")
            c.save()
            
            # 3. Download
            st.download_button(
                label="📥 Download Printable PDF",
                data=pdf_buffer.getvalue(),
                file_name="hitster_cards.pdf",
                mime="application/pdf"
            )