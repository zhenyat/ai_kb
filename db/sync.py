#! /usr/bin/env python3
# sync.py — Sync AI Knowledge Base markdown entries to SQLite3 and JSON mirror
# 2026-06-09 | Claude Sonnet 4.6

"""
Workflow:
  1. Load controlled vocabulary from _meta/tags.yaml
  2. Scan all topics/*/*.md entry files and parse YAML frontmatter
  3. Validate each entry (required fields, topic_ru against controlled vocab)
  4. Rebuild index.sqlite3 from scratch (full sync, idempotent)
  5. Export entries.json as a Git-friendly diffable mirror
  6. Regenerate models/<model>/_index.md cross-reference files

Usage:
  python3 db/sync.py                  # run from repo root
  python3 db/sync.py --dry-run        # validate only, no writes
  python3 db/sync.py --verbose        # show each processed entry
"""

import argparse
import json
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

import yaml  # pip install pyyaml


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT    = Path(__file__).resolve().parent.parent
TOPICS_DIR   = REPO_ROOT / "topics"
MODELS_DIR   = REPO_ROOT / "models"
META_DIR     = REPO_ROOT / "_meta"
TAGS_YAML    = META_DIR / "tags.yaml"
DB_PATH      = REPO_ROOT / "db" / "index.sqlite3"
JSON_PATH    = REPO_ROOT / "db" / "entries.json"

VALID_SOURCES = {"conversation", "manual", "export"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_controlled_vocabulary() -> dict:
    """Load topic taxonomy from _meta/tags.yaml.
    Returns a dict mapping topic slug -> {ru: <label>}.
    """
    if not TAGS_YAML.exists():
        abort(f"tags.yaml not found at {TAGS_YAML}")
    with TAGS_YAML.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    topics = data.get("topics", {})
    if not topics:
        abort("tags.yaml contains no 'topics' section.")
    return topics


def parse_frontmatter(md_path: Path) -> dict:
    """Extract YAML frontmatter block from a Markdown file.
    Raises ValueError with a descriptive message on parse failure.
    """
    text = md_path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        raise ValueError("No valid YAML frontmatter block found.")
    try:
        fm = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML parse error: {exc}") from exc
    if not isinstance(fm, dict):
        raise ValueError("Frontmatter did not parse to a key-value mapping.")
    return fm


def validate_entry(fm: dict, vocab: dict, path: Path) -> list[str]:
    """Validate frontmatter fields. Returns a list of error strings (empty = OK)."""
    errors = []

    # Required scalar fields
    for field in ("id", "date", "topic", "topic_ru", "source"):
        if not fm.get(field):
            errors.append(f"Missing or empty required field: '{field}'")

    # topic must be in controlled vocabulary
    topic = fm.get("topic", "")
    if topic and topic not in vocab:
        errors.append(
            f"Unknown topic '{topic}'. "
            f"Valid topics: {', '.join(sorted(vocab.keys()))}"
        )

    # topic_ru must match the controlled vocabulary label for the given topic
    topic_ru = fm.get("topic_ru", "")
    if topic and topic in vocab and topic_ru:
        expected_ru = vocab[topic]["ru"]
        if topic_ru != expected_ru:
            errors.append(
                f"topic_ru '{topic_ru}' does not match controlled vocabulary "
                f"for topic '{topic}' (expected: '{expected_ru}')"
            )

    # source must be one of the allowed values
    source = fm.get("source", "")
    if source and source not in VALID_SOURCES:
        errors.append(
            f"Invalid source '{source}'. Must be one of: "
            f"{', '.join(sorted(VALID_SOURCES))}"
        )

    # models must be a non-empty list
    models = fm.get("models")
    if not models or not isinstance(models, list):
        errors.append("Field 'models' must be a non-empty list.")

    return errors


def abort(message: str) -> None:
    print(f"\n[ABORT] {message}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DDL = """
CREATE TABLE IF NOT EXISTS entries (
    id          TEXT PRIMARY KEY,
    date        TEXT NOT NULL,
    topic       TEXT NOT NULL,
    topic_ru    TEXT NOT NULL,
    subtopic    TEXT,
    source      TEXT,
    url         TEXT,
    project     TEXT,
    file_path   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entry_models (
    entry_id    TEXT NOT NULL REFERENCES entries(id),
    model       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entry_tags (
    entry_id    TEXT NOT NULL REFERENCES entries(id),
    tag         TEXT NOT NULL
);
"""


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(DDL)
    conn.execute("DELETE FROM entry_tags")
    conn.execute("DELETE FROM entry_models")
    conn.execute("DELETE FROM entries")
    conn.commit()


def insert_entry(conn: sqlite3.Connection, fm: dict, file_path: Path) -> None:
    rel_path = str(file_path.relative_to(REPO_ROOT))

    conn.execute(
        """
        INSERT INTO entries
            (id, date, topic, topic_ru, subtopic, source, url, project, file_path)
        VALUES
            (:id, :date, :topic, :topic_ru, :subtopic, :source, :url, :project, :file_path)
        """,
        {
            "id":        fm["id"],
            "date":      str(fm["date"]),
            "topic":     fm["topic"],
            "topic_ru":  fm["topic_ru"],
            "subtopic":  fm.get("subtopic") or None,
            "source":    fm.get("source") or None,
            "url":       fm.get("url") or None,
            "project":   fm.get("project") or None,
            "file_path": rel_path,
        },
    )

    for model in (fm.get("models") or []):
        conn.execute(
            "INSERT INTO entry_models (entry_id, model) VALUES (?, ?)",
            (fm["id"], model),
        )

    for tag in (fm.get("tags") or []):
        conn.execute(
            "INSERT INTO entry_tags (entry_id, tag) VALUES (?, ?)",
            (fm["id"], tag),
        )


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------

def export_json(conn: sqlite3.Connection) -> list[dict]:
    """Build a list of fully-hydrated entry dicts and write to entries.json."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM entries ORDER BY id").fetchall()

    entries = []
    for row in rows:
        entry = dict(row)
        eid = entry["id"]

        entry["models"] = [
            r[0] for r in
            conn.execute(
                "SELECT model FROM entry_models WHERE entry_id = ? ORDER BY model",
                (eid,)
            ).fetchall()
        ]
        entry["tags"] = [
            r[0] for r in
            conn.execute(
                "SELECT tag FROM entry_tags WHERE entry_id = ? ORDER BY tag",
                (eid,)
            ).fetchall()
        ]
        entries.append(entry)

    JSON_PATH.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return entries


# ---------------------------------------------------------------------------
# Model index regeneration
# ---------------------------------------------------------------------------

def regenerate_model_indexes(entries: list[dict]) -> None:
    """Rewrite models/<model>/_index.md for each model found in entries."""
    model_map: dict[str, list[dict]] = {}
    for entry in entries:
        for model in entry.get("models", []):
            model_map.setdefault(model, []).append(entry)

    for model, model_entries in sorted(model_map.items()):
        index_dir = MODELS_DIR / model
        index_dir.mkdir(parents=True, exist_ok=True)
        index_path = index_dir / "_index.md"

        lines = [
            f"# {model.capitalize()} — Entry Index\n",
            f"_Auto-generated by sync.py on {date.today().isoformat()}_\n",
            f"Total entries: {len(model_entries)}\n",
            "",
            "| ID | Date | Topic | Subtopic | File |",
            "|---|---|---|---|---|",
        ]
        for e in sorted(model_entries, key=lambda x: x["id"]):
            lines.append(
                f"| {e['id']} "
                f"| {e['date']} "
                f"| {e['topic']} "
                f"| {e.get('subtopic') or '—'} "
                f"| [{Path(e['file_path']).name}](../../{e['file_path']}) |"
            )

        index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync KB markdown entries to SQLite3 and JSON mirror."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate all entries and report errors; make no writes."
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print each processed entry."
    )
    args = parser.parse_args()

    vocab = load_controlled_vocabulary()

    # ---- Discover and validate all entry files ----------------------------
    md_files = sorted(TOPICS_DIR.rglob("*.md"))
    # Skip _index.md or README.md files inside topics/
    md_files = [f for f in md_files if not f.name.startswith("_") and f.name != "README.md"]

    if not md_files:
        print("No entry files found under topics/. Nothing to sync.")
        sys.exit(0)

    valid_entries: list[tuple[dict, Path]] = []
    error_count = 0

    for md_path in md_files:
        rel = md_path.relative_to(REPO_ROOT)
        try:
            fm = parse_frontmatter(md_path)
        except ValueError as exc:
            print(f"[ERROR] {rel}: {exc}", file=sys.stderr)
            error_count += 1
            continue

        errors = validate_entry(fm, vocab, md_path)
        if errors:
            for err in errors:
                print(f"[ERROR] {rel}: {err}", file=sys.stderr)
            error_count += 1
            continue

        valid_entries.append((fm, md_path))
        if args.verbose:
            print(f"[OK]    {rel}")

    if error_count:
        abort(
            f"{error_count} entry file(s) failed validation. "
            "Fix all errors before syncing."
        )

    print(f"\nValidated {len(valid_entries)} entr{'y' if len(valid_entries) == 1 else 'ies'}.")

    if args.dry_run:
        print("Dry-run mode — no files written.")
        sys.exit(0)

    # ---- Write SQLite3 ----------------------------------------------------
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        init_db(conn)
        for fm, path in valid_entries:
            insert_entry(conn, fm, path)
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        abort(f"SQLite error: {exc}")
    finally:
        conn.close()

    print(f"SQLite:  {DB_PATH.relative_to(REPO_ROOT)}")

    # ---- Write JSON mirror ------------------------------------------------
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    entries = export_json(conn)
    conn.close()
    print(f"JSON:    {JSON_PATH.relative_to(REPO_ROOT)}")

    # ---- Regenerate model indexes -----------------------------------------
    regenerate_model_indexes(entries)
    print(f"Indexes: models/<model>/_index.md regenerated.")

    print(f"\nSync complete — {len(valid_entries)} entries written.\n")


if __name__ == "__main__":
    main()
