from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, EmailStr

app = FastAPI()

HEDGEDOC_BASE = os.environ.get("HEDGEDOC_BASE", "http://hedgedoc:3000").rstrip("/")
REPO_DIR = Path(os.environ.get("GIT_REPO_DIR", "/blog"))
BLOG_DIR = Path(os.environ.get("BLOG_CONTENT_DIR", str(REPO_DIR)))
POSTS_DIR = BLOG_DIR / "_posts"
MAP_FILE = Path(os.environ.get("HEDGEDOC_MAP_FILE", str(BLOG_DIR / "hedgedoc-map.yml")))
LEGACY_MAP_FILE = BLOG_DIR / ".hedgedoc-map.yml"
ALLOWED_EMAILS_FILE = Path(
    os.environ.get("ALLOWED_EMAILS_FILE", "/etc/oauth2-proxy/emails.txt")
)
ADMIN_EMAILS_FILE = Path(
    os.environ.get("ADMIN_EMAILS_FILE", "/etc/oauth2-proxy/admins.txt")
)
PUBLIC_BLOG_BASE_URL = os.environ.get("PUBLIC_BLOG_BASE_URL", "").rstrip("/")
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("PUBLISHER_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

if ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


class NoteRequest(BaseModel):
    note_id: str
    user_email: EmailStr
    display_name: str | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


def load_emails(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        line.strip().lower()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def load_map() -> dict[str, str]:
    source = MAP_FILE if MAP_FILE.exists() else LEGACY_MAP_FILE
    if not source.exists():
        return {}
    with source.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def save_map(mapping: dict[str, str]) -> None:
    MAP_FILE.parent.mkdir(parents=True, exist_ok=True)
    with MAP_FILE.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(mapping, handle, sort_keys=True)


def slugify(title: str) -> str:
    text = title.strip().lower()
    out: list[str] = []
    for char in text:
        if char.isalnum():
            out.append(char)
        elif char in " _-":
            out.append("-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "post"


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break

    if end_index is None:
        return {}, text

    raw_frontmatter = "\n".join(lines[1:end_index])
    body = "\n".join(lines[end_index + 1 :])
    parsed = yaml.safe_load(raw_frontmatter) or {}
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=422, detail="frontmatter must be a YAML object")
    return parsed, body


def render_frontmatter(metadata: dict[str, Any], body: str) -> str:
    frontmatter = yaml.safe_dump(
        metadata,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).strip()
    normalized_body = body.lstrip("\n").rstrip()
    if normalized_body:
        return f"---\n{frontmatter}\n---\n\n{normalized_body}\n"
    return f"---\n{frontmatter}\n---\n"


def extract_title(markdown: str) -> str:
    metadata, body = split_frontmatter(markdown)
    existing_title = metadata.get("title")
    if isinstance(existing_title, str) and existing_title.strip():
        return existing_title.strip()

    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return "Untitled"


def filename_date(filename: str) -> str | None:
    stem = Path(filename).stem
    parts = stem.split("-", 3)
    if len(parts) < 4:
        return None
    maybe_date = "-".join(parts[:3])
    try:
        datetime.strptime(maybe_date, "%Y-%m-%d")
    except ValueError:
        return None
    return maybe_date


def derive_author(display_name: str | None, user_email: str) -> str:
    if display_name and display_name.strip():
        return display_name.strip()
    return user_email.split("@", 1)[0]


def normalize_post(markdown: str, note_id: str, filename: str, author: str) -> str:
    metadata, body = split_frontmatter(markdown)
    date_str = filename_date(filename) or datetime.now(UTC).strftime("%Y-%m-%d")

    metadata["layout"] = metadata.get("layout") or "post"
    metadata["title"] = extract_title(markdown)
    metadata["date"] = metadata.get("date") or f"{date_str} 00:00:00 +0000"
    metadata["hedgedoc_id"] = note_id
    metadata["published"] = True
    metadata["author"] = metadata.get("author") or author

    return render_frontmatter(metadata, body)


def blog_url_for(filename: str) -> str | None:
    if not PUBLIC_BLOG_BASE_URL:
        return None

    stem = Path(filename).stem
    parts = stem.split("-", 3)
    if len(parts) < 4:
        return None
    year, month, day, slug = parts
    return f"{PUBLIC_BLOG_BASE_URL}/{year}/{month}/{day}/{slug}.html"


def note_state(note_id: str) -> dict[str, Any]:
    mapping = load_map()
    filename = mapping.get(note_id)
    if not filename:
        return {
            "mapped": False,
            "note_id": note_id,
            "published": False,
            "status": "draft",
        }

    target = POSTS_DIR / filename
    if not target.exists():
        return {
            "mapped": True,
            "note_id": note_id,
            "filename": filename,
            "file_exists": False,
            "published": False,
            "status": "missing",
        }

    metadata, _body = split_frontmatter(target.read_text(encoding="utf-8"))
    published = bool(metadata.get("published", True))
    return {
        "mapped": True,
        "note_id": note_id,
        "filename": filename,
        "file_exists": True,
        "published": published,
        "status": "published" if published else "unpublished",
        "author": metadata.get("author"),
        "title": metadata.get("title"),
        "url": blog_url_for(filename),
    }


def ensure_allowed(user_email: str) -> dict[str, bool]:
    normalized = user_email.strip().lower()
    if not normalized:
        raise HTTPException(status_code=400, detail="user_email required")

    allowed_emails = load_emails(ALLOWED_EMAILS_FILE)
    admin_emails = load_emails(ADMIN_EMAILS_FILE)
    is_admin = normalized in admin_emails
    is_allowed = normalized in allowed_emails or is_admin
    if not is_allowed:
        raise HTTPException(status_code=403, detail="user is not allowed to publish")
    return {"is_admin": is_admin, "is_allowed": is_allowed}


def fetch_note_markdown(note_id: str) -> str:
    url = f"{HEDGEDOC_BASE}/{note_id}/download"
    response = requests.get(url, timeout=15)
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"HedgeDoc returned {response.status_code} for {url}",
        )
    return response.text


def stage_paths(paths: list[Path]) -> None:
    unique_paths = sorted({path for path in paths}, key=lambda item: str(item))
    command = [
        "git",
        "add",
        "--",
        *[str(path.relative_to(REPO_DIR)) for path in unique_paths],
    ]
    subprocess.run(command, cwd=REPO_DIR, check=True)


def commit_and_push(message: str, paths: list[Path]) -> str:
    stage_paths(paths)
    diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=REPO_DIR,
        check=False,
    )
    if diff.returncode == 0:
        return "noop"
    if diff.returncode != 1:
        raise HTTPException(status_code=500, detail="failed to inspect staged changes")

    subprocess.run(["git", "commit", "-m", message], cwd=REPO_DIR, check=True)
    subprocess.run(["git", "push"], cwd=REPO_DIR, check=True)
    return "pushed"


def mapped_target(note_id: str) -> tuple[dict[str, str], str, Path]:
    mapping = load_map()
    filename = mapping.get(note_id)
    if not filename:
        raise HTTPException(status_code=404, detail="note_id not mapped")
    target = POSTS_DIR / filename
    return mapping, filename, target


@app.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/status/{note_id}")
def status(note_id: str, user_email: str | None = Query(default=None)) -> dict[str, Any]:
    state = note_state(note_id.strip())
    if user_email:
        state.update(ensure_allowed(user_email))
    return state


@app.post("/publish")
def publish(request: NoteRequest) -> dict[str, Any]:
    note_id = request.note_id.strip()
    if not note_id:
        raise HTTPException(status_code=400, detail="note_id required")

    auth = ensure_allowed(str(request.user_email))
    markdown = fetch_note_markdown(note_id)
    mapping = load_map()
    filename = mapping.get(note_id)
    if not filename:
        slug = slugify(extract_title(markdown))
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        filename = f"{today}-{slug}.md"
        mapping[note_id] = filename

    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    target = POSTS_DIR / filename
    author = derive_author(request.display_name, str(request.user_email))
    content = normalize_post(markdown, note_id=note_id, filename=filename, author=author)
    target.write_text(content, encoding="utf-8")
    save_map(mapping)

    git_status = commit_and_push(
        f"Publish HedgeDoc note {note_id} -> {filename}",
        [target, MAP_FILE],
    )
    state = note_state(note_id)
    state.update(auth)
    state["git_status"] = git_status
    return state


@app.post("/sync-one")
def sync_one(request: NoteRequest) -> dict[str, Any]:
    return publish(request)


@app.post("/unpublish")
def unpublish(request: NoteRequest) -> dict[str, Any]:
    note_id = request.note_id.strip()
    if not note_id:
        raise HTTPException(status_code=400, detail="note_id required")

    auth = ensure_allowed(str(request.user_email))
    mapping, filename, target = mapped_target(note_id)
    if not target.exists():
        raise HTTPException(status_code=404, detail="mapped file not found")

    metadata, body = split_frontmatter(target.read_text(encoding="utf-8"))
    metadata["published"] = False
    if request.display_name and not metadata.get("author"):
        metadata["author"] = request.display_name.strip()
    target.write_text(render_frontmatter(metadata, body), encoding="utf-8")
    save_map(mapping)

    git_status = commit_and_push(
        f"Unpublish HedgeDoc note {note_id} -> {filename}",
        [target, MAP_FILE],
    )
    state = note_state(note_id)
    state.update(auth)
    state["git_status"] = git_status
    return state
