#!/usr/bin/env python3

"""
Hitster Card Generator
Generate custom Hitster-style music game cards from Spotify playlists.
"""

import time
import os
import json
import random
import textwrap
import re
from dotenv import load_dotenv
import qrcode
import requests
import numpy as np
from bs4 import BeautifulSoup
from PIL import Image, ImageOps, ImageDraw, ImageFont
import matplotlib.colors as mcolors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import cm
import utils

# =============================================================================
# CONFIGURATION
# =============================================================================

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
# Step UP one level to reach the project root
PROJECT_ROOT = os.path.dirname(SRC_DIR)

# Correct paths relative to Project Root
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
FONT_DIR = os.path.join(PROJECT_ROOT, "fonts")
LINKS_FILE = os.path.join(PROJECT_ROOT, "links.txt")

FONT_PATHS = {
    'year': os.path.join(FONT_DIR, "Montserrat-Bold.ttf"),
    'artist': os.path.join(FONT_DIR, "Montserrat-SemiBold.ttf"),
    'song': os.path.join(FONT_DIR, "Montserrat-MediumItalic.ttf")
}
# Color gradient for year-based card colors (oldest to newest)
COLOR_GRADIENT = [
    "#7030A0",  # Purple (oldest)
    "#E31C79",  # Pink
    "#FF6B9D",  # Light pink
    "#FFA500",  # Orange
    "#FFD700",  # Gold
    "#87CEEB",  # Sky blue
    "#4169E1",  # Royal blue (newest)
]

# Card design parameters
CARD_SIZE = 2000  # pixels
NEON_COLORS = [(255, 0, 100), (0, 200, 255), (255, 255, 0), (0, 255, 120)]

db = {"fonts_dict": FONT_PATHS, 
      "color_gradient": COLOR_GRADIENT,
      "card_size": CARD_SIZE,
      "neon_colors": NEON_COLORS}
utils.db = db 

# =============================================================================
# FINAL INTEGRATED PIPELINE
# =============================================================================

def generate_hitster_cards(db, playlist_url=None, client_id=None, client_secret=None, output_dir="hitster_cards"):
    print("=== Hitster Card Generator ===\n")
    full_output_path = os.path.join(OUTPUT_DIR, output_dir)
    os.makedirs(full_output_path, exist_ok=True)
    json_file = os.path.join(OUTPUT_DIR, output_dir, "songs.json")
    
    songs = []

    # --- DATA FETCHING LOGIC ---
    if os.path.exists(json_file):
        print(f"Step 1: Loading local data from {json_file}...")
        with open(json_file, 'r', encoding='utf-8') as f:
            songs = json.load(f)
            
    elif os.path.exists(LINKS_FILE):
        print(f"Step 1: No JSON found. Using {LINKS_FILE} (Scraper Mode)...")
        songs = utils.fetch_no_api_data(LINKS_FILE)
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(songs, f, indent=2)

    elif client_id and client_secret and playlist_url:
        print("Step 1: Fetching from Spotify API...")
        playlist_data = utils.fetch_spotify_playlist(playlist_url, client_id, client_secret)
        songs = utils.parse_playlist_data(playlist_data)
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(songs, f, indent=2)
    else:
        print("ERROR: No API credentials AND no links.txt found.")
        return
    

    # --- CARD GENERATION ---
    print(f"\nStep 2: Generating {len(songs)} cards...")
    release_years = [song['year'] for song in songs]
    for i, song in enumerate(songs):
        qr_path = os.path.join(full_output_path, f"card_{i+1:03d}_qr.png")
        sol_path = os.path.join(full_output_path, f"card_{i+1:03d}_solution.png")
        
        qr_code = utils.create_qr_code(song['link'])
        utils.create_qr_with_neon_rings(qr_code, qr_path)
        utils.create_solution_side(song['name'], song['artist'], song['year'], release_years, sol_path)
        if (i + 1) % 20 == 0:
            print(f"  Progress: {i+1}/{len(songs)}...")

    # --- PDF CREATION ---
    print("\nStep 3: Creating PDF...")
    pdf_path = os.path.join(OUTPUT_DIR, f"{output_dir}.pdf")
    utils.create_cards_pdf(os.path.join(OUTPUT_DIR, output_dir), pdf_path)
    print(f"\n✓ Done! PDF ready at: {pdf_path}")

if __name__ == "__main__":

    # If API is down, you can leave these blank and just have 'links.txt' ready
    load_dotenv()  # take environment variables from .env file

    PLAYLIST_URL = os.getenv("PLAYLIST_URL", "")
    CLIENT_ID = os.getenv("CLIENT_ID", "")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")

    # Default values are the original settings:
    INK_SAVING_MODE = os.getenv("INK_SAVING_MODE", "False").lower() == "true"
    CARD_DRAW_BORDER = os.getenv("CARD_DRAW_BORDER", "False").lower() == "true"

    db['ink_saving_mode'] = INK_SAVING_MODE
    db['card_draw_border'] = CARD_DRAW_BORDER
    db['card_background_color'] = 'white' if INK_SAVING_MODE else 'black'
    db['card_border_color'] = 'black' if INK_SAVING_MODE else 'white'

    print(f"Using client id {CLIENT_ID} to fetch playlist url {PLAYLIST_URL}...")
    
    generate_hitster_cards(db, PLAYLIST_URL, CLIENT_ID, CLIENT_SECRET)