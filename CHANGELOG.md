# Changelog

All notable changes to **JobPilot AI** are documented here.

## [1.1.0] — 2026-06-07

### Professional release polish — Md. Mahamudul Hasan

- Reorganized project structure (`web/templates/`, `docs/`, `scripts/`, `setup/`)
- Removed unused modules (`resumes/`, `javascript/unfollow_companies.js`, `__deprecated__/`)
- Full Python code quality pass: docstrings, type hints, PEP8, clean imports
- Professional README with badges, roadmap, and installation guide
- Pinned `requirements.txt` with grouped dependencies
- Added `SECURITY.md`, `.env.example`, and sanitized `secrets.example.py`
- Updated `.gitignore` for secrets, logs, CSVs, and resumes

## [1.0.0] — 2026-06-07

### JobPilot AI — Initial release by Md. Mahamudul Hasan

- Rebranded from upstream LinkedIn auto-applier to **JobPilot AI**
- Restructured monolith into modular architecture (`modules/jobs/`, `modules/ai/`, `modules/browser/`)
- Single entry point: `python main.py`
- Lazy Chrome session init (browser opens after config validation)
- **AI Job Relevance Scoring** via Google Gemini (0–100, configurable threshold)
- **AI Resume Tailoring** — per-job cover letters from `base_resume_text`
- Unified AI client factory (OpenAI, DeepSeek, Gemini)
- Applied jobs dashboard with Relevance Score column
- Config templates: `secrets.example.py`, `personals.example.py`
- Gemini as default AI provider

### Removed

- Legacy `runAiBot.py` entry point
- Duplicate modules: `open_chrome.py`, `clickers_and_finders.py`, `*Connections.py`
