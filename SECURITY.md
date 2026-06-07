# Security Policy

**JobPilot AI** — Author: Md. Mahamudul Hasan

## What Never to Share

The following contain sensitive data. **Do not commit, paste, or share them publicly:**

| Item | Location |
|------|----------|
| LinkedIn email and password | `config/secrets.py` |
| AI API keys (Gemini, OpenAI, DeepSeek) | `config/secrets.py` |
| Personal profile data | `config/personals.py` |
| Application answers, resume text, contact info | `config/questions.py` |
| Application history | `all excels/*.csv` |
| Debug logs (may contain form answers) | `logs/log.txt`, `logs/screenshots/` |
| Resume files | `all resumes/` |
| Environment files | `.env` |

## Safe to Share

- `config/secrets.example.py` — template with placeholders only
- `config/personals.example.py` — generic example values
- `config/questions.example.py` — generic application answer templates
- `.env.example` — placeholder environment variables
- Source code under `modules/`, `config/*.example.py`, `main.py`, `app.py`

## Before Publishing to GitHub

1. Confirm `config/secrets.py`, `config/personals.py`, and `config/questions.py` are listed in `.gitignore`.
2. Use `*.example.py` templates with placeholder credentials — never real passwords or API keys.
3. Remove or rotate any API key that was ever committed to a public repository.
4. Do not include CSV exports or log files in commits.

## Reporting Vulnerabilities

If you discover a security issue in JobPilot AI, contact the author privately via GitHub:
[github.com/mahamudul-hasan-cse](https://github.com/mahamudul-hasan-cse)

Please do not open public issues for undisclosed credential leaks or exploit details.

## Responsible Use

- Automating LinkedIn applications may violate LinkedIn's Terms of Service.
- Use this tool at your own risk on your own account.
- Store credentials locally only; never hard-code them in files intended for version control.
