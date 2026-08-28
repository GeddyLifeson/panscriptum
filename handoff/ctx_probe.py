"""Does the num_ctx MISMATCH, on its own, close the local rung?

The standing diagnosis (orders a8464e348c5e and 505177847f43) is that `config.yaml` asks for
num_ctx=12288 while the resident runner serves qwen3:8b at context_length=4096, and that Ollama
holds a model at ONE context size -- so every Panscriptum request forces a 6 GB reload, a
foreign client immediately re-pins it at 4096, and nothing ever settles. That is a MECHANISM,
and it was inferred rather than demonstrated.

This demonstrates it or refutes it. The SAME trivial prompt is sent three times: once naming no
num_ctx at all (takes whatever is resident), once naming the resident 4096, once naming the
configured 12288. If the first two return in seconds and the third hangs, the mismatch is the
cause and the fix is a one-line config change plus a check that would have caught it. If all
three behave the same, the diagnosis is wrong and the real cause is elsewhere -- which is worth
just as much, because two orders currently name it.

Deliberately NOT run through `local_agent`: that adds the whole agent scaffold to the
measurement, and the question here is about one HTTP request.
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "http://localhost:11434/api/chat"
PROMPT = "Reply with the single word: ready"
TIMEOUT = 90


def ask(num_ctx):
    """One chat request. -> (seconds, verdict string). Never raises."""
    body = {"model": "qwen3:8b", "stream": False,
            "messages": [{"role": "user", "content": PROMPT}],
            "options": {"num_predict": 16}}
    if num_ctx is not None:
        body["options"]["num_ctx"] = num_ctx
    payload = os.path.join(HERE, "state", "_ctxprobe_%s.json" % (num_ctx or "none"))
    with open(payload, "w", encoding="utf-8") as fh:
        json.dump(body, fh)
    cmd = ["curl.exe", "-s", "--max-time", str(TIMEOUT), "-X", "POST", URL,
           "-H", "Content-Type: application/json", "--data-binary", "@" + payload]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                           timeout=TIMEOUT + 15)
        dt = time.time() - t0
        out = (p.stdout or "").strip()
        if not out:
            return dt, "NO RESPONSE (curl rc=%s) -- timed out or refused" % p.returncode
        try:
            got = json.loads(out)
        except ValueError:
            return dt, "UNPARSEABLE: " + out[:160]
        msg = (got.get("message") or {}).get("content", "")
        if got.get("error"):
            return dt, "ERROR: " + str(got["error"])[:160]
        return dt, "ok, %d chars of content" % len(msg)
    except subprocess.TimeoutExpired:
        return time.time() - t0, "HARD TIMEOUT"
    finally:
        try:
            os.remove(payload)
        except OSError:
            pass


def resident():
    cmd = ["curl.exe", "-s", "--max-time", "15", "http://localhost:11434/api/ps"]
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    try:
        models = json.loads(p.stdout or "{}").get("models") or []
    except ValueError:
        return None
    return [(m.get("name"), m.get("context_length")) for m in models]


def main():
    print("resident before:", resident())
    for ctx in (None, 4096, 12288, 4096):
        dt, verdict = ask(ctx)
        print("num_ctx=%-6s %7.1fs  %s" % (ctx, dt, verdict))
        print("   resident now:", resident())
    return 0


if __name__ == "__main__":
    sys.exit(main())
