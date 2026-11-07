# Quick OCR

CLI tool that watches a folder for new PNG screenshots, runs **Tesseract OCR** to extract text, and optionally sends the text to **OpenAI** for structured answers—useful for automating screenshot-based Q&A workflows without a GUI.

## Highlights

- **Folder watcher** — one-shot or continuous mode (`--continuous`)
- **OCR-only mode** — extract and print text with no API key (`--ocr-only`)
- **Configurable paths** — env vars or CLI for input and processed folders
- **Graceful shutdown** — `Ctrl-C` stops the watcher cleanly
- **Poetry-packaged** — installable as `quick-ocr`

## Prerequisites

- Python 3.10+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed on your system and available on `PATH`
- OpenAI API key (only required when not using `--ocr-only`)

## Quick start

```bash
poetry install
cp .env.example .env
# Set OPENAI_API_KEY in .env when using LLM mode
```

Watch the default folder continuously:

```bash
poetry run quick-ocr --continuous --verbose
```

Use a custom screenshot folder:

```bash
poetry run quick-ocr ~/Desktop/questions --continuous
```

OCR without calling OpenAI:

```bash
poetry run quick-ocr --ocr-only
```

## Configuration

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key (required unless `--ocr-only`) |
| `SCREENSHOT_FOLDER` | Folder to watch for `.png` files (default: `~/Desktop/questions`) |
| `PROCESSED_FOLDER` | Where processed images are moved (default: `~/Desktop/processed`) |

CLI flags: `--api-key`, `--processed-folder`, `-v` / `--verbose`, `-c` / `--continuous`, `-o` / `--ocr-only`.

## How it works

```text
[Screenshot folder *.png] → Tesseract OCR → (optional) OpenAI chat completion → terminal output
                                                      ↓
                              move image → processed folder
```

1. Discover PNG files in the watch folder.
2. Extract text with Pillow + `pytesseract`.
3. Unless `--ocr-only`, send extracted text to OpenAI with a deterministic (temperature 0) academic-assistant prompt.
4. Move each processed file into the processed folder.

## Project layout

```text
quick_ocr/
├── quick_ocr/
│   ├── __init__.py
│   └── main.py          # Click CLI entrypoint
├── pyproject.toml
├── poetry.lock
├── .env.example
└── README.md
```

## Security

- Never commit `.env` or API keys.
- Sample screenshots under `quick_ocr/tests/` are for local experiments only and are gitignored.

## License

Personal initiative—use and adapt with attribution as you see fit.
