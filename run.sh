#!/bin/bash
# Launch Chrome with remote debugging, wait for it, then run the bot

/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-debug-profile &

CHROME_PID=$!
echo "Chrome started (PID $CHROME_PID), waiting for it to be ready..."
sleep 3

# Activate venv and run
source "$(dirname "$0")/linkedin-bot-env/bin/activate"
python3 "$(dirname "$0")/linkedin_easy_apply.py"

# After bot finishes, kill Chrome
kill $CHROME_PID 2>/dev/null
echo "Done. Chrome closed."
