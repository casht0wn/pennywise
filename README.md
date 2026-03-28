# Pennywise

Pennywise is a Flet-based personal finance app focused on one thing: helping you reliably track recurring bills.

It combines automatic recurring-payment detection with manual controls, so you can keep your bill list accurate even when transaction labels are inconsistent.

## What it does

- Detects recurring payments from transaction history
- Tracks known bills and expected due dates
- Helps notify you about upcoming payments
- Supports manual bill creation and bill-payment tagging
- Includes CSV import support for bringing in transaction data

## Tech stack

- Python
- Flet (desktop + web UI)
- Local app storage under `storage/`

## Project layout

```
src/
	main.py                 # app entry point
	pages/                  # UI pages (dashboard, bills, transactions, etc.)
	services/               # business logic (db, labeling, notifications, detection)
storage/
	data/                   # persisted app data
	temp/                   # temporary files
```

## Quick start

### Prerequisites

- Python 3.10+
- One of:
	- `uv` (recommended)
	- `poetry`

### Option 1: Run with uv

Run as a desktop app:

```bash
uv run flet run
```

Run as a web app:

```bash
uv run flet run --web
```

### Option 2: Run with Poetry

Install dependencies:

```bash
poetry install
```

Run as a desktop app:

```bash
poetry run flet run
```

Run as a web app:

```bash
poetry run flet run --web
```

For additional runtime details, see the Flet [Getting Started Guide](https://flet.dev/docs/getting-started/).

## Typical workflow

1. Import transactions (for example via CSV import).
2. Review automatically detected recurring payments.
3. Confirm or adjust bill groupings.
4. Add manual bills when needed.
5. Monitor upcoming payments from the dashboard.

## Build packages

### Android

```bash
flet build apk -v
```

Android packaging/signing docs: [Android Packaging Guide](https://flet.dev/docs/publish/android/).

### iOS

```bash
flet build ipa -v
```

iOS packaging/signing docs: [iOS Packaging Guide](https://flet.dev/docs/publish/ios/).

### macOS

```bash
flet build macos -v
```

macOS packaging docs: [macOS Packaging Guide](https://flet.dev/docs/publish/macos/).

### Linux

```bash
flet build linux -v
```

Linux packaging docs: [Linux Packaging Guide](https://flet.dev/docs/publish/linux/).

### Windows

```bash
flet build windows -v
```

Windows packaging docs: [Windows Packaging Guide](https://flet.dev/docs/publish/windows/).

## Troubleshooting

- If dependencies fail to resolve, re-run install in a clean virtual environment.
- If the app opens but data looks stale, clear temporary files in `storage/temp/` and relaunch.
- If build commands fail, verify platform-specific requirements in the relevant Flet packaging guide.

## Roadmap ideas

- Better recurring-payment confidence scoring
- Smarter vendor-name normalization
- More configurable reminder timing
- Export and backup helpers