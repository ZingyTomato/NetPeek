import gi
from datetime import date, datetime, timedelta

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib

from ..widgets import ToastMixin
from .. import storage
from .helpers import build_radio_menu, parse_scan_dt


@Gtk.Template(resource_path='/io/github/zingytomato/netpeek/gtk/history_dialog.ui')
class HistoryDialog(Adw.Dialog, ToastMixin):
    """Dialog listing previous scans grouped by date, with date range filtering"""
    __gtype_name__ = 'HistoryDialog'

    toast_overlay = Gtk.Template.Child()
    history_stack = Gtk.Template.Child()
    history_list = Gtk.Template.Child()
    history_scrolled = Gtk.Template.Child()
    scroll_top_button = Gtk.Template.Child()
    filter_button = Gtk.Template.Child()
    filter_popover = Gtk.Template.Child()
    custom_toggle = Gtk.Template.Child()
    custom_revealer = Gtk.Template.Child()
    custom_error_label = Gtk.Template.Child()
    custom_bottom_bar = Gtk.Template.Child()
    start_button = Gtk.Template.Child()
    start_calendar = Gtk.Template.Child()
    end_button = Gtk.Template.Child()
    end_calendar = Gtk.Template.Child()
    custom_apply_button = Gtk.Template.Child()
    custom_clear_button = Gtk.Template.Child()
    empty_status_page = Gtk.Template.Child()

    _FILTER_PRESETS = [
        {"label": _("All"), "mode": "all"},
        {"label": _("Today"), "mode": "today"},
        {"label": _("Yesterday"), "mode": "yesterday"},
        {"label": _("Last 7 days"), "mode": "7d"},
        {"label": _("Last 30 days"), "mode": "30d"},
    ]

    _scroll_positions = {}

    def __init__(self, on_select, settings, **kwargs):
        super().__init__(**kwargs)
        self._on_select = on_select
        self._settings = settings
        self._mode = settings.get_string('history-filter-mode')
        cs = settings.get_string('history-custom-start')
        ce = settings.get_string('history-custom-end')
        self._custom_start = date.fromisoformat(cs) if cs else None
        self._custom_end = date.fromisoformat(ce) if ce else None
        self.connect('closed', self._on_closed)

        self.filter_popover.add_css_class("filter-popover")
        self.filter_menu_model = Gio.Menu()
        self.filter_popover.set_menu_model(self.filter_menu_model)
        self._filter_action_group = Gio.SimpleActionGroup()
        # Settings-backed action: the menu tick tracks the key directly.
        self._filter_action_group.add_action(
            self._settings.create_action('history-filter-mode'))
        self.insert_action_group("filter", self._filter_action_group)
        self._settings.connect(
            'changed::history-filter-mode', self._on_filter_mode_setting)
        self._build_filter_menu()

        self._connect_signals()
        self._update_button_labels()
        self._rebuild_list()
        self._connect_scroll()

    @staticmethod
    def _format_calendar_date(d):
        return GLib.DateTime.new_local(d.year, d.month, d.day, 0, 0, 0).format('%x')

    @staticmethod
    def _calendar_to_date(calendar):
        gdt = calendar.get_date()
        return date(gdt.get_year(), gdt.get_month(), gdt.get_day_of_month())

    @staticmethod
    def _date_to_calendar(calendar, d):
        calendar.set_date(GLib.DateTime.new_local(d.year, d.month, d.day, 0, 0, 0))

    def _build_filter_menu(self):
        # Built once; targets are mode strings, so the tick follows the
        # 'history-filter-mode' key — 'custom' matches nothing, unticked.
        build_radio_menu(
            self.filter_menu_model,
            [p["label"] for p in self._FILTER_PRESETS],
            "filter.history-filter-mode",
            targets=[p["mode"] for p in self._FILTER_PRESETS])

    def _connect_signals(self):
        self.custom_toggle.connect('toggled', self._on_custom_toggled)
        self.custom_apply_button.connect('clicked', self._on_custom_apply)
        self.custom_clear_button.connect('clicked', self._on_custom_clear)
        self.start_calendar.connect('day-selected', self._on_start_day_selected)
        self.end_calendar.connect('day-selected', self._on_end_day_selected)

    def _connect_scroll(self):
        vadj = self.history_scrolled.get_vadjustment()
        if vadj:
            vadj.connect('value-changed', self._on_scroll)

    def _on_scroll(self, vadj):
        self.scroll_top_button.set_visible(vadj.get_value() > 100)

    def _on_closed(self, _dialog):
        vadj = self.history_scrolled.get_vadjustment()
        if vadj:
            key = (self._mode, self._custom_start, self._custom_end)
            HistoryDialog._scroll_positions[key] = int(vadj.get_value())

    def _reset_scroll(self):
        vadj = self.history_scrolled.get_vadjustment()
        if vadj:
            vadj.set_value(0)

    def _restore_scroll(self):
        vadj = self.history_scrolled.get_vadjustment()
        key = (self._mode, self._custom_start, self._custom_end)
        saved = HistoryDialog._scroll_positions.get(key, 0)
        if vadj and saved > 0:
            vadj.set_value(min(saved, vadj.get_upper() - vadj.get_page_size()))
        return False


    # ---- Preset handling ----

    def _on_filter_mode_setting(self, settings, _key):
        """Re-filter when the mode key changes (menu, custom range, dconf)."""
        self._mode = settings.get_string('history-filter-mode')
        self.custom_toggle.set_active(False)
        self._apply_filter_change()

    # ---- Custom range ----

    def _on_custom_toggled(self, toggle):
        reveal = toggle.get_active()
        self.custom_revealer.set_reveal_child(reveal)
        self.custom_bottom_bar.set_visible(reveal)
        # Enter confirms the range only while the custom UI is open.
        self.set_default_widget(self.custom_apply_button if reveal else None)
        if reveal:
            self.custom_error_label.set_visible(False)
            self._seed_calendars(self._custom_start or self._today_local(),
                                 self._custom_end or self._today_local())

    def _seed_calendars(self, start, end):
        self._date_to_calendar(self.start_calendar, start)
        self._date_to_calendar(self.end_calendar, end)
        self.start_button.set_label(self._format_calendar_date(start))
        self.end_button.set_label(self._format_calendar_date(end))

    def _on_start_day_selected(self, calendar):
        start = self._calendar_to_date(calendar)
        self.start_button.set_label(self._format_calendar_date(start))
        self.custom_error_label.set_visible(False)
        self.start_button.popdown()

    def _on_end_day_selected(self, calendar):
        end = self._calendar_to_date(calendar)
        self.end_button.set_label(self._format_calendar_date(end))
        self.custom_error_label.set_visible(False)
        self.end_button.popdown()

    def _on_custom_apply(self, _button):
        # Calendars only yield valid dates, so only ordering needs checking.
        start = self._calendar_to_date(self.start_calendar)
        end = self._calendar_to_date(self.end_calendar)
        if start > end:
            self.custom_error_label.set_visible(True)
            return
        self.custom_error_label.set_visible(False)
        self._custom_start = start
        self._custom_end = end
        self._settings.set_string('history-custom-start', start.isoformat())
        self._settings.set_string('history-custom-end', end.isoformat())
        self._settings.set_string('history-filter-mode', 'custom')

    def _on_custom_clear(self, _button):
        self._custom_start = None
        self._custom_end = None
        self.custom_error_label.set_visible(False)
        self._settings.set_string('history-custom-start', '')
        self._settings.set_string('history-custom-end', '')
        self._settings.set_string('history-filter-mode', 'all')

    def _apply_filter_change(self):
        self._update_button_labels()
        self._reset_scroll()
        self._rebuild_list()

    def _update_button_labels(self):
        for preset in self._FILTER_PRESETS:
            if preset['mode'] == self._mode:
                self.filter_button.set_label(preset['label'])
                break
        else:
            self.filter_button.set_label(_("All"))

        if self._mode == 'custom' and self._custom_start and self._custom_end:
            self.custom_toggle.set_label(_("{start} – {end}").format(
                start=self._custom_start.strftime('%b %d'),
                end=self._custom_end.strftime('%b %d')))
        else:
            self.custom_toggle.set_label(_("Custom range"))

    # ---- Date range helpers ----

    @staticmethod
    def _today_local():
        return datetime.now().astimezone().date()

    def _range_for_mode(self, mode):
        today = self._today_local()
        if mode == 'today':
            return today, today
        if mode == 'yesterday':
            yesterday = today - timedelta(days=1)
            return yesterday, yesterday
        if mode == '7d':
            return today - timedelta(days=6), today
        if mode == '30d':
            return today - timedelta(days=29), today
        if mode == 'custom' and self._custom_start and self._custom_end:
            return self._custom_start, self._custom_end
        return None

    def _scan_date(self, scan):
        dt = parse_scan_dt(scan.get('timestamp', ''))
        return dt.astimezone().date() if dt else None

    def _get_filtered_scans(self):
        scans = storage.load_scans()
        rng = self._range_for_mode(self._mode)
        if rng is None:
            return scans
        date_from, date_to = rng
        return [s for s in scans
                if (sd := self._scan_date(s)) is not None
                and date_from <= sd <= date_to]

    # ---- List building ----

    @staticmethod
    def _make_header_row(title):
        label = Gtk.Label(label=title)
        label.set_halign(Gtk.Align.START)
        label.set_margin_start(16)
        label.set_margin_end(16)
        label.set_margin_top(24)
        label.set_margin_bottom(6)
        label.add_css_class('heading')
        row = Gtk.ListBoxRow()
        row.set_selectable(False)
        row.set_activatable(False)
        row.set_can_focus(False)
        row.set_property('accessible-role', Gtk.AccessibleRole.HEADING)
        row.set_child(label)
        return row

    @staticmethod
    def _format_date_header(iso_string):
        dt = parse_scan_dt(iso_string)
        if not dt:
            return iso_string
        local_dt = dt.astimezone()
        today = datetime.now(local_dt.tzinfo).date()
        scan_date = local_dt.date()
        if scan_date == today:
            return _("Today")
        if scan_date == today - timedelta(days=1):
            return _("Yesterday")
        gdt = GLib.DateTime.new_local(
            local_dt.year, local_dt.month, local_dt.day, 0, 0, 0
        )
        if local_dt.year != today.year:
            return gdt.format('%A, %B %d, %Y')
        return gdt.format('%A, %B %d')

    def _rebuild_list(self):
        child = self.history_list.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.history_list.remove(child)
            child = next_child

        scans = storage.load_scans()
        total_scans = len(scans)
        filtered = self._get_filtered_scans()

        if total_scans == 0:
            self.empty_status_page.set_title(_("No previous scans"))
            self.empty_status_page.set_description(_("Your scan history will appear here."))
            self.history_stack.set_visible_child_name('empty')
            return

        if not filtered:
            self.empty_status_page.set_title(_("No scans found"))
            self.empty_status_page.set_description(_("No scans match the selected time range."))
            self.history_stack.set_visible_child_name('empty')
            return

        self.history_stack.set_visible_child_name('list')

        groups = {}
        for scan in filtered:
            dt = parse_scan_dt(scan.get('timestamp', ''))
            date_key = dt.astimezone().date().isoformat() if dt else scan.get('timestamp', '')
            groups.setdefault(date_key, []).append(scan)

        for date_key in sorted(groups.keys(), reverse=True):
            scans_in_group = groups[date_key]
            header = self._make_header_row(
                self._format_date_header(scans_in_group[0].get('timestamp', ''))
            )
            self.history_list.append(header)
            for scan in scans_in_group:
                self.history_list.append(self._build_row(scan))

        GLib.idle_add(self._restore_scroll)

    def _build_row(self, scan):
        row = Adw.ActionRow()
        row.set_title(scan.get('ip_range', ''))
        device_count = len(scan.get('devices', []))
        dt = parse_scan_dt(scan.get('timestamp', ''))
        time_str = dt.astimezone().strftime('%H:%M') if dt else ""
        count_str = ngettext(
            "{count} device", "{count} devices", device_count,
        ).format(count=device_count)
        if scan.get("deep_scan", False):
            row.set_subtitle(_("{time} · {count} · Deep").format(
                time=time_str, count=count_str))
        else:
            row.set_subtitle(_("{time} · {count}").format(
                time=time_str, count=count_str))
        row.set_activatable(True)
        row.scan_data = scan

        delete_button = Gtk.Button()
        delete_button.set_icon_name('user-trash-symbolic')
        delete_button.set_tooltip_text(_("Delete this scan"))
        delete_button.update_property(
            [Gtk.AccessibleProperty.LABEL], [_("Delete this scan")])
        delete_button.set_valign(Gtk.Align.CENTER)
        delete_button.add_css_class('flat')
        delete_button.connect('clicked', self._on_delete_clicked, row)
        row.add_suffix(delete_button)

        chevron = Gtk.Image.new_from_icon_name('go-next-symbolic')
        chevron.set_property('accessible-role', Gtk.AccessibleRole.PRESENTATION)
        row.add_suffix(chevron)
        return row

    def _on_delete_clicked(self, button, row):
        scan_data = getattr(row, 'scan_data', None)
        if not scan_data:
            return

        scan_label = scan_data.get('ip_range', '')
        confirmation = Adw.AlertDialog.new(
            _("Delete scan?"),
            _("“{scan}” will be permanently removed from your history. "
              "This cannot be undone.").format(scan=scan_label),
        )
        confirmation.add_response("cancel", _("Cancel"))
        confirmation.add_response("delete", _("Delete Scan"))
        confirmation.set_response_appearance(
            "delete", Adw.ResponseAppearance.DESTRUCTIVE)
        confirmation.set_default_response("cancel")
        confirmation.set_close_response("cancel")
        confirmation.connect(
            "response",
            lambda _dialog, response: self._delete_confirmed(response, scan_data),
        )
        confirmation.present(self)

    def _delete_confirmed(self, response, scan_data):
        if response != "delete":
            return
        deleted = dict(scan_data)
        storage.delete_scan(scan_data.get('timestamp', ''))
        self._rebuild_list()
        toast = Adw.Toast(title=_("Scan deleted"))
        toast.set_button_label(_("Undo"))
        toast.connect("button-clicked", self._on_delete_undone, deleted)
        self.toast_overlay.add_toast(toast)

    def _on_delete_undone(self, _toast, scan):
        storage.restore_scan(scan)
        self._rebuild_list()

    @Gtk.Template.Callback()
    def on_scan_row_activated(self, listbox, row):
        if not row.get_selectable():
            return
        scan_data = getattr(row, 'scan_data', None)
        if scan_data:
            self._on_select(scan_data)
            self.close()

    @Gtk.Template.Callback()
    def on_scroll_top_clicked(self, button):
        vadj = self.history_scrolled.get_vadjustment()
        if vadj:
            vadj.set_value(0)
