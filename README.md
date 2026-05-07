# Anima Prompter Forge

An AlwaysVisible Forge/WebUI extension that generates Anima-style prompts from a concept string and optional reference image via LM Studio, then applies the result to the active prompt box.

## Features

- Works in both `txt2img` and `img2img`
- Generates a structured Anima prompt from LM Studio `/v1/chat/completions`
- Supports optional vision input through a dedicated reference image upload
- Replaces the current positive prompt only; generation still uses the standard WebUI `Generate` button

## Settings

Open `Settings -> Anima Prompter` and configure:

- `LM Studio base URL`
- `Request timeout`

Default LM Studio URL: `http://192.168.11.21:1234`
