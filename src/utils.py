import io
import time
import os
import random
import textwrap
import re
import qrcode
import requests
import numpy as np
import urllib.parse
from datetime import datetime
from bs4 import BeautifulSoup
from PIL import Image, ImageOps, ImageDraw, ImageFont
import matplotlib.colors as mcolors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import cm
db = None

# =============================================================================
# FONT CACHE (loaded once, reused across all cards)
# =============================================================================
_font_cache = None

# =============================================================================
# YEAR VALIDATION
# =============================================================================
MIN_VALID_YEAR = 1900
MAX_VALID_YEAR = datetime.now().year + 1

def _validate_year(year: int | None) -> int | None:
    """Return year only if it falls in a plausible range, else None."""
    if year is None:
        return None
    if MIN_VALID_YEAR <= year <= MAX_VALID_YEAR:
        return year
    return None

# =============================================================================
# Year fetching functions using MusicBrainz and iTunes APIs
# =============================================================================
def get_year_from_musicbrainz(title, artist) -> int | None:
    q = f'recording:"{title}" AND artist:"{artist}"'
    params = {"query": q, "fmt": "json", "limit": 5}
    headers = {"User-Agent": "hitster-card-generator/2.0 (https://github.com/WhiteShunpo/hitster-cards-generator)"}
    try:
        r = requests.get("https://musicbrainz.org/ws/2/recording", params=params, headers=headers, timeout=10)
        if r.status_code in (429, 503):
            time.sleep(2)
            r = requests.get("https://musicbrainz.org/ws/2/recording", params=params, headers=headers, timeout=10)
        r.raise_for_status()
        result_json = r.json()
        years = []
        if not result_json or "recordings" not in result_json:
            return None
        for rec in result_json.get("recordings", []):
            for rel in rec.get("releases", []) or []:
                date = rel.get("date")
                if date:
                    y = _validate_year(int(date.split("-")[0]))
                    if y is not None:
                        years.append(y)
        if not years:
            return None
        return min(years)
    except Exception:
        return None

def get_year_from_itunes(title, artist) -> int | None:
    q = urllib.parse.quote(f"{artist} {title}")
    url = f"https://itunes.apple.com/search?term={q}&entity=song&limit=5"
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        result_json = r.json()
        if not result_json or "results" not in result_json:
            return None
        years = []
        for res in result_json.get("results", []):
            rd = res.get("releaseDate")
            if rd:
                y = _validate_year(int(rd.split("-")[0]))
                if y is not None:
                    years.append(y)
        if not years:
            return None
        return min(years)
    except Exception:
        return None
    
def get_year_and_source(title, artist, orig_year) -> tuple[int | None, str | None]:
    """Get release year and source ('iTunes' or 'MusicBrainz') for a song.
    
    Args:
        title: Song title (first!)
        artist: Artist name (second!)
        orig_year: Fallback year from Spotify
    """
    itunes_year = get_year_from_itunes(title, artist)
    if itunes_year is not None:
        return itunes_year, 'iTunes'
    
    # Rate-limit: MusicBrainz enforces ~1 req/sec
    time.sleep(1.1)
    musicbrainz_year = get_year_from_musicbrainz(title, artist)
    if musicbrainz_year is not None:
        return musicbrainz_year, 'MusicBrainz'
    
    validated = _validate_year(orig_year)
    if validated is not None:
        return validated, 'Spotify'
    return None, None

# =============================================================================
# NAME SANITIZATION
# =============================================================================
def sanitize_name(name):
    """Remove remastered/version info from title."""
    sanitized = re.sub(
        r'\s*[-/]\s*(?:\d{4}\s*)?remaster(?:ed)?(?:\s*\d{4})?'
        r'|\s*\((?:\d{4}\s*)?remaster(?:ed)?(?:\s*\d{4})?\)'
        r'|\s*[-/]\s*(?:\d{4}\s*)?version(?:\s*\d{4})?'
        r'|\s*[-/]\s*version\s*\d{4}',
        '', name, flags=re.IGNORECASE
    )
    return sanitized.strip()


# =============================================================================
# NO-API SCRAPER FUNCTIONS (FALLBACK)
# =============================================================================

def fetch_no_api_data(links_file):
    """Scrapes metadata from public Spotify pages based on links.txt."""
    if not os.path.exists(links_file):
        return None
        
    print(f"Found {links_file}. Switching to No-API Scraper Mode...")
    with open(links_file, 'r') as f:
        urls = [line.strip() for line in f.readlines() if 'spotify.com/track/' in line]

    return fetch_no_api_data_from_list(urls)

# =============================================================================
# SPOTIFY API FUNCTIONS
# =============================================================================

def fetch_spotify_playlist(playlist_url, client_id, client_secret):
    """
    Fetch all tracks from a Spotify playlist (handles pagination).
    
    Args:
        playlist_url: Full Spotify playlist URL
        client_id: Spotify API client ID
        client_secret: Spotify API client secret
        
    Returns:
        dict: Complete playlist data with all tracks
    """
    # Extract playlist ID
    playlist_id = playlist_url.split('/playlist/')[1].split('?')[0]
    
    # Get access token
    auth_response = requests.post('https://accounts.spotify.com/api/token', {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
    })
    access_token = auth_response.json()['access_token']
    
    # Fetch playlist data
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(f'https://api.spotify.com/v1/playlists/{playlist_id}', 
                           headers=headers)
    playlist_data = response.json()
    
    print(f"Playlist: {playlist_data['name']}")
    print(f"Total tracks: {playlist_data['tracks']['total']}")
    
    # Handle pagination (Spotify returns max 100 tracks per request)
    all_tracks = playlist_data['tracks']['items']
    next_url = playlist_data['tracks']['next']
    
    while next_url:
        print(f"Fetching more tracks... (currently have {len(all_tracks)})")
        response = requests.get(next_url, headers=headers)
        data = response.json()
        all_tracks.extend(data['items'])
        next_url = data.get('next')
    
    playlist_data['tracks']['items'] = all_tracks
    print(f"✓ Fetched all {len(all_tracks)} tracks!")
    
    return playlist_data


def parse_playlist_data(playlist_data):
    """
    Extract song information from playlist data.
    
    Returns:
        array of songs ('name', 'year', 'artist', 'link')
    """
    tracks = playlist_data['tracks']['items']

    songs = []

    for item in tracks:
        track = item['track']

        name = track['name']
        artist = track['artists'][0]['name']
        release_date = track['album']['release_date']
        spotify_year = int(release_date.split("-")[0])
        year = spotify_year # default
        
        # Try to get more accurate year from MusicBrainz or iTunes   
        year, year_source = get_year_and_source(name, artist, spotify_year)     

        song = {}
        song['name'] = sanitize_name(name)
        song['original_name'] = name
        song['original_year'] = spotify_year
        song['year'] = year
        song['year_source'] = year_source
        song['artist'] = artist
        song['link'] = track['external_urls']['spotify']
        song['album'] = track['album']['name']
        songs.append(song)
        
    return songs


# =============================================================================
# SPOTIFY SCRAPER — extract track links from a public playlist page
# =============================================================================

def scrape_playlist_track_links(playlist_url) -> list[str]:
    """
    Scrape individual track URLs from a public Spotify playlist page.
    Returns a list of 'https://open.spotify.com/track/...' URLs.
    """
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(playlist_url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')

        track_links = []
        # Spotify embeds track links in <meta> and <a> tags on the public page
        for tag in soup.find_all("meta"):
            content = tag.get("content", "")
            if "open.spotify.com/track/" in content:
                # Extract just the track URL (strip query params)
                url = content.split("?")[0]
                if url not in track_links:
                    track_links.append(url)

        # Also look in <a> href attributes
        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            if "/track/" in href:
                if href.startswith("/"):
                    href = "https://open.spotify.com" + href
                url = href.split("?")[0]
                if url not in track_links:
                    track_links.append(url)

        return track_links
    except Exception as e:
        print(f"Error scraping playlist: {e}")
        return []


# =============================================================================
# CARD GENERATION FUNCTIONS
# =============================================================================

def create_qr_code(song_link):
    """Generate inverted QR code (white on black)."""
    qr = qrcode.QRCode(version=1, box_size=10, border=0)
    qr.add_data(song_link)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    return ImageOps.invert(img)


def create_qr_with_neon_rings(qr_code, output_path):
    """
    Create QR code card with colorful neon rings background.
    """
    img = create_qr_with_neon_rings_in_memory(qr_code)
    img.save(output_path)
    return output_path


def get_year_color(year, all_years):
    """
    Get color for a year based on its percentile in the distribution.
    """
    sorted_years = sorted(all_years)
    
    # Calculate percentile position
    count_below = sum(1 for y in sorted_years if y < year)
    count_equal = sum(1 for y in sorted_years if y == year)
    percentile = (count_below + count_equal / 2) / len(sorted_years)
    
    # Map to color gradient
    n_colors = len(db['color_gradient'])
    idx = percentile * (n_colors - 1)
    idx_low = int(np.floor(idx))
    idx_high = int(np.ceil(idx))
    
    if idx_low == idx_high:
        return mcolors.hex2color(db['color_gradient'][idx_low])
    
    # Linear interpolation
    color_low = mcolors.hex2color(db['color_gradient'][idx_low])
    color_high = mcolors.hex2color(db['color_gradient'][idx_high])
    frac = idx - idx_low
    
    r = color_low[0] + (color_high[0] - color_low[0]) * frac
    g = color_low[1] + (color_high[1] - color_low[1]) * frac
    b = color_low[2] + (color_high[2] - color_low[2]) * frac
    
    return (r, g, b)


def load_fonts():
    """Load Montserrat fonts with cross-platform fallback. Cached after first call."""
    global _font_cache
    if _font_cache is not None:
        return _font_cache

    # Try Montserrat first
    try:
        result = (
            ImageFont.truetype(db['fonts_dict']['year'], 380),
            ImageFont.truetype(db['fonts_dict']['artist'], 110),
            ImageFont.truetype(db['fonts_dict']['song'], 100),
            ImageFont.truetype(db['fonts_dict']['artist'], 50),
        )
        _font_cache = result
        return result
    except Exception:
        pass
    
    # Try common system fonts (cross-platform)
    fallback_fonts = [
        # Linux
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"),
        # macOS
        ("/System/Library/Fonts/Helvetica.ttc",
         "/System/Library/Fonts/Helvetica.ttc",
         "/System/Library/Fonts/Helvetica.ttc"),
        # Windows
        ("C:\\Windows\\Fonts\\arialbd.ttf",
         "C:\\Windows\\Fonts\\arial.ttf",
         "C:\\Windows\\Fonts\\ariali.ttf"),
    ]
    
    for bold_path, regular_path, italic_path in fallback_fonts:
        try:
            result = (
                ImageFont.truetype(bold_path, 300),
                ImageFont.truetype(regular_path, 140),
                ImageFont.truetype(italic_path, 140),
                ImageFont.truetype(regular_path, 50),
            )
            _font_cache = result
            return result
        except Exception:
            continue
    
    # Last resort
    print("Warning: Using default fonts (may not look optimal)")
    default = ImageFont.load_default()
    result = (default, default, default, default)
    _font_cache = result
    return result


def create_solution_side(song_name, artist, year, all_years, output_path, card_label=None):
    """
    Create solution card with year-based color background.
    """
    img = create_solution_side_in_memory(song_name, artist, year, all_years, card_label=card_label)    
    img.save(output_path)
    return output_path

# =============================================================================
# PDF GENERATION
# =============================================================================

def create_cards_pdf(cards_folder, output_pdf_path):
    """
    Create print-ready PDF with alternating front/back pages.
    4x5 grid (20 cards per page), 5cm x 5cm cards, ready for duplex printing.
    """
    c = canvas.Canvas(output_pdf_path, pagesize=A4)
    width, height = A4
    
    # Card configuration
    card_size = 5 * cm
    gap_size = 0.2 * cm
    cards_per_row = 4
    cards_per_col = 5
    cards_per_page = cards_per_row * cards_per_col
    
    # Calculate layout
    total_width = cards_per_row * card_size + (cards_per_row - 1) * gap_size
    total_height = cards_per_col * card_size + (cards_per_col - 1) * gap_size
    margin_x = (width - total_width) / 2
    margin_y = (height - total_height) / 2
    
    # Get sorted card files
    qr_images = sorted([f for f in os.listdir(cards_folder) if f.endswith('_qr.png')],
                      key=lambda x: int(re.search(r'(\d+)', x).group()))
    solution_images = sorted([f for f in os.listdir(cards_folder) if f.endswith('_solution.png')],
                            key=lambda x: int(re.search(r'(\d+)', x).group()))
    
    total_pages = (len(qr_images) + cards_per_page - 1) // cards_per_page
    
    # Create alternating front/back pages
    for page_idx in range(total_pages):
        start_card = page_idx * cards_per_page
        end_card = min(start_card + cards_per_page, len(qr_images))
        
        # FRONT PAGE (QR codes)
        if db.get('ink_saving_mode'):
            c.setFillColorRGB(1, 1, 1)
        else:
            c.setFillColorRGB(0, 0, 0)
        c.rect(0, 0, width, height, stroke=0, fill=1)
        
        for card_idx in range(start_card, end_card):
            idx = card_idx - start_card
            row = idx // cards_per_row
            col = idx % cards_per_row
            
            x = margin_x + col * (card_size + gap_size)
            y = height - margin_y - (row + 1) * card_size - row * gap_size
            
            qr_path = os.path.join(cards_folder, qr_images[card_idx])
            c.drawImage(ImageReader(qr_path), x, y, 
                       width=card_size, height=card_size, preserveAspectRatio=True)
        
        c.showPage()
        
        # BACK PAGE (Solutions) - white background, mirrored
        c.setFillColorRGB(1, 1, 1)
        c.rect(0, 0, width, height, stroke=0, fill=1)
        
        for card_idx in range(start_card, end_card):
            idx = card_idx - start_card
            row = idx // cards_per_row
            col = idx % cards_per_row
            col_mirrored = cards_per_row - 1 - col  # Mirror for duplex
            
            x = margin_x + col_mirrored * (card_size + gap_size)
            y = height - margin_y - (row + 1) * card_size - row * gap_size
            
            sol_path = os.path.join(cards_folder, solution_images[card_idx])
            c.drawImage(ImageReader(sol_path), x, y,
                       width=card_size, height=card_size, preserveAspectRatio=True)
        
        c.showPage()
    
    c.save()
    print(f"\n✓ Created PDF: {output_pdf_path}")
    print(f"  - {len(qr_images)} cards total")
    print(f"  - {total_pages * 2} pages (alternating front/back)")
    print(f"  - Ready for duplex printing!")
    return output_pdf_path


# =============================================================================
# WEBUTILS
# =============================================================================

def create_qr_with_neon_rings_in_memory(qr_code, seed=42):
    """
    Create QR code card with colorful neon rings background.
    seed: per-card seed for unique ring patterns.
    """
    size = db['card_size']
    background_color = db['card_background_color']
    border_color = db['card_border_color']
    draw_border = db.get('card_draw_border', False)
    img = Image.new("RGB", (size, size), background_color)
    # draw border around the card for easier cutting
    if draw_border:
        border_draw = ImageDraw.Draw(img)
        border_width = 20
        border_draw.rectangle(
            [(border_width, border_width), (size - border_width, size - border_width)],
            outline=border_color,
            width=border_width
        )

    draw = ImageDraw.Draw(img)
    
    # Draw neon rings — unique pattern per card
    center = size // 2
    max_radius = size // 2 - 50
    
    random.seed(seed)
    for i, color in enumerate(db['neon_colors'] * 2):
        radius = max_radius - i * 50
        if radius <= 0:
            break
        
        # Draw arc with random gaps
        num_gaps = random.randint(1, 3)
        for gap in range(num_gaps):
            gap_start = random.randint(0, 360)
            gap_length = random.randint(20, 60)
            
            draw.arc(
                (center - radius, center - radius, center + radius, center + radius),
                start=0, end=360, fill=color, width=12
            )
            draw.arc(
                (center - radius, center - radius, center + radius, center + radius),
                start=gap_start, end=gap_start + gap_length, fill=background_color, width=12
            )
    
    # Overlay QR code
    qr_size = int(size * 0.45)
    qr_code_rgb = qr_code.convert('RGB')
    qr_code_resized = qr_code_rgb.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
    
    # Create a robust module mask
    qr_l = qr_code_resized.convert('L')
    arr = np.array(qr_l)
    dark_mask = arr < 128
    num_dark = dark_mask.sum()
    total = arr.size
    if num_dark < total / 2:
        modules_mask = dark_mask
    else:
        modules_mask = ~dark_mask

    mask_img = Image.fromarray((modules_mask.astype('uint8') * 255)).convert('1')
    
    left = center - qr_size // 2
    top = center - qr_size // 2
    bg_crop = img.crop((left, top, left + qr_size, top + qr_size)).convert('L')
    bg_mean = np.array(bg_crop).mean()
    module_color = (0, 0, 0) if bg_mean > 127 else (255, 255, 255)
    
    overlay = Image.new('RGB', (qr_size, qr_size), module_color)
    img.paste(overlay, (left, top), mask_img)
    
    return img

def create_solution_side_in_memory(song_name, artist, year, all_years, card_label=None):
    """
    Create solution card and return the PIL Image object directly.
    """
    size = db['card_size']
    margin = 150
    max_width = size - (2 * margin)
    
    # Handle unknown year gracefully
    display_year = str(year) if year is not None else "????"
    effective_year = year if year is not None else int(np.median(all_years))
    
    # Filter None years out of all_years for color calculation
    valid_years = [y for y in all_years if y is not None]
    if not valid_years:
        valid_years = [2000]  # fallback

    # Get color for this year
    color_rgb = get_year_color(effective_year, valid_years)
    color_int = tuple(int(c * 255) for c in color_rgb)
    
    # Create the base image
    ink_saving_mode = db.get('ink_saving_mode', False)
    background_color = db.get('card_background_color', 'white') if ink_saving_mode else color_int
    border_width = 100

    img = Image.new("RGB", (size, size), background_color)
    if ink_saving_mode:
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0, 0), (size - 1, size - 1)], outline=color_int, width=border_width)
    draw = ImageDraw.Draw(img)
    
    font_year, font_artist, font_song, font_label = load_fonts()
    
    # Choose text color based on background luminance for contrast
    if ink_saving_mode:
        text_color = "black"
    else:
        luminance = 0.299 * color_rgb[0] + 0.587 * color_rgb[1] + 0.114 * color_rgb[2]
        text_color = "black" if luminance > 0.5 else "white"

    def get_fitted_text_in_memory(text, font, max_width):
        """Wrap text to fit within max_width."""
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        
        if text_width <= max_width:
            return text
        
        avg_char_width = text_width / len(text)
        chars_per_line = int(max_width / avg_char_width * 0.85)
        wrapped = '\n'.join(textwrap.wrap(text, width=max(chars_per_line, 10)))
        
        return wrapped
    
    # Prepare text
    song_text = get_fitted_text_in_memory(song_name, font_song, max_width)
    artist_text = get_fitted_text_in_memory(artist, font_artist, max_width)
    year_text = display_year
    
    # Draw centered text
    gap = 400
    center_x = size / 2
    center_y = size / 2
    
    draw.text((center_x, center_y), year_text, fill=text_color, 
             font=font_year, anchor="mm")
    
    artist_y = center_y - gap
    if '\n' in artist_text:
        draw.multiline_text((center_x, artist_y), artist_text, fill=text_color,
                          font=font_artist, align="center", anchor="mm")
    else:
        draw.text((center_x, artist_y), artist_text, fill=text_color,
                 font=font_artist, anchor="mm")
    
    song_y = center_y + gap
    if '\n' in song_text:
        draw.multiline_text((center_x, song_y), song_text, fill=text_color,
                          font=font_song, align="center", anchor="mm")
    else:
        draw.text((center_x, song_y), song_text, fill=text_color,
                 font=font_song, anchor="mm")
        
    if card_label:
        label_y = size - border_width // 2
        label_x = size - border_width // 2
        draw.text((label_x, label_y), card_label, fill=text_color, font=font_label, anchor="rm")
    
    return img


def fetch_no_api_data_from_list(urls, progress_bar=None):
    """
    Scrapes metadata from public Spotify pages based on a provided list of URLs.
    """
    songs = []
    errors = []
    total = len(urls)
    
    for i, url in enumerate(urls):
        idx = i + 1
        print(f"  [{idx}/{total}] Scraping: {url}")
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Metadata from OpenGraph tags
            title_tag = soup.find("meta", property="og:title")
            desc_tag = soup.find("meta", property="og:description")
            if not title_tag or not desc_tag:
                errors.append({"url": url, "error": "Missing metadata tags"})
                continue

            title = title_tag['content']
            desc = desc_tag['content']
            artist = desc.split(" · ")[0]
            
            # FIX: correct argument order — (title, artist, fallback)
            year, year_source = get_year_and_source(title, artist, None)
            
            song = {
                'name': sanitize_name(title),
                'original_name': title,
                'original_year': None,
                'year': year,
                'year_source': year_source,
                'artist': artist,
                'link': url,
            }
            songs.append(song)
            
            print(f"  {year} | {artist} - {title}")
            time.sleep(0.5)
            
            # Update Progress — fixed off-by-one
            if progress_bar:
                percent = idx / total
                progress_bar.progress(percent, text=f"Scraped {idx}/{total}: {title[:30]}...")

        except Exception as e:
            print(f"  Error scraping {url}: {e}")
            errors.append({"url": url, "error": str(e)})
    
    if errors:
        print(f"\n⚠ {len(errors)} song(s) failed to scrape:")
        for err in errors:
            print(f"  - {err['url']}: {err['error']}")
            
    return songs

def create_pdf_in_memory(songs, progress_bar=None):
    if not songs:
        return None

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Grid Settings (5x5 cm cards)
    card_size = 5 * cm
    cols, rows = 4, 5  # 20 cards per page
    margin_x = (width - (cols * card_size)) / 2
    margin_y = (height - (rows * card_size)) / 2

    total_cards = len(songs)
    years = [song['year'] for song in songs]

    card_label = db.get('card_label', None)

    for i in range(0, total_cards, 20):
        batch_songs = list(songs[i:i+20])

        # --- PAGE 1: FRONT (QR CODES) ---
        if db.get('ink_saving_mode'):
            c.setFillColorRGB(1, 1, 1)
        else:
            c.setFillColorRGB(0, 0, 0)
        c.rect(0, 0, width, height, stroke=0, fill=1)

        for idx, song in enumerate(batch_songs):
            col = idx % cols
            row = (idx // cols) 
            x = margin_x + col * card_size
            y = height - margin_y - (row + 1) * card_size
            
            base_qr = create_qr_code(song['link']) 
            # Per-card unique ring pattern based on link hash
            qr_pil = create_qr_with_neon_rings_in_memory(base_qr, seed=hash(song['link'])) 
            
            img_byte_arr = io.BytesIO()
            qr_pil.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            c.drawImage(ImageReader(img_byte_arr), x, y, width=card_size, height=card_size)
        
        c.showPage()

        # --- PAGE 2: BACK (SOLUTIONS - MIRRORED) ---
        c.setFillColorRGB(1, 1, 1)
        c.rect(0, 0, width, height, stroke=0, fill=1)

        for idx, song in enumerate(batch_songs):
            orig_col = idx % cols
            mirrored_col = (cols - 1) - orig_col
            row = (idx // cols)
            
            x = margin_x + mirrored_col * card_size
            y = height - margin_y - (row + 1) * card_size
            
            sol_pil = create_solution_side_in_memory(
                song['name'], song['artist'], song['year'], years, card_label=card_label
            ) 
            sol_byte_arr = io.BytesIO()
            sol_pil.save(sol_byte_arr, format='PNG')
            sol_byte_arr.seek(0)
            
            c.drawImage(ImageReader(sol_byte_arr), x, y, width=card_size, height=card_size)

        if progress_bar:
            processed = min(i + 20, total_cards)
            percent = processed / total_cards
            progress_bar.progress(percent, text=f"Generated {processed}/{total_cards} cards...")
        c.showPage()

    c.save()
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data