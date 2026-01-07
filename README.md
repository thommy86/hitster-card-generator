# Hitster Card Generator 🎵

> [![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Donate-orange?style=for-the-badge&logo=buy-me-a-coffee)](https://www.buymeacoffee.com/WhiteShunpo)

**Generate custom Hitster-style music game cards from any Spotify playlist!**

Turn your favorite playlists into a physical card game. This tool creates professional-looking cards with neon QR codes for scanning and date-based colored solution backs. It automatically handles the layout for double-sided printing.

> [!IMPORTANT]
> **2026 API Update:** As of January 2, 2026, Spotify has temporarily disabled the "Create App" button for new developer accounts. 
> **If you cannot create a Spotify App, use Method 1 (The Webapp) or for more control Method 2 (The Scraper) below.** It requires no API keys and works for any playlist.

## 👀 Preview

The script generates a PDF optimized for duplex printing (the backs are mirrored so they align perfectly when cut).

| **Page 1: Front (Scan to Play)** | **Page 2: Back (Solutions)** |
|:---:|:---:|
| <img src="example_pictures/qr_code_side.png" width="400" alt="PDF Front Page QR Codes"> | <img src="example_pictures/solution_side.png" width="400" alt="PDF Back Page Solutions"> |
| *Neon rings with Spotify QR codes* | *Year-based color gradients (Purple=Oldest, Blue=Newest)* |

---

## ✨ Features
- **Web Interface:** New Streamlit UI for easy link pasting and instant PDF generation.
- **No API Key Required:** Use the new "Links Mode" to bypass Spotify Developer restrictions.
- **Neon Design:** Generates QR codes with a randomized neon ring aesthetic.
- **Smart Timeline Colors:** Dynamic gradients (Purple → Pink → Gold → Blue) representing release years.
- **Ink Saving Mode:** Option to print with white backgrounds to save toner.
- **Print Ready:** Outputs a standard A4 PDF with 5x5cm cards (20 per page).
- **Duplex Optimized:** Automatically generates alternating pages with mirrored layouts.

---

## Installation

1. **Clone this repository:**
   ```bash
   git clone https://github.com/WhiteShunpo/hitster-card-generator.git
   cd hitster-card-generator
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## Usage

### 🌐 Method 1: Web Interface (Easiest)
The easiest way to generate cards is via my free to use live web app:
👉 **[Hitster Card Generator](https://hitster-card-generator.streamlit.app/)**

1. **Copy Links**: In Spotify Desktop, go into your playlist, select your songs with 'Ctrl+A' and press 'Ctrl+C'.
2. **Paste**: Enter the links into the web app text area.
3. **Download**: Click "Create My PDF" and save your high-res printable file.

>[!TIP] A Note on Accuracy (Web App): When using the Web Interface, the years are pulled directly from Spotify/iTunes metadata. While highly convenient, these sources occasionally provide "Remaster" or "Re-release" years.

If you need 100% original release dates: Please use Method 2 (Local Script), which allows you to review and edit the songs.json metadata before the final PDF is generated.

### Method 2: No-API Scraper (Patch for current problems with unavailable Spotify API keys)
Use this if you can't get Spotify API keys. It handles playlists of any size (300+ songs).

1. **Collect Links:** Open the Spotify Desktop App, select your songs ('Ctrl+A'), and ('Ctrl+C').
2. **Save Links:** Create a file named `links.txt` in the project root and paste the links inside.
3. **Run:**
   ```bash
   python src/hitster_card_creator.py
   # Or with options:
   python src/hitster_card_creator.py --ink-save-mode
### Method 3: Official Spotify API
Use this if you already have an existing Spotify App.

Create an `.env` file with the instructions of given in the `.env.example` file

Then run:
```bash
python src/hitster_card_creator.py
```

## Setup Spotify API Credentials

1. **Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)**

2. **Log in with your Spotify account** (or create one)

3. **Create an app:**
   - Click "Create app"
   - App name: `Hitster Card Generator` (or any name)
   - App description: `Generate game cards from playlists`
   - Redirect URI: `https://localhost` (required but not used)
   - Check "Web API"
   - Click "Save"

4. **Get your credentials:**
   - On your app page, click "Settings"
   - Copy your **Client ID**
   - Click "View client secret" and copy your **Client Secret**

## 🔧 Accuracy Fix (Incorrect Years)

Spotify often provides "Remaster" or "Greatest Hits" years (e.g., 2011) instead of the original release date. To fix this:

1.  Run the script once. It will save `output/hitster_cards/songs.json`.
2.  Open `songs.json` or paste it into ChatGPT/Gemini with this prompt:
    > "Correct the years in this JSON to the original single release dates. Return valid JSON."
3.  Save the corrected file back to `output/hitster_cards/songs.json`.
4.  Run again without --fetch to use your local JSON.

## Output

The script generates:
- **Card images:** `output/hitster_cards/card_001_qr.png`, `card_001_solution.png`, etc.
- **JSON Data:** `output/hitster_cards/songs.json` (Editable for corrections)
- **Print-ready PDF:** `output/hitster_cards.pdf`

## Printing Instructions

1. Print the PDF double-sided (flip on long edge)
2. Cut along the gaps (2mm spacing between cards)
3. Each card should be 5cm x 5cm

## Customization

Copy the `.env.example` file to `.env` (this allows to set spotify credentials and use `git` to manage your changes without commiting the secrets to git!).

The `.env` file can then be used to configure the creation of the cards

### Save Ink & Borders
* **Web App:** Use the toggles in the sidebar (⚙️ Settings).
* **CLI:** Use `--ink-save-mode` and `--card-draw-border`.
* **Config:** Set `INK_SAVING_MODE=true` in your `.env` file.

```bash
# layout of cards:
# print the qr cards in ink saving mode (white background, black qr code)
INK_SAVING_MODE=true
# draw border around the qr cards for easier cutting
CARD_DRAW_BORDER=true
```


### Change color gradient
Edit the `COLOR_GRADIENT` list in the script:
```python
COLOR_GRADIENT = [
    "#7030A0",  # Purple (oldest)
    "#4169E1",  # Blue (newest)
]
```

## Troubleshooting

**"Module not found" error:**
```bash
pip install -r requirements.txt
```

**"Playlist not found" (404 error):**
- Make sure your playlist is **public** (Spotify API can't access private playlists with client credentials)

**QR codes not scanning:**
- Ensure printer settings: "Actual size" (not "Fit to page")
- Print at high quality/resolution

## License

MIT License - Feel free to use and modify!

## Credits

- Inspired by the original [Hitster game](https://www.jumbodiset.com/hitster)
- Montserrat font by [Julieta Ulanovsky](https://github.com/JulietaUla/Montserrat)

## Contributing

Pull requests welcome! Feel free to:
- Add new card designs
- Improve font handling
- Add command-line interface
- Support other music platforms

---


