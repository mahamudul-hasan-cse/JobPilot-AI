# JobPilot AI — setup helper (Bash / Git Bash on Windows)
# Author: Md. Mahamudul Hasan

echo "JobPilot AI: checking Python..."
if ! command -v python &> /dev/null && ! command -v py &> /dev/null; then
    echo "Install Python from https://www.python.org/downloads/"
    exit 1
fi

pip install -r requirements.txt

JSON_URL="https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
curl -sS "$JSON_URL" -o /tmp/chrome-for-testing.json
DOWNLOAD_URL=$(python -c "import json; d=json.load(open('/tmp/chrome-for-testing.json')); print(next(x['url'] for x in d['channels']['Stable']['downloads'] if x['platform']=='win64' and 'chromedriver' in x['url']))")
curl -o /tmp/chromedriver.zip "$DOWNLOAD_URL"
unzip -o /tmp/chromedriver.zip -d /tmp/chromedriver_extract
mkdir -p "/c/Program Files/Google/Chrome"
cp /tmp/chromedriver_extract/chromedriver-win64/chromedriver.exe "/c/Program Files/Google/Chrome/chromedriver.exe"
echo "JobPilot AI setup complete."
