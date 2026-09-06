import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib

from ..widgets import ThemeSelector, ToastMixin, clear_focus
from ..scanner import NetworkScanner
from .helpers import build_radio_menu


@Gtk.Template(resource_path='/io/github/zingytomato/netpeek/gtk/home_page.ui')
class HomePage(ToastMixin, Adw.NavigationPage):
    """Home page with IP input functionality"""
    __gtype_name__ = 'HomePage'

    ip_entry_row = Gtk.Template.Child()
    scan_button = Gtk.Template.Child()
    preset_box = Gtk.Template.Child()
    primary_popover = Gtk.Template.Child()
    deep_scan_row = Gtk.Template.Child()

    def __init__(self, window, navigation_view, toast_overlay, scanner, settings):
        super().__init__()

        self.window = window
        self.navigation_view = navigation_view
        self.toast_overlay = toast_overlay
        self.scanner = scanner
        self.settings = settings
        self.results_page = None

        self.primary_popover.add_child(ThemeSelector(), "theme")
        # Apply the saved thread count at startup; edited via PreferencesDialog.
        self.scanner.set_max_workers(self.settings.get_int('thread-count'))

        self.setup_presets()
        self._restore_preset()

        # Deep scan switch follows GSettings both ways.
        self.settings.bind('deep-scan', self.deep_scan_row, 'active',
                           Gio.SettingsBindFlags.DEFAULT)

        # Entry text restores once from GSettings; only validated ranges are
        # written back, at the existing save points below. One-time set_text,
        # not bind(GET): a live binding echoes set_string() back into the row
        # while focused and re-reveals the apply button right after apply.
        saved_range = self.settings.get_string('last-ip-range')
        if saved_range:
            self.ip_entry_row.set_text(saved_range)
        if not self.ip_entry_row.get_text() or not saved_range:
            if self._active_preset["range"] is None:
                self.auto_detect_network()
            else:
                self.ip_entry_row.set_text(self._active_preset["range"])

        # Clear initial focus so the IP entry isn't pre-selected.
        GLib.idle_add(self._reset_launch_highlight)
        self.ip_entry_row.connect("changed", self._on_ip_entry_changed)

    def _reset_launch_highlight(self):
        clear_focus(self)
        self.ip_entry_row.set_position(-1)
        return GLib.SOURCE_REMOVE

    def _on_ip_entry_changed(self, _row):
        self.ip_entry_row.remove_css_class("error")

    def _clear_focus(self):
        clear_focus(self)
        self.ip_entry_row.set_position(-1)
        return GLib.SOURCE_REMOVE

    def connect_results_page(self, results_page):
        self.results_page = results_page

    def focus_ip_entry(self):
        """Focus the IP range entry (for win.focus-ip)."""
        self.ip_entry_row.grab_focus()

    @staticmethod
    def _preset_short_label(preset_range):
        octets = preset_range.split("/")[0].split(".")
        prefix_len = int(preset_range.split("/")[1]) // 8
        octets[prefix_len:] = ["x"] * (4 - prefix_len)
        return ".".join(octets)

    _RANGE_PRESETS = [
        {"label": _("Auto-detect"), "range": None, "desc": _("Automatically detect your local network")},
        {"label": _preset_short_label("192.168.1.0/24"), "range": "192.168.1.0/24", "desc": _("Home network (192.168.1.x)")},
        {"label": _preset_short_label("192.168.0.0/24"), "range": "192.168.0.0/24", "desc": _("Home network (192.168.0.x)")},
        {"label": _preset_short_label("10.0.0.0/24"), "range": "10.0.0.0/24", "desc": _("Corporate (10.0.0.x)")},
        {"label": _preset_short_label("172.16.0.0/24"), "range": "172.16.0.0/24", "desc": _("Private (172.16.0.x)")},
    ]

    def setup_presets(self):
        self._active_preset = self._RANGE_PRESETS[0]

        self.preset_menu_model = Gio.Menu()
        self.preset_popover = Gtk.PopoverMenu.new_from_model(self.preset_menu_model)
        self.preset_popover.add_css_class("preset-popover")

        self.preset_button = Adw.SplitButton()
        self.preset_button.add_css_class("preset-split")
        self.preset_button.set_label(_("Auto-detect"))
        self.preset_button.set_tooltip_text(_("Automatically detect your local network"))
        self.preset_button.set_dropdown_tooltip(_("Choose a different preset range"))
        self.preset_button.set_can_shrink(True)
        self.preset_button.set_popover(self.preset_popover)
        self.preset_button.connect("clicked", self.on_preset_button_clicked)

        select_action = Gio.SimpleAction.new_stateful(
            "preset-select",
            GLib.VariantType.new("s"),
            GLib.Variant.new_string("0"),
        )
        select_action.connect("activate", self._on_preset_menu_activate)
        select_action.connect("change-state", self._on_preset_menu_change_state)
        self.window.add_action(select_action)
        self._preset_action = select_action

        self.preset_box.append(self.preset_button)
        self._build_preset_menu()
        # Preferred side; GTK flips automatically when space runs out.
        self.preset_popover.set_position(Gtk.PositionType.TOP)

    def _restore_preset(self):
        saved_preset = self.settings.get_string('last-preset')
        if not saved_preset:
            return
        target = "auto" if saved_preset == "auto" else saved_preset
        for preset in self._RANGE_PRESETS:
            if (preset["range"] is None and target == "auto") or preset["range"] == target:
                self._sync_preset_ui(preset)
                break

    def _sync_preset_ui(self, preset):
        self._active_preset = preset
        self.preset_button.set_label(preset["label"])
        self.preset_button.set_tooltip_text(preset["desc"])
        self._sync_preset_action_state()

    def _apply_preset(self, preset, popdown=False):
        self._sync_preset_ui(preset)
        if preset["range"] is None:
            self.auto_detect_network()
        else:
            self.ip_entry_row.set_text(preset["range"])
        if popdown:
            self.preset_popover.popdown()
        self._save_preset_settings()

    def _save_preset_settings(self):
        self.settings.set_string('last-preset', self._active_preset["range"] or "auto")
        self.settings.set_string('last-ip-range', self.ip_entry_row.get_text().strip())

    def _build_preset_menu(self):
        # Built once; the tick follows the stateful action's state.
        build_radio_menu(
            self.preset_menu_model,
            [p["label"] for p in self._RANGE_PRESETS],
            "win.preset-select")

    def _sync_preset_action_state(self):
        index = self._RANGE_PRESETS.index(self._active_preset)
        state = GLib.Variant.new_string(str(index))
        if self._preset_action.get_state() != state:
            self._preset_action.set_state(state)

    def auto_detect_network(self):
        self.ip_entry_row.set_text(NetworkScanner.get_local_ip_range())

    @Gtk.Template.Callback()
    def on_scan_clicked(self, button):
        """Start scan when 'Scan My Network' is clicked"""
        if self.scanner.is_scanning:
            self.show_toast(_("Scan already in progress"))
            return
        if not self.validate_ip_range():
            return
        ip_range = self.ip_entry_row.get_text().strip()
        self.settings.set_string('last-ip-range', ip_range)
        if self.results_page:
            self.navigation_view.push(self.results_page)
            self.results_page.start_scan(ip_range, deep_scan=self.deep_scan_row.get_active())

    @Gtk.Template.Callback()
    def on_ip_range_apply(self, _widget):
        """When the apply button is clicked or Enter is pressed in the IP entry"""
        if not self.validate_ip_range():
            return
        self.settings.set_string('last-ip-range', self.ip_entry_row.get_text().strip())
        # Defer focus clear so AdwEntryRow finishes its apply/button
        # handling first; clearing synchronously leaves the apply
        # button visible until a second click.
        GLib.idle_add(self._clear_focus)

    def on_preset_button_clicked(self, button):
        if self._active_preset["range"] is None:
            self.auto_detect_network()
        else:
            self.ip_entry_row.set_text(self._active_preset["range"])
        self._save_preset_settings()

    def _on_preset_menu_activate(self, action, parameter):
        action.change_state(parameter)

    def _on_preset_menu_change_state(self, action, state):
        try:
            index = int(state.get_string())
        except (ValueError, AttributeError):
            return
        if not 0 <= index < len(self._RANGE_PRESETS):
            return
        action.set_state(state)
        self._apply_preset(self._RANGE_PRESETS[index], popdown=True)

    def validate_ip_range(self):
        ip_range = self.ip_entry_row.get_text().strip()
        is_valid, message = self.scanner.validate_ip_range(ip_range)
        if not is_valid:
            # Persistent error state on the row; the message toasts once
            # and the ring clears on the next edit.
            self.ip_entry_row.add_css_class("error")
            self.show_toast(message)
        else:
            self.ip_entry_row.remove_css_class("error")
        return is_valid
