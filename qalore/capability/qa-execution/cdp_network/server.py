#!/usr/bin/env python3
"""
CDP Network MCP Server — Real-time HTTP request interception via Chrome DevTools Protocol.

Launch Chrome with remote debugging, connect via CDP WebSocket, monitor the Network
domain in real-time, and expose captured requests as MCP tools.

Works alongside Playwright MCP independently — Playwright handles UI, this handles API.

Usage:
    python server.py

Requirements:
    pip install websocket-client requests
    Chrome installed at standard path
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Optional

import requests
import websocket

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CHROME_DEBUG_PORT = 9222

# Chrome detection
_CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Chromium\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    "google-chrome",
    "chromium",
    "chromium-browser",
]


def find_chrome() -> Optional[str]:
    for path in _CHROME_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


# ---------------------------------------------------------------------------
# CDP Network Monitor (core engine — sync, runs in background thread)
# ---------------------------------------------------------------------------


class CDPNetworkMonitor:
    """Connects to a Chrome instance via CDP and captures all network traffic."""

    def __init__(self) -> None:
        self.ws: Optional[websocket.WebSocket] = None
        self.requests: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._alive = False
        self._browser: Optional[subprocess.Popen] = None
        self._next_cmd_id = 1000
        self._pending_bodies: dict[int, str] = {}  # cmd_id → requestId

    # -- Chrome lifecycle --------------------------------------------------

    def launch_chrome(self) -> None:
        chrome = find_chrome()
        if not chrome:
            raise RuntimeError(
                "Chrome not found. Set CHROME_PATH env var to the chrome.exe location."
            )

        import tempfile

        profile_dir = tempfile.mkdtemp(prefix="cdp-chrome-")

        cmd = [
            chrome,
            f"--remote-debugging-port={CHROME_DEBUG_PORT}",
            "--remote-allow-origins=*",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            f"--user-data-dir={profile_dir}",
        ]
        self._browser = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        time.sleep(3)

    def is_chrome_alive(self) -> bool:
        try:
            requests.get(f"http://localhost:{CHROME_DEBUG_PORT}/json/version", timeout=2)
            return True
        except Exception:
            return False

    def connect(self, url: str | None = None) -> dict[str, Any]:
        """Connect to Chrome CDP, optionally navigate to *url*."""
        # Ensure Chrome is running
        if not self.is_chrome_alive():
            self.launch_chrome()

        # Resolve a debuggable page
        resp = requests.get(
            f"http://localhost:{CHROME_DEBUG_PORT}/json", timeout=5
        )
        pages = resp.json()
        page_targets = [p for p in pages if p["type"] == "page"]

        if not page_targets:
            resp2 = requests.get(
                f"http://localhost:{CHROME_DEBUG_PORT}/json/new?about:blank",
                timeout=5,
            )
            page_targets = [resp2.json()]

        ws_url = page_targets[0]["webSocketDebuggerUrl"]

        # WebSocket handshake
        self.ws = websocket.create_connection(ws_url, timeout=10)
        self._alive = True

        # Enable Network domain (capture post data up to 64 KB)
        self._send_cdp("Network.enable", {"maxPostDataSize": 65536})
        self._send_cdp("Page.enable")
        time.sleep(0.5)  # Let Chrome process the enable commands

        # Background listener thread
        t = threading.Thread(target=self._recv_loop, daemon=True)
        t.start()

        # Navigate if requested
        if url:
            self._send_cdp("Page.navigate", {"url": url})

        return {"id": page_targets[0]["id"], "url": page_targets[0].get("url", "")}

    # -- CDP helpers -------------------------------------------------------

    def _send_cdp(self, method: str, params: dict | None = None) -> int:
        """Send a CDP command; return the command id."""
        cid = self._next_cmd_id
        self._next_cmd_id += 1
        msg = {"id": cid, "method": method, "params": params or {}}
        if self.ws:
            self.ws.send(json.dumps(msg))
        return cid

    # -- Background listener -----------------------------------------------

    def _recv_loop(self) -> None:
        """Continuously read CDP messages."""
        while self._alive and self.ws:
            try:
                self.ws.settimeout(0.3)
                raw = self.ws.recv()
                if not raw:
                    continue
                # Parse JSON directly (CDP sends one complete message per frame)
                try:
                    self._dispatch(json.loads(raw))
                except json.JSONDecodeError:
                    pass
            except websocket.WebSocketTimeoutException:
                continue
            except Exception:
                if self._alive:
                    break

    def _dispatch(self, msg: dict) -> None:
        """Route CDP event or command response."""
        # Command response (has "id" and "result" or "error")
        msg_id = msg.get("id")
        if msg_id is not None:
            rid = self._pending_bodies.pop(msg_id, None)
            if rid is None:
                return
            with self._lock:
                if rid not in self.requests:
                    return
                if "result" in msg:
                    body = msg["result"].get("body", "")
                    self.requests[rid]["body"] = body if body else "(empty)"
                elif "error" in msg:
                    self.requests[rid]["body"] = f"(CDP: {msg['error'].get('message','?')})"
            return

        # CDP event
        method = msg.get("method", "")
        params = msg.get("params", {})
        if not method:
            return

        handler = getattr(self, f"_on_{self._safe_attr(method)}", None)
        if handler:
            handler(params)

    @staticmethod
    def _safe_attr(method: str) -> str:
        return method.replace(".", "_").replace("-", "_")

    # -- Network event handlers -------------------------------------------

    def _on_Network_requestWillBeSent(self, params: dict) -> None:
        rid = params["requestId"]
        req = params["request"]
        with self._lock:
            self.requests[rid] = {
                "request": {
                    "url": req["url"],
                    "method": req["method"],
                    "headers": req.get("headers", {}),
                    "postData": req.get("postData", ""),
                },
                "response": None,
                "body": None,
                "type": params.get("type", ""),
                "timestamp_ns": params.get("timestamp", 0),
            }

    def _on_Network_responseReceived(self, params: dict) -> None:
        rid = params["requestId"]
        resp = params["response"]
        with self._lock:
            if rid in self.requests:
                self.requests[rid]["response"] = {
                    "status": resp["status"],
                    "statusText": resp.get("statusText", ""),
                    "headers": resp.get("headers", {}),
                    "mimeType": resp.get("mimeType", ""),
                    "fromDiskCache": resp.get("fromDiskCache", False),
                }

        # Only fetch body for API calls (not images/fonts/etc)
        resource_type = self.requests.get(rid, {}).get("type", "")
        mime_type = resp.get("mimeType", "")
        if resource_type in ("XHR", "Fetch", "Document") or "json" in mime_type or "text" in mime_type:
            cid = self._send_cdp("Network.getResponseBody", {"requestId": rid})
            self._pending_bodies[cid] = rid

    def _on_Network_loadingFinished(self, params: dict) -> None:
        rid = params["requestId"]
        # If body wasn't fetched yet, try once more
        with self._lock:
            if rid in self.requests and self.requests[rid]["body"] is None and self.requests[rid]["response"] is not None:
                pass  # body fetch already triggered in responseReceived
        cid = self._send_cdp("Network.getResponseBody", {"requestId": rid})
        self._pending_bodies[cid] = rid

    # -- Public query API -------------------------------------------------

    def wait_for(self, url_pattern: str, timeout_ms: int = 15000) -> dict[str, Any]:
        """Block until a captured request matches *url_pattern* and has a response body."""
        regex = re.compile(url_pattern)
        deadline = time.time() + timeout_ms / 1000
        while time.time() < deadline:
            with self._lock:
                for rid, data in self.requests.items():
                    if regex.search(data["request"]["url"]):
                        resp = data.get("response")
                        if resp is None:
                            continue
                        body = data.get("body")
                        # For non-text responses, don't wait for body
                        mime = resp.get("mimeType", "")
                        if body is None and "json" not in mime and "text" not in mime and "html" not in mime:
                            body = "(binary — image/font/etc.)"
                        if body is not None:
                            return self._build_reply(rid, data, body)
            time.sleep(0.15)
        return {"error": f"No request matching /{url_pattern}/ completed within {timeout_ms}ms"}

    def list_requests(self, url_pattern: str = ".*") -> list[dict[str, Any]]:
        regex = re.compile(url_pattern)
        result: list[dict[str, Any]] = []
        with self._lock:
            for rid, data in sorted(
                self.requests.items(),
                key=lambda kv: kv[1].get("timestamp_ns", 0),
            ):
                if regex.search(data["request"]["url"]):
                    resp = data.get("response")
                    result.append(
                        {
                            "requestId": rid,
                            "method": data["request"]["method"],
                            "url": data["request"]["url"],
                            "status": resp["status"] if resp else None,
                            "hasBody": data.get("body") is not None,
                        }
                    )
        return result

    def get_request(self, request_id: str) -> dict[str, Any]:
        with self._lock:
            data = self.requests.get(request_id)
        if not data:
            return {"error": f"Request {request_id} not found"}
        body = data.get("body") or ""
        return self._build_reply(request_id, data, body)

    @staticmethod
    def _build_reply(rid: str, data: dict, body: str) -> dict[str, Any]:
        resp = data.get("response") or {}
        req = data["request"]
        return {
            "requestId": rid,
            "url": req["url"],
            "method": req["method"],
            "status": resp.get("status"),
            "statusText": resp.get("statusText", ""),
            "requestHeaders": req.get("headers", {}),
            "requestBody": req.get("postData", ""),
            "responseHeaders": resp.get("headers", {}),
            "responseBody": body,
        }

    def close(self) -> None:
        self._alive = False
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        if self._browser:
            try:
                self._browser.terminate()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# MCP Server — raw JSON-RPC over stdio (no framework dependency needed)
# ---------------------------------------------------------------------------

monitor = CDPNetworkMonitor()

TOOLS = [
    {
        "name": "navigate_and_capture",
        "description": "Launch Chrome (if needed), navigate to a URL, and start capturing ALL network requests in real-time. Call this FIRST before any other tool. After this, all API calls the page makes will be recorded automatically.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Full URL to navigate to (e.g. https://data-agent-daily.wdtrip.com/agents)",
                }
            },
            "required": ["url"],
        },
    },
    {
        "name": "network_wait",
        "description": "Wait for an API request matching a URL regex to complete, then return its FULL details including request body, response body, headers, and status. Use this to verify that the frontend called the correct API with the correct parameters and received the expected response.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url_pattern": {
                    "type": "string",
                    "description": "Regex pattern (e.g. '/api/agent/.*/sessions' or 'POST.*messages')",
                },
                "timeout_ms": {
                    "type": "integer",
                    "description": "Max wait in ms (default 15000)",
                    "default": 15000,
                },
            },
            "required": ["url_pattern"],
        },
    },
    {
        "name": "network_list",
        "description": "List all captured network requests matching a URL filter. Use this to see what APIs the page has called so far. Each entry includes requestId, method, URL, and HTTP status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url_pattern": {
                    "type": "string",
                    "description": "Regex filter (default '.*' shows all captured requests)",
                    "default": ".*",
                }
            },
        },
    },
    {
        "name": "network_detail",
        "description": "Get the FULL request/response details for a specific request by its ID. Use after network_list to drill into a specific API call.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "request_id": {
                    "type": "string",
                    "description": "The requestId value from network_list output",
                }
            },
            "required": ["request_id"],
        },
    },
]


def _dispatch_tool(name: str, args: dict) -> dict | str:
    """Route tool call to the correct handler."""
    if name == "navigate_and_capture":
        result = monitor.connect(args["url"])
        return {
            "status": "capturing",
            "message": f"Connected. All network requests are being recorded in real-time.",
            "pageId": result["id"],
        }

    elif name == "network_wait":
        url_pattern = args["url_pattern"]
        timeout_ms = args.get("timeout_ms", 15000)
        return monitor.wait_for(url_pattern, timeout_ms)

    elif name == "network_list":
        url_pattern = args.get("url_pattern", ".*")
        return monitor.list_requests(url_pattern)

    elif name == "network_detail":
        return monitor.get_request(args["request_id"])

    else:
        return {"error": f"Unknown tool: {name}"}


def _run_mcp() -> None:
    """Minimal MCP JSON-RPC server over stdio."""
    import sys as _sys

    for line in _sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        req_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params", {})

        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "cdp-network-mcp",
                        "version": "1.0.0",
                    },
                },
            }

        elif method == "notifications/initialized":
            continue  # No response needed

        elif method == "tools/list":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": TOOLS},
            }

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            try:
                tool_result = _dispatch_tool(tool_name, arguments)
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    tool_result, ensure_ascii=False, indent=2, default=str
                                ),
                            }
                        ]
                    },
                }
            except Exception as exc:
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Error: {exc}"}],
                        "isError": True,
                    },
                }

        else:
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

        _sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
        _sys.stdout.flush()


if __name__ == "__main__":
    _run_mcp()
