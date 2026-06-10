# AI Knowledge Base — Specification v1

**Author:** Personal project  
**Created:** 2026-06-09  
**Status:** Draft v1 — iterative, subject to revision  

---

## 1. Purpose

A personal, structured Knowledge Base (KB) for systematizing information collected during AI learning and experimentation across multiple models. Designed for individual use with VS Code as the primary editor and GitHub as version control / backup.

---

## 2. Stack & Environment

| Component | Choice |
|---|---|
| OS | macOS Tahoe 26.5.1 (Mac mini M4) |
| Editor | VS Code 1.123.0 |
| Primary format | Markdown `.md` (HTML on demand) |
| Structured data | SQLite3 (`index.sqlite3`) |
| Backup / export | `entries.json` (JSON mirror of SQLite) |
| Version control | GitHub — private repository |
| Commit strategy | Thematic batches (per learning session or topic block) |

---

## 3. Repository Layout

```
ai-knowledge-base/
│
├── README.md                        # Entry point — navigation & quick-start
├── CHANGELOG.md                     # Version history of the KB structure itself
│
├── _meta/
│   ├── schema.md                    # ← This document
│   ├── models.yaml                  # Model registry
│   └── tags.yaml                    # Controlled vocabulary (topics + Russian labels)
│
├── topics/                          # Primary axis — WHAT was learned
│   ├── prompt-engineering/
│   ├── rag-and-retrieval/
│   ├── agents-and-tools/
│   ├── fine-tuning/
│   ├── model-evaluation/
│   ├── ai-in-process-optimization/
│   └── fundamentals/
│
├── models/                          # Secondary axis — WHO answered
│   ├── claude/
│   │   └── _index.md                # Index of all Claude-sourced entries
│   ├── deepseek/
│   │   └── _index.md
│   ├── gemini/
│   │   └── _index.md
│   └── _template.md                 # Template for adding a new model
│
├── projects/                        # Goal-oriented / applied work
│   └── kb-construction/             # This project
│
├── conversations/                   # Raw captured material (append-only)
│   ├── exports/                     # Full exported conversation files
│   └── snippets/                    # Copy-paste fragments
│
└── db/
    ├── index.sqlite3                # Primary query layer (excluded from Git)
    └── entries.json                 # Diffable JSON mirror (committed to Git)
```

> **Note:** `index.sqlite3` is listed in `.gitignore`. `entries.json` is the canonical version-controlled representation of the database state.

---

## 4. Topic Taxonomy

Defined in `_meta/tags.yaml`. Labels are fixed — `topic_ru` must be selected from this list, never typed freehand.

```yaml
topics:
  prompt-engineering:
    ru: "Промпт-инжиниринг"
  rag-and-retrieval:
    ru: "RAG и поиск"
  agents-and-tools:
    ru: "Агенты и инструменты"
  fine-tuning:
    ru: "Дообучение моделей"
  model-evaluation:
    ru: "Оценка моделей"
  ai-in-process-optimization:
    ru: "ИИ в оптимизации процессов"
  fundamentals:
    ru: "Основы ИИ"
```

---

## 5. Model Registry

Defined in `_meta/models.yaml`. Add new models here before referencing them in entries.

```yaml
models:
  claude:
    full_name: "Claude (Anthropic)"
    current_version: "claude-sonnet-4"
  deepseek:
    full_name: "DeepSeek"
    current_version: "DeepSeek-V3"
  gemini:
    full_name: "Gemini (Google)"
    current_version: "Gemini 2.5 Pro"
```

---

## 6. Entry — Atomic Unit

### 6.1 ID Format

```
YYYY-MM-DD-NNN-slug
```

| Component | Description |
|---|---|
| `YYYY-MM-DD` | Creation date (ISO 8601) |
| `NNN` | Global sequential counter (001, 002, … 999) — never reused |
| `slug` | Short human-readable descriptor, lowercase, hyphen-separated |

**Examples:**
```
2026-06-09-001-chain-of-thought.md
2026-06-09-002-few-shot-examples.md
2026-08-14-003-chain-of-thought.md    ← same topic revisited — unambiguous
```

### 6.2 File Location

Entries live under `topics/<topic-name>/`. Each entry file is the single source of truth — no content duplication. Model and topic indexes reference entries by path only.

### 6.3 Markdown Template

```markdown
---
id: 2026-06-09-001-chain-of-thought
date: 2026-06-09
topic: prompt-engineering
topic_ru: "Промпт-инжиниринг"
subtopic: chain-of-thought
models: [claude, gemini]
tags: [reasoning, few-shot, comparison]
source: conversation          # conversation | manual | export
url: https://...              # original source URL in English (if any)
project:                      # reference to projects/ folder (if any)
---

## Summary

One-paragraph distillation of what was learned or observed.

## Prompt Used

(The exact prompt submitted to the model, if applicable.)

## Model Responses

### Claude
...

### Gemini
...

## Key Takeaways

- Takeaway 1
- Takeaway 2

## References / Links

- [Source title](url)
```

---

## 7. SQLite Schema

Database file: `db/index.sqlite3`

```sql
CREATE TABLE entries (
    id          TEXT PRIMARY KEY,     -- e.g. 2026-06-09-001-chain-of-thought
    date        TEXT NOT NULL,        -- ISO 8601: 2026-06-09
    topic       TEXT NOT NULL,        -- FK-like ref to tags.yaml topics
    topic_ru    TEXT,                 -- Russian label from controlled vocabulary
    subtopic    TEXT,
    source      TEXT,                 -- conversation | manual | export
    url         TEXT,                 -- original source URL, nullable
    project     TEXT,                 -- ref to projects/ folder, nullable
    file_path   TEXT NOT NULL         -- relative path to .md entry file
);

CREATE TABLE entry_models (
    entry_id    TEXT REFERENCES entries(id),
    model       TEXT NOT NULL         -- claude | deepseek | gemini | ...
);

CREATE TABLE entry_tags (
    entry_id    TEXT REFERENCES entries(id),
    tag         TEXT NOT NULL
);
```

### Example queries

```sql
-- All entries on prompt-engineering using Claude
SELECT e.id, e.date, e.subtopic
FROM entries e
JOIN entry_models m ON e.id = m.entry_id
WHERE e.topic = 'prompt-engineering' AND m.model = 'claude'
ORDER BY e.date;

-- All entries where both Claude and Gemini were compared
SELECT e.id, e.topic, e.subtopic
FROM entries e
JOIN entry_models m1 ON e.id = m1.entry_id AND m1.model = 'claude'
JOIN entry_models m2 ON e.id = m2.entry_id AND m2.model = 'gemini';

-- All entries tagged 'reasoning'
SELECT e.id, e.topic, e.date
FROM entries e
JOIN entry_tags t ON e.id = t.entry_id
WHERE t.tag = 'reasoning';
```

---

## 8. Cross-referencing Strategy

- Each `models/<model>/_index.md` contains a list of entry IDs and file paths where that model was used — generated, not maintained manually.
- Each `topics/<topic>/` directory contains only the actual entry files for that topic. No symlinks — paths in `index.sqlite3` and `entries.json` serve as the cross-reference layer.
- A lightweight Python sync script (`db/sync.py`) is responsible for: parsing frontmatter of all `.md` entries → updating `index.sqlite3` → exporting `entries.json` → regenerating `models/_index.md` files.

---

## 9. GitHub Workflow

| Element | Decision |
|---|---|
| Visibility | Private repository |
| Commit strategy | Thematic batches — after a learning session or topic block |
| What is committed | All `.md` files, `entries.json`, `_meta/*.yaml`, `db/sync.py` |
| What is excluded (`.gitignore`) | `index.sqlite3` (binary, non-diffable) |
| Branch strategy | Single `main` branch — sufficient for solo project |

### Suggested `.gitignore`

```
db/index.sqlite3
.DS_Store
```

---

## 10. Conventions & Rules

- `topic_ru` must be selected from `_meta/tags.yaml` — never typed freehand.
- Entry IDs are globally unique and never reused, even if an entry is deleted.
- Sequential counter (`NNN`) is maintained in `_meta/schema.md` under "Last entry number" (updated on each new entry).
- `source` field accepts exactly three values: `conversation`, `manual`, `export`.
- `url` is in English; leave blank if no original source exists.
- All dates in ISO 8601 format: `YYYY-MM-DD`.

**Last entry number:** `000` ← update this with each new entry

---

## 11. Revision History

| Version | Date | Changes |
|---|---|---|
| v1 | 2026-06-09 | Initial specification |
