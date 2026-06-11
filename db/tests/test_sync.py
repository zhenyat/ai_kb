#! /usr/bin/env python3
# test_sync.py — pytest suite for sync.py
# 2026-06-09 | Claude Sonnet 4.6

"""
Test coverage:
  - parse_frontmatter   : valid input, missing block, malformed YAML
  - validate_entry      : all required fields, topic_ru vocab, source values,
                          models list, unknown topic
  - init_db / insert    : schema creation, row insertion, junction tables
  - export_json         : output structure, Cyrillic encoding, models/tags hydration
  - regenerate_indexes  : file created, table content, multiple models
  - sync_all (integration): happy path, validation failure blocks writes,
                             dry-run produces no files
"""

import json
import sqlite3
import textwrap
from pathlib import Path

import pytest

# Import all testable units from sync.py.
# Tests are run from the repo root: pytest db/tests/
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sync import (
    DDL,
    VALID_SOURCES,
    export_json,
    init_db,
    insert_entry,
    load_controlled_vocabulary,
    parse_frontmatter,
    regenerate_model_indexes,
    sync_all,
    validate_entry,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def vocab() -> dict:
    return {
        "prompt-engineering": {"ru": "Промпт-инжиниринг"},
        "fundamentals":       {"ru": "Основы ИИ"},
    }


@pytest.fixture
def base_fm() -> dict:
    """A fully valid frontmatter dict."""
    return {
        "id":       "2026-06-09-001-test",
        "date":     "2026-06-09",
        "topic":    "prompt-engineering",
        "topic_ru": "Промпт-инжиниринг",
        "subtopic": "chain-of-thought",
        "models":   ["claude", "gemini"],
        "tags":     ["reasoning"],
        "source":   "manual",
        "url":      "https://example.com",
        "project":  None,
    }


@pytest.fixture
def mem_db() -> sqlite3.Connection:
    """In-memory SQLite connection, schema pre-created, closed after test."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def tags_yaml(tmp_path) -> Path:
    """Minimal tags.yaml written to a temp directory."""
    content = textwrap.dedent("""\
        topics:
          prompt-engineering:
            ru: "Промпт-инжиниринг"
          fundamentals:
            ru: "Основы ИИ"
    """)
    p = tmp_path / "_meta" / "tags.yaml"
    p.parent.mkdir(parents=True)
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def repo(tmp_path, tags_yaml) -> Path:
    """
    Minimal repo scaffold in a temp directory:
      <tmp>/
        _meta/tags.yaml
        topics/
        models/
        db/
    Returns tmp_path as repo_root.
    """
    (tmp_path / "topics").mkdir()
    (tmp_path / "models").mkdir()
    (tmp_path / "db").mkdir()
    return tmp_path


def make_entry_file(repo_root: Path, fm: dict, extra_content: str = "") -> Path:
    """Write a valid .md entry file under topics/<topic>/ and return its path."""
    topic_dir = repo_root / "topics" / fm["topic"]
    topic_dir.mkdir(parents=True, exist_ok=True)
    path = topic_dir / f"{fm['id']}.md"

    lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            items = ", ".join(v)
            lines.append(f"{k}: [{items}]")
        elif v is None:
            lines.append(f"{k}:")
        else:
            lines.append(f"{k}: {v}")
    lines += ["---", "", extra_content or "## Summary\n\nTest entry."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------

class TestParseFrontmatter:

    def test_valid_frontmatter(self, tmp_path):
        md = tmp_path / "entry.md"
        md.write_text("---\nid: test-001\ntopic: fundamentals\n---\n\n## Body\n")
        fm = parse_frontmatter(md)
        assert fm["id"] == "test-001"
        assert fm["topic"] == "fundamentals"

    def test_missing_frontmatter_block(self, tmp_path):
        md = tmp_path / "entry.md"
        md.write_text("# No frontmatter here\n")
        with pytest.raises(ValueError, match="No valid YAML frontmatter block"):
            parse_frontmatter(md)

    def test_malformed_yaml(self, tmp_path):
        md = tmp_path / "entry.md"
        md.write_text("---\nkey: [unclosed\n---\n\nbody\n")
        with pytest.raises(ValueError, match="YAML parse error"):
            parse_frontmatter(md)

    def test_non_mapping_frontmatter(self, tmp_path):
        md = tmp_path / "entry.md"
        md.write_text("---\n- item1\n- item2\n---\n\nbody\n")
        with pytest.raises(ValueError, match="key-value mapping"):
            parse_frontmatter(md)


# ---------------------------------------------------------------------------
# validate_entry
# ---------------------------------------------------------------------------

class TestValidateEntry:

    @pytest.mark.parametrize("missing_field", [
        "id", "date", "topic", "topic_ru", "source"
    ])
    def test_required_fields_missing(self, base_fm, vocab, missing_field):
        fm = {**base_fm, missing_field: None}
        errors = validate_entry(fm, vocab, Path("test.md"))
        assert any(missing_field in e for e in errors), (
            f"Expected error mentioning '{missing_field}', got: {errors}"
        )

    def test_valid_entry_produces_no_errors(self, base_fm, vocab):
        errors = validate_entry(base_fm, vocab, Path("test.md"))
        assert errors == []

    def test_unknown_topic(self, base_fm, vocab):
        fm = {**base_fm, "topic": "nonexistent-topic"}
        errors = validate_entry(fm, vocab, Path("test.md"))
        assert any("Unknown topic" in e for e in errors)

    def test_wrong_topic_ru(self, base_fm, vocab):
        fm = {**base_fm, "topic_ru": "Неправильный перевод"}
        errors = validate_entry(fm, vocab, Path("test.md"))
        assert any("does not match controlled vocabulary" in e for e in errors)

    @pytest.mark.parametrize("bad_source", ["web", "api", "unknown", "MANUAL"])
    def test_invalid_source_values(self, base_fm, vocab, bad_source):
        fm = {**base_fm, "source": bad_source}
        errors = validate_entry(fm, vocab, Path("test.md"))
        assert any("Invalid source" in e for e in errors)

    @pytest.mark.parametrize("good_source", list(VALID_SOURCES))
    def test_valid_source_values(self, base_fm, vocab, good_source):
        fm = {**base_fm, "source": good_source}
        errors = validate_entry(fm, vocab, Path("test.md"))
        assert not any("Invalid source" in e for e in errors)

    def test_models_empty_list(self, base_fm, vocab):
        fm = {**base_fm, "models": []}
        errors = validate_entry(fm, vocab, Path("test.md"))
        assert any("models" in e for e in errors)

    def test_models_not_a_list(self, base_fm, vocab):
        fm = {**base_fm, "models": "claude"}
        errors = validate_entry(fm, vocab, Path("test.md"))
        assert any("models" in e for e in errors)

    def test_models_none(self, base_fm, vocab):
        fm = {**base_fm, "models": None}
        errors = validate_entry(fm, vocab, Path("test.md"))
        assert any("models" in e for e in errors)


# ---------------------------------------------------------------------------
# load_controlled_vocabulary
# ---------------------------------------------------------------------------

class TestLoadControlledVocabulary:

    def test_loads_correctly(self, tags_yaml):
        vocab = load_controlled_vocabulary(tags_yaml)
        assert "prompt-engineering" in vocab
        assert vocab["prompt-engineering"]["ru"] == "Промпт-инжиниринг"

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_controlled_vocabulary(tmp_path / "nonexistent.yaml")

    def test_empty_topics_raises(self, tmp_path):
        p = tmp_path / "tags.yaml"
        p.write_text("topics: {}\n", encoding="utf-8")
        with pytest.raises(ValueError, match="no 'topics' section"):
            load_controlled_vocabulary(p)


# ---------------------------------------------------------------------------
# Database — init_db / insert_entry
# ---------------------------------------------------------------------------

class TestDatabase:

    def test_tables_created(self, mem_db):
        tables = {
            row[0] for row in
            mem_db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {"entries", "entry_models", "entry_tags"}.issubset(tables)

    def test_insert_entry_scalar_fields(self, mem_db, base_fm, tmp_path):
        path = tmp_path / "entry.md"
        insert_entry(mem_db, base_fm, path, tmp_path)
        mem_db.commit()

        row = mem_db.execute(
            "SELECT id, topic, topic_ru, source FROM entries WHERE id = ?",
            (base_fm["id"],)
        ).fetchone()

        assert row is not None
        assert row[0] == base_fm["id"]
        assert row[1] == "prompt-engineering"
        assert row[2] == "Промпт-инжиниринг"
        assert row[3] == "manual"

    def test_insert_entry_models_junction(self, mem_db, base_fm, tmp_path):
        insert_entry(mem_db, base_fm, tmp_path / "entry.md", tmp_path)
        mem_db.commit()

        models = [
            r[0] for r in
            mem_db.execute(
                "SELECT model FROM entry_models WHERE entry_id = ? ORDER BY model",
                (base_fm["id"],)
            ).fetchall()
        ]
        assert models == sorted(base_fm["models"])

    def test_insert_entry_tags_junction(self, mem_db, base_fm, tmp_path):
        insert_entry(mem_db, base_fm, tmp_path / "entry.md", tmp_path)
        mem_db.commit()

        tags = [
            r[0] for r in
            mem_db.execute(
                "SELECT tag FROM entry_tags WHERE entry_id = ? ORDER BY tag",
                (base_fm["id"],)
            ).fetchall()
        ]
        assert tags == sorted(base_fm["tags"])

    def test_init_db_is_idempotent(self, mem_db, base_fm, tmp_path):
        """Running init_db again should clear all rows."""
        insert_entry(mem_db, base_fm, tmp_path / "entry.md", tmp_path)
        mem_db.commit()
        init_db(mem_db)
        count = mem_db.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        assert count == 0

    def test_topic_ru_not_null_constraint(self, mem_db, base_fm, tmp_path):
        fm = {**base_fm, "topic_ru": None}
        with pytest.raises(sqlite3.IntegrityError):
            insert_entry(mem_db, fm, tmp_path / "entry.md", tmp_path)
            mem_db.commit()


# ---------------------------------------------------------------------------
# export_json
# ---------------------------------------------------------------------------

class TestExportJson:

    def test_output_file_created(self, mem_db, base_fm, tmp_path):
        insert_entry(mem_db, base_fm, tmp_path / "entry.md", tmp_path)
        mem_db.commit()

        json_path = tmp_path / "entries.json"
        export_json(mem_db, json_path)
        assert json_path.exists()

    def test_output_is_valid_json(self, mem_db, base_fm, tmp_path):
        insert_entry(mem_db, base_fm, tmp_path / "entry.md", tmp_path)
        mem_db.commit()

        json_path = tmp_path / "entries.json"
        export_json(mem_db, json_path)
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) == 1

    def test_cyrillic_preserved(self, mem_db, base_fm, tmp_path):
        insert_entry(mem_db, base_fm, tmp_path / "entry.md", tmp_path)
        mem_db.commit()

        json_path = tmp_path / "entries.json"
        export_json(mem_db, json_path)
        raw = json_path.read_text(encoding="utf-8")
        assert "Промпт-инжиниринг" in raw  # ensure_ascii=False

    def test_models_and_tags_hydrated(self, mem_db, base_fm, tmp_path):
        insert_entry(mem_db, base_fm, tmp_path / "entry.md", tmp_path)
        mem_db.commit()

        json_path = tmp_path / "entries.json"
        entries = export_json(mem_db, json_path)
        assert sorted(entries[0]["models"]) == sorted(base_fm["models"])
        assert sorted(entries[0]["tags"])   == sorted(base_fm["tags"])


# ---------------------------------------------------------------------------
# regenerate_model_indexes
# ---------------------------------------------------------------------------

class TestRegenerateModelIndexes:

    def _make_entry(self, eid, models):
        return {
            "id": eid, "date": "2026-06-09",
            "topic": "prompt-engineering", "subtopic": "cot",
            "file_path": f"topics/prompt-engineering/{eid}.md",
            "models": models,
        }

    def test_index_file_created(self, tmp_path):
        models_dir = tmp_path / "models"
        entries = [self._make_entry("2026-06-09-001-test", ["claude"])]
        regenerate_model_indexes(entries, models_dir)
        assert (models_dir / "claude" / "_index.md").exists()

    def test_index_contains_entry_id(self, tmp_path):
        models_dir = tmp_path / "models"
        entries = [self._make_entry("2026-06-09-001-test", ["claude"])]
        regenerate_model_indexes(entries, models_dir)
        content = (models_dir / "claude" / "_index.md").read_text(encoding="utf-8")
        assert "2026-06-09-001-test" in content

    def test_multiple_models_each_get_index(self, tmp_path):
        models_dir = tmp_path / "models"
        entries = [self._make_entry("2026-06-09-001-test", ["claude", "gemini"])]
        regenerate_model_indexes(entries, models_dir)
        assert (models_dir / "claude" / "_index.md").exists()
        assert (models_dir / "gemini" / "_index.md").exists()

    def test_entry_count_in_header(self, tmp_path):
        models_dir = tmp_path / "models"
        entries = [
            self._make_entry("2026-06-09-001-a", ["claude"]),
            self._make_entry("2026-06-09-002-b", ["claude"]),
        ]
        regenerate_model_indexes(entries, models_dir)
        content = (models_dir / "claude" / "_index.md").read_text(encoding="utf-8")
        assert "Total entries: 2" in content


# ---------------------------------------------------------------------------
# sync_all  (integration)
# ---------------------------------------------------------------------------

class TestSyncAll:

    def test_happy_path(self, repo, base_fm):
        make_entry_file(repo, base_fm)
        db_path   = repo / "db" / "index.sqlite3"
        json_path = repo / "db" / "entries.json"

        code = sync_all(
            topics_dir=repo / "topics",
            models_dir=repo / "models",
            db_path=db_path,
            json_path=json_path,
            tags_yaml=repo / "_meta" / "tags.yaml",
            repo_root=repo,
        )

        assert code == 0
        assert db_path.exists()
        assert json_path.exists()

        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        conn.close()
        assert count == 1

    def test_dry_run_writes_nothing(self, repo, base_fm):
        make_entry_file(repo, base_fm)
        db_path   = repo / "db" / "index.sqlite3"
        json_path = repo / "db" / "entries.json"

        code = sync_all(
            topics_dir=repo / "topics",
            models_dir=repo / "models",
            db_path=db_path,
            json_path=json_path,
            tags_yaml=repo / "_meta" / "tags.yaml",
            repo_root=repo,
            dry_run=True,
        )

        assert code == 0
        assert not db_path.exists()
        assert not json_path.exists()

    def test_validation_failure_blocks_writes(self, repo, base_fm):
        bad_fm = {**base_fm, "topic_ru": None, "id": "2026-06-09-002-bad"}
        make_entry_file(repo, bad_fm)
        db_path   = repo / "db" / "index.sqlite3"
        json_path = repo / "db" / "entries.json"

        code = sync_all(
            topics_dir=repo / "topics",
            models_dir=repo / "models",
            db_path=db_path,
            json_path=json_path,
            tags_yaml=repo / "_meta" / "tags.yaml",
            repo_root=repo,
        )

        assert code == 1
        assert not db_path.exists()
        assert not json_path.exists()

    def test_empty_topics_dir(self, repo):
        code = sync_all(
            topics_dir=repo / "topics",
            models_dir=repo / "models",
            db_path=repo / "db" / "index.sqlite3",
            json_path=repo / "db" / "entries.json",
            tags_yaml=repo / "_meta" / "tags.yaml",
            repo_root=repo,
        )
        assert code == 0

    def test_json_contains_correct_entry(self, repo, base_fm):
        make_entry_file(repo, base_fm)
        json_path = repo / "db" / "entries.json"

        sync_all(
            topics_dir=repo / "topics",
            models_dir=repo / "models",
            db_path=repo / "db" / "index.sqlite3",
            json_path=json_path,
            tags_yaml=repo / "_meta" / "tags.yaml",
            repo_root=repo,
        )

        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data[0]["id"] == base_fm["id"]
        assert data[0]["topic_ru"] == "Промпт-инжиниринг"
        assert "claude" in data[0]["models"]
