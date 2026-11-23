#!/usr/bin/env python3
"""
b-hubit fork (branch komplikacja): glucose on any Apple Watch face, through the Calendar complication.

Third-party watch complications may refresh only about 4 times an hour. The system Calendar
complication has no such limit, so this script keeps one event in an iCloud calendar up to date with
the newest reading - "116 ↗ +3", starting at the time of the reading. The watch shows it next to the
clock or in a circle, on any face that has a Calendar complication.

    aaps_calendar.py tick     every 30 seconds from Home Assistant; writes when there is a new reading
    aaps_calendar.py test     checks the iCloud login and finds the calendar, writes nothing

Uses the same config.json as aaps_live_activity.py (Nightscout part), plus:
    "icloud_user":          Apple ID e-mail
    "icloud_app_password":  app-specific password from account.apple.com (not the Apple ID password)
    "calendar_name":        name of a calendar made only for this, e.g. "Glukoza"
    "caldav_url":           optional, defaults to https://caldav.icloud.com/
"""

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aaps_live_activity as live  # noqa: E402  Nightscout reading and config, shared

STATE_FILE = os.path.join(HERE, "calendar_state.json")
EVENT_UID = "aaps-glucose-b-hubit"
# How long the event lasts. When no new reading comes, it ends and the complication stops showing an
# old value as if it were current.
EVENT_MINUTES = 20

NS = {"d": "DAV:", "c": "urn:ietf:params:xml:ns:caldav"}


def log(msg):
    print(f"aaps_calendar: {msg}", file=sys.stderr)


class CalDav:
    def __init__(self, cfg):
        self.base = cfg.get("caldav_url", "https://caldav.icloud.com/")
        token = base64.b64encode(f"{cfg['icloud_user']}:{cfg['icloud_app_password']}".encode()).decode()
        self.auth = f"Basic {token}"

    def request(self, method, url, body=None, headers=None):
        url = urllib.parse.urljoin(self.base, url)
        data = body.encode() if isinstance(body, str) else body
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", self.auth)
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, r.read(), r.geturl()
        except urllib.error.HTTPError as e:
            return e.code, e.read(), url

    def propfind(self, url, props, depth="0"):
        body = ('<?xml version="1.0" encoding="utf-8"?><d:propfind xmlns:d="DAV:" '
                'xmlns:c="urn:ietf:params:xml:ns:caldav"><d:prop>' + props + "</d:prop></d:propfind>")
        status, data, final = self.request("PROPFIND", url, body, {
            "Depth": depth, "Content-Type": "application/xml; charset=utf-8"})
        if status != 207:
            raise RuntimeError(f"PROPFIND {url}: HTTP {status} {data[:200]!r}")
        return ET.fromstring(data), final

    def find_calendar(self, name):
        root, url = self.propfind(self.base, "<d:current-user-principal/>")
        principal = root.find(".//d:current-user-principal/d:href", NS).text
        root, url = self.propfind(urllib.parse.urljoin(url, principal), "<c:calendar-home-set/>")
        home = urllib.parse.urljoin(url, root.find(".//c:calendar-home-set/d:href", NS).text)
        root, url = self.propfind(home, "<d:displayname/><d:resourcetype/>", depth="1")
        found = []
        for response in root.findall("d:response", NS):
            if response.find(".//d:resourcetype/c:calendar", NS) is None:
                continue
            display = response.find(".//d:displayname", NS)
            label = (display.text or "").strip() if display is not None else ""
            href = urllib.parse.urljoin(url, response.find("d:href", NS).text)
            found.append(label)
            if label.lower() == name.lower():
                return href if href.endswith("/") else href + "/"
        raise RuntimeError(f"no calendar named '{name}'; found: {', '.join(found) or 'none'}")

    def put_event(self, calendar_url, ics):
        status, data, _ = self.request("PUT", calendar_url + EVENT_UID + ".ics", ics,
                                       {"Content-Type": "text/calendar; charset=utf-8"})
        if status not in (200, 201, 204):
            raise RuntimeError(f"PUT event: HTTP {status} {data[:200]!r}")


def ics_time(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def escape(text):
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def event_ics(content):
    start = int(content["readingTime"]) // 60 * 60
    title = " ".join(x for x in (content["value"], content["arrow"], content["delta"]) if x)
    details = ", ".join(x for x in (
        f"IOB {content['iob']} U" if content["iob"] else "",
        f"COB {content['cob']} g" if content["cob"] else "") if x)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//b-hubit//AAPS glucose//PL",
        "BEGIN:VEVENT",
        f"UID:{EVENT_UID}",
        f"DTSTAMP:{ics_time(time.time())}",
        f"DTSTART:{ics_time(start)}",
        f"DTEND:{ics_time(start + EVENT_MINUTES * 60)}",
        f"SUMMARY:{escape(title)}",
        f"DESCRIPTION:{escape(details)}",
        "TRANSP:TRANSPARENT",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines) + "\r\n"


def main(argv):
    command = argv[1] if len(argv) > 1 else ""
    cfg = live.load_json(live.CONFIG_FILE, None)
    if cfg is None:
        log(f"missing {live.CONFIG_FILE}")
        return 1
    if not cfg.get("icloud_user") or not cfg.get("icloud_app_password"):
        log("icloud_user / icloud_app_password missing in config.json")
        return 1
    dav = CalDav(cfg)
    name = cfg.get("calendar_name", "Glukoza")

    if command == "test":
        url = dav.find_calendar(name)
        print(json.dumps({"calendar": name, "url": url}, indent=2))
        return 0
    if command != "tick":
        print(__doc__)
        return 2

    state = live.load_json(STATE_FILE, {})
    content = live.read_nightscout(cfg)
    if content is None or content["readingTime"] == state.get("last_reading_time"):
        return 0
    try:
        if not state.get("calendar_url"):
            state["calendar_url"] = dav.find_calendar(name)
        dav.put_event(state["calendar_url"], event_ics(content))
    except Exception as e:
        state.pop("calendar_url", None)  # found again next time, in case it moved
        log(f"calendar not updated: {e}")
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
        return 0
    state["last_reading_time"] = content["readingTime"]
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)
    log(f"calendar: {content['value']} {content['arrow']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
