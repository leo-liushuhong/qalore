#!/usr/bin/env python3
"""
probe_hook.py - Probe Claude Code Stop Hook stdin content.
Robust version: writes marker first, reads stdin with timeout thread (Windows-safe).
"""
import sys
import json
import threading
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

output_path = Path.home() / ".claude" / "probe_hook_output.json"
ts = datetime.now().strftime('%H:%M:%S')

# --- Step 1: write marker immediately, before any stdin read ---
with open(output_path, "w", encoding="utf-8") as f:
    f.write(json.dumps({"probe_started": ts}))

# --- Step 2: read stdin with 3-second timeout (thread, Windows-safe) ---
raw_holder = [None]
err_holder = [None]

def _read():
    try:
        raw_bytes = sys.stdin.buffer.read()
        raw_holder[0] = raw_bytes.decode('utf-8', errors='replace')
    except Exception as e:
        err_holder[0] = str(e)

t = threading.Thread(target=_read, daemon=True)
t.start()
t.join(timeout=3.0)

raw = raw_holder[0] if raw_holder[0] is not None else ""
read_err = err_holder[0]
timed_out = raw_holder[0] is None and read_err is None

# --- Step 3: overwrite file with actual result ---
with open(output_path, "w", encoding="utf-8") as f:
    f.write(raw if raw.strip() else "{}")

# --- Step 4: build summary ---
lines = []
lines.append(f"[probe] Hook fired at {ts}")
lines.append(f"[probe] stdin timed_out={timed_out}, length={len(raw)} chars")

if read_err:
    lines.append(f"[probe] stdin read error: {read_err}")
elif timed_out:
    lines.append("[probe] stdin read timed out after 3s (no data piped)")
elif not raw.strip():
    lines.append("[probe] stdin is empty")
else:
    try:
        data = json.loads(raw)
        keys = list(data.keys())
        lines.append(f"[probe] Top-level keys: {keys}")

        if "usage" in data:
            lines.append(f"[probe] FOUND usage: {json.dumps(data['usage'])}")
        else:
            lines.append("[probe] NO usage field at top level")

        found = []
        def search(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    cur = f"{path}.{k}" if path else k
                    if any(w in k.lower() for w in ["token", "usage", "cost", "cache"]):
                        found.append((cur, v))
                    search(v, cur)
            elif isinstance(obj, list):
                for i, item in enumerate(obj[:5]):
                    search(item, f"{path}[{i}]")
        search(data)

        if found:
            lines.append("[probe] Token/usage fields found:")
            for p, v in found:
                lines.append(f"  {p} = {v}")
        else:
            lines.append("[probe] No token/usage/cache/cost fields found")

    except json.JSONDecodeError:
        lines.append(f"[probe] stdin not JSON. Raw: {raw[:200]}")

lines.append(f"[probe] Full content -> {output_path}")

# Output JSON systemMessage so Claude Code shows it in UI
print(json.dumps({"systemMessage": "\n".join(lines)}, ensure_ascii=False))
