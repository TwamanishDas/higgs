import json
import sys
import requests
import logger

logger.setup()
CONFIG_FILE = "config.json"


def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        print("[FAIL] config.json not found. Make sure you run this from the desktop-companion folder.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[FAIL] config.json is not valid JSON: {e}")
        sys.exit(1)


def test_connection(endpoint: str, api_key: str, deployment: str, api_version: str):
    print(f"  Endpoint   : {endpoint}")
    print(f"  Deployment : {deployment}")
    print(f"  API Version: {api_version}")
    print()

    url = f"{endpoint.rstrip('/')}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "messages": [
            {"role": "user", "content": "Reply with exactly one word: hello"}
        ],
        "max_completion_tokens": 10,
    }

    print(f"  Calling: {url}")
    logger.log.info(f"Testing connection | url={url}")
    print()

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        logger.log.info(f"Response status: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            reply = data["choices"][0]["message"]["content"].strip()
            print(f"  [PASS] Connection successful!")
            print(f"  Model reply: \"{reply}\"")
            logger.log.info(f"Connection test PASSED | model reply: {reply}")
            return True

        elif resp.status_code == 401:
            msg = "Authentication failed (401) — API key is wrong or expired."
            print(f"  [FAIL] {msg}")
            print(f"  Response: {resp.text[:300]}")
            logger.log.error(f"Connection test FAILED | {msg} | {resp.text[:300]}")

        elif resp.status_code == 404:
            msg = "Deployment not found (404) — check deployment name in config.json."
            print(f"  [FAIL] {msg}")
            print(f"  Response: {resp.text[:300]}")
            logger.log.error(f"Connection test FAILED | {msg} | {resp.text[:300]}")

        elif resp.status_code == 400:
            body = resp.text[:300]
            if "api version" in body.lower():
                msg = "API version not supported (400) — try a different api_version in config.json."
            else:
                msg = f"Bad request (400): {body}"
            print(f"  [FAIL] {msg}")
            logger.log.error(f"Connection test FAILED | {msg}")

        else:
            msg = f"HTTP {resp.status_code}: {resp.text[:300]}"
            print(f"  [FAIL] {msg}")
            logger.log.error(f"Connection test FAILED | {msg}")

        return False

    except requests.exceptions.ConnectionError as e:
        msg = "Cannot reach endpoint — check your internet/VPN connection."
        print(f"  [FAIL] {msg}")
        logger.log.error(f"Connection test FAILED | {msg} | {e}")
        return False
    except requests.exceptions.Timeout:
        msg = "Request timed out after 20 seconds."
        print(f"  [FAIL] {msg}")
        logger.log.error(f"Connection test FAILED | {msg}")
        return False
    except Exception as e:
        print(f"  [FAIL] Unexpected error: {e}")
        logger.log.error(f"Connection test FAILED | Unexpected error: {e}")
        return False


def main():
    print("=" * 55)
    print("  Desktop Companion — Azure Connection Test")
    print("=" * 55)
    print()

    cfg = load_config()
    az = cfg.get("azure", {})

    endpoint   = az.get("endpoint", "")
    api_key    = az.get("api_key", "")
    deployment = az.get("deployment", "")
    api_version = az.get("api_version", "2024-12-01-preview")

    if not endpoint or endpoint == "YOUR_AZURE_AI_FOUNDRY_ENDPOINT":
        print("[FAIL] endpoint is not set in config.json")
        sys.exit(1)
    if not api_key or api_key == "YOUR_AZURE_AI_FOUNDRY_API_KEY":
        print("[FAIL] api_key is not set in config.json")
        sys.exit(1)
    if not deployment:
        print("[FAIL] deployment is not set in config.json")
        sys.exit(1)

    success = test_connection(endpoint, api_key, deployment, api_version)

    print()
    print("=" * 55)
    if success:
        print("  All good! Run run.bat to start the widget.")
    else:
        print("  Fix the issue above, then re-run test_connection.bat")
    print("=" * 55)
    print()
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()
