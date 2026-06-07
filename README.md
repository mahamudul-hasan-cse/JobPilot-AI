<div align="center">

# JobPilot AI

**Intelligent LinkedIn Easy Apply automation with AI-powered job matching**

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-AGPL--3.0-green)](LICENSE)
[![LinkedIn](https://img.shields.io/badge/Platform-LinkedIn-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/)
[![Author](https://img.shields.io/badge/Author-Md.%20Mahamudul%20Hasan-purple)](https://github.com/mahamudul-hasan-cse)

*Automate Easy Apply, score job relevance with Gemini, and track every application — built by Md. Mahamudul Hasan.*

</div>

---

## ✨ Key Features

- 🤖 **Easy Apply automation** — Fills LinkedIn application forms automatically
- 🎯 **AI relevance scoring** — Gemini scores each job 0–100; skips low-match listings
- 📝 **AI cover letter tailoring** — Generates per-job cover letters from your resume text
- 📊 **Applied-jobs dashboard** — Flask UI with relevance scores and external link tracking
- 🌐 **Multi-provider AI** — Gemini (default), OpenAI, and DeepSeek supported
- 🕵️ **Stealth browser mode** — Uses undetected-chromedriver to reduce bot detection
- 📁 **CSV history** — Full audit trail of applied, skipped, and failed jobs

---

## 🛠 Tech Stack

| Category | Technologies |
|----------|--------------|
| Language | Python 3.11+ |
| Browser automation | Selenium, undetected-chromedriver |
| AI | Google Gemini, OpenAI SDK, DeepSeek |
| Web dashboard | Flask, Flask-CORS |
| Desktop automation | PyAutoGUI |
| Data storage | CSV (local files) |

---

## 📋 Prerequisites

- **Windows 10/11** (primary platform; Linux/macOS partially supported)
- **Python 3.11+** — [python.org/downloads](https://www.python.org/downloads/)
- **Google Chrome** (latest stable)
- **LinkedIn account** with Easy Apply access
- **Gemini API key** (optional, for AI features) — [Google AI Studio](https://aistudio.google.com/apikey)

---

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/mahamudul-hasan-cse/JobPilot-AI.git
cd JobPilot-AI
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure credentials

```bash
copy config\secrets.example.py config\secrets.py
copy config\personals.example.py config\personals.py
copy config\questions.example.py config\questions.py
```

Edit `config/secrets.py`:
- Set your LinkedIn `username` and `password`
- Add your Gemini `llm_api_key`
- Set `ai_provider = "gemini"`

Edit `config/personals.py` with your real name, phone, and address.

### 4. Add your resume

Place your PDF resume at:

```
all resumes/default/resume.pdf
```

Paste your resume as plain text in `config/questions.py` → `base_resume_text` for AI tailoring.

### 5. (Optional) Install ChromeDriver

Run as Administrator on Windows:

```
setup\windows-setup.bat
```

---

## ⚙️ Configuration

| File | Purpose |
|------|---------|
| `config/secrets.py` | LinkedIn login, API keys, AI feature flags |
| `config/personals.py` | Name, phone, address, EEO answers |
| `config/questions.py` | Resume path, salary, cover letter, AI resume text |
| `config/search.py` | Job titles, location, filters, blacklists |
| `config/settings.py` | Bot behavior, browser timeouts, CSV paths |

### AI setup (`config/secrets.py`)

```python
use_AI = True
ai_provider = "gemini"
llm_api_key = "YOUR_GEMINI_API_KEY"
llm_model = "gemini-2.0-flash"

use_relevance_scoring = True
ai_relevance_threshold = 65
strict_relevance_scoring = False
```

### Job search (`config/search.py`)

```python
search_terms = ["AI Engineer", "ML Engineer"]
location = "Bangladesh"
easy_apply_only = True
switch_number = 3   # Max successful applies per run
```

> See [SECURITY.md](SECURITY.md) for what never to commit or share.

---

## ▶️ How to Run

### Bot (main application)

**Windows — double-click:**

| File | Description |
|------|-------------|
| `Start JobPilot AI.vbs` | Recommended — opens console and runs the bot |
| `start_jobpilotai.bat` | Command Prompt launcher |

**Or from terminal:**

```bash
python main.py
```

The launcher will: close Chrome → validate config → open guest Chrome → log into LinkedIn → apply to jobs.

### Dashboard (optional)

```bash
python app.py
```

Open **http://localhost:5000** to view applied jobs.

### Preflight check

```bash
python scripts/preflight.py
```

---

## 📂 Project Structure

```
JobPilot AI/
├── main.py                      # Bot entry point
├── app.py                       # Flask dashboard entry point
├── requirements.txt
├── README.md
├── CHANGELOG.md
├── COPYRIGHT
├── LICENSE
├── SECURITY.md
├── .gitignore
├── .env.example
├── Start JobPilot AI.vbs        # Windows double-click launcher
├── start_jobpilotai.bat         # Windows batch launcher
│
├── config/                      # User settings (*.py gitignored except *.example.py)
│   ├── secrets.example.py
│   ├── personals.example.py
│   ├── questions.example.py
│   ├── search.py
│   └── settings.py
│
├── modules/                     # Core application code
│   ├── auth.py                  # LinkedIn login
│   ├── helpers.py               # Utilities and logging
│   ├── validator.py             # Config validation
│   ├── browser/                 # Chrome session + Selenium helpers
│   ├── ai/                      # Gemini, scoring, tailoring, factory
│   └── jobs/                    # Applier, form filler, filters, logger
│
├── scripts/
│   └── preflight.py             # Pre-run config/deps check
│
├── setup/                       # One-time environment setup
│   ├── windows-setup.bat
│   ├── windows-setup.ps1
│   ├── setup.sh
│   └── start_jobpilotai.ps1
│
├── web/
│   └── templates/
│       └── index.html           # Dashboard UI
│
├── all excels/                  # CSV history (gitignored, created at runtime)
├── all resumes/                 # Resume files (gitignored)
└── logs/                        # Debug logs (gitignored)
```
---

## 🗺 Roadmap

- [ ] Multi-account support with profile switching
- [ ] PostgreSQL / SQLite backend for application history
- [ ] Email notifications on apply completion
- [ ] Docker container for one-command deployment
- [ ] Improved Easy Apply button detection (Next / Review / Submit)
- [ ] Scheduled runs via Windows Task Scheduler integration
- [ ] Application analytics dashboard (success rate, company stats)
- [ ] Support for Indeed and Glassdoor

---

## 👤 Author

**Md. Mahamudul Hasan**

- GitHub: [@mahamudul-hasan-cse](https://github.com/mahamudul-hasan-cse)

---

## 📄 License

This project is licensed under the **GNU Affero General Public License v3.0**.

See [LICENSE](LICENSE) for the full text.

Copyright (C) 2026 Md. Mahamudul Hasan

---

<div align="center">

⭐ Star this repo if JobPilot AI helps your job search!

</div>
