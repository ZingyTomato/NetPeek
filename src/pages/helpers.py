import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gio, GLib

from datetime import datetime


def build_radio_menu(model, labels, action_name, targets=None):
    """Build a radio-style menu bound to a stateful string action.

    Each item shares ``action_name`` with its index as the string target
    (e.g. ``win.preset-select::0``), or the matching entry of ``targets``
    when given (e.g. mode strings for a settings-backed action). GTK
    renders the item whose target equals the action's state with a
    check/radio indicator — no manual tick prefix needed. Selection
    changes via action state, not rebuilds.
    """
    model.remove_all()
    for i, label in enumerate(labels):
        target = targets[i] if targets is not None else str(i)
        item = Gio.MenuItem.new(label, None)
        item.set_action_and_target_value(
            action_name,
            GLib.Variant.new_string(target),
        )
        model.append_item(item)


def parse_scan_dt(ts):
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None
