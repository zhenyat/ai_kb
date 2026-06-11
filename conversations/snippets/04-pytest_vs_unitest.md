Good question to settle before writing anything.

---

### Head-to-head comparison

| Dimension | `unittest` | `pytest` |
|---|---|---|
| **Origin** | Python standard library | Third-party (`pip install pytest`) |
| **Test syntax** | Class-based, inherits `TestCase` | Plain functions — no classes required |
| **Assertions** | `self.assertEqual()`, `self.assertRaises()` etc. | Plain `assert` — Python native |
| **Fixtures** | `setUp()` / `tearDown()` per class | Dependency-injected, reusable, composable |
| **Temp files** | Manual setup/cleanup | `tmp_path` built-in — auto-cleaned |
| **Output** | Verbose but noisy | Clean, color-coded, shows diffs on failure |
| **Discovery** | Explicit or configured | Automatic — finds any `test_*.py` |
| **Parametrize** | Verbose workaround needed | `@pytest.mark.parametrize` — native |
| **Plugin ecosystem** | Minimal | Rich — coverage, mock, asyncio, etc. |
| **Extra install** | None | `pip install pytest` |

---

### Concrete example — same test, both frameworks

Testing that a missing `topic_ru` field fails validation:

**`unittest`:**
```python
import unittest

class TestValidateEntry(unittest.TestCase):
    def setUp(self):
        self.vocab = {
            "prompt-engineering": {"ru": "Промпт-инжиниринг"}
        }
        self.base_fm = {
            "id": "2026-06-09-001-test",
            "date": "2026-06-09",
            "topic": "prompt-engineering",
            "topic_ru": "Промпт-инжиниринг",
            "source": "manual",
            "models": ["claude"],
        }

    def test_missing_topic_ru(self):
        fm = {**self.base_fm, "topic_ru": None}
        errors = validate_entry(fm, self.vocab, Path("test.md"))
        self.assertTrue(len(errors) > 0)
        self.assertIn("topic_ru", errors[0])
```

**`pytest`:**
```python
import pytest

@pytest.fixture
def vocab():
    return {"prompt-engineering": {"ru": "Промпт-инжиниринг"}}

@pytest.fixture
def base_fm():
    return {
        "id": "2026-06-09-001-test",
        "date": "2026-06-09",
        "topic": "prompt-engineering",
        "topic_ru": "Промпт-инжиниринг",
        "source": "manual",
        "models": ["claude"],
    }

def test_missing_topic_ru(base_fm, vocab):
    fm = {**base_fm, "topic_ru": None}
    errors = validate_entry(fm, vocab, Path("test.md"))
    assert len(errors) > 0
    assert "topic_ru" in errors[0]
```

---

### The parametrize advantage — most relevant for your case

You have ~6 validation rules to test. With `pytest` you write one test, not six:

```python
@pytest.mark.parametrize("missing_field", [
    "id", "date", "topic", "topic_ru", "source"
])
def test_required_fields(base_fm, vocab, missing_field):
    fm = {**base_fm, missing_field: None}
    errors = validate_entry(fm, vocab, Path("test.md"))
    assert any(missing_field in e for e in errors)
```

The `unittest` equivalent requires five separate methods or a manual loop.

---

### Verdict for your project

**`pytest` is the clear choice.** The only argument for `unittest` is zero extra install — not relevant here since you already have a `venv` and `pyyaml` installed. `pytest` produces cleaner code, better output, and the `tmp_path` + `parametrize` features are directly applicable to `sync.py` testing.

---

Shall I proceed with the `sync.py` refactor first (extracting `sync_all()`) and then write the full `pytest` suite?