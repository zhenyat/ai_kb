# AI Knowledge Base

Personal knowledge base for systematizing information collected during AI
learning and experimentation across multiple models.

---

## Stack

| Component       | Choice                           |
|-----------------|----------------------------------|
| OS              | macOS Tahoe 26.5.1 (Mac mini M4) |
| Editor          | VS Code 1.123.0                  |
| Primary format  | Markdown `.md` (HTML on demand)  |
| Structured data | SQLite3 (`db/index.sqlite3`)     |
| Backup / export | `db/entries.json`                |
| Version control | GitHub — private repository       |

---

## Repository Structure

```
ai-knowledge-base/
│
├── README.md                        # This file
├── CHANGELOG.md                     # KB structure version history
│
├── _meta/
│   ├── schema.md                    # Full KB specification
│   ├── tags.yaml                    # Controlled vocabulary (topics + Russian labels)
│   └── models.yaml                  # AI model registry
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
│   ├── claude/_index.md
│   ├── deepseek/_index.md
│   └── gemini/_index.md
│
├── projects/                        # Goal-oriented / applied work
│   └── kb-construction/
│
├── conversations/                   # Raw captured material (append-only)
│   ├── exports/                     # Full conversation files exported directly from an AI interface
|   |                                #   — the complete session as it was delivered by the platform.
│   └── snippets/                    # Fragments manually copy-pasted from a conversation — a single 
|                                    #   exchange, a specific response, or a prompt you want to 
|                                    #   preserve but don't have the full session for
| 
└── db/
    ├── sync.py                      # Sync script
    ├── index.sqlite3                # Primary query layer (not in Git)
    └── entries.json                 # Diffable JSON mirror (in Git)
```

---

## Topic Taxonomy

| Topic | Russian Label |
|---|---|
| `prompt-engineering` | Промпт-инжиниринг |
| `rag-and-retrieval` | RAG и поиск |
| `agents-and-tools` | Агенты и инструменты |
| `fine-tuning` | Дообучение моделей |
| `model-evaluation` | Оценка моделей |
| `ai-in-process-optimization` | ИИ в оптимизации процессов |
| `fundamentals` | Основы ИИ |

Full definitions in [`_meta/tags.yaml`](_meta/tags.yaml).

---

## AI Models

| Key | Full Name | Current Version |
|---|---|---|
| `claude` | Claude (Anthropic) | claude-sonnet-4-6 |
| `deepseek` | DeepSeek | DeepSeek-V3 |
| `gemini` | Gemini (Google) | gemini-2.5-pro |

Full registry in [`_meta/models.yaml`](_meta/models.yaml).

---

## Entry ID Format

```
YYYY-MM-DD-NNN-slug
```

| Component | Description |
|---|---|
| `YYYY-MM-DD` | Creation date (ISO 8601) |
| `NNN` | Global sequential counter — never reused |
| `slug` | Short human-readable descriptor |

**Example:** `2026-06-09-001-chain-of-thought.md`

**Last entry number:** `001` ← update with each new entry

---

## Adding a New Entry

**1. Create the Markdown file** in `topics/<topic>/` using this filename format:
```
YYYY-MM-DD-NNN-slug.md
```

**2. Fill in the frontmatter** (all required fields):
```yaml
---
id: 2026-06-09-001-chain-of-thought
date: 2026-06-09
topic: prompt-engineering
topic_ru: "Промпт-инжиниринг"        # must match _meta/tags.yaml exactly
subtopic: chain-of-thought
models: [claude, gemini]
tags: [reasoning, step-by-step]
source: conversation                  # conversation | manual | export
url:                                  # original source URL (if any)
project:                              # ref to projects/ (if any)
---
```

**3. Validate and sync:**
```bash
python3 db/sync.py --dry-run --verbose   # validate only
python3 db/sync.py --verbose             # full sync
```

**4. Commit:**
```bash
git add topics/ db/entries.json models/
git commit -m "feat: add entry NNN — <short description>"
git push
```

---

## Useful SQLite Queries

```bash
# Open the database
sqlite3 db/index.sqlite3
```

```sql
-- All entries by topic
SELECT id, date, subtopic
FROM entries
WHERE topic = 'prompt-engineering'
ORDER BY date;

-- All entries for a specific model
SELECT e.id, e.topic, e.date
FROM entries e
JOIN entry_models m ON e.id = m.entry_id
WHERE m.model = 'claude'
ORDER BY e.date;

-- All entries where two models were compared
SELECT e.id, e.topic, e.subtopic
FROM entries e
JOIN entry_models m1 ON e.id = m1.entry_id AND m1.model = 'claude'
JOIN entry_models m2 ON e.id = m2.entry_id AND m2.model = 'gemini';

-- All entries with a specific tag
SELECT e.id, e.topic, e.date
FROM entries e
JOIN entry_tags t ON e.id = t.entry_id
WHERE t.tag = 'reasoning';
```

---

## Git Workflow

| Element | Decision |
|---|---|
| Visibility | Private repository |
| Commit strategy | Thematic batches — per learning session or topic block |
| Committed | All `.md` files, `entries.json`, `_meta/*.yaml`, `db/sync.py` |
| Excluded | `db/index.sqlite3` (binary, non-diffable) |
| Branch strategy | Single `main` branch |

---

## Full Specification

See [`_meta/schema.md`](_meta/schema.md) for the complete KB specification
including data model, validation rules, and design decisions.
