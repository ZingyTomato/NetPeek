# storage.py
#
# Copyright 2026 ZingyTomato
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import os
from datetime import datetime, timezone

from gi.repository import GLib

MAX_SCAN_HISTORY = 50


def _data_dir():
    path = os.path.join(GLib.get_user_data_dir(), "netpeek")
    os.makedirs(path, exist_ok=True)
    return path


def _devices_path():
    return os.path.join(_data_dir(), "devices.json")


def _scans_path():
    return os.path.join(_data_dir(), "scans.json")


def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path, data):
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, path)


def _now():
    return datetime.now(timezone.utc).isoformat()


def device_key(mac, ip):
    return mac or ip


def load_devices():
    """Return the device registry as {key: device_record}."""
    return _load_json(_devices_path(), {})


def save_devices(devices):
    _save_json(_devices_path(), devices)


def load_scans():
    """Return saved scans, newest first."""
    return _load_json(_scans_path(), [])


def save_scans(scans):
    _save_json(_scans_path(), scans)


def set_custom_name(key, name):
    devices = load_devices()
    record = devices.setdefault(key, {})
    record["custom_name"] = name
    save_devices(devices)


def apply_custom_names(devices):
    """Return copies of the given device dicts with custom_name refreshed
    from the live registry, so renames show up in older scans too."""
    registry = load_devices()
    refreshed = []
    for device in devices:
        record = registry.get(device_key(device.get("mac", ""), device.get("ip", "")))
        merged = dict(device)
        if record is not None:
            merged["custom_name"] = record.get("custom_name", "")
        refreshed.append(merged)
    return refreshed


def record_scan(ip_range, devices, deep_scan=False):
    """Persist a completed scan and update the device registry.

    Annotates and returns the given device list with `custom_name` and
    `known` (whether this device was already in the registry before now).
    """
    registry = load_devices()
    now = _now()
    annotated = []

    for device in devices:
        key = device_key(device.get("mac", ""), device.get("ip", ""))
        existing = registry.get(key)
        known = existing is not None

        record = existing or {"first_seen": now}
        record["last_seen"] = now
        record["last_ip"] = device.get("ip", "")
        record["last_hostname"] = device.get("hostname", "")
        record["mac"] = device.get("mac", "") or record.get("mac", "")
        record.setdefault("custom_name", "")
        registry[key] = record

        enriched = dict(device)
        enriched["custom_name"] = record["custom_name"]
        enriched["known"] = known
        annotated.append(enriched)

    save_devices(registry)

    scans = load_scans()
    scans.insert(0, {
        "timestamp": now,
        "ip_range": ip_range,
        "devices": annotated,
        "deep_scan": deep_scan,
    })
    save_scans(scans[:MAX_SCAN_HISTORY])

    return annotated


def delete_scan(timestamp):
    """Remove a single scan history entry by its timestamp."""
    scans = load_scans()
    scans = [scan for scan in scans if scan.get("timestamp") != timestamp]
    save_scans(scans)
