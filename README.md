# LinkedIn Easy Apply Bot

Selenium-based automation bot that applies to LinkedIn jobs using the Easy Apply flow. Attaches to a running Chrome instance via remote debugging and walks through multi-page application modals automatically.

## Features

- Searches LinkedIn Jobs with configurable keywords, location, and filters
- Auto-fills multi-page Easy Apply forms (text, dropdowns, radios, checkboxes, textareas, file uploads)
- Context-aware form answers (visa sponsorship, work authorization, years of experience, etc.)
- Verifies each job card click actually loaded a new job before proceeding
- Detects validation errors and stuck pages — aborts gracefully instead of looping
- Skips jobs already applied to
- Unchecks "Follow company" before submission
- Random delays between actions to mimic human behavior
- Graceful shutdown on Ctrl+C (finishes current job, prints summary)
- Detailed logging to timestamped log files
- External config via `config.json` (no need to edit source code)

## Prerequisites

- Python 3
- Google Chrome
- ChromeDriver (must match your Chrome version)

## Setup

```bash
# Clone the repo
git clone https://github.com/siavashahmadi/linkedin-easy-apply-bot.git
cd linkedin-easy-apply-bot

# Create and activate virtual environment
python3 -m venv linkedin-bot-env
source linkedin-bot-env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Option 1: Manual (recommended)

```bash
# 1. Close Chrome completely
# 2. Relaunch with remote debugging enabled:
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# 3. Log into LinkedIn in that Chrome window

# 4. In a separate terminal:
source linkedin-bot-env/bin/activate
python3 linkedin_easy_apply.py
```

### Option 2: Helper script

```bash
./run.sh
```

`run.sh` launches Chrome, waits for it to be ready, and prompts you to log into LinkedIn before starting the bot.

## Configuration

Edit the `CONFIG` dict at the top of `linkedin_easy_apply.py`, or create a `config.json` in the project root to override any values without editing source code:

```json
{
    "search_keywords": "software engineer",
    "location": "San Francisco",
    "max_applications": 10,
    "resume_path": "/path/to/resume.pdf",
    "default_experience_text": "Your custom experience summary here."
}
```

### Available Settings

| Key | Default | Description |
|-----|---------|-------------|
| `search_keywords` | Complex OR query | Job search terms |
| `location` | `"New York City"` | Search location |
| `experience_levels` | `"2,3,4"` | 2=Entry, 3=Associate, 4=Mid-Senior |
| `job_type` | `"F"` | F=Full-time |
| `work_type` | `""` | 1=On-site, 2=Remote, 3=Hybrid (empty=all) |
| `time_posted` | `"r86400"` | r86400=24h, r604800=week, r2592000=month |
| `max_applications` | `50` | Cap per run (LinkedIn daily limit is ~50) |
| `min_delay` / `max_delay` | `2` / `5` | Random delay range between actions (seconds) |
| `chrome_debug_port` | `9222` | Must match Chrome launch flag |
| `resume_path` | `""` | Path to resume PDF for file upload fields |
| `default_experience_text` | Canned blurb | Text used for experience/relevant textareas |

## How It Works

1. Connects to Chrome via remote debugging port
2. Navigates to LinkedIn Jobs search with Easy Apply + Most Recent filters
3. Iterates through job cards on each page:
   - Clicks each card and verifies the detail pane actually updated
   - Skips if already applied
   - Clicks the Easy Apply button
   - Walks through each page of the modal, filling form fields
   - Detects validation errors or stuck pages and aborts if needed
   - Submits and dismisses post-apply dialogs
4. Paginates through results until `max_applications` is reached

### Form Filling Strategy

- **Text/number inputs**: Context-aware defaults — "5" for years of experience, "0" for salary, skips URL fields, "1" as final fallback
- **Dropdowns**: Context-aware — "No" for visa/sponsorship, "Yes" for work authorization, first option as fallback
- **Radio buttons**: Same context-aware logic as dropdowns
- **Checkboxes**: Checks agreement/T&C boxes only
- **Textareas**: Configurable experience blurb or "N/A"
- **File uploads**: Uploads `resume_path` if configured

## Logging

Each run creates a timestamped log file in the project root:
```
linkedin_apply_YYYYMMDD_HHMMSS.log
```

## Disclaimer

Use at your own risk. Automated interaction with LinkedIn may violate their Terms of Service. This tool is for educational purposes.
