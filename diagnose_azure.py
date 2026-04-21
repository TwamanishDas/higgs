"""
Azure AI Foundry — Standalone Diagnostic Tool
Run this independently to test connectivity before launching the widget.
Usage: python diagnose_azure.py
"""

import json
import socket
import sys
from datetime import datetime

# ─── CONFIG — edit these directly ────────────────────────────────────────────
ENDPOINT   = "https://myopenaitwam.openai.azure.com"
API_KEY    = "0befbaa55e0047ea97ca934bf1e765eb"
DEPLOYMENT = "gpt-4o"
API_VERSION = "2024-12-01-preview"
# ─────────────────────────────────────────────────────────────────────────────

LOG_FILE = "diagnose_azure.log"
_results = []


def _log(level: str, msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts}  [{level:<8}]  {msg}"
    print(line)
    _results.append(line)


def _save_log():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(_results))
    print(f"\nLog saved to: {LOG_FILE}")


def _header(title: str):
    print()
    print("─" * 60)
    print(f"  {title}")
    print("─" * 60)
    _results.append(f"\n{'─'*60}\n  {title}\n{'─'*60}")


# ── Step 1: DNS resolution ────────────────────────────────────────────────────
def test_dns():
    _header("STEP 1 — DNS Resolution")
    host = ENDPOINT.replace("https://", "").replace("http://", "").split("/")[0]
    try:
        ip = socket.gethostbyname(host)
        _log("PASS", f"DNS resolved: {host} → {ip}")
        return True
    except socket.gaierror as e:
        _log("FAIL", f"DNS failed for {host}: {e}")
        _log("INFO", "Check internet/VPN connection on this VM.")
        return False


# ── Step 2: TCP connectivity ──────────────────────────────────────────────────
def test_tcp():
    _header("STEP 2 — TCP Connectivity (port 443)")
    host = ENDPOINT.replace("https://", "").replace("http://", "").split("/")[0]
    try:
        sock = socket.create_connection((host, 443), timeout=10)
        sock.close()
        _log("PASS", f"TCP connection to {host}:443 succeeded.")
        return True
    except Exception as e:
        _log("FAIL", f"TCP connection failed: {e}")
        _log("INFO", "Port 443 may be blocked by firewall on this VM.")
        return False


# ── Step 3: Import requests ───────────────────────────────────────────────────
def check_requests():
    _header("STEP 3 — Python 'requests' library")
    try:
        import requests
        _log("PASS", f"requests version: {requests.__version__}")
        return requests
    except ImportError:
        _log("FAIL", "requests not installed. Run: pip install requests")
        return None


# ── Step 4: Raw HTTP GET to endpoint root ─────────────────────────────────────
def test_http_get(requests):
    _header("STEP 4 — HTTP GET to endpoint root")
    try:
        resp = requests.get(ENDPOINT, timeout=10)
        _log("PASS", f"HTTP GET status: {resp.status_code}")
        _log("INFO", f"Response (first 200 chars): {resp.text[:200]}")
        return True
    except Exception as e:
        _log("FAIL", f"HTTP GET failed: {e}")
        return False


# ── Step 5: List deployments ──────────────────────────────────────────────────
def test_list_deployments(requests):
    _header("STEP 5 — List Deployments (verify API key)")
    url = f"{ENDPOINT.rstrip('/')}/openai/deployments?api-version={API_VERSION}"
    headers = {"api-key": API_KEY}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        _log("INFO", f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            deployments = [d.get("id", "?") for d in data.get("data", [])]
            _log("PASS", f"API key valid. Deployments found: {deployments}")
            if DEPLOYMENT not in deployments:
                _log("WARN", f"'{DEPLOYMENT}' not in deployment list — check deployment name!")
            else:
                _log("PASS", f"Deployment '{DEPLOYMENT}' confirmed.")
            return True
        elif resp.status_code == 401:
            _log("FAIL", "401 Unauthorized — API key is invalid or expired.")
        elif resp.status_code == 404:
            _log("FAIL", f"404 Not Found — endpoint or API version wrong. Response: {resp.text[:300]}")
        else:
            _log("FAIL", f"Unexpected status {resp.status_code}: {resp.text[:300]}")
        return False
    except Exception as e:
        _log("FAIL", f"Request failed: {e}")
        return False


# ── Step 6: Try multiple API versions ────────────────────────────────────────
def test_api_versions(requests):
    _header("STEP 6 — API Version Compatibility")
    versions = [
        "2024-12-01-preview",
        "2025-01-01-preview",
        "2024-10-01-preview",
        "2024-08-01-preview",
        "2024-05-01-preview",
        "2024-02-01",
    ]
    url_template = f"{ENDPOINT.rstrip('/')}/openai/deployments/{DEPLOYMENT}/chat/completions?api-version={{v}}"
    headers = {"api-key": API_KEY, "Content-Type": "application/json"}
    payload = {
        "messages": [{"role": "user", "content": "say hi"}],
        "max_completion_tokens": 5,
    }

    working_version = None
    for v in versions:
        try:
            resp = requests.post(url_template.format(v=v), headers=headers, json=payload, timeout=20)
            if resp.status_code == 200:
                _log("PASS", f"API version {v} → WORKS ✓")
                working_version = v
            elif resp.status_code == 400 and "api version" in resp.text.lower():
                _log("INFO", f"API version {v} → not supported")
            elif resp.status_code == 400 and "max_tokens" in resp.text.lower():
                _log("PASS", f"API version {v} → reached model (param issue, fixable) ✓")
                working_version = v
            elif resp.status_code == 401:
                _log("FAIL", f"API version {v} → 401 Unauthorized (bad API key)")
                break
            else:
                _log("INFO", f"API version {v} → {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            _log("FAIL", f"API version {v} → error: {e}")

    if working_version:
        _log("INFO", f"Recommended api_version for config.json: \"{working_version}\"")
    else:
        _log("WARN", "No working API version found. Check endpoint and deployment name.")
    return working_version


# ── Step 7: Full chat completion ──────────────────────────────────────────────
def test_chat_completion(requests, api_version: str):
    _header(f"STEP 7 — Full Chat Completion (api-version={api_version})")
    url = f"{ENDPOINT.rstrip('/')}/openai/deployments/{DEPLOYMENT}/chat/completions?api-version={api_version}"
    headers = {"api-key": API_KEY, "Content-Type": "application/json"}

    for attempt, payload in enumerate([
        {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant. Always respond with valid JSON."},
                {"role": "user", "content": "Reply with this exact JSON: {\"status\": \"ok\"}"},
            ],
            "max_completion_tokens": 5000,
            "response_format": {"type": "json_object"},
        },
        {
            "messages": [
                {"role": "user", "content": "Say hello in one word."},
            ],
            "max_completion_tokens": 5000,
        },
    ]):
        label = "with response_format=json_object" if attempt == 0 else "without response_format"
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=20)
            _log("INFO", f"Attempt {attempt+1} ({label}) → status {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                _log("INFO", f"Full response JSON:\n{json.dumps(data, indent=2)[:800]}")
                content = data["choices"][0]["message"]["content"]
                _log("PASS", f"Model replied: \"{content}\"")
                return True
            else:
                _log("INFO", f"Response body: {resp.text[:400]}")
        except Exception as e:
            _log("FAIL", f"Attempt {attempt+1} failed: {e}")

    _log("FAIL", "Chat completion failed on all attempts.")
    return False


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Azure AI Foundry — Diagnostic Tool")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    _results.append(f"Azure AI Foundry Diagnostic\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    _log("INFO", f"Endpoint   : {ENDPOINT}")
    _log("INFO", f"Deployment : {DEPLOYMENT}")
    _log("INFO", f"API Version: {API_VERSION}")

    if not test_dns():
        _save_log(); input("\nPress Enter to exit..."); sys.exit(1)

    if not test_tcp():
        _save_log(); input("\nPress Enter to exit..."); sys.exit(1)

    requests = check_requests()
    if not requests:
        _save_log(); input("\nPress Enter to exit..."); sys.exit(1)

    test_http_get(requests)
    test_list_deployments(requests)
    working_version = test_api_versions(requests)

    use_version = working_version or API_VERSION
    test_chat_completion(requests, use_version)

    print()
    print("=" * 60)
    print("  Diagnosis complete. See diagnose_azure.log for full report.")
    print("=" * 60)
    _save_log()
    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
