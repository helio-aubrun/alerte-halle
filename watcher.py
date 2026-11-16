"""
Surveille les tournois One Piece Card Game de la boutique officielle
"One Piece Official Shop Paris" (Forum des Halles) sur Bandai TCG+
et envoie une notification Discord :
  - quand un nouveau tournoi est publié ;
  - quand les inscriptions d'un tournoi ouvrent.

Variables d'environnement :
  DISCORD_WEBHOOK_URL  (obligatoire) URL du webhook Discord
  ORGANIZER_ID         (optionnel) id de la boutique sur TCG+, 7388 par défaut
  NOTIFY_REG_OPEN      (optionnel) "0" pour désactiver l'alerte d'ouverture des inscriptions
  STATE_FILE           (optionnel) chemin du fichier d'état, state.json par défaut
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests

API = "https://api.bandai-tcg-plus.com/api/user/event/list"
EVENT_URL = "https://www.bandai-tcg-plus.com/event/{id}"
# 4 = ONE PIECE CARD GAME (anglais), 13 = ONE PIECE CARD GAME (français)
GAME_TITLE_IDS = [4, 13]
ORGANIZER_ID = int(os.environ.get("ORGANIZER_ID", "7388"))
WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
NOTIFY_REG_OPEN = os.environ.get("NOTIFY_REG_OPEN", "1") != "0"
STATE_FILE = os.environ.get("STATE_FILE", "state.json")
PARIS = ZoneInfo("Europe/Paris")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (op-halles-watch; notification perso)",
    "Accept": "application/json",
    "Origin": "https://www.bandai-tcg-plus.com",
    "Referer": "https://www.bandai-tcg-plus.com/",
}

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]


# ---------------------------------------------------------------- API Bandai

def fetch_events() -> dict:
    """Renvoie {id: event} pour tous les tournois à venir de la boutique."""
    today = datetime.now(PARIS).strftime("%Y-%m-%d")
    events = {}
    for game_id in GAME_TITLE_IDS:
        offset = 0
        while True:
            params = {
                "game_title_id": game_id,
                "organizer_id": ORGANIZER_ID,
                "start_date": today,
                "favorite": 0,
                "limit": 100,
                "offset": offset,
            }
            r = requests.get(API, params=params, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()
            if "success" not in data:
                raise RuntimeError(f"Réponse inattendue de l'API : {str(data)[:300]}")
            batch = data["success"].get("event_list") or []
            for ev in batch:
                # double sécurité : on ne garde que la boutique visée
                if int(ev.get("organizer_id", 0)) == ORGANIZER_ID:
                    events[str(ev["id"])] = ev
            total = int(data["success"].get("total") or 0)
            offset += len(batch)
            if not batch or offset >= total:
                break
            time.sleep(1)
        time.sleep(1)
    return events


# ---------------------------------------------------------------- Formatage

def parse_dt(value):
    """Les dates de début sont en heure locale, les dates d'inscription en UTC."""
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=PARIS)
    return dt.astimezone(PARIS)


def fr_date(dt):
    if dt is None:
        return "?"
    return f"{JOURS[dt.weekday()]} {dt.day} {MOIS[dt.month - 1]} {dt.year} à {dt:%Hh%M}"


def price(ev):
    try:
        p = float(ev.get("entryFee") or ev.get("entry_fee") or 0)
    except ValueError:
        return "?"
    if p == 0:
        return "Gratuit"
    cur = ev.get("entry_fee_currency_code") or "€"
    return f"{p:.2f}".rstrip("0").rstrip(".").replace(".", ",") + f" {cur}"


def title(ev):
    return " ".join((ev.get("excerpt") or ev.get("event_series_title") or "Tournoi").split())


def build_embed(ev, kind):
    start = parse_dt(ev.get("start_datetime"))
    apply_start = parse_dt(ev.get("apply_start_datetime"))
    lang = ev.get("game_title_language") or ""
    if kind == "new":
        header, color = "🏴‍☠️ Nouveau tournoi publié", 0xE53935
    else:
        header, color = "🔔 Inscriptions ouvertes", 0x43A047
    fields = [
        {"name": "📅 Date", "value": fr_date(start), "inline": False},
        {"name": "💰 Prix", "value": price(ev), "inline": True},
        {"name": "👥 Places", "value": str(ev.get("max_join_count") or "?"), "inline": True},
    ]
    if lang:
        fields.append({"name": "🌐 Cartes", "value": lang, "inline": True})
    if kind == "new" and apply_start:
        fields.append({"name": "📝 Ouverture des inscriptions",
                       "value": fr_date(apply_start), "inline": False})
    return {
        "title": f"{header} : {title(ev)}"[:256],
        "url": EVENT_URL.format(id=ev["id"]),
        "color": color,
        "fields": fields,
        "footer": {"text": "One Piece Official Shop Paris · Forum des Halles"},
    }


# ---------------------------------------------------------------- Discord

def send_discord(embeds, content=None):
    if not WEBHOOK:
        print("DISCORD_WEBHOOK_URL manquant : notification affichée seulement ici.")
        print(json.dumps(embeds, ensure_ascii=False, indent=2))
        return
    # Discord accepte 10 embeds max par message
    for i in range(0, max(len(embeds), 1), 10):
        payload = {"username": "Tournois OP Halles", "embeds": embeds[i:i + 10]}
        if content and i == 0:
            payload["content"] = content
        for attempt in range(3):
            r = requests.post(WEBHOOK, json=payload, timeout=30)
            if r.status_code == 429:  # limite de débit Discord
                time.sleep(float(r.json().get("retry_after", 2)) + 0.5)
                continue
            r.raise_for_status()
            break
        time.sleep(1)


# ---------------------------------------------------------------- État

def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


# ---------------------------------------------------------------- Main

def main():
    events = fetch_events()
    now = datetime.now(timezone.utc)
    state = load_state()
    first_run = state is None
    state = state or {"seen": {}, "reg_notified": []}
    seen = state.setdefault("seen", {})
    reg_notified = set(state.setdefault("reg_notified", []))

    def reg_open(ev):
        a = parse_dt(ev.get("apply_start_datetime"))
        return a is not None and a <= now

    new_embeds, open_embeds = [], []
    for eid, ev in sorted(events.items(), key=lambda kv: kv[1].get("start_datetime", "")):
        if ev.get("is_canceled"):
            continue
        if eid not in seen:
            seen[eid] = {"title": title(ev), "start": ev.get("start_datetime")}
            if not first_run:
                new_embeds.append(build_embed(ev, "new"))
            if reg_open(ev):
                reg_notified.add(eid)  # déjà ouvertes : pas de 2e alerte
        elif NOTIFY_REG_OPEN and eid not in reg_notified and reg_open(ev):
            reg_notified.add(eid)
            open_embeds.append(build_embed(ev, "open"))

    if first_run:
        send_discord([], content=(
            f"✅ Surveillance activée : {len(events)} tournoi(s) à venir déjà publiés "
            "à la boutique officielle des Halles. Tu seras prévenu des prochains !"))
    else:
        if new_embeds:
            send_discord(new_embeds)
        if open_embeds:
            send_discord(open_embeds)

    # on oublie les tournois passés depuis plus de 30 jours
    cutoff = datetime.now(PARIS).timestamp() - 30 * 86400
    for eid in list(seen):
        st = parse_dt(seen[eid].get("start"))
        if st and st.timestamp() < cutoff:
            del seen[eid]
            reg_notified.discard(eid)

    state["reg_notified"] = sorted(reg_notified)
    # change une fois par semaine -> un commit hebdo qui garde le workflow actif
    state["heartbeat"] = datetime.now(PARIS).strftime("%G-W%V")
    save_state(state)
    print(f"{len(events)} tournoi(s) suivis, {len(new_embeds)} nouveau(x), "
          f"{len(open_embeds)} ouverture(s) d'inscription.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # visible dans les logs GitHub Actions
        print(f"Erreur : {e}", file=sys.stderr)
        sys.exit(1)
