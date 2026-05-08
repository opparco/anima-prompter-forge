# Anima Prompter Forge

An AlwaysVisible extension for [SD WebUI Forge Neo](https://github.com/Haoming02/sd-webui-forge-classic/tree/neo) that generates structured [Anima](https://civitai.com/models/676675)-style prompts from a concept string and optional reference image via [LM Studio](https://lmstudio.ai/), then writes the result into the active prompt box.

## Features

- Works in both **txt2img** and **img2img** tabs
- Generates a structured Anima prompt from any LM Studio-compatible model via `/v1/chat/completions`
- Optional **vision input**: upload a reference image to let the model extract pose, colors, and atmosphere
- **Post-process overrides**: independently control period tag, safety rating, and artist tags after generation
- Auto-fills the negative prompt with Anima-standard quality tags when the field is empty
- Shows the raw JSON response from the LLM for inspection and debugging

## Requirements

- [SD WebUI Forge Neo](https://github.com/Haoming02/sd-webui-forge-classic/tree/neo) (`neo` branch)
- [LM Studio](https://lmstudio.ai/) running locally or on your LAN with a model loaded
  - Any instruction-following model works for text-only mode
  - A **vision-capable model** (e.g. LLaVA, Qwen-VL, Pixtral) is required when uploading a reference image

## Installation

1. Open the **Extensions** tab in WebUI.
2. Click **Install from URL**, paste this repository URL, and click Install.
3. Restart WebUI.

Or clone directly into your extensions folder:

```bash
cd sd-webui-forge-classic/extensions
git clone https://github.com/opparco/anima-prompter-forge
```

## Usage

1. Start LM Studio and load a model (Server → Start Server).
2. Open **txt2img** or **img2img** in WebUI.
3. Expand the **Anima Prompter** accordion near the top of the page.
4. Enter a concept (e.g. `"a girl reading under a cherry blossom tree at dusk"`).
5. Optionally upload a **Reference Image** to guide the visual style.
6. Adjust the **Post-process** overrides if needed (see below).
7. Click **Generate Prompt** — the positive prompt box and (if empty) the negative prompt box are filled automatically.
8. Click **Generate** to create the image.

## Post-process Overrides

These controls let you override specific fields after the LLM generates the base prompt:

| Control | Options | Description |
|---|---|---|
| **Period** | Generated / Fixed / None | Use the LLM's choice, pin a specific era, or strip the tag entirely |
| **Safety** | Generated / Fixed | Use the LLM's rating or force a specific level |
| **Artist tags** | Generated / Fixed / None | Use LLM-selected artists, provide your own list, or remove all artist tags |

Setting **Period** or **Safety** to **Fixed** shows a dropdown; setting **Artist tags** to **Fixed** shows a text field for a comma-separated list.

## Generated Prompt Format

The extension produces Anima-style comma-separated tags in this order:

```
{period}, {scores}, {quality}, {safety}, {subject}, {character}, {series}, {artists}, {tags}. {natural_language}
```

Example:

```
newest, score_9, score_8, score_7, masterpiece, best quality, safe, 1girl, @john doe, @jane smith, long hair, blue eyes, cherry blossoms, sunset. She sits beneath a canopy of falling petals, a worn paperback open in her hands.
```

- `period`: `newest` / `recent` / `mid` / `early` / `old` (the LLM may also output `year YYYY`; the **Fixed** dropdown covers the five keyword forms only)
- `safety`: `safe` / `sensitive` / `nsfw` / `explicit`
- Artist names are prefixed with `@` (duplicates deduplicated automatically)
- Tag underscores are converted to spaces

## Settings

Open **Settings → Anima Prompter** to configure:

| Setting | Default | Description |
|---|---|---|
| LM Studio base URL | `http://localhost:1234` | Base URL of your LM Studio server |
| Request timeout (seconds) | `60.0` | Maximum wait time per request (5–300 s) |

Changes take effect immediately without restarting WebUI.

## Development

### Running tests

```bash
python -m unittest tests.test_anima_prompter
```

Tests run standalone — no WebUI instance required.

### Linting

```bash
black .
ruff check .
```

### Architecture

```
anima_prompter/prompter.py   — pure Python core (no Gradio/WebUI dependencies)
scripts/anima_prompter.py    — Gradio/WebUI integration layer
tests/test_anima_prompter.py — unit tests
```
