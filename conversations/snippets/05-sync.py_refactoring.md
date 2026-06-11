### What changes in sync.py:

* Extract `sync_all(topics_dir, models_dir, db_path, json_path, tags_yaml, verbose, dry_run)` — accepts all paths as arguments instead of reading module-level constants
* `export_json()` gets a `json_path` parameter instead of using `JSON_PATH` directly
* `regenerate_model_indexes()` gets a models_dir parameter
* `insert_entry()` gets `r`epo_root` as parameter instead of closing over the constant
* `main()` becomes a thin wrapper: parse args → call s`ync_all()` with REPO_ROOT-derived paths
* All constants remain at module level for CLI use — nothing removed, only made injectable

### What does NOT change:

* All function signatures for pure logic functions (`parse_frontmatter, validate_entry`) — they're already testable as-is
* DDL, error handling, output format, CLI behaviour`