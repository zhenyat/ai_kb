## Prompt: clarify the components: conversations/exports/ & conversations/snippets/

### `conversations/exports/`
Full conversation files exported directly from an AI interface — the **complete session** as it was delivered by the platform.

**Examples:**
- A `.json` file exported from claude.ai via "Export conversation"
- A `.txt` or `.md` file saved from a ChatGPT or Gemini session
- A full transcript downloaded via API

These are **raw, unedited, append-only** — you never modify them. They serve as the original source of record, the equivalent of a primary document in an archive.

---

### `conversations/snippets/`
**Fragments** manually copy-pasted from a conversation — a single exchange, a specific response, or a prompt you want to preserve but don't have the full session for.

**Examples:**
- A particularly good model response you copied before closing the tab
- A prompt + response pair you want to reference later
- A short exchange that didn't warrant a full export

---

### Relationship to `topics/`

Neither folder is a KB entry. They are **source material** — raw inputs that you later distill into a proper entry under `topics/`. The workflow is:

```
conversations/exports/   ──►  read & extract  ──►  topics/<topic>/<entry>.md
conversations/snippets/  ──►  read & extract  ──►  topics/<topic>/<entry>.md
```

Think of `conversations/` as your **inbox** and `topics/` as your **processed knowledge**.