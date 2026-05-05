"""
Check remaining quota for all configured Groq API keys.
Makes a minimal 1-token probe request to each key and reads rate-limit headers.

Run: python scripts/check_groq_quota.py
"""
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.config import get_settings

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
PROBE_MODEL = "llama-3.1-8b-instant"
PROBE_PAYLOAD = {
    "model": PROBE_MODEL,
    "messages": [{"role": "user", "content": "hi"}],
    "max_tokens": 1,
}

HEADER_MAP = {
    "x-ratelimit-limit-requests":           "RPM limit",
    "x-ratelimit-remaining-requests":       "RPM remaining",
    "x-ratelimit-reset-requests":           "RPM resets in",
    "x-ratelimit-limit-tokens":             "TPM limit",
    "x-ratelimit-remaining-tokens":         "TPM remaining",
    "x-ratelimit-reset-tokens":             "TPM resets in",
    "x-ratelimit-limit-tokens-day":         "TPD limit",
    "x-ratelimit-remaining-tokens-day":     "TPD remaining",
    "x-ratelimit-reset-tokens-day":         "TPD resets in",
    "x-ratelimit-limit-requests-day":       "RPD limit",
    "x-ratelimit-remaining-requests-day":   "RPD remaining",
}


def probe_key(label: str, api_key: str) -> None:
    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"  Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"{'='*50}")

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                GROQ_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=PROBE_PAYLOAD,
            )

        if resp.status_code == 401:
            print("  ERROR: Invalid API key (401 Unauthorized)")
            return
        if resp.status_code == 429:
            print("  RATE LIMITED — reading headers from 429 response")
        elif resp.status_code not in (200, 201):
            print(f"  ERROR: HTTP {resp.status_code}")
            print(f"  {resp.text[:200]}")
            return

        found_any = False
        for header, label_str in HEADER_MAP.items():
            val = resp.headers.get(header)
            if val is not None:
                found_any = True
                # Highlight near-zero remaining
                flag = " <-- LOW" if ("remaining" in header and val.lstrip("-").isdigit() and int(val) < 1000) else ""
                print(f"  {label_str:<28} {val}{flag}")

        if not found_any:
            print("  No rate-limit headers returned (Groq may not expose these for this model)")
            # Show all x-ratelimit-* headers as fallback
            rl_headers = {k: v for k, v in resp.headers.items() if "ratelimit" in k.lower()}
            if rl_headers:
                for k, v in rl_headers.items():
                    print(f"  {k}: {v}")

    except httpx.ConnectError:
        print("  ERROR: Could not connect to api.groq.com")
    except Exception as e:
        print(f"  ERROR: {e}")


def main() -> None:
    settings = get_settings()

    keys = [
        ("Key 1 (GROQ_API_KEY)", settings.groq_api_key),
    ]
    if settings.groq_api_key_2:
        keys.append(("Key 2 (GROQ_API_KEY_2)", settings.groq_api_key_2))
    if settings.groq_api_key_3:
        keys.append(("Key 3 (GROQ_API_KEY_3)", settings.groq_api_key_3))

    print(f"Checking {len(keys)} Groq API key(s)...")
    print(f"Probe model: {PROBE_MODEL}")

    for label, key in keys:
        probe_key(label, key)

    print(f"\n{'='*50}")
    print("Done.")


if __name__ == "__main__":
    main()
