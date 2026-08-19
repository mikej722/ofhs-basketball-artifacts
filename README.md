# Video Archive

A free, self-updating home for the documents that accompany your YouTube videos.
Each video gets one tidy URL you paste into its description; that page lists
every clipping, photo, and PDF for that video, each opening in its own tab.

Everything below is done in a web browser. Nothing needs to be installed.

---

## One-time setup (about ten minutes)

### 1. Create the repository

On GitHub, click **+** (top right) → **New repository**.

- **Name it** whatever you like — `video-archive` is a good default. The name
  becomes part of your URLs, so keep it short and lowercase.
- Set it to **Public**. This matters: GitHub Pages is only free on public
  repositories. (Public means anyone who has the link can view the files —
  which is what you want anyway, since YouTube viewers need to reach them.)
- Do **not** tick "Add a README" — this bundle already has one.
- Click **Create repository**.

### 2. Upload these files

On the empty repository page, click **uploading an existing file**.

Drag in *everything* from this bundle: the `data` and `artifacts` folders,
`build.py`, `requirements.txt`, `README.md`, and the `.github` folder.

> **If the `.github` folder doesn't upload:** some browsers skip folders whose
> name starts with a dot. In that case, create it by hand — click
> **Add file → Create new file**, and type `.github/workflows/build.yml` as the
> filename (GitHub turns the slashes into folders as you type). Then paste in
> the contents of `build.yml` from this bundle.

Scroll down, click **Commit changes**.

### 3. Turn on Pages

Go to **Settings** (in the repo) → **Pages** in the left sidebar → under
**Source**, choose **GitHub Actions**. That's the only setting to change.

### 4. Wait for the first build

Click the **Actions** tab. You'll see a run called "Build and publish archive."
Give it a minute or two to turn green. When it does, your site is live at:

```
https://YOUR-USERNAME.github.io/YOUR-REPO-NAME/
```

The sample content is already in place so you can confirm it works before
replacing it with your own.

---

## The URL you put in a YouTube description

```
https://YOUR-USERNAME.github.io/YOUR-REPO-NAME/v/SLUG/
```

where `SLUG` is the `slug` value from `data/videos.json`. For the included
example, that's `.../v/1957-flood/`.

If you ever want to link one single document instead of a whole page:

```
https://YOUR-USERNAME.github.io/YOUR-REPO-NAME/artifacts/FILENAME.pdf
```

YouTube turns both into clickable links automatically. No need for a link
shortener — but if you want prettier links, these work fine behind one.

---

## Adding a new video

Three steps, all in the browser.

**Step 1 — upload the documents.**
Open the `artifacts` folder in your repo → **Add file → Upload files** → drag
your scans and photos in → **Commit changes**.

Name files with lowercase letters, numbers, and hyphens. No spaces, no `#`,
no `&`. `1957-tribune-flood.pdf` is good; `Tribune Flood (final).pdf` will
cause trouble.

**Step 2 — describe them in `data/artifacts.json`.**
Open that file → click the pencil icon → add a block for each new document:

```json
"gazette-1961-bridge": {
  "file": "1961-gazette-bridge.pdf",
  "title": "New bridge opens to traffic",
  "source": "Evening Gazette",
  "date": "June 4, 1961"
}
```

The key on the first line (`gazette-1961-bridge`) is an ID you invent — it's
how videos refer to this document. Only `file` and `title` are required;
`source` and `date` are optional and simply won't display if you leave them out.

**Watch your commas.** Every block needs a comma after its closing `}` except
the very last one in the file. This is the single most common thing to get
wrong, and the build will tell you the line number if you do.

**Step 3 — add the video in `data/videos.json`.**
Add a block to the `videos` list:

```json
{
  "slug": "the-1961-bridge",
  "title": "The 1961 Bridge",
  "youtube_url": "https://www.youtube.com/watch?v=abc123",
  "description": "How the crossing finally got built.",
  "artifacts": ["gazette-1961-bridge", "levee-map-1954"]
}
```

Commit. Within a minute or two the Actions tab goes green and your new page is
live at `/v/the-1961-bridge/`.

---

## Using the same document for several videos

This is the whole point of splitting the two files. Define the artifact **once**
in `artifacts.json`, then list its ID under as many videos as you want in
`videos.json`. The file is stored once, and each video page shows a small
"Also appears with: ..." note pointing at the other videos that use it.

The included sample does this with `levee-map-1954` — it appears on both
example video pages.

---

## Changing the site title

Edit the `site` block at the top of `data/videos.json`:

```json
"site": {
  "title": "Video Archive",
  "subtitle": "Source material and documents accompanying the video series",
  "footer": "Assembled by MJ"
}
```

---

## When something goes wrong

If the Actions tab shows a red ✗ instead of a green ✓, the site didn't rebuild
and the old version stays live — nothing breaks for viewers. Click the failed
run and open the "Build site" step to see the reason. The build checks for the
three mistakes that actually happen:

| Message | What to do |
|---|---|
| `... is not valid JSON` | A comma problem, at the line number given. Usually a missing comma between blocks or a stray one after the last block. |
| `refers to artifact "x", which is not defined` | The ID in `videos.json` doesn't match any key in `artifacts.json`. Check for a typo. |
| `points at artifacts/x.pdf, which is not in the artifacts folder` | The `file` value doesn't match the actual uploaded filename. Capitalization counts. |

Fix the file, commit again, and it rebuilds.

---

## Limits worth knowing

- **1 GB** total for the whole site, and **100 MB** per individual file. For
  scanned clippings you'll likely never approach either — but if you're
  scanning at 600 dpi, consider saving at 300 dpi instead. It's plenty for
  screen reading and keeps pages loading fast on phones.
- **100 GB/month** bandwidth, a soft limit. Realistically not a concern.
- GitHub Pages is for non-commercial use, which an archive like this is.

## A note on copyright

Newspaper material published in the US before 1930 is public domain. Later
clippings may still be under copyright. Posting a single clipping for
historical and educational context is a normal, low-risk archival practice, but
it's worth knowing the distinction if a paper's rights are actively managed.

---

## For the curious: how it works

`build.py` reads the two JSON files, copies your documents into an output
folder, renders a thumbnail for each one (page 1 for PDFs), and writes plain
static HTML. The GitHub Action runs it on every commit and publishes the
result. There's no database, no JavaScript on the pages, and nothing to keep
paying for. If GitHub ever disappeared, the `artifacts` folder is still just
your files in a folder.
