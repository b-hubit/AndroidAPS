#!/usr/bin/env python3
"""
b-hubit fork (branch ios-live-activity): pushes glucose from Nightscout to the AAPSClient Live Activity.

Runs inside Home Assistant (shell_command), which already has everything it needs: Python with PyJWT
and cryptography. Nothing leaves your own systems except the push itself, which goes to Apple.

    aaps_live_activity.py register <start|update> <token> [activity_id]
        Called by the webhook automation when the iPhone app reports a push token.
    aaps_live_activity.py tick
        Called every 30 seconds. Sends a push when Nightscout has a new reading, and starts a new
        Live Activity when the current one is close to the 8 hour limit iOS sets.
    aaps_live_activity.py test
        Prints what it would push, without pushing. For checking the Nightscout part.

Configuration: config.json next to this file (see config.example.json). State: state.json, written
by this script.
"""

import fcntl
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(HERE, "config.json")
STATE_FILE = os.path.join(HERE, "state.json")
LOCK_FILE = os.path.join(HERE, ".lock")

# iOS ends a Live Activity after 8 hours. A fresh one is started by push a little before that.
RESTART_AFTER_S = 7 * 3600 + 45 * 60
# Apple wants the provider token refreshed at most once per 20 minutes and at least once per hour.
JWT_LIFETIME_S = 50 * 60
# The Lock Screen greys the value out this long after the reading.
STALE_AFTER_S = 11 * 60

ARROWS = {
    "DoubleUp": "⇈", "SingleUp": "↑", "FortyFiveUp": "↗", "Flat": "→",
    "FortyFiveDown": "↘", "SingleDown": "↓", "DoubleDown": "⇊",
}
TOKEN_RE = re.compile(r"^[0-9a-f]{16,512}$")


def log(msg):
    print(f"aaps_live: {msg}", file=sys.stderr)


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save_state(state):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, STATE_FILE)


# ---------------------------------------------------------------------------------------------------
# Nightscout
# ---------------------------------------------------------------------------------------------------

def ns_get(cfg, path, params):
    params = dict(params)
    headers = {"Accept": "application/json"}
    if cfg.get("nightscout_token"):
        params["token"] = cfg["nightscout_token"]
    if cfg.get("nightscout_api_secret"):
        import hashlib
        headers["api-secret"] = hashlib.sha1(cfg["nightscout_api_secret"].encode()).hexdigest()
    url = cfg["nightscout_url"].rstrip("/") + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def fmt_number(x, decimals):
    s = f"{x:.{decimals}f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def read_nightscout(cfg):
    entries = ns_get(cfg, "/api/v1/entries/sgv.json", {"count": 2})
    if not entries:
        return None
    latest = entries[0]
    sgv = int(latest["sgv"])
    reading_time = latest.get("date", 0) / 1000.0
    mmol = cfg.get("units", "mg/dl").lower().startswith("mmol")

    delta = ""
    if len(entries) > 1 and abs(latest["date"] - entries[1]["date"]) <= 15 * 60 * 1000:
        d = sgv - int(entries[1]["sgv"])
        if mmol:
            d = d / 18.0182
            delta = ("+" if d >= 0 else "") + f"{d:.1f}"
        else:
            delta = f"{d:+d}"

    iob, cob = "", ""
    try:
        status = ns_get(cfg, "/api/v1/devicestatus.json", {"count": 1})
        openaps = (status[0] if status else {}).get("openaps", {})
        iob_value = (openaps.get("iob") or {}).get("iob")
        if iob_value is not None:
            iob = fmt_number(float(iob_value), 2)
        for key in ("suggested", "enacted"):
            cob_value = (openaps.get(key) or {}).get("COB")
            if cob_value is not None:
                cob = fmt_number(float(cob_value), 0)
                break
    except Exception as e:  # IOB/COB are extras, glucose must still go out
        log(f"devicestatus not read: {e}")

    return {
        "value": fmt_number(sgv / 18.0182, 1) if mmol else str(sgv),
        "mgdl": sgv,
        "arrow": ARROWS.get(latest.get("direction", ""), ""),
        "delta": delta,
        "readingTime": reading_time,
        "iob": iob,
        "cob": cob,
        "low": int(cfg.get("low_mgdl", 70)),
        "high": int(cfg.get("high_mgdl", 180)),
    }


# ---------------------------------------------------------------------------------------------------
# APNs
# ---------------------------------------------------------------------------------------------------

def provider_token(cfg, state):
    now = int(time.time())
    cached = state.get("jwt")
    if cached and now - state.get("jwt_issued", 0) < JWT_LIFETIME_S:
        return cached
    import jwt  # PyJWT, part of Home Assistant
    key_file = cfg["key_file"]
    if not os.path.isabs(key_file):
        key_file = os.path.join(HERE, key_file)
    with open(key_file) as f:
        key = f.read()
    token = jwt.encode({"iss": cfg["team_id"], "iat": now}, key, algorithm="ES256",
                       headers={"kid": cfg["key_id"]})
    if isinstance(token, bytes):
        token = token.decode()
    state["jwt"], state["jwt_issued"] = token, now
    return token


def send_push(cfg, state, device_token, payload, priority=10):
    """Returns the HTTP status. APNs speaks HTTP/2 only."""
    host = cfg.get("apns_host", "api.push.apple.com")
    base = host if "://" in host else f"https://{host}"  # a scheme only for local testing
    url = f"{base}/3/device/{device_token}"
    headers = {
        "authorization": f"bearer {provider_token(cfg, state)}",
        "apns-push-type": "liveactivity",
        "apns-topic": f"{cfg['bundle_id']}.push-type.liveactivity",
        "apns-priority": str(priority),
    }
    body = json.dumps(payload, separators=(",", ":"))
    try:
        import httpx
        with httpx.Client(http2=True, timeout=20) as client:
            r = client.post(url, headers=headers, content=body)
            status, text = r.status_code, r.text
    except ImportError:
        status, text = curl_push(url, headers, body)
    if status != 200:
        log(f"APNs {status}: {text}")
    return status, text


def curl_push(url, headers, body):
    cmd = ["curl", "--http2", "-sS", "-o", "-", "-w", "\n%{http_code}", "-X", "POST", "--data-binary", "@-"]
    for k, v in headers.items():
        cmd += ["-H", f"{k}: {v}"]
    cmd.append(url)
    out = subprocess.run(cmd, input=body.encode(), capture_output=True, timeout=30)
    text = out.stdout.decode(errors="replace")
    body_text, _, code = text.rpartition("\n")
    try:
        return int(code), body_text or out.stderr.decode(errors="replace")
    except ValueError:
        return 0, out.stderr.decode(errors="replace")


def token_is_dead(status, text):
    return status == 410 or (status == 400 and ("BadDeviceToken" in text or "DeviceTokenNotForTopic" in text))


# ---------------------------------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------------------------------

def update_payload(content):
    now = int(time.time())
    return {"aps": {
        "timestamp": now,
        "event": "update",
        "content-state": content,
        "stale-date": int(content["readingTime"]) + STALE_AFTER_S if content["readingTime"] else now + STALE_AFTER_S,
    }}


def start_payload(content):
    payload = update_payload(content)
    payload["aps"].update({
        "event": "start",
        "attributes-type": "GlucoseActivityAttributes",
        "attributes": {"name": "AAPS"},
        "alert": {"title": "AAPS", "body": "Glukoza na ekranie blokady"},
    })
    return payload


def end_payload():
    now = int(time.time())
    return {"aps": {"timestamp": now, "event": "end", "dismissal-date": now}}


def tick(cfg, state, force=False):
    content = read_nightscout(cfg)
    if content is None:
        log("no reading in Nightscout")
        return
    now = time.time()
    new_reading = content["readingTime"] != state.get("last_reading_time")

    update_token = state.get("update_token")
    started_at = state.get("started_at", 0)

    # Close to the 8 hour limit: end the old activity and start the next one by push.
    if state.get("start_token") and (not update_token or now - started_at > RESTART_AFTER_S):
        if update_token:
            send_push(cfg, state, update_token, end_payload())
        if not update_token and now - state.get("last_start_push", 0) < 60 * 60:
            pass  # a start was sent recently; wait for the app to report the new activity's token
        else:
            status, text = send_push(cfg, state, state["start_token"], start_payload(content))
            state["last_start_push"] = now
            state.pop("update_token", None)
            if token_is_dead(status, text):
                state.pop("start_token", None)
            if status == 200:
                log("started a new Live Activity")
                state["last_reading_time"] = content["readingTime"]
            return

    if not update_token:
        return
    if not (new_reading or force):
        return
    status, text = send_push(cfg, state, update_token, update_payload(content))
    if status == 200:
        state["last_reading_time"] = content["readingTime"]
    elif token_is_dead(status, text):
        state.pop("update_token", None)


def register(cfg, state, kind, token, activity_id):
    if not TOKEN_RE.match(token):
        log("ignored a token that is not hex")
        return
    if kind == "start":
        state["start_token"] = token
        log("push-to-start token stored")
    elif kind == "update":
        if activity_id != state.get("activity_id") or token != state.get("update_token"):
            if activity_id != state.get("activity_id"):
                state["started_at"] = time.time()
            state["activity_id"] = activity_id
            state["update_token"] = token
            log(f"update token stored for activity {activity_id}")
        tick(cfg, state, force=True)
    else:
        log(f"unknown token kind {kind}")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cfg = load_json(CONFIG_FILE, None)
    if cfg is None:
        log(f"missing {CONFIG_FILE}")
        return 1
    with open(LOCK_FILE, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_json(STATE_FILE, {})
        command = argv[1]
        if command == "register" and len(argv) >= 4:
            register(cfg, state, argv[2], argv[3].strip().lower(), argv[4] if len(argv) > 4 else "")
        elif command == "tick":
            tick(cfg, state)
        elif command == "test":
            content = read_nightscout(cfg)
            print(json.dumps(update_payload(content) if content else None, indent=2, ensure_ascii=False))
            return 0
        else:
            print(__doc__)
            return 2
        save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
