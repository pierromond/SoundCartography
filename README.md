# Sound Cartography

A curated static catalogue of sound maps and sonic geography projects from around the world — compiled by **Pierre Aumond**.

🔗 **Live site:** https://pierromond.github.io/SoundCartography

---

## Structure

```
├── media/                         # Images (flat — all files at root level)
├── data/
│   └── entries.json               # All 85 entries (title, tags, body, image…)
├── index.html                     # Catalogue index with filters
├── fiche.html                     # Single entry template (JS reads entries.json)
├── portfolio.css                  # Shared stylesheet
├── fiches/
│   └── submit.html                # Community submission form
├── sitemap.xml                    # SEO sitemap
└── README.md
```

> **Local only (gitignored):** `generate_portfolio.py` (generator script) and `soundcartography.WordPress.2026-03-03.xml` (WordPress data source) are not committed to the repository.

## How to generate the site

The static files are committed directly. If you need to regenerate from the WordPress export, you'll need both local-only files (`generate_portfolio.py` and the XML export), then:

```bash
python3 generate_portfolio.py
```

Output:
- `portfolio.css` — shared stylesheet
- `data/entries.json` — all 85 entries as JSON (title, tags, body, image…)
- `fiche.html` — single entry template (JS fetches `data/entries.json` and renders by `?slug=`)
- `index.html` — filterable catalogue (year / topic / place / search)
- `fiches/submit.html` — community submission form
- `sitemap.xml` — for search engines

### Adding a new entry manually

Edit `data/entries.json` and add an object to the array:

```json
{
  "slug": "my-project",
  "title": "My Sound Map",
  "date": "March 2026",
  "year": "2026",
  "ext_url": "https://example.com",
  "local_img": "media/cover.jpg",
  "topics": ["soundscape"],
  "places": ["France"],
  "tags": [],
  "excerpt": "Short description…",
  "body": "<p>Full HTML content.</p>"
}
```

Then add a card in `index.html` linking to `fiche.html?slug=my-project`.

## Deploy to GitHub Pages

The site is served as-is from the `main` branch (or `gh-pages`).  
Set it up in **Settings → Pages → Deploy from branch → main → / (root)**.

The homepage will be served at:  
`https://pierromond.github.io/SoundCartography/`

## Analytics — GoatCounter

The site uses [GoatCounter](https://www.goatcounter.com/), an open-source, GDPR-friendly analytics tool that can be:
- **Self-hosted** on any server (Go binary, no database required)
- **Cloud-hosted** for free at goatcounter.com (100k pageviews/month)

### Setup

1. Sign up at https://www.goatcounter.com/ and choose a code (e.g. `soundcartography`)
2. Open `generate_portfolio.py` and update line ~175:
   ```python
   GOATCOUNTER_CODE = 'soundcartography'  # ← your code here
   ```
3. Re-run `python3 generate_portfolio.py`
4. Commit and push

### Self-hosting GoatCounter

```bash
# Download the binary from https://github.com/arp242/goatcounter/releases
./goatcounter serve -listen :8080 -db sqlite+/path/to/db.sqlite3
```

## Submitting a new entry

Visitors can propose a new entry via the **"Submit an entry"** card (first in the grid).  
The form collects: title, URL, description, tags, and an image (1 000 × 1 000 px).  
On submit, the user's mail client opens with all fields pre-filled, addressed to  
`pierre.aumond@univ-eiffel.fr`.

## Modifying the catalogue

All content comes from the WordPress XML export (local only). To update:

1. Edit or replace `soundcartography.WordPress.2026-03-03.xml`
2. Re-run `python3 generate_portfolio.py`
3. Commit the generated files (`index.html`, `portfolio.css`, `fiches/`, `sitemap.xml`) and push → GitHub Pages updates automatically

## Contact

Pierre Aumond — [pierre.aumond@univ-eiffel.fr](mailto:pierre.aumond@univ-eiffel.fr)
