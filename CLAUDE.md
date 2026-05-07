# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Anima Prompter Forge — a Forge/WebUI AlwaysVisible extension that generates structured Anima-style image prompts from a concept string and optional reference image by calling a local LM Studio server, then writes the result into the active WebUI prompt box.

## Running Tests

```bash
python -m unittest tests.test_anima_prompter
```

Tests run standalone without a WebUI instance — `tests/test_anima_prompter.py` inserts the repo root into `sys.path` to import `anima_prompter.prompter` directly.

## Linting

Follow the parent repo conventions (see `../../CLAUDE.md`):

```bash
black .
ruff check .
```

## Architecture

### Two-layer separation

```
anima_prompter/prompter.py   — pure Python, no WebUI dependencies
scripts/anima_prompter.py    — Gradio/WebUI integration layer
```

`anima_prompter/` is importable and testable with no Gradio or `modules` import required. `scripts/anima_prompter.py` is discovered automatically by Forge at startup.

### Core data flow

```
User input (concept str + optional image bytes)
  → LMStudioPrompter.generate()
      POST /v1/chat/completions to LM Studio
      extract_json()  ← strips markdown fences, falls back to brace-search
  → AnimaPrompt.from_dict()
  → AnimaPrompt.build_string()
      "year YYYY, score_7, …, subject, @artist, tag1, tag2. Natural language."
  → gr.update(value=…) applied to the WebUI prompt textbox
```

### WebUI integration pattern

`AnimaPrompterScript` extends `scripts.Script` with `show()` returning `scripts.AlwaysVisible`. It uses `after_component()` to capture the target prompt `gr.Textbox` by `elem_id` (`txt2img_prompt` / `img2img_prompt`) before `ui()` is called. If the component isn't found, the extension falls back to a hidden shadow textbox and warns the user.

### Settings

Registered via `script_callbacks.on_ui_settings`. Read at call time from `shared.opts.data` — not cached at startup — so changes in Settings take effect without restart:

- `anima_prompter_lmstudio_url` (default `http://192.168.11.21:1234`)
- `anima_prompter_timeout` (default `60.0` s)

### `AnimaPrompt.build_string()` format

Artists are normalized to `@name` (leading `@` deduplicated). Tags have underscores replaced with spaces. Field order: `period`, scores, quality, `safety`, subject, character, series, artists, tags, then `. {natural_language}` appended if present.

`period` is a string tag — either a keyword (`newest`, `recent`, `mid`, `early`, `old`) or a specific year string like `"year 2025"`. `safety` is one of `safe`, `sensitive`, `nsfw`, `explicit`.

### Error handling

`LMStudioError` is raised for all LM Studio failures. HTTP 400 with a vision payload produces a targeted message prompting the user to load a vision-capable model. `sanitize_payload()` truncates base64 image data in log output.
