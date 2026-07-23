#!/usr/bin/env python3
"""
Busca as tarefas de hoje no tarefas-casa e manda um push via ntfy.
Pensado pra rodar 1x por dia via cron, direto no homeserver.

A lógica de is_due / resolve_responsible espelha exatamente a do
static/index.html (mesmo algoritmo de hash e de rodízio) para que a
pessoa anunciada aqui seja sempre a mesma que aparece no app.
Se você mudar essa lógica lá, replique aqui também.

Variáveis de ambiente:
  TAREFAS_URL   - base URL do app (default: http://tarefas.cirillo)
  NTFY_URL      - servidor ntfy (default: https://ntfy.sh)
  NTFY_TOPIC    - tópico ntfy (obrigatório)
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta

TAREFAS_URL = os.environ.get("TAREFAS_URL", "http://tarefas.cirillo")
NTFY_URL = os.environ.get("NTFY_URL", "https://ntfy.sh")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC")
STORAGE_KEY = "household_tasks_data_v1"


def fetch_state():
    url = f"{TAREFAS_URL}/api/kv/{STORAGE_KEY}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return json.loads(payload["value"])


def js_weekday(d: date) -> int:
    # replica o Date.getDay() do JS: domingo=0 ... sabado=6
    return (d.weekday() + 1) % 7


def is_due(task, target: date) -> bool:
    f = task["freq"]
    if f["type"] == "weekdays":
        return js_weekday(target) in f["days"]
    if f["type"] == "interval":
        start = date.fromisoformat(f["start"])
        diff = (target - start).days
        return diff >= 0 and diff % f["every"] == 0
    if f["type"] == "monthly":
        if target.month == 12:
            next_month = date(target.year + 1, 1, 1)
        else:
            next_month = date(target.year, target.month + 1, 1)
        last_day = (next_month - timedelta(days=1)).day
        day = last_day if f["day"] == "last" else min(f["day"], last_day)
        return target.day == day
    if f["type"] == "once":
        return target.isoformat() == f["date"]
    return False


def occurrence_index_since(task, start: date, target: date) -> int:
    count = -1
    cur = start
    iterations = 0
    while cur <= target and iterations < 3660:
        if is_due(task, cur):
            count += 1
        cur += timedelta(days=1)
        iterations += 1
    return count


def hash_str(s: str) -> int:
    # replica: h = (h*31 + charCode) | 0  (overflow de 32 bits com sinal)
    h = 0
    for ch in s:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
        if h >= 0x80000000:
            h -= 0x100000000
    return abs(h)


def resolve_responsible(task, target: date) -> str:
    if task["responsible"] != "both":
        return task["responsible"]
    rot = task.get("rotation") or {"mode": "random"}
    if rot.get("mode") == "alternating":
        start = date.fromisoformat(rot.get("start") or target.isoformat())
        first = rot.get("first", "p1")
        if target < start:
            return first
        idx = occurrence_index_since(task, start, target)
        if idx < 0:
            return first
        other = "p2" if first == "p1" else "p1"
        return first if idx % 2 == 0 else other
    h = hash_str(f"{task['id']}|{target.isoformat()}")
    return "p1" if h % 2 == 0 else "p2"


def send_ntfy(message: str, title: str):
    if not NTFY_TOPIC:
        print("NTFY_TOPIC não definido, abortando.", file=sys.stderr)
        sys.exit(1)
    url = f"{NTFY_URL.rstrip('/')}/{NTFY_TOPIC}"
    req = urllib.request.Request(
        url,
        data=message.encode("utf-8"),
        method="POST",
        headers={"Title": title, "Click": TAREFAS_URL},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        resp.read()


def main():
    try:
        data = fetch_state()
    except (urllib.error.URLError, TimeoutError, KeyError) as e:
        print(f"Erro buscando dados do tarefas-casa: {e}", file=sys.stderr)
        sys.exit(1)

    people = data.get("people", {"p1": "Pessoa 1", "p2": "Pessoa 2"})
    today = date.today()
    tasks = [t for t in data.get("tasks", []) if t.get("active", True)]
    due = [t for t in tasks if is_due(t, today)]

    title = f"Tarefas de hoje ({today.strftime('%d/%m')})"

    if not due:
        send_ntfy("Nenhuma tarefa hoje.", title)
        print("Nenhuma tarefa hoje.")
        return

    lines = []
    for t in due:
        person_key = resolve_responsible(t, today)
        person_name = people.get(person_key, person_key)
        lines.append(f"- {t['name']} \u2014 {person_name}")

    message = "\n".join(lines)
    send_ntfy(message, title)
    print(message)


if __name__ == "__main__":
    main()
