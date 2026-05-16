"""
IBM Bob API deep probe.
Run: python scripts/check_bob.py
"""
import os, sys
from dotenv import load_dotenv
import requests

load_dotenv()

api_key = os.environ.get("IBM_BOB_API_KEY", "").strip()
if not api_key:
    sys.exit("ERROR: IBM_BOB_API_KEY not set")

print(f"API Key: {api_key[:24]}...\n")

MINI_CHAT = {"messages": [{"role": "user", "content": "ping"}], "max_tokens": 5}

# --- 1. Inspect the 405 responses for Allow header + body ---
print("=== 1. 405 response details on bob.ibm.com ===")
for path in ["/api/v1/chat/completions", "/api/v1/chat", "/api/chat", "/api/ask"]:
    url = "https://bob.ibm.com" + path
    for auth in [
        {"Authorization": f"Bearer {api_key}"},
        {"x-api-key": api_key},
        {"Authorization": f"ApiKey {api_key}"},
    ]:
        r = requests.post(url, headers={**auth, "Content-Type": "application/json"}, json=MINI_CHAT, timeout=10)
        allow = r.headers.get("Allow", "—")
        ct    = r.headers.get("Content-Type", "—")
        body  = r.text[:120].replace("\n", " ")
        is_html = body.lstrip().startswith("<!DOCTYPE") or "<html" in body[:60]
        print(f"  POST {path:35s} → {r.status_code}  Allow:{allow}  CT:{ct}")
        if not is_html:
            print(f"    Body: {body}")

# --- 2. Try other subdomains ---
print("\n=== 2. Subdomain probes ===")
subdomains = [
    "inference.bob.ibm.com",
    "api-inference.bob.ibm.com",
    "chat.bob.ibm.com",
    "hackathon.bob.ibm.com",
    "llm.bob.ibm.com",
    "gateway.bob.ibm.com",
]
for host in subdomains:
    url = f"https://{host}/v1/chat/completions"
    try:
        r = requests.post(url, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                          json=MINI_CHAT, timeout=6)
        body = r.text[:200].replace("\n", " ")
        is_html = body.lstrip().startswith("<!DOCTYPE") or "<html" in body[:60]
        tag = "[HTML]" if is_html else "[API ✓]"
        print(f"  {host:40s} → {r.status_code} {tag}")
        if not is_html:
            print(f"    {body}")
    except requests.exceptions.ConnectionError:
        print(f"  {host:40s} → DNS fail")
    except Exception as e:
        print(f"  {host:40s} → {e}")

# --- 3. Decode the key for clues ---
print("\n=== 3. Key structure ===")
parts = api_key.split("_")
print(f"  Prefix segments: {parts[:4]}")
# e.g. bob / prod / bob-user / <instance?> / <token>
print()
print("Done.")
