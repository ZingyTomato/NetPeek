import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib

from datetime import datetime


def build_checkmark_menu(model, labels, active_index, action_name):
    model.remove_all()
    for i, label in enumerate(labels):
        prefix = "✓ " if i == active_index else ""
        item = Gio.MenuItem.new(prefix + label, None)
        item.set_action_and_target_value(
            action_name,
            GLib.Variant.new_string(str(i)),
        )
        model.append_item(item)


def setup_popover_breakpoints(host, popover, desktop_position=Gtk.PositionType.BOTTOM):
    bp_desktop = Adw.Breakpoint.new(
        Adw.BreakpointCondition.parse("min-width: 400sp")
    )
    bp_desktop.add_setter(popover, "position", desktop_position)
    bp_desktop.connect(
        "apply", lambda _: popover.remove_css_class("mobile-layout")
    )
    bp_desktop.connect(
        "unapply", lambda _: popover.add_css_class("mobile-layout")
    )
    host.add_breakpoint(bp_desktop)

    bp_mobile = Adw.Breakpoint.new(
        Adw.BreakpointCondition.parse("max-width: 400sp")
    )
    bp_mobile.add_setter(popover, "position", Gtk.PositionType.TOP)
    bp_mobile.connect(
        "apply", lambda _: popover.add_css_class("mobile-layout")
    )
    bp_mobile.connect(
        "unapply", lambda _: popover.remove_css_class("mobile-layout")
    )
    host.add_breakpoint(bp_mobile)


def parse_scan_dt(ts):
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None
