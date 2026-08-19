#!/usr/bin/env python3
"""
Builds the static artifact site from data/videos.json and data/artifacts.json.

Run:  python3 build.py
Out:  _site/   (index.html, v/<slug>/index.html, artifacts/, thumbs/)

You normally never run this by hand -- GitHub Actions runs it on every push.
"""

import json
import re
import shutil
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
ARTIFACT_SRC = ROOT / "artifacts"
OUT = ROOT / "_site"

THUMB_WIDTH = 480
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tif", ".tiff", ".bmp"}
PDF_EXT = {".pdf"}

errors = []
warnings = []


# ---------------------------------------------------------------- data loading

def load_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        sys.exit(f"ERROR: {path.name} is missing from the data/ folder.")
    except json.JSONDecodeError as exc:
        sys.exit(
            f"ERROR: {path.name} is not valid JSON.\n"
            f"  {exc.msg} at line {exc.lineno}, column {exc.colno}.\n"
            f"  Most often this is a missing comma between entries, or a "
            f"trailing comma after the last one."
        )


def strip_comments(obj):
    """Remove _comment keys so they never render."""
    if isinstance(obj, dict):
        return {k: strip_comments(v) for k, v in obj.items() if k != "_comment"}
    if isinstance(obj, list):
        return [strip_comments(v) for v in obj]
    return obj


# ---------------------------------------------------------------- thumbnails

def make_thumb(src: Path, dest_stem: Path):
    """Render a thumbnail. Returns the output filename, or None if not possible."""
    ext = src.suffix.lower()
    try:
        if ext in IMAGE_EXT:
            from PIL import Image
            with Image.open(src) as im:
                im = im.convert("RGB")
                ratio = THUMB_WIDTH / im.width
                if ratio < 1:
                    im = im.resize(
                        (THUMB_WIDTH, max(1, round(im.height * ratio))),
                        Image.LANCZOS,
                    )
                out = dest_stem.with_suffix(".jpg")
                out.parent.mkdir(parents=True, exist_ok=True)
                im.save(out, "JPEG", quality=82, optimize=True)
                return out.name
        if ext in PDF_EXT:
            import pymupdf
            with pymupdf.open(src) as doc:
                if not doc.page_count:
                    return None
                page = doc.load_page(0)
                zoom = THUMB_WIDTH / page.rect.width if page.rect.width else 1
                pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
                out = dest_stem.with_suffix(".jpg")
                out.parent.mkdir(parents=True, exist_ok=True)
                pix.save(out)
                return out.name
    except Exception as exc:  # a broken file should not kill the whole build
        warnings.append(f"could not thumbnail {src.name}: {exc}")
    return None


def kind_of(path: Path):
    ext = path.suffix.lower()
    if ext in PDF_EXT:
        return "PDF"
    if ext in IMAGE_EXT:
        return "Image"
    return ext.lstrip(".").upper() or "File"


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:,.1f} {unit}"
        n /= 1024


# ---------------------------------------------------------------- html pieces

CSS = """
*,*::before,*::after{box-sizing:border-box}
:root{
  --bg:#ffffff; --fg:#16181d; --muted:#5f6672; --line:#e4e7ec;
  --accent:#1f5fd8; --card:#ffffff; --shadow:0 1px 2px rgba(16,24,40,.05),0 4px 14px rgba(16,24,40,.06);
}
@media (prefers-color-scheme:dark){
  :root{--bg:#0f1115;--fg:#e8eaed;--muted:#9aa2b1;--line:#252a33;
        --accent:#7aa7ff;--card:#161a21;--shadow:0 1px 2px rgba(0,0,0,.4)}
}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);
  font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased}
.wrap{max-width:940px;margin:0 auto;padding:40px 20px 72px}
a{color:var(--accent)}
header.site{border-bottom:1px solid var(--line);padding-bottom:24px;margin-bottom:32px}
h1{font-size:1.75rem;line-height:1.25;margin:0 0 8px;letter-spacing:-.02em}
.sub{color:var(--muted);margin:0}
.back{display:inline-block;font-size:.875rem;color:var(--muted);
  text-decoration:none;margin-bottom:20px}
.back:hover{color:var(--accent)}
.watch{display:inline-flex;align-items:center;gap:7px;margin-top:14px;
  font-size:.875rem;font-weight:500;text-decoration:none;color:var(--accent)}
.watch:hover{text-decoration:underline}
.count{color:var(--muted);font-size:.8125rem;margin:0 0 18px;
  text-transform:uppercase;letter-spacing:.06em;font-weight:600}
.grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fill,minmax(270px,1fr))}
.card{display:flex;flex-direction:column;background:var(--card);border:1px solid var(--line);
  border-radius:12px;overflow:hidden;text-decoration:none;color:inherit;
  box-shadow:var(--shadow);transition:transform .15s ease,box-shadow .15s ease,border-color .15s ease}
.card:hover{transform:translateY(-2px);border-color:var(--accent);
  box-shadow:0 4px 10px rgba(16,24,40,.09),0 12px 28px rgba(16,24,40,.10)}
.card:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.thumb-wrap{position:relative}
.thumb{aspect-ratio:4/3;background:#f2f4f7 center/cover no-repeat;
  border-bottom:1px solid var(--line)}
@media (prefers-color-scheme:dark){.thumb{background-color:#1d222b}}
.thumb.pdf{background-size:cover;background-position:top center}
.noimg{display:flex;align-items:center;justify-content:center;height:100%;
  color:var(--muted);font-size:.8125rem;font-weight:600;letter-spacing:.04em}
.badge{position:absolute;top:9px;left:9px;background:rgba(16,24,40,.82);color:#fff;
  font-size:.6875rem;font-weight:600;letter-spacing:.05em;padding:3px 8px;border-radius:5px}
.meta{padding:14px 16px 16px}
.t{font-weight:600;line-height:1.35;margin:0 0 5px}
.s{color:var(--muted);font-size:.875rem;margin:0}
.also{color:var(--muted);font-size:.75rem;margin:8px 0 0;font-style:italic}
ul.videos{list-style:none;padding:0;margin:0;border-top:1px solid var(--line)}
ul.videos li{border-bottom:1px solid var(--line)}
ul.videos a{display:block;padding:18px 4px;text-decoration:none;color:inherit}
ul.videos a:hover .t{color:var(--accent)}
footer{margin-top:56px;padding-top:22px;border-top:1px solid var(--line);
  color:var(--muted);font-size:.8125rem}
.empty{color:var(--muted);font-style:italic}
"""


def page(title, body, depth):
    """depth = how many folders deep this page sits, for relative asset paths."""
    up = "../" * depth
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title>
<meta name="robots" content="index,follow">
<link rel="stylesheet" href="{up}style.css">
</head>
<body>
<div class="wrap">
{body}
</div>
</body>
</html>
"""


def card_html(art, up):
    """One artifact card. Links straight at the file so it opens in a tab."""
    href = f"{up}artifacts/{art['file']}"
    if art.get("thumb"):
        style = f"background-image:url('{up}thumbs/{art['thumb']}')"
        thumb = f'<div class="thumb {art["kind"].lower()}" style="{style}"></div>'
    else:
        thumb = (
            f'<div class="thumb"><div class="noimg">{escape(art["kind"])}</div></div>'
        )
    line = " &middot; ".join(
        escape(str(art[k])) for k in ("source", "date") if art.get(k)
    )
    also = ""
    if art.get("also_in"):
        names = ", ".join(escape(n) for n in art["also_in"])
        also = f'<p class="also">Also appears with: {names}</p>'
    return f"""<a class="card" href="{href}" target="_blank" rel="noopener">
  <div class="thumb-wrap">{thumb}<span class="badge">{escape(art['kind'])}</span></div>
  <div class="meta">
    <p class="t">{escape(art['title'])}</p>
    <p class="s">{line}</p>
    {also}
  </div>
</a>"""


# ---------------------------------------------------------------- build

def main():
    videos_data = strip_comments(load_json(DATA / "videos.json"))
    artifacts = strip_comments(load_json(DATA / "artifacts.json"))

    site = videos_data.get("site", {})
    videos = videos_data.get("videos", [])
    site_title = site.get("title", "Video Archive")

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    (OUT / "style.css").write_text(CSS.strip() + "\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    # Which videos reference each artifact -- powers the "also appears with" note.
    used_by = {}
    for v in videos:
        for aid in v.get("artifacts", []):
            used_by.setdefault(aid, []).append(v.get("title", v.get("slug", "?")))

    # Resolve every artifact once: copy the file, build one thumbnail.
    resolved = {}
    for aid, art in artifacts.items():
        fname = art.get("file")
        if not fname:
            errors.append(f'artifact "{aid}" has no "file" value')
            continue
        src = ARTIFACT_SRC / fname
        if not src.exists():
            errors.append(
                f'artifact "{aid}" points at artifacts/{fname}, which is not in '
                f"the artifacts folder"
            )
            continue
        (OUT / "artifacts").mkdir(exist_ok=True)
        shutil.copy2(src, OUT / "artifacts" / fname)
        thumb = make_thumb(src, OUT / "thumbs" / re.sub(r"[^a-zA-Z0-9_-]", "-", aid))
        resolved[aid] = {
            **art,
            "kind": kind_of(src),
            "thumb": thumb,
            "size": human_size(src.stat().st_size),
            "title": art.get("title", fname),
        }

    for aid in used_by:
        if aid not in artifacts:
            errors.append(
                f'videos.json refers to artifact "{aid}", which is not defined '
                f"in artifacts.json"
            )

    if errors:
        print("\nBuild failed:\n")
        for e in errors:
            print(f"  - {e}")
        print()
        sys.exit(1)

    # ---- per-video pages
    seen_slugs = set()
    for v in videos:
        slug = v.get("slug")
        if not slug:
            sys.exit(f'ERROR: a video entry is missing its "slug".')
        if slug in seen_slugs:
            sys.exit(f'ERROR: two videos share the slug "{slug}". Slugs must be unique.')
        seen_slugs.add(slug)

        cards = []
        for aid in v.get("artifacts", []):
            art = dict(resolved[aid])
            others = [t for t in used_by.get(aid, []) if t != v.get("title")]
            art["also_in"] = others
            cards.append(card_html(art, "../../"))

        body = [
            '<a class="back" href="../../">&larr; All videos</a>',
            '<header class="site">',
            f"<h1>{escape(v.get('title', slug))}</h1>",
        ]
        if v.get("description"):
            body.append(f'<p class="sub">{escape(v["description"])}</p>')
        if v.get("youtube_url") and "REPLACE_ME" not in v["youtube_url"]:
            body.append(
                f'<a class="watch" href="{escape(v["youtube_url"])}" '
                f'target="_blank" rel="noopener">&#9654;&nbsp; Watch on YouTube</a>'
            )
        body.append("</header>")

        n = len(cards)
        body.append(
            f'<p class="count">{n} document{"" if n == 1 else "s"}</p>'
            if n
            else '<p class="empty">No documents listed for this video yet.</p>'
        )
        if cards:
            body.append('<div class="grid">' + "\n".join(cards) + "</div>")
        body.append(
            f'<footer>{escape(site.get("footer", ""))}</footer>'
            if site.get("footer")
            else ""
        )

        dest = OUT / "v" / slug
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "index.html").write_text(
            page(f"{v.get('title', slug)} — {site_title}", "\n".join(body), depth=2),
            encoding="utf-8",
        )

    # ---- index
    items = []
    for v in videos:
        n = len(v.get("artifacts", []))
        items.append(
            f'<li><a href="v/{escape(v["slug"])}/">'
            f'<p class="t">{escape(v.get("title", v["slug"]))}</p>'
            f'<p class="s">{n} document{"" if n == 1 else "s"}</p></a></li>'
        )
    body = [
        '<header class="site">',
        f"<h1>{escape(site_title)}</h1>",
        f'<p class="sub">{escape(site.get("subtitle", ""))}</p>',
        "</header>",
        '<ul class="videos">' + "\n".join(items) + "</ul>"
        if items
        else '<p class="empty">No videos yet.</p>',
    ]
    if site.get("footer"):
        body.append(f'<footer>{escape(site["footer"])}</footer>')
    (OUT / "index.html").write_text(
        page(site_title, "\n".join(body), depth=0), encoding="utf-8"
    )

    shared = sum(1 for a, vids in used_by.items() if len(vids) > 1)
    print(f"Built {len(videos)} video page(s), {len(resolved)} artifact(s).")
    if shared:
        print(f"  {shared} artifact(s) shared across more than one video.")
    for w in warnings:
        print(f"  note: {w}")
    print(f"Output in {OUT}/")


if __name__ == "__main__":
    main()
