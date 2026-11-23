#!/usr/bin/env python3
"""
b-hubit fork (branch ios-live-activity): pushes glucose from Nightscout to the AAPSClient Live Activity.

Runs inside Home Assistant (shell_command), which already has everything it needs: Python with PyJWT
and cryptography. Nothing leaves your own systems except the push itself, which goes to Apple.

    aaps_live_activity.py register <start|update> <token> [activity_id] [device]
        Called by the webhook automation when an iPhone reports a push token. Every iPhone (device
        id from the app) gets its own Live Activity, so several people can follow at once.
    aaps_live_activity.py tick
        Called every 30 seconds. Sends a push when Nightscout has a new reading, and starts a new
        Live Activity when the current one is close to the 8 hour limit iOS sets.
    aaps_live_activity.py test
        Prints what it would push, without pushing. For checking the Nightscout part.
    aaps_live_activity.py status
        Prints whether the iPhone has reported its tokens and when the last push went out.

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
# "3' temu" is refreshed by low-priority pushes once a minute, for this long after the reading.
AGE_UPDATES_FOR_S = 60 * 60

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

def age_text(reading_time, now=None):
    """ "3' temu" - whole minutes since the reading, as AAPS shows it. """
    if not reading_time:
        return ""
    minutes = int(((now or time.time()) - reading_time) // 60)
    return "teraz" if minutes < 1 else f"{minutes}' temu"


def update_payload(content):
    now = int(time.time())
    content = dict(content, age=age_text(content["readingTime"], now))
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


DEVICE_KEYS = ("start_token", "update_token", "activity_id", "started_at",
               "last_reading_time", "last_age", "last_start_push")
DEVICE_RE = re.compile(r"^[A-Za-z0-9-]{1,64}$")


def devices(state):
    """Per-iPhone state. Every phone that opens the app gets its own Live Activity and tokens.

    A state file from the single-phone version is moved under "default", the name an app build
    without a device id registers as.
    """
    devs = state.setdefault("devices", {})
    if any(k in state for k in DEVICE_KEYS):
        old = {k: state.pop(k) for k in DEVICE_KEYS if k in state}
        devs.setdefault("default", {}).update(old)
    return devs


def tick(cfg, state, force_device=None):
    content = read_nightscout(cfg)
    if content is None:
        log("no reading in Nightscout")
        return
    devs = devices(state)
    if not devs:
        log("no iPhone registered yet - open the app with the webhook set")
    for name, dev in list(devs.items()):
        tick_device(cfg, state, name, dev, content, force=(name == force_device))


def tick_device(cfg, state, name, dev, content, force=False):
    now = time.time()
    new_reading = content["readingTime"] != dev.get("last_reading_time")

    update_token = dev.get("update_token")
    started_at = dev.get("started_at", 0)

    # Close to the 8 hour limit: end the old activity and start the next one by push.
    if dev.get("start_token") and (not update_token or now - started_at > RESTART_AFTER_S):
        if update_token:
            send_push(cfg, state, update_token, end_payload())
        if not update_token and now - dev.get("last_start_push", 0) < 60 * 60:
            pass  # a start was sent recently; wait for the app to report the new activity's token
        else:
            status, text = send_push(cfg, state, dev["start_token"], start_payload(content))
            dev["last_start_push"] = now
            dev.pop("update_token", None)
            if token_is_dead(status, text):
                dev.pop("start_token", None)
            if status == 200:
                log(f"{name}: started a new Live Activity")
                dev["last_reading_time"] = content["readingTime"]
            return

    if not update_token:
        return

    age = age_text(content["readingTime"], now)
    if new_reading or force:
        # A new reading: high priority, counted against the budget iOS gives the app.
        priority = 10
    elif age != dev.get("last_age") and now - content["readingTime"] < AGE_UPDATES_FOR_S:
        # Only the minutes changed: low priority, which iOS does not count against the budget and
        # may deliver a little later. Keeps "3' temu" right without an always-running timer view.
        priority = 5
    else:
        return
    status, text = send_push(cfg, state, update_token, update_payload(content), priority=priority)
    if status == 200:
        dev["last_reading_time"] = content["readingTime"]
        dev["last_age"] = age
        if priority == 10:
            log(f"{name}: pushed {content['value']} {content['arrow']}")
    elif token_is_dead(status, text):
        dev.pop("update_token", None)


def register(cfg, state, kind, token, activity_id, device):
    if not TOKEN_RE.match(token):
        log("ignored a token that is not hex")
        return
    if not DEVICE_RE.match(device or ""):
        device = "default"
    devs = devices(state)
    if device != "default" and "default" in devs:
        # The entry of an app build that sent no device id. Once a phone reports one, that build is
        # gone from it; keeping the entry would push to a dead activity and restart it every 8 hours.
        del devs["default"]
    dev = devs.setdefault(device, {})
    if kind == "start":
        dev["start_token"] = token
        # The same phone under another name (an older app build registered as "default"): drop that
        # entry, or the phone would get every push twice and a second Live Activity every 8 hours.
        for other in [n for n, d in devs.items() if n != device and d.get("start_token") == token]:
            del devs[other]
        log(f"{device}: push-to-start token stored")
    elif kind == "update":
        if activity_id != dev.get("activity_id") or token != dev.get("update_token"):
            if activity_id != dev.get("activity_id"):
                dev["started_at"] = time.time()
            dev["activity_id"] = activity_id
            dev["update_token"] = token
            log(f"{device}: update token stored for activity {activity_id}")
        tick(cfg, state, force_device=device)
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
            register(cfg, state, argv[2], argv[3].strip().lower(),
                     argv[4] if len(argv) > 4 else "", argv[5] if len(argv) > 5 else "default")
        elif command == "tick":
            tick(cfg, state)
        elif command == "status":
            now = time.time()
            print(json.dumps({name: {
                "update_token": bool(dev.get("update_token")),
                "start_token": bool(dev.get("start_token")),
                "activity_id": dev.get("activity_id"),
                "activity_age_min": round((now - dev["started_at"]) / 60) if dev.get("started_at") else None,
                "last_pushed_reading_min_ago":
                    round((now - dev["last_reading_time"]) / 60) if dev.get("last_reading_time") else None,
            } for name, dev in devices(state).items()}, indent=2))
            save_state(state)
            return 0
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
