Good initiative — unit testing `sync.py` is worth doing properly given it's the critical pipeline component. Let me think through the approach before writing anything.

---

### What needs testing in `sync.py`

There are four distinct functional layers:

| Layer | Function | Test type |
|---|---|---|
| Frontmatter parsing | `parse_frontmatter()` | Unit |
| Entry validation | `validate_entry()` | Unit — most critical |
| SQLite operations | `init_db()`, `insert_entry()` | Integration (in-memory DB) |
| File I/O | JSON export, index regeneration | Integration (temp directory) |

---

### My recommended approach

**Framework:** `pytest` — standard, minimal boilerplate, excellent on macOS.

**Key principles for this codebase:**

- Use **in-memory SQLite** (`sqlite3.connect(":memory:")`) for DB tests — no temp files, no cleanup, fast
- Use `tmp_path` (pytest built-in fixture) for file I/O tests — isolated temp directory per test, auto-cleaned
- Validation tests should be **exhaustive** — one test per rule (missing field, wrong `topic_ru`, invalid `source`, empty models list, etc.)
- No mocking needed — the functions are pure enough to test directly

---

### Proposed test file structure

```
db/
├── sync.py
└── tests/
    ├── __init__.py
    ├── test_parse_frontmatter.py    # parsing edge cases
    ├── test_validate_entry.py       # all validation rules — most tests here
    ├── test_database.py             # insert, query, junction tables
    └── test_integration.py         # full pipeline: .md → SQLite → JSON → _index.md
```

---

### Two questions before I write the tests:

1. **Coverage target** — thorough (every validation rule + edge case) or lean (happy path + critical failure paths only)?
2. **`sync.py` refactor needed** — currently `main()` is monolithic, which makes integration testing harder. I'd suggest extracting `sync_all()` as a pure callable function that accepts paths as arguments rather than reading from constants. Do you want me to refactor `sync.py` first, or write tests around the current structure?