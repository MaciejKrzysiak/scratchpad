from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
import subprocess
import os
import requests
import yaml
from datetime import datetime

app = FastAPI()

HEDGEDOC_BASE = os.environ.get("HEDGEDOC_BASE", "http://hedgedoc:3000")
BLOG_DIR = Path(os.environ.get("GIT_REPO_DIR", "/blog"))
POSTS_DIR = BLOG_DIR / "_posts"
MAP_FILE = BLOG_DIR / ".hedgedoc-map.yml"

class SyncRequest(BaseModel):
    note_id: str

def load_map() -> dict:
    if not MAP_FILE.exists():
        return {}
    with MAP_FILE.open("r") as f:
        return yaml.safe_load(f) or {}

def save_map(mapping: dict) -> None:
    with MAP_FILE.open("w") as f:
        yaml.safe_dump(mapping, f)

def slugify(title: str) -> str:
    s = title.strip().lower()
    out = []
    for ch in s:
        if ch.isalnum():
            out.append(ch)
        elif ch in " _-":
            out.append("-")
        # ignore other chars
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "post"

def extract_title(md: str) -> str:
    # very naive: first non-empty line starting with '#'
    for line in md.splitlines():
        if line.strip().startswith("#"):
            return line.lstrip("#").strip()
    return "Untitled"

def add_frontmatter(md: str, note_id: str, filename: str) -> str:
    title = extract_title(md)
    # Jekyll likes YYYY-MM-DD in filename; if present, use that date
    date_str = None
    base = Path(filename).stem
    parts = base.split("-", 3)
    if len(parts) >= 3:
        maybe_date = "-".join(parts[:3])
        try:
            datetime.strptime(maybe_date, "%Y-%m-%d")
            date_str = maybe_date
        except ValueError:
            pass
    if date_str is None:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")

    body = md
    # If the note already has YAML frontmatter, leave it in place for now
    if md.startswith("---\n"):
        return md

    frontmatter = f"""---
layout: post
title: "{title}"
date: {date_str} 00:00:00 +0000
hedgedoc_id: {note_id}
published: true
---

"""
    return frontmatter + body.lstrip()

def git_commit(message: str) -> None:
    # assume repo and remote are already configured
    subprocess.run(["git", "add", "."], cwd=BLOG_DIR, check=False)
    # commit may fail if no changes; ignore error
    subprocess.run(["git", "commit", "-m", message], cwd=BLOG_DIR, check=False)
    subprocess.run(["git", "push"], cwd=BLOG_DIR, check=False)

@app.post("/sync-one")
def sync_one(req: SyncRequest):
    note_id = req.note_id.strip()
    if not note_id:
        raise HTTPException(status_code=400, detail="note_id required")

    # 1) fetch markdown from HedgeDoc
    url = f"{HEDGEDOC_BASE}/{note_id}/download"
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"HedgeDoc returned {resp.status_code} for {url}",
        )
    md = resp.text

    # 2) load or create mapping
    mapping = load_map()
    filename = mapping.get(note_id)
    if not filename:
        # first-time: create a filename in _posts
        title = extract_title(md)
        slug = slugify(title)
        today = datetime.utcnow().strftime("%Y-%m-%d")
        filename = f"{today}-{slug}.md"
        mapping[note_id] = filename

    # 3) write file into _posts
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    target = POSTS_DIR / filename
    content = add_frontmatter(md, note_id, filename)
    target.write_text(content, encoding="utf-8")

    # 4) save map + git commit/push
    save_map(mapping)
    git_commit(f"Sync HedgeDoc note {note_id} -> {filename}")

    return {"status": "ok", "note_id": note_id, "file": str(target)}

class UnpublishRequest(BaseModel):
    note_id: str

def set_published_flag(path: Path, published: bool) -> None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or not lines[0].startswith("---"):
        # no frontmatter, leave for now
        return
    # find end of frontmatter
    end = None
    for i in range(1, len(lines)):
        if lines[i].startswith("---"):
            end = i
            break
    if end is None:
        return

    # mutate frontmatter lines
    fm = lines[1:end]
    new_fm = []
    found = False
    for line in fm:
        if line.strip().startswith("published:"):
            new_fm.append(f"published: {'true' if published else 'false'}")
            found = True
        else:
            new_fm.append(line)
    if not found:
        new_fm.append(f"published: {'true' if published else 'false'}")

    new_lines = ["---", *new_fm, "---", *lines[end+1:]]
    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

@app.post("/unpublish")
def unpublish(req: UnpublishRequest):
    note_id = req.note_id.strip()
    if not note_id:
        raise HTTPException(status_code=400, detail="note_id required")

    mapping = load_map()
    filename = mapping.get(note_id)
    if not filename:
        raise HTTPException(status_code=404, detail="note_id not mapped")

    target = POSTS_DIR / filename
    if not target.exists():
        raise HTTPException(status_code=404, detail="file not found")

    set_published_flag(target, published=False)
    save_map(mapping)
    git_commit(f"Unpublish HedgeDoc note {note_id} -> {filename}")

    return {"status": "ok", "note_id": note_id, "file": str(target)}
