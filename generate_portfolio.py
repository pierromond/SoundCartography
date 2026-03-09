#!/usr/bin/env python3
"""
Generate a static HTML portfolio + individual fiche pages from
the Sound Cartography WordPress XML export.

Output:
  portfolio.css            shared stylesheet
  index.html               index grid with filters
  index.html           index grid with filters
"""

import re, os, html as html_module, json
from datetime import datetime
from collections import Counter

# ═══════════════════════════════════════════════════════════════
# 1. LOAD DATA
# ═══════════════════════════════════════════════════════════════
with open('soundcartography.WordPress.2026-03-03.xml', 'r', encoding='utf-8') as f:
    content = f.read()

items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL)

# attachment map
attachments = {}
for item in items:
    pt = re.search(r'<wp:post_type><!\[CDATA\[(.*?)\]\]>', item)
    if pt and pt.group(1) == 'attachment':
        pid = re.search(r'<wp:post_id>(\d+)</wp:post_id>', item)
        au  = re.search(r'<wp:attachment_url><!\[CDATA\[(.*?)\]\]>', item)
        if pid and au:
            attachments[pid.group(1)] = au.group(1)

# local media map
local_files = {}
for root, dirs, files in os.walk('media'):
    for fname in files:
        local_files[fname.lower()] = os.path.join(root, fname)

# ═══════════════════════════════════════════════════════════════
# 2. EXTRACT PUBLISHED POSTS
# ═══════════════════════════════════════════════════════════════
posts = []
for item in items:
    pt = re.search(r'<wp:post_type><!\[CDATA\[(.*?)\]\]>', item)
    st = re.search(r'<wp:status><!\[CDATA\[(.*?)\]\]>', item)
    if not (pt and pt.group(1) == 'post' and st and st.group(1) == 'publish'):
        continue

    pid      = re.search(r'<wp:post_id>(\d+)</wp:post_id>', item)
    title    = re.search(r'<title><!\[CDATA\[(.*?)\]\]>', item)
    date     = re.search(r'<wp:post_date><!\[CDATA\[(.*?)\]\]>', item)
    slug_m   = re.search(r'<wp:post_name><!\[CDATA\[(.*?)\]\]>', item)
    exc_m    = re.search(r'<excerpt:encoded><!\[CDATA\[(.*?)\]\]>', item, re.DOTALL)
    body_m   = re.search(r'<content:encoded><!\[CDATA\[(.*?)\]\]></content:encoded>', item, re.DOTALL)

    cats = re.findall(r'<category domain="category"[^>]*><!\[CDATA\[(.*?)\]\]>', item)
    tags = re.findall(r'<category domain="post_tag"[^>]*><!\[CDATA\[(.*?)\]\]>', item)

    body_raw = body_m.group(1) if body_m else ''
    ext_url = None
    for m in re.finditer(r'href="(https?://[^"]+)"', body_raw):
        u = m.group(1)
        if 'wordpress.com' not in u and 'soundcartography' not in u:
            ext_url = u; break

    thumb_id = re.search(
        r'<wp:meta_key><!\[CDATA\[_thumbnail_id\]\]>.*?<wp:meta_value><!\[CDATA\[(\d+)\]\]>',
        item, re.DOTALL)
    local_img = None
    if thumb_id:
        au = attachments.get(thumb_id.group(1))
        if au:
            local_img = local_files.get(au.split('/')[-1].lower())

    raw_date = date_str = ''; year = '—'
    if date:
        raw_date = date.group(1)[:10]; year = raw_date[:4]
        try: date_str = datetime.strptime(raw_date, '%Y-%m-%d').strftime('%B %Y')
        except: date_str = raw_date

    exc = ''
    if exc_m and exc_m.group(1).strip():
        exc = exc_m.group(1).strip()
    elif body_raw:
        r = re.sub(r'<[^>]+>', '', body_raw).strip()
        r = re.sub(r'\s+', ' ', r)
        exc = r[:220] + ('…' if len(r) > 220 else '')

    posts.append({
        'pid':      int(pid.group(1)) if pid else 0,
        'title':    html_module.unescape(title.group(1)) if title else '',
        'date':     date_str, 'raw_date': raw_date, 'year': year,
        'excerpt':  html_module.unescape(exc),
        'cats': cats, 'tags': tags,
        'ext_url':  ext_url or '#',
        'local_img': local_img or '',
        'slug':     slug_m.group(1) if slug_m else f'post-{pid.group(1)}',
        'body_raw': body_raw,
    })

posts.sort(key=lambda x: x['raw_date'], reverse=True)
print(f"Posts from XML: {len(posts)}")

# ── Load manual entries (not in the XML) ──
MANUAL_ENTRIES_FILE = 'data/manual_entries.json'
if os.path.exists(MANUAL_ENTRIES_FILE):
    with open(MANUAL_ENTRIES_FILE, 'r', encoding='utf-8') as f:
        manual = json.load(f)
    existing_slugs = {p['slug'] for p in posts}
    # Override categories/tags on existing XML entries
    for me in manual:
        if me['slug'] in existing_slugs:
            for p in posts:
                if p['slug'] == me['slug']:
                    if me.get('topics') or me.get('places'):
                        p['cats'] = me.get('topics', []) + me.get('places', [])
                    if me.get('tags'):
                        p['tags'] = me['tags']
                    break
            continue
        raw_date = ''
        year = me.get('year', '—')
        date_str = me.get('date', '')
        # Attempt to derive raw_date from date string like "March 2026"
        try:
            raw_date = datetime.strptime(date_str, '%B %Y').strftime('%Y-%m-01')
        except Exception:
            raw_date = f'{year}-01-01' if year != '—' else ''
        posts.append({
            'pid':      0,
            'title':    me.get('title', ''),
            'date':     date_str, 'raw_date': raw_date, 'year': year,
            'excerpt':  me.get('excerpt', ''),
            'cats':     me.get('topics', []) + me.get('places', []),
            'tags':     me.get('tags', []),
            'ext_url':  me.get('ext_url', '#'),
            'local_img': me.get('local_img', ''),
            'slug':     me['slug'],
            'body_raw': me.get('body', ''),
        })
    posts.sort(key=lambda x: x['raw_date'], reverse=True)
    print(f"  + {len(manual)} manual entries → {len(posts)} total")

print(f"Posts: {len(posts)}")

# ═══════════════════════════════════════════════════════════════
# 3. NORMALISE CATEGORIES
# ═══════════════════════════════════════════════════════════════
raw_cats = {c.strip() for p in posts for c in p['cats'] if c.strip() and c.strip().lower() != 'none'}
cat_map = {}
for c in sorted(raw_cats):
    k = c.lower()
    if k not in cat_map: cat_map[k] = c
for p in posts:
    p['cats'] = [cat_map.get(c.lower(), c) for c in p['cats'] if c.strip() and c.strip().lower() != 'none']

PLACE_CATS = {
    'Africa','Asia','Europe','Global','Latin America','North America','South Korea','World',
    'Austria','Brazil','Canada','Chili','China','France','Greece','Israel','Italy','Japan',
    'Netherlands','Palestine','Peru','Portugal','Spain','Switzerland','Turkey','Turkey - Europe',
    'United Kingdom','US',
    'Andalucia','Asturias','Cáceres','Fleurieu','Guarda',
    'Athens','Bahia Blanca','Barcelona','Belfast','Boston','Braga','Brussels','Caen','Canberra',
    'Chicago','Curitiba','Jerusalem','Karlsruhe','Lisboa','London','Lugo','Madrid','Manchester',
    'Marseille','Miami','Milan','Mississauga','Montréal','New Orleans','New York','Paris','Porto',
    'Rio de Janeiro','Rome','San Francisco','Seattle','Seoul','Soria','Tokio','Torres verdas',
    'Toulouse','Valdivia','Washington',
}
place_keys = {c.lower() for c in PLACE_CATS}
for p in posts:
    p['places'] = [c for c in p['cats'] if c.lower() in place_keys]
    p['topics'] = [c for c in p['cats'] if c.lower() not in place_keys]

# ── Topic normalisation / merges ─────────────────────────────
# Maps old topic → new topic (None = remove)
TOPIC_REMAP = {
    'Sound levels':              'Sound Level Noise Map',  # fusionner
    'Pathway Listening':         'Sound Walks',            # fusionner
    'Geolocalized playlist':     'Geolocalized recordings',# fusionner
    'Video':                     None,                     # supprimer
    'Urban sound dictionary':    None,                     # supprimer
    'Sea - Ocean':               None,                     # supprimer
}
for p in posts:
    new_topics = []
    for t in p['topics']:
        if t in TOPIC_REMAP:
            replacement = TOPIC_REMAP[t]
            if replacement and replacement not in new_topics and replacement not in p['topics']:
                new_topics.append(replacement)
            elif replacement and replacement in p['topics']:
                pass  # already present, will appear naturally
            # None → drop silently
        else:
            new_topics.append(t)
    # deduplicate while preserving order
    seen = set()
    p['topics'] = [x for x in new_topics if not (x in seen or seen.add(x))]

place_counts = Counter(c for p in posts for c in p['places'])
topic_counts = Counter(c for p in posts for c in p['topics'])
all_years  = sorted({p['year'] for p in posts if p['year'] != '—'}, reverse=True)
all_places = sorted(place_counts, key=str.lower)
all_topics = sorted(topic_counts, key=str.lower)

# ═══════════════════════════════════════════════════════════════
# 4. HELPERS
# ═══════════════════════════════════════════════════════════════
def sl(s): return s.lower().replace(' ','-').replace('/','-')

def clean_content(html_str, prefix=''):
    def fix_src(m):
        # strip query params like ?w=300 before local lookup
        fname = m.group(1).split('/')[-1].lower().split('?')[0]
        local = local_files.get(fname)
        return f'src="{prefix}{local}"' if local else m.group(0)
    html_str = re.sub(r'src="https?://[^"]*?/([^/"]+\.(png|jpg|jpeg|gif|webp|svg))"',
                      fix_src, html_str, flags=re.IGNORECASE)
    def cap(m):
        inner = m.group(1)
        img = re.search(r'(<img[^>]+>)', inner)
        img_h = img.group(1) if img else ''
        cap_t = re.sub(r'\s+',' ', re.sub(r'<[^>]+>','', re.sub(r'<img[^>]+>','',inner))).strip()
        return (f'<figure class="wp-figure">{img_h}'
                f'<figcaption>{cap_t}</figcaption></figure>' if cap_t else
                f'<figure class="wp-figure">{img_h}</figure>')
    html_str = re.sub(r'\[caption[^\]]*\](.*?)\[/caption\]', cap, html_str, re.DOTALL)
    html_str = re.sub(r'\[[^\]]+\]', '', html_str)
    html_str = re.sub(r'<hr\s*/?>\s*<p><em>This entry is part of.*?</em></p>', '',
                      html_str, flags=re.DOTALL)
    return html_str.strip()

GFONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600'
    '&family=Playfair+Display:wght@600;700&display=swap" rel="stylesheet">'
)
# ── Analytics (GoatCounter — open-source, GDPR, auto-hébergeable) ──
# 1. Crée un compte sur https://www.goatcounter.com/
# 2. Choisis un code (ex: 'soundcartography')
# 3. Remplace YOURCODE ci-dessous par ce code
GOATCOUNTER_CODE = 'soundcartography'
SITE_URL = 'https://pierromond.github.io/SoundCartography'
ANALYTICS = f'  <!-- GoatCounter analytics -->\n  <script data-goatcounter="https://{GOATCOUNTER_CODE}.goatcounter.com/count"\n          async src="//gc.zgo.at/count.js"></script>'

def head_seo(title, description, canonical, og_image='', json_ld=''):
    """Return canonical + Open Graph + Twitter Card + JSON-LD meta block."""
    et = html_module.escape(title)
    ed = html_module.escape(description[:160])
    eu = html_module.escape(canonical)
    ei = html_module.escape(og_image)
    lines = [
        f'  <link rel="canonical" href="{eu}">',
        f'  <meta property="og:type"        content="website">',
        f'  <meta property="og:site_name"   content="Sound Cartography">',
        f'  <meta property="og:title"       content="{et}">',
        f'  <meta property="og:description" content="{ed}">',
        f'  <meta property="og:url"         content="{eu}">',
    ]
    if og_image:
        lines.append(f'  <meta property="og:image"       content="{ei}">')
    lines += [
        f'  <meta name="twitter:card"        content="summary_large_image">',
        f'  <meta name="twitter:title"       content="{et}">',
        f'  <meta name="twitter:description" content="{ed}">',
    ]
    if og_image:
        lines.append(f'  <meta name="twitter:image"       content="{ei}">')
    if json_ld:
        lines.append(f'  <script type="application/ld+json">{json_ld}</script>')
    return '\n'.join(lines)

FOOTER_HTML = """\
<footer class="site-footer">
  <p>Sound Cartography &nbsp;·&nbsp; Curated by Pierre Aumond
    &nbsp;·&nbsp; Content sourced from referenced projects — not authored by the curator.</p>
</footer>"""

# ═══════════════════════════════════════════════════════════════
# 5. CSS
# ═══════════════════════════════════════════════════════════════
CSS = """\
/* ── Reset & base ── */
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}

/* ── Design tokens — dark (default) ── */
:root{
  --bg:#08090b;--surface:#111318;--surface2:#181d26;
  --border:rgba(255,255,255,.11);
  --accent:#6495f0;--accent2:#3ecfb2;
  --accent-glow:rgba(100,149,240,.22);
  --accent-subtle:color-mix(in oklch,#6495f0 18%,transparent);
  --text:#d4ddf2;--text-dim:#7088a8;--heading:#f2f5ff;
  --radius:14px;--radius-sm:8px;--max-w:1440px;
  --header-grad:
    radial-gradient(ellipse 90% 55% at 50% -5%,rgba(100,149,240,.14) 0%,transparent 70%),
    radial-gradient(ellipse 45% 35% at 85% 110%,rgba(62,207,178,.09) 0%,transparent 60%);
}
/* ── Design tokens — light mode ── */
@media(prefers-color-scheme:light){
  :root{
    --bg:#f5f7fa;--surface:#ffffff;--surface2:#eef1f6;
    --border:rgba(0,0,0,.10);
    --accent:#3a6be8;--accent2:#1aaf96;
    --accent-glow:rgba(58,107,232,.18);
    --accent-subtle:color-mix(in oklch,#3a6be8 12%,transparent);
    --text:#1a1d26;--text-dim:#5a6478;--heading:#0d1117;
    --header-grad:
      radial-gradient(ellipse 90% 55% at 50% -5%,rgba(58,107,232,.08) 0%,transparent 70%),
      radial-gradient(ellipse 45% 35% at 85% 110%,rgba(26,175,150,.06) 0%,transparent 60%);
  }
}
/* ── Manual theme overrides (localStorage) ── */
[data-theme="light"]{
  --bg:#f5f7fa;--surface:#ffffff;--surface2:#eef1f6;
  --border:rgba(0,0,0,.10);
  --accent:#3a6be8;--accent2:#1aaf96;
  --accent-glow:rgba(58,107,232,.18);
  --accent-subtle:color-mix(in oklch,#3a6be8 12%,transparent);
  --text:#1a1d26;--text-dim:#5a6478;--heading:#0d1117;
  --header-grad:
    radial-gradient(ellipse 90% 55% at 50% -5%,rgba(58,107,232,.08) 0%,transparent 70%),
    radial-gradient(ellipse 45% 35% at 85% 110%,rgba(26,175,150,.06) 0%,transparent 60%);
}
[data-theme="dark"]{
  --bg:#08090b;--surface:#111318;--surface2:#181d26;
  --border:rgba(255,255,255,.11);
  --accent:#6495f0;--accent2:#3ecfb2;
  --accent-glow:rgba(100,149,240,.22);
  --accent-subtle:color-mix(in oklch,#6495f0 18%,transparent);
  --text:#d4ddf2;--text-dim:#7088a8;--heading:#f2f5ff;
  --header-grad:
    radial-gradient(ellipse 90% 55% at 50% -5%,rgba(100,149,240,.14) 0%,transparent 70%),
    radial-gradient(ellipse 45% 35% at 85% 110%,rgba(62,207,178,.09) 0%,transparent 60%);
}
html{scroll-behavior:smooth}
body{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--text);line-height:1.6;font-size:15px;-webkit-font-smoothing:antialiased;transition:background .3s,color .3s}
:focus-visible{outline:2px solid var(--accent);outline-offset:3px;border-radius:var(--radius-sm)}
@media(prefers-reduced-motion:reduce){
  *,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important;scroll-behavior:auto!important}
}
@media(forced-colors:active){.card{border:1px solid CanvasText}.tag{border:1px solid CanvasText}}

/* ── Header ── */
.site-header{
  padding:5.5rem 2rem 4.5rem;text-align:center;
  position:relative;overflow:hidden;background:var(--bg);
}
.site-header::before{
  content:'';position:absolute;inset:0;
  background:var(--header-grad);
  pointer-events:none;
}
.theme-toggle{
  position:absolute;top:1.1rem;right:1.2rem;
  background:none;border:1px solid var(--border);
  border-radius:50%;width:2.1rem;height:2.1rem;
  font-size:1rem;line-height:1;cursor:pointer;
  color:var(--text-dim);display:flex;align-items:center;justify-content:center;
  transition:border-color .2s,color .2s;z-index:10;
}
.theme-toggle:hover{border-color:var(--accent);color:var(--accent)}
.site-eyebrow{
  font-size:.68rem;font-weight:600;letter-spacing:.24em;text-transform:uppercase;
  color:var(--accent2);margin-bottom:1.4rem;
  display:inline-flex;align-items:center;gap:.7rem;
}
.site-eyebrow::before,.site-eyebrow::after{
  content:'';display:block;width:32px;height:1px;background:currentColor;opacity:.45;
}
.site-title{
  font-family:'Playfair Display',Georgia,serif;
  font-size:clamp(2.8rem,6vw,4.4rem);font-weight:700;
  color:var(--heading);letter-spacing:-.025em;line-height:1.08;margin-bottom:1.5rem;
  text-wrap:balance;
}
.site-title--fiche{font-size:clamp(1.4rem,3vw,2.2rem)}
.site-subtitle{font-size:.88rem;color:var(--text-dim);max-width:460px;margin:0 auto 1.8rem;font-weight:400;line-height:1.75;text-wrap:balance}
.site-meta{font-size:.77rem;color:var(--text-dim);opacity:.65}
.site-meta a{color:var(--accent2);text-decoration:none;opacity:1}.site-meta a:hover{text-decoration:underline}

/* ── Wave ── */
.wave-sep{display:block;width:100%;height:1px;opacity:.3;
  background:linear-gradient(90deg,transparent 0%,var(--accent) 35%,var(--accent2) 65%,transparent 100%)}

/* ── Tags ── */
.card-tags{display:flex;flex-wrap:wrap;gap:.28rem}
.tag{
  font-size:.62rem;font-weight:600;padding:.18rem .58rem;
  border-radius:99px;letter-spacing:.05em;text-transform:uppercase;line-height:1.4;
}
.tag--topic{background:rgba(100,149,240,.11);color:#8ab4ff;border:1px solid rgba(100,149,240,.2)}
.tag--place{background:rgba(62,207,178,.09);color:var(--accent2);border:1px solid rgba(62,207,178,.18)}

/* ── Footer ── */
.site-footer{border-top:1px solid var(--border);padding:2.5rem 2rem;text-align:center;font-size:.77rem;color:var(--text-dim)}
.site-footer a{color:var(--accent2);text-decoration:none}.site-footer a:hover{text-decoration:underline}

/* ══ PORTFOLIO INDEX ══ */
.controls{
  position:sticky;top:0;z-index:100;
  background:rgba(8,9,11,.88);
  backdrop-filter:blur(24px) saturate(180%);-webkit-backdrop-filter:blur(24px) saturate(180%);
  border-bottom:1px solid var(--border);
}
.controls-inner{
  max-width:var(--max-w);margin:0 auto;
  display:flex;flex-wrap:wrap;align-items:center;gap:.75rem;padding:.85rem 2rem;
}
.search-wrap{flex:1 1 200px;position:relative}
.search-wrap::before{
  content:'⌕';position:absolute;left:.8rem;top:50%;transform:translateY(-52%);
  color:var(--text-dim);font-size:1rem;pointer-events:none;
}
#search{
  width:100%;background:var(--surface2);
  border:1px solid var(--border);border-radius:99px;
  padding:.4rem 1rem .4rem 2.3rem;
  color:var(--text);font-size:.82rem;font-family:inherit;
  outline:none;transition:border-color .2s,background .2s;
}
#search::placeholder{color:var(--text-dim)}
#search:focus{border-color:var(--accent);background:var(--surface)}
.filter-group{display:flex;flex-wrap:wrap;gap:.3rem;align-items:center}
.filter-group#year-filter-group{flex-wrap:nowrap;overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none;max-width:100%}
.filter-group#year-filter-group::-webkit-scrollbar{display:none}
.filter-label{font-size:.67rem;text-transform:uppercase;letter-spacing:.12em;color:var(--text-dim);margin-right:.1rem}
.filter-btn{
  font-family:inherit;font-size:.7rem;font-weight:500;
  padding:.27rem .64rem;border-radius:99px;
  border:1px solid var(--border);background:transparent;color:var(--text-dim);
  cursor:pointer;transition:all .15s;white-space:nowrap;
}
.filter-btn:hover{border-color:var(--accent);color:var(--accent)}
.filter-btn.active{background:var(--accent);border-color:var(--accent);color:#fff}
.cat-select{
  font-family:inherit;font-size:.74rem;padding:.33rem 2.1rem .33rem .8rem;
  border-radius:99px;border:1px solid var(--border);
  background:var(--surface2)
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%2358677f'/%3E%3C/svg%3E")
    no-repeat right .8rem center;
  color:var(--text);cursor:pointer;outline:none;
  -webkit-appearance:none;appearance:none;
  min-width:145px;transition:border-color .18s;
}
.cat-select:focus{border-color:var(--accent)}
.cat-select option{background:var(--surface2);color:var(--text)}

.counter{max-width:var(--max-w);margin:1.2rem auto .3rem;padding:0 2rem;font-size:.73rem;color:var(--text-dim);letter-spacing:.05em}

.grid{
  max-width:var(--max-w);margin:0 auto;padding:.4rem 2rem 5rem;
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(min(260px,100%),1fr));
  gap:1rem;
}
.card{
  background:var(--surface);border-radius:var(--radius);
  overflow:hidden;
  box-shadow:0 1px 3px rgba(0,0,0,.45),0 4px 18px rgba(0,0,0,.28);
  display:flex;flex-direction:column;
  text-decoration:none;color:inherit;
  transition:transform .3s cubic-bezier(.34,1.26,.64,1),box-shadow .3s ease,outline-color .15s;
  outline:1px solid transparent;
  contain:layout style paint;
  content-visibility:auto;
  contain-intrinsic-size:260px 320px;
}
.card:hover{
  transform:translateY(-6px) scale(1.012);
  box-shadow:0 0 0 1px var(--accent),0 12px 40px var(--accent-glow),0 24px 64px rgba(0,0,0,.45);
  outline-color:var(--accent);
}
.card.hidden{display:none}
.card-img{
  width:100%;aspect-ratio:1/1;overflow:hidden;
  background:var(--surface2);flex-shrink:0;
  position:relative;
}
.card-img img{width:100%;height:100%;object-fit:cover;transition:transform .55s cubic-bezier(.25,.46,.45,.94);display:block}
.card:hover .card-img img{transform:scale(1.06)}
.card-img::after{
  content:'';position:absolute;inset:0;
  background:linear-gradient(to top,rgba(0,0,0,.55) 0%,rgba(0,0,0,.1) 42%,transparent 70%);
  opacity:0;transition:opacity .35s;pointer-events:none;
}
.card:hover .card-img::after{opacity:1}
.card-img--placeholder{display:flex;align-items:center;justify-content:center;font-size:3rem;color:var(--border)}
.card-body{padding:.65rem .9rem .75rem;display:flex;flex-direction:column;gap:.3rem}
.card-meta{font-size:.6rem;text-transform:uppercase;letter-spacing:.1em;color:var(--text-dim);font-weight:500}
.card-title{font-family:'Playfair Display',Georgia,serif;font-size:.95rem;font-weight:700;color:var(--heading);line-height:1.25;text-wrap:balance}
#no-results{display:none;grid-column:1/-1;text-align:center;padding:4rem 2rem;color:var(--text-dim)}
#no-results p{font-size:1.1rem}
@keyframes card-reveal{from{opacity:0;transform:translateY(28px)}to{opacity:1;transform:translateY(0)}}
@supports(animation-timeline:view()){
  .card{animation:card-reveal .5s ease both;animation-timeline:view();animation-range:entry 5% entry 80%;}
}

/* ── Intro block ── */
.site-intro{background:var(--surface);border-bottom:1px solid var(--border);padding:1rem 2rem}
.site-intro-inner{max-width:var(--max-w);margin:0 auto;font-size:.79rem;color:var(--text-dim);line-height:1.8;display:flex;flex-wrap:wrap;gap:.15rem 3rem}
.site-intro-inner p{margin:0}
.site-intro-inner strong{color:var(--text)}
.site-intro-inner a{color:var(--accent2);text-decoration:none}.site-intro-inner a:hover{text-decoration:underline}

/* ══ FICHE PAGE ══ */
.fiche-nav{max-width:860px;margin:2rem auto 0;padding:0 2rem;display:flex;justify-content:space-between;align-items:center}
.fiche-nav-arrows{display:flex;gap:.6rem}
.nav-arrow{
  display:inline-flex;align-items:center;gap:.3rem;
  text-decoration:none;color:var(--accent);font-size:.82rem;font-weight:500;
  padding:.3rem .7rem;border:1px solid var(--border);border-radius:var(--radius-sm);
  background:var(--surface);transition:border-color .2s,background .2s;
}
.nav-arrow:hover{border-color:var(--accent);background:var(--surface2)}
.back-link{font-size:.8rem;color:var(--text-dim);text-decoration:none;display:inline-flex;align-items:center;gap:.4rem;transition:color .15s}
.back-link:hover{color:var(--accent)}

.fiche-hero{max-width:860px;margin:1.5rem auto 0;padding:0 2rem;position:relative}
.fiche-hero img{width:100%;border-radius:var(--radius);display:block;max-height:480px;object-fit:cover;cursor:zoom-in}
.lightbox-btn{
  position:absolute;bottom:1rem;right:2.6rem;
  background:rgba(8,9,11,.72);backdrop-filter:blur(10px);
  border:1px solid rgba(255,255,255,.14);color:#fff;border-radius:99px;
  padding:.33rem .9rem;font-size:.72rem;font-weight:500;cursor:pointer;
  transition:background .15s;display:inline-flex;align-items:center;gap:.35rem;letter-spacing:.03em;
}
.lightbox-btn:hover{background:rgba(8,9,11,.96)}
.lightbox{
  display:none;position:fixed;inset:0;z-index:9999;
  background:rgba(0,0,0,.96);align-items:center;justify-content:center;padding:2rem;
}
.lightbox.open{display:flex}
.lightbox>img{max-width:100%;max-height:90vh;object-fit:contain;border-radius:10px;box-shadow:0 8px 80px rgba(0,0,0,.8)}
.lightbox-close{
  position:absolute;top:1.2rem;right:1.5rem;background:none;border:none;
  color:#fff;font-size:1.8rem;cursor:pointer;line-height:1;opacity:.55;padding:.3rem .5rem;
  transition:opacity .15s;
}
.lightbox-close:hover{opacity:1}

.fiche-main{max-width:860px;margin:2rem auto 4rem;padding:0 2rem}
.fiche-header{margin-bottom:1.5rem}
.fiche-eyebrow{font-size:.68rem;letter-spacing:.2em;text-transform:uppercase;color:var(--accent2);font-weight:600;margin-bottom:.7rem}
.fiche-title{
  font-family:'Playfair Display',Georgia,serif;
  font-size:clamp(1.7rem,4vw,2.6rem);font-weight:700;
  color:var(--heading);line-height:1.2;margin-bottom:1.1rem;
  text-wrap:balance;
}
.fiche-tags{margin-bottom:1.3rem}
.fiche-visit{
  display:inline-flex;align-items:center;gap:.5rem;padding:.58rem 1.4rem;
  background:var(--accent);color:#fff;border-radius:99px;text-decoration:none;
  font-size:.82rem;font-weight:600;
  transition:background .18s,transform .18s,box-shadow .18s;
  margin-bottom:2rem;box-shadow:0 4px 20px var(--accent-glow);
}
.fiche-visit:hover{background:#5585e8;transform:translateY(-2px);box-shadow:0 8px 30px var(--accent-glow)}
.fiche-divider{border:none;border-top:1px solid var(--border);margin:2rem 0}

.fiche-content{font-size:.95rem;line-height:1.8;color:var(--text)}
.fiche-content p{margin-bottom:1em}
.fiche-content h2,.fiche-content h3,.fiche-content h4{
  font-family:'Playfair Display',Georgia,serif;color:var(--heading);margin:1.6em 0 .5em;line-height:1.3;
}
.fiche-content h2{font-size:1.4rem}.fiche-content h3{font-size:1.15rem}
.fiche-content a{color:var(--accent)}.fiche-content a:hover{color:var(--accent2)}
.fiche-content img{max-width:100%;border-radius:8px;display:block;margin:1.2em auto}
.fiche-content figure.wp-figure{margin:1.5em 0;text-align:center}
.fiche-content figure.wp-figure img{margin:0 auto .5em}
.fiche-content figcaption{font-size:.78rem;color:var(--text-dim);font-style:italic}
.fiche-content blockquote{border-left:3px solid var(--accent);padding:.6em 1.2em;margin:1em 0;color:var(--text-dim);font-style:italic}
.fiche-content ul,.fiche-content ol{padding-left:1.4em;margin-bottom:1em}
.fiche-content li{margin-bottom:.3em}
.fiche-content hr{border:none;border-top:1px solid var(--border);margin:1.5em 0}
.fiche-content strong{color:var(--heading)}
.fiche-content iframe,.fiche-content embed,.fiche-content video{max-width:100%;border-radius:8px}
.fiche-content .wp-block-embed,.fiche-content .video-container{position:relative;padding-bottom:56.25%;height:0;overflow:hidden;margin:1.2em 0}
.fiche-content .wp-block-embed iframe,.fiche-content .video-container iframe{position:absolute;top:0;left:0;width:100%;height:100%}
.fiche-notice{
  margin-top:2.5rem;padding:1rem 1.2rem;
  background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-sm);
  font-size:.78rem;color:var(--text-dim);font-style:italic;
}

/* ── Similar entries ── */
.similar-section{
  max-width:860px;margin:3rem auto 4rem;padding:0 2rem;
}
.similar-title{
  font-family:'Playfair Display',Georgia,serif;font-size:1.15rem;font-weight:700;
  color:var(--heading);margin-bottom:1.2rem;
}
.similar-grid{
  display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;
}
.similar-card{
  display:flex;flex-direction:column;text-decoration:none;color:inherit;
  border:1px solid var(--border);border-radius:var(--radius-sm);overflow:hidden;
  background:var(--surface);transition:border-color .2s,transform .22s;
}
.similar-card:hover{border-color:var(--accent);transform:translateY(-3px)}
.similar-img{width:100%;aspect-ratio:16/10;overflow:hidden;background:var(--surface2)}
.similar-img img{width:100%;height:100%;object-fit:cover}
.similar-img--placeholder{display:flex;align-items:center;justify-content:center;font-size:2rem;color:var(--text-dim);opacity:.35}
.similar-body{padding:.6rem .7rem}
.similar-card-title{font-size:.8rem;font-weight:600;color:var(--heading);line-height:1.3;margin-bottom:.3rem;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.similar-tags{display:flex;flex-wrap:wrap;gap:3px}

@media(max-width:900px){
  .grid{grid-template-columns:repeat(auto-fill,minmax(min(220px,100%),1fr));gap:.85rem}
  .site-header{padding:4rem 1.5rem 3.5rem}
  .fiche-hero img{max-height:360px}
}
@media(max-width:640px){
  .controls-inner{flex-direction:column;align-items:stretch}
  .search-wrap{flex:0 0 auto}
  .grid{padding:.5rem 1rem 3rem;grid-template-columns:repeat(auto-fill,minmax(min(155px,100%),1fr));gap:.65rem}
  .site-header{padding:3rem 1rem 2.5rem}
  .site-intro{padding:1rem 1rem}
  .fiche-main,.fiche-hero,.fiche-nav{padding:0 1rem}
  .similar-section{padding:0 1rem}
  .similar-grid{grid-template-columns:1fr}
  .fiche-hero img{max-height:280px}
  .cat-select{min-width:0;width:100%}
  .filter-btn{padding:.35rem .75rem;min-height:36px}
  .card-title{font-size:.82rem}
  .card-meta{font-size:.55rem}
  .tag{font-size:.55rem;padding:.14rem .45rem}
}
@media(max-width:400px){
  .grid{grid-template-columns:1fr 1fr;gap:.5rem;padding:.4rem .65rem 2.5rem}
  .card-body{padding:.5rem .65rem .6rem}
  .card-title{font-size:.75rem}
  .site-title{font-size:clamp(2rem,8vw,2.8rem)}
}

/* ── Submit card ── */
.card--submit{
  background:var(--surface);border:2px dashed rgba(100,149,240,.22);
  border-radius:var(--radius);overflow:hidden;display:flex;flex-direction:column;
  transition:transform .28s cubic-bezier(.34,1.26,.64,1),border-color .3s;
  text-decoration:none;color:inherit;
}
.card--submit:hover{transform:translateY(-7px) scale(1.015);border-color:var(--accent)}
.card--submit .card-img{
  width:100%;aspect-ratio:1/1;overflow:hidden;background:var(--surface2);flex-shrink:0;
  display:flex;align-items:center;justify-content:center;
}
.card--submit .card-img .submit-icon{font-size:4rem;color:var(--accent);opacity:.5;transition:opacity .3s,transform .4s}
.card--submit:hover .card-img .submit-icon{opacity:.9;transform:scale(1.15)}
.card--submit .card-body{padding:.8rem .95rem .9rem;display:flex;flex-direction:column;gap:.38rem}
.card--submit .card-title{font-family:'Playfair Display',Georgia,serif;font-size:.97rem;font-weight:700;color:var(--accent);line-height:1.3}
.card--submit .card-meta{font-size:.64rem;text-transform:uppercase;letter-spacing:.1em;color:var(--text-dim);font-weight:500}

/* ── Submit form page ── */
.submit-form{max-width:720px;margin:0 auto}
.form-group{margin-bottom:1.6rem}
.form-group label{display:block;font-size:.78rem;font-weight:600;color:var(--heading);letter-spacing:.06em;text-transform:uppercase;margin-bottom:.4rem}
.form-group .hint{font-size:.72rem;color:var(--text-dim);margin-bottom:.45rem;display:block}
.form-group input[type=text],.form-group input[type=url],.form-group textarea{
  width:100%;background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius-sm);
  padding:.55rem .85rem;color:var(--text);font-size:.88rem;font-family:inherit;outline:none;transition:border-color .2s;
}
.form-group input:focus,.form-group textarea:focus{border-color:var(--accent)}
.form-group textarea{min-height:160px;resize:vertical;line-height:1.65}
.form-group input::placeholder,.form-group textarea::placeholder{color:var(--text-dim);opacity:.6}
.submit-btn{
  display:inline-flex;align-items:center;gap:.5rem;padding:.65rem 1.8rem;
  background:var(--accent);color:#fff;border:none;border-radius:99px;cursor:pointer;
  font-size:.88rem;font-weight:600;font-family:inherit;
  transition:background .18s,transform .18s,box-shadow .18s;box-shadow:0 4px 20px var(--accent-glow);
}
.submit-btn:hover{background:color-mix(in oklch,var(--accent) 80%,white);transform:translateY(-2px);box-shadow:0 8px 30px var(--accent-glow)}
.form-note{margin-top:2rem;padding:1rem 1.2rem;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-sm);font-size:.78rem;color:var(--text-dim);line-height:1.7}
@media(prefers-color-scheme:light){
  .controls{background:rgba(245,247,250,.9)}
  .card{box-shadow:0 1px 4px rgba(0,0,0,.1),0 4px 18px rgba(0,0,0,.07)}
  .card:hover{box-shadow:0 0 0 1px var(--accent),0 10px 32px var(--accent-glow),0 20px 48px rgba(0,0,0,.1)}
}
[data-theme="light"] .controls{background:rgba(245,247,250,.9)}
[data-theme="light"] .card{box-shadow:0 1px 4px rgba(0,0,0,.1),0 4px 18px rgba(0,0,0,.07)}
[data-theme="light"] .card:hover{box-shadow:0 0 0 1px var(--accent),0 10px 32px var(--accent-glow),0 20px 48px rgba(0,0,0,.1)}
"""
# 6. WRITE portfolio.css
# ═══════════════════════════════════════════════════════════════
with open('portfolio.css','w',encoding='utf-8') as f: f.write(CSS)
print(f"portfolio.css  {os.path.getsize('portfolio.css'):,}B")

# ═══════════════════════════════════════════════════════════════
# 7. FICHE PAGES
# ═══════════════════════════════════════════════════════════════
os.makedirs('data', exist_ok=True)

# ── Export JSON ──
entries = []
for p in posts:
    entries.append({
        'slug':      p['slug'],
        'title':     p['title'],
        'date':      p['date'],
        'year':      p['year'],
        'ext_url':   p['ext_url'],
        'local_img': p['local_img'],
        'topics':    p['topics'],
        'places':    p['places'],
        'tags':      p['tags'],
        'excerpt':   p['excerpt'],
        'body':      clean_content(p['body_raw'], prefix=''),
    })

with open('data/entries.json', 'w', encoding='utf-8') as f:
    json.dump(entries, f, ensure_ascii=False, indent=2)
print(f"data/entries.json  {len(entries)} entries, {os.path.getsize('data/entries.json'):,}B")

# ── Single fiche.html template ──
fiche_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title id="page-title">Sound Cartography</title>
  <meta name="description" id="page-desc" content="">
  {GFONTS}
  <link rel="stylesheet" href="portfolio.css">
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <script>(function(){{var t=localStorage.getItem('theme');if(t)document.documentElement.setAttribute('data-theme',t);}})();</script>
{ANALYTICS}
</head>
<body>

<header class="site-header">
  <button class="theme-toggle" id="theme-toggle" aria-label="Toggle light/dark mode" title="Toggle light/dark mode">&#9728;</button>
  <p class="site-eyebrow">Sound Cartography &mdash; Catalogue entry</p>
  <h1 class="site-title site-title--fiche" id="entry-title"></h1>
  <p class="site-meta"><a href="index.html">&larr; Back to catalogue</a></p>
</header>
<span class="wave-sep"></span>

<nav class="fiche-nav">
  <a class="back-link" href="index.html">&larr; All entries</a>
  <div class="fiche-nav-arrows" id="nav-arrows"></div>
</nav>
<div id="hero-zone"></div>

<article class="fiche-main">
  <header class="fiche-header">
    <p class="fiche-eyebrow" id="entry-date"></p>
    <h2 class="fiche-title" id="entry-title2"></h2>
    <div class="fiche-tags card-tags" id="entry-tags"></div>
    <a class="fiche-visit" id="entry-link" target="_blank" rel="noopener"></a>
  </header>
  <hr class="fiche-divider">
  <div class="fiche-content" id="entry-body"></div>
  <div class="fiche-notice">
    Catalogue entry compiled by Pierre Aumond (curator).
    Content sourced from the original project&#8217;s website &mdash; not authored by the curator.
  </div>
</article>

<section class="similar-section" id="similar-section" style="display:none">
  <h3 class="similar-title">Similar projects</h3>
  <div class="similar-grid" id="similar-grid"></div>
</section>

{FOOTER_HTML}
<script>
(function() {{
  function escH(s) {{
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }}
  var params = new URLSearchParams(location.search);
  var slug = params.get('slug');
  if (!slug) {{ document.getElementById('entry-title').textContent = 'Entry not found'; return; }}
  fetch('data/entries.json')
    .then(function(r) {{ return r.json(); }})
    .then(function(entries) {{
      var entry = entries.find(function(e) {{ return e.slug === slug; }});
      if (!entry) {{ document.getElementById('entry-title').textContent = 'Entry not found'; return; }}
      document.title = entry.title + ' \u2014 Sound Cartography';
      document.getElementById('page-desc').setAttribute('content', entry.excerpt.slice(0,160));
      document.getElementById('entry-title').textContent  = entry.title;
      document.getElementById('entry-title2').textContent = entry.title;
      document.getElementById('entry-date').textContent   = entry.date;
      // Hero image + lightbox
      if (entry.local_img) {{
        document.getElementById('hero-zone').innerHTML =
          '<div class="fiche-hero">'+
          '<img src="'+entry.local_img+'" alt="'+escH(entry.title)+'" class="hero-img">'+
          '<button class="lightbox-btn" aria-label="View full size">&#x26F6; Full size</button>'+
          '</div>'+
          '<div class="lightbox" id="lb" role="dialog" aria-modal="true">'+
          '<button class="lightbox-close" aria-label="Close">&times;</button>'+
          '<img src="'+entry.local_img+'" alt="'+escH(entry.title)+'">'+
          '</div>';
        var lb = document.getElementById('lb');
        document.querySelector('.hero-img').addEventListener('click',     function(){{lb.classList.add('open')}});
        document.querySelector('.lightbox-btn').addEventListener('click',  function(){{lb.classList.add('open')}});
        document.querySelector('.lightbox-close').addEventListener('click',function(){{lb.classList.remove('open')}});
        lb.addEventListener('click', function(e){{if(e.target===lb)lb.classList.remove('open')}});
        document.addEventListener('keydown', function(e){{if(e.key==='Escape')lb.classList.remove('open')}});
      }}
      // Tags
      var tags = entry.topics.map(function(t){{
        return '<span class="tag tag--topic">'+escH(t)+'</span>';
      }}).concat(entry.places.map(function(p){{
        return '<span class="tag tag--place">&#128205; '+escH(p)+'</span>';
      }}));
      document.getElementById('entry-tags').innerHTML = tags.join('');
      // Visit link
      var lk = document.getElementById('entry-link');
      if (entry.ext_url && entry.ext_url !== '#') {{
        var domain = entry.ext_url.split('/')[2] || entry.ext_url;
        lk.href = entry.ext_url;
        lk.textContent = 'Visit project: '+domain+' \u2197';
      }} else {{ lk.style.display='none'; }}
      // Body
      document.getElementById('entry-body').innerHTML = entry.body;

      // ── Prev / Next navigation (top bar) ──
      var idx = entries.indexOf(entry);
      var arrows = document.getElementById('nav-arrows');
      var ah = '';
      if (idx > 0) {{
        var prev = entries[idx - 1];
        ah += '<a class="nav-arrow" href="fiche.html?slug='+encodeURIComponent(prev.slug)+'" title="'+escH(prev.title)+'">&larr; Prev</a>';
      }}
      if (idx < entries.length - 1) {{
        var next = entries[idx + 1];
        ah += '<a class="nav-arrow" href="fiche.html?slug='+encodeURIComponent(next.slug)+'" title="'+escH(next.title)+'">Next &rarr;</a>';
      }}
      arrows.innerHTML = ah;

      // ── Keyboard arrow navigation ──
      var prevUrl = idx > 0 ? 'fiche.html?slug='+encodeURIComponent(entries[idx-1].slug) : null;
      var nextUrl = idx < entries.length-1 ? 'fiche.html?slug='+encodeURIComponent(entries[idx+1].slug) : null;
      document.addEventListener('keydown', function(e) {{
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        if (e.key === 'ArrowLeft'  && prevUrl) window.location.href = prevUrl;
        if (e.key === 'ArrowRight' && nextUrl) window.location.href = nextUrl;
      }});

      // ── Swipe navigation (touch) ──
      var touchStartX = null;
      document.addEventListener('touchstart', function(e) {{
        if (e.touches.length === 1) touchStartX = e.touches[0].clientX;
      }}, {{passive:true}});
      document.addEventListener('touchend', function(e) {{
        if (touchStartX === null) return;
        var dx = e.changedTouches[0].clientX - touchStartX;
        touchStartX = null;
        if (Math.abs(dx) < 60) return;
        if (dx > 0 && prevUrl) window.location.href = prevUrl;
        if (dx < 0 && nextUrl) window.location.href = nextUrl;
      }});

      // ── Similar entries (by shared topics) ──
      var scored = entries.filter(function(e2){{ return e2.slug !== entry.slug; }}).map(function(e2){{
        var shared = 0;
        entry.topics.forEach(function(t){{ if(e2.topics.indexOf(t)!==-1) shared++; }});
        return {{entry:e2, score:shared}};
      }}).filter(function(s){{ return s.score > 0; }});
      scored.sort(function(a,b){{ return b.score - a.score || a.entry.title.localeCompare(b.entry.title); }});
      var top3 = scored.slice(0, 3);
      if (top3.length) {{
        document.getElementById('similar-section').style.display = '';
        var gridHtml = top3.map(function(s){{
          var e2 = s.entry;
          var imgH = e2.local_img
            ? '<div class="similar-img"><img src="'+escH(e2.local_img)+'" alt="'+escH(e2.title)+'" loading="lazy"></div>'
            : '<div class="similar-img similar-img--placeholder"><span>\u266A</span></div>';
          var sharedTopics = entry.topics.filter(function(t){{ return e2.topics.indexOf(t)!==-1; }}).slice(0,2);
          var tagsH = sharedTopics.map(function(t){{ return '<span class="tag tag--topic" style="font-size:.62rem">'+escH(t)+'</span>'; }}).join('');
          return '<a class="similar-card" href="fiche.html?slug='+encodeURIComponent(e2.slug)+'">' +
            imgH +
            '<div class="similar-body">' +
            '<div class="similar-card-title">'+escH(e2.title)+'</div>' +
            (tagsH ? '<div class="similar-tags">'+tagsH+'</div>' : '') +
            '</div></a>';
        }}).join('');
        document.getElementById('similar-grid').innerHTML = gridHtml;
      }}
    }});
}})();
</script>
<script>(function(){{var root=document.documentElement;var btn=document.getElementById('theme-toggle');function isDark(){{var t=root.getAttribute('data-theme');return t?t==='dark':!window.matchMedia('(prefers-color-scheme:light)').matches;}}function sync(){{btn.textContent=isDark()?'\u2600':'\u263D';}}btn.addEventListener('click',function(){{var n=isDark()?'light':'dark';root.setAttribute('data-theme',n);localStorage.setItem('theme',n);sync();}});sync();}})();</script>
</body>
</html>"""

with open('fiche.html','w',encoding='utf-8') as f: f.write(fiche_template)
print(f"fiche.html     {os.path.getsize('fiche.html'):,}B  (single template)")

# ═══════════════════════════════════════════════════════════════
# 7b. SUBMIT PAGE
# ═══════════════════════════════════════════════════════════════
SUBMIT_EMAIL = 'pierre.aumond@univ-eiffel.fr'
submit_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Submit an entry \u2014 Sound Cartography</title>
  <meta name="description" content="Propose a sound map project for the Sound Cartography catalogue.">
  {GFONTS}
  <link rel="stylesheet" href="../portfolio.css">
  <link rel="icon" href="../favicon.svg" type="image/svg+xml">
  <script>(function(){{var t=localStorage.getItem('theme');if(t)document.documentElement.setAttribute('data-theme',t);}})();</script>
{ANALYTICS}
</head>
<body>

<header class="site-header">
  <button class="theme-toggle" id="theme-toggle" aria-label="Toggle light/dark mode" title="Toggle light/dark mode">&#9728;</button>
  <p class="site-eyebrow">Sound Cartography</p>
  <h1 class="site-title site-title--fiche">Submit an entry</h1>
  <p class="site-meta"><a href="../index.html">\u2190 Back to catalogue</a></p>
</header>
<span class="wave-sep"></span>

<nav class="fiche-nav"><a class="back-link" href="../index.html">\u2190 All entries</a></nav>

<article class="fiche-main">
  <div class="submit-form">
    <p style="color:var(--text-dim);font-size:.9rem;line-height:1.7;margin-bottom:2rem">
      Know a sound map that should be in this catalogue? Fill in the fields below and click
      <strong style="color:var(--heading)">Send via email</strong>.
      Your mail client will open with all the information pre-filled \u2014
      just attach the image and hit send.
    </p>

    <div class="form-group">
      <label for="f-title">Project title *</label>
      <input type="text" id="f-title" placeholder="e.g. Cities and Memory" required>
    </div>

    <div class="form-group">
      <label for="f-url">Project URL *</label>
      <input type="url" id="f-url" placeholder="https://..." required>
    </div>

    <div class="form-group">
      <label for="f-desc">Description *</label>
      <span class="hint">A short text about the project (2\u20135 sentences). This will appear on the catalogue entry.</span>
      <textarea id="f-desc" placeholder="Describe the project: what is it, who made it, what does it map\u2026"></textarea>
    </div>

    <div class="form-group">
      <label for="f-cats">Categories / tags</label>
      <span class="hint">Comma-separated \u2014 e.g. noise, soundscape, France, Europe</span>
      <input type="text" id="f-cats" placeholder="sound map, participatory, France">
    </div>

    <div class="form-group">
      <label>Image</label>
      <span class="hint">
        Please prepare a square image of the project (1\u202f000\u00a0\u00d7\u00a01\u202f000\u00a0px, JPG or PNG).
        You will be asked to <strong style="color:var(--heading)">attach it to the email</strong> after clicking the button.
      </span>
    </div>

    <button class="submit-btn" id="send-btn">Send via email \u2709</button>

    <div class="form-note">
      <strong style="color:var(--heading)">How it works:</strong>
      Clicking the button opens your default mail client with the information pre-filled.
      Don\u2019t forget to <strong style="color:var(--heading)">attach the image</strong> (1\u202f000\u00a0\u00d7\u00a01\u202f000\u00a0px)
      before sending. Your submission will be reviewed and added to the catalogue.
    </div>
  </div>
</article>

{FOOTER_HTML}
<script>
(function(){{{{
  document.getElementById('send-btn').addEventListener('click', function() {{{{
    var title = document.getElementById('f-title').value.trim();
    var url   = document.getElementById('f-url').value.trim();
    var desc  = document.getElementById('f-desc').value.trim();
    var cats  = document.getElementById('f-cats').value.trim();
    if (!title || !url || !desc) {{{{
      alert('Please fill in the title, URL and description.');
      return;
    }}}}
    var nl = '\\n';
    var body = 'PROJECT TITLE: ' + title + nl + nl
             + 'URL: ' + url + nl + nl
             + 'DESCRIPTION:' + nl + desc + nl + nl
             + 'CATEGORIES: ' + (cats || '(none)') + nl + nl
             + '---' + nl
             + 'Please attach the image (1000x1000 px) to this email.';
    var subject = 'Sound Cartography \u2014 New entry: ' + title;
    window.location.href = 'mailto:{SUBMIT_EMAIL}'
      + '?subject=' + encodeURIComponent(subject)
      + '&body=' + encodeURIComponent(body);
  }}}});
}}}})();
</script>
<script>(function(){{var root=document.documentElement;var btn=document.getElementById('theme-toggle');function isDark(){{var t=root.getAttribute('data-theme');return t?t==='dark':!window.matchMedia('(prefers-color-scheme:light)').matches;}}function sync(){{btn.textContent=isDark()?'\u2600':'\u263D';}}btn.addEventListener('click',function(){{var n=isDark()?'light':'dark';root.setAttribute('data-theme',n);localStorage.setItem('theme',n);sync();}});sync();}})();</script>
</body>
</html>"""

with open('fiches/submit.html','w',encoding='utf-8') as f: f.write(submit_page)
print("fiches/submit.html written")

# ═══════════════════════════════════════════════════════════════
# 8. index.html
# ═══════════════════════════════════════════════════════════════
idx_canonical = f"{SITE_URL}/index.html"
idx_desc      = ('A curated catalogue of sound maps and related projects '
                 'from around the world. Compiled by Pierre Aumond.')
idx_jsonld    = json.dumps({
    '@context':     'https://schema.org',
    '@type':        'CollectionPage',
    'name':         'Sound Cartography \u2014 Catalogue of Sound Maps',
    'description':  idx_desc,
    'url':          idx_canonical,
    'author':       {'@type': 'Person', 'name': 'Pierre Aumond'},
    'numberOfItems': len(posts),
}, ensure_ascii=False, separators=(',', ':'))
idx_seo = head_seo('Sound Cartography \u2014 Catalogue of Sound Maps',
                   idx_desc, idx_canonical, f'{SITE_URL}/media/sow.png', idx_jsonld)

portfolio = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sound Cartography — Catalogue of Sound Maps</title>
  <meta name="description" content="A curated catalogue of sound maps and related projects from around the world. Compiled by Pierre Aumond.">
  {GFONTS}
  <link rel="stylesheet" href="portfolio.css">
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <script>(function(){{var t=localStorage.getItem('theme');if(t)document.documentElement.setAttribute('data-theme',t);}})();</script>
{ANALYTICS}
{idx_seo}
</head>
<body>
<header class="site-header">
  <button class="theme-toggle" id="theme-toggle" aria-label="Toggle light/dark mode" title="Toggle light/dark mode">&#9728;</button>
  <p class="site-eyebrow">Curated catalogue</p>
  <h1 class="site-title">Sound Cartography</h1>
  <p class="site-subtitle">A catalogue of sound maps and sonic geography projects from around the world —
    compiled by <strong>Pierre Aumond</strong>.</p>
  <p class="site-meta" id="header-count">Loading…&nbsp;·&nbsp; 2015–2026</p>
  <p style="margin-top:1.2rem"><a href="constellation.html" style="display:inline-block;padding:.5rem 1.4rem;background:var(--accent);color:var(--bg);border-radius:24px;font-size:.85rem;font-weight:600;text-decoration:none;letter-spacing:.02em;box-shadow:0 0 18px var(--accent-glow);transition:transform .2s,box-shadow .2s" onmouseover="this.style.transform='scale(1.06)';this.style.boxShadow='0 0 28px var(--accent-glow)'" onmouseout="this.style.transform='scale(1)';this.style.boxShadow='0 0 18px var(--accent-glow)'">✦ Explore the Constellation view</a></p>
</header>
<span class="wave-sep"></span>

<section class="site-intro">
  <div class="site-intro-inner">
    <p>This catalogue gathers sound cartography projects selected since 2015.
    Texts, images and content <strong>come from the creators of each project</strong>
    &#8212; artists, researchers, sound collectives. This site is solely a curation and collection effort.</p>
  </div>
</section>

<div class="controls">
  <div class="controls-inner">
    <div class="search-wrap">
      <input type="search" id="search" placeholder="Search by title or description…" autocomplete="off">
    </div>
    <div class="filter-group" id="year-filter-group">
      <span class="filter-label">Year</span>
      <button class="filter-btn active" data-filter="all" data-type="year">All</button>
    </div>
    <div class="filter-group">
      <span class="filter-label">Topic</span>
      <select class="cat-select" id="topic-select">
        <option value="all">All topics</option>
      </select>
    </div>
    <div class="filter-group">
      <span class="filter-label">Place</span>
      <select class="cat-select" id="place-select">
        <option value="all">All places</option>
      </select>
    </div>
  </div>
</div>

<p class="counter" id="counter">Loading entries…</p>
<main>
  <div class="grid" id="grid">
    <a class="card card--submit" href="fiches/submit.html"
       data-year="all" data-topic="" data-place="">
      <div class="card-img"><span class="submit-icon">+</span></div>
      <div class="card-body">
        <div class="card-meta">Community</div>
        <h2 class="card-title">Submit an entry</h2>
      </div>
    </a>
    <div id="no-results" style="display:none"><p>No entries match your search.</p></div>
  </div>
</main>

{FOOTER_HTML}
<script>
(function(){{
  function sl(s){{return String(s).toLowerCase().replace(/ /g,'-').replace(/\\//g,'-');}}
  function escH(s){{return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}}

  var counter=document.getElementById('counter');
  var headerCount=document.getElementById('header-count');
  var noRes=document.getElementById('no-results');
  var grid=document.getElementById('grid');
  var yrGroup=document.getElementById('year-filter-group');
  var topicSel=document.getElementById('topic-select');
  var placeSel=document.getElementById('place-select');
  var aYear='all',aTopic='all',aPlace='all',sTerm='';
  var allCards=[];

  function apply(){{
    var v=0;
    allCards.forEach(function(c){{
      var ok=(aYear==='all'||c.dataset.year===aYear)
           &&(aTopic==='all'||c.dataset.topic.split(' ').includes(aTopic))
           &&(aPlace==='all'||c.dataset.place.split(' ').includes(aPlace))
           &&(!sTerm||c.textContent.toLowerCase().includes(sTerm));
      c.classList.toggle('hidden',!ok);if(ok)v++;
    }});
    counter.textContent=v+(v===1?' entry':' entries');
    noRes.style.display=v===0?'block':'none';
  }}

  fetch('data/entries.json')
    .then(function(r){{return r.json();}})
    .then(function(entries){{
      // Build filter option sets
      var years=[],topicMap={{}},placeMap={{}};
      entries.forEach(function(e){{
        if(e.year&&e.year!=='—'&&!years.includes(e.year))years.push(e.year);
        e.topics.forEach(function(t){{topicMap[t]=(topicMap[t]||0)+1;}});
        e.places.forEach(function(p){{placeMap[p]=(placeMap[p]||0)+1;}});
      }});
      years.sort(function(a,b){{return b-a;}});

      // Year buttons
      years.forEach(function(y){{
        var btn=document.createElement('button');
        btn.className='filter-btn';btn.dataset.filter=y;btn.dataset.type='year';
        btn.textContent=y;yrGroup.appendChild(btn);
      }});

      // Topic select
      Object.keys(topicMap).sort(function(a,b){{return a.toLowerCase().localeCompare(b.toLowerCase());}})
        .forEach(function(t){{
          var o=document.createElement('option');
          o.value=sl(t);o.textContent=t+' ('+topicMap[t]+')';topicSel.appendChild(o);
        }});

      // Place select
      Object.keys(placeMap).sort(function(a,b){{return a.toLowerCase().localeCompare(b.toLowerCase());}})
        .forEach(function(p){{
          var o=document.createElement('option');
          o.value=sl(p);o.textContent=p+' ('+placeMap[p]+')';placeSel.appendChild(o);
        }});

      // Render cards
      var frag=document.createDocumentFragment();
      entries.forEach(function(e){{
        var imgHtml=e.local_img
          ?'<div class="card-img"><img src="'+escH(e.local_img)+'" alt="'+escH(e.title)+'" loading="lazy"></div>'
          :'<div class="card-img card-img--placeholder"><span>\u266a</span></div>';
        var allTags=e.topics.map(function(t){{return {{label:t,kind:'topic'}}}})
                    .concat(e.places.map(function(p){{return {{label:p,kind:'place'}}}}))
                    .slice(0,3);
        var tagsHtml=allTags.map(function(tg){{
          return '<span class="tag tag--'+tg.kind+'">'+(tg.kind==='place'?'\U0001F4CD ':'')+escH(tg.label)+'</span>';
        }}).join('');
        var card=document.createElement('a');
        card.className='card';
        card.href='fiche.html?slug='+encodeURIComponent(e.slug);
        card.dataset.year=e.year;
        card.dataset.topic=e.topics.map(sl).join(' ');
        card.dataset.place=e.places.map(sl).join(' ');
        card.innerHTML=imgHtml
          +'<div class="card-body">'
            +'<div class="card-meta">'+escH(e.date)+'</div>'
            +'<h2 class="card-title">'+escH(e.title)+'</h2>'
            +(tagsHtml?'<div class="card-tags">'+tagsHtml+'</div>':'')
          +'</div>';
        frag.appendChild(card);
        allCards.push(card);
      }});
      // Insert cards before the no-results sentinel
      grid.insertBefore(frag,noRes);

      // Update header + counter
      var n=entries.length;
      counter.textContent=n+' entries';
      headerCount.innerHTML=n+' entries&nbsp;&middot;&nbsp; 2015\u20132026';

      // Attach events after DOM is ready
      document.querySelectorAll('[data-type="year"]').forEach(function(b){{
        b.addEventListener('click',function(){{
          document.querySelectorAll('[data-type="year"]').forEach(function(x){{x.classList.remove('active');}});
          b.classList.add('active');aYear=b.dataset.filter;apply();
        }});
      }});
      topicSel.addEventListener('change',function(e){{aTopic=e.target.value;apply();}});
      placeSel.addEventListener('change',function(e){{aPlace=e.target.value;apply();}});
      var t;document.getElementById('search').addEventListener('input',function(e){{
        clearTimeout(t);t=setTimeout(function(){{sTerm=e.target.value.toLowerCase().trim();apply();}},180);
      }});
    }})
    .catch(function(){{counter.textContent='Error loading entries.';}});
}})();
</script>
<script>(function(){{var root=document.documentElement;var btn=document.getElementById('theme-toggle');function isDark(){{var t=root.getAttribute('data-theme');return t?t==='dark':!window.matchMedia('(prefers-color-scheme:light)').matches;}}function sync(){{btn.textContent=isDark()?'\u2600':'\u263D';}}btn.addEventListener('click',function(){{var n=isDark()?'light':'dark';root.setAttribute('data-theme',n);localStorage.setItem('theme',n);sync();}});sync();}})();</script>
</body>
</html>"""

with open('index.html','w',encoding='utf-8') as f: f.write(portfolio)
print(f"index.html {os.path.getsize('index.html'):,}B")

# ═══════════════════════════════════════════════════════════════
# 9. SITEMAP
# ═══════════════════════════════════════════════════════════════
today = datetime.utcnow().strftime('%Y-%m-%d')
sm = ['<?xml version="1.0" encoding="UTF-8"?>',
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
      f'  <url><loc>{SITE_URL}/index.html</loc>'
      f'<lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>1.0</priority></url>']
sm.append(f'  <url><loc>{SITE_URL}/fiches/submit.html</loc>'
          f'<lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.5</priority></url>')
sm.append(f'  <url><loc>{SITE_URL}/constellation.html</loc>'
          f'<lastmod>{today}</lastmod><changefreq>monthly</changefreq><priority>0.8</priority></url>')
for p in posts:
    sm.append(f'  <url><loc>{SITE_URL}/fiche.html?slug={p["slug"]}</loc>'
              f'<lastmod>{p["raw_date"]}</lastmod><changefreq>yearly</changefreq><priority>0.8</priority></url>')
sm.append('</urlset>')
with open('sitemap.xml','w',encoding='utf-8') as f: f.write('\n'.join(sm))
print(f"sitemap.xml    {os.path.getsize('sitemap.xml'):,}B")
