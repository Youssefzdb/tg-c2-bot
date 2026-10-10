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
| `TG_HTTP_TOKEN` | *(empty)* | relay auth secret — **relay disabled if unset** |
| `TG_HTTP_PORT` | `8080` | relay listen port |
| `TG_HTTP_BIND` | `0.0.0.0` | relay bind address |

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

## HTTP relay

Same shell, driven over HTTP instead of Telegram (operator API):

```bash
export TG_HTTP_TOKEN="<secret>"
python3 bot.py
```

```bash
# raw command
curl -s -X POST http://<host>:8080/exec -H "X-Token: <secret>" --data 'id'

# json
curl -s -X POST http://<host>:8080/exec -H "X-Token: <secret>" \
  -H "Content-Type: application/json" -d '{"cmd":"uname -a"}'

# bearer auth
curl -s -X POST http://<host>:8080/exec -H "Authorization: Bearer <secret>" --data 'whoami'

curl -s http://<host>:8080/health
```

Responses are `text/plain`: stdout+stderr, `[rc=N]` appended on failure, `cd` persists across calls.
Auth: `X-Token` header or `Authorization: Bearer`. Missing/wrong token → `401`.

## Sandbox deploy

```bash
git clone https://github.com/<you>/tg-c2-bot.git
cd tg-c2-bot
export TG_TOKEN="<bot token>"
python3 bot.py
```
