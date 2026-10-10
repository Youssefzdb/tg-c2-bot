# tg-c2-bot

Telegram C2 bot — lab / sandbox use. Polls Telegram, executes shell commands, returns output to chat.

No dependencies (Python 3.8+ stdlib only).

## Run

```bash
export TG_TOKEN="<bot token>"
python3 bot.py
```

Optional env:

| var | default | desc |
|---|---|---|
| `TG_ALLOW` | *(empty)* | lock to one chat id — **set this in production** |
| `TG_TIMEOUT` | `60` | command timeout (seconds) |
| `TG_CWD` | cwd | initial working directory |

Get your chat id: message `@userinfobot` on Telegram.

```bash
export TG_TOKEN="<bot token>"
export TG_ALLOW="<your chat id>"
python3 bot.py
```

## Commands

| sent in chat | action |
|---|---|
| any text | executed as shell in the bot's cwd |
| `cd <path>` | handled by bot, persists across commands |
| `/ping` | `pong` |
| `/cwd` | print current working dir |
| `/help` | help |

Output longer than 4000 chars is split across multiple messages.

## Sandbox deploy

```bash
git clone https://github.com/<you>/tg-c2-bot.git
cd tg-c2-bot
export TG_TOKEN="<bot token>"
python3 bot.py
```
