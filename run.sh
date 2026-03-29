#!/bin/bash
# Launch Chrome with remote debugging and run the LinkedIn Easy Apply bot

/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 &

CHROME_PID=$!
echo "Chrome starting (PID $CHROME_PID)..."

# Poll the debug port until Chrome is ready (up to 30 seconds)
for i in $(seq 1 30); do
  if curl -s http://127.0.0.1:9222/json/version > /dev/null 2>&1; then
    echo "Chrome is ready on port 9222."
    break
  fi
  sleep 1
done

if ! curl -s http://127.0.0.1:9222/json/version > /dev/null 2>&1; then
  echo "ERROR: Chrome did not start within 30 seconds."
  kill $CHROME_PID 2>/dev/null
  exit 1
fi

echo ""
echo "==> Please log into LinkedIn in the Chrome window if needed."
read -p "==> Press Enter when you're logged in and ready to start... "

# Activate venv and run
source "$(dirname "$0")/linkedin-bot-env/bin/activate"
python3 "$(dirname "$0")/linkedin_easy_apply.py"

echo "Done. Chrome is still running (close it manually if desired)."
