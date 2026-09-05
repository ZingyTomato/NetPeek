import gi
from datetime import date, datetime, timedelta

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib

from ..widgets import ToastMixin
from .. import storage
from .helpers import build_checkmark_menu, setup_popover_breakpoints, parse_scan_dt


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
    start_day = Gtk.Template.Child()
    start_month = Gtk.Template.Child()
    start_year = Gtk.Template.Child()
    end_day = Gtk.Template.Child()
    end_month = Gtk.Template.Child()
    end_year = Gtk.Template.Child()
    custom_apply_button = Gtk.Template.Child()
    custom_clear_button = Gtk.Template.Child()
    empty_status_page = Gtk.Template.Child()

    _FILTER_PRESETS = [
        {"label": "All", "mode": "all"},
        {"label": "Today", "mode": "today"},
        {"label": "Yesterday", "mode": "yesterday"},
        {"label": "Last 7 Days", "mode": "7d"},
        {"label": "Last 30 Days", "mode": "30d"},
    ]

    _MONTHS = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
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
        self.install_action("filter.select", "s", self._on_filter_menu_select)
        self._build_filter_menu()

        setup_popover_breakpoints(self, self.filter_popover)

        self._build_date_dropdowns()
        self._connect_signals()
        self._update_button_labels()
        self._rebuild_list()
        self._connect_scroll()

    def _build_filter_menu(self):
        try:
            active = next(i for i, p in enumerate(self._FILTER_PRESETS) if p["mode"] == self._mode)
        except StopIteration:
            active = -1
        build_checkmark_menu(
            self.filter_menu_model,
            [_(p["label"]) for p in self._FILTER_PRESETS],
            active, "filter.select")

    def _build_date_dropdowns(self):
        days = Gtk.StringList.new([str(d) for d in range(1, 32)])
        months = Gtk.StringList.new(self._MONTHS)
        now = self._today_local()
        years = Gtk.StringList.new([str(y) for y in range(now.year - 5, now.year + 2)])
        for dropdown in (self.start_day, self.end_day):
            dropdown.set_model(days)
        for dropdown in (self.start_month, self.end_month):
            dropdown.set_model(months)
        for dropdown in (self.start_year, self.end_year):
            dropdown.set_model(years)

    def _connect_signals(self):
        self.custom_toggle.connect('toggled', self._on_custom_toggled)
        self.custom_apply_button.connect('clicked', self._on_custom_apply)
        self.custom_clear_button.connect('clicked', self._on_custom_clear)

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
        self._settings.set_string('history-filter-mode', self._mode)
        self._settings.set_string('history-custom-start',
                                   self._custom_start.isoformat() if self._custom_start else '')
        self._settings.set_string('history-custom-end',
                                   self._custom_end.isoformat() if self._custom_end else '')

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

    def _on_filter_menu_select(self, _widget, _action, param):
        try:
            index = int(param.get_string())
        except (ValueError, AttributeError):
            return
        if not 0 <= index < len(self._FILTER_PRESETS):
            return
        self._mode = self._FILTER_PRESETS[index]["mode"]
        self.custom_toggle.set_active(False)
        self.filter_popover.popdown()
        self._apply_filter_change()

    # ---- Custom range ----

    def _on_custom_toggled(self, toggle):
        reveal = toggle.get_active()
        self.custom_revealer.set_reveal_child(reveal)
        if reveal:
            self._seed_date_dropdowns(self._custom_start or self._today_local(),
                                      self._custom_end or self._today_local())

    def _seed_date_dropdowns(self, start, end):
        self._set_dropdown_date(self.start_day, self.start_month, self.start_year, start)
        self._set_dropdown_date(self.end_day, self.end_month, self.end_year, end)

    @staticmethod
    def _set_dropdown_date(day_dd, month_dd, year_dd, d):
        year_list = [int(year_dd.get_model().get_string(i)) for i in range(year_dd.get_model().get_n_items())]
        day_dd.set_selected(d.day - 1)
        month_dd.set_selected(d.month - 1)
        if d.year in year_list:
            year_dd.set_selected(year_list.index(d.year))

    def _get_dropdown_date(self, day_dd, month_dd, year_dd):
        day = day_dd.get_selected() + 1
        month = month_dd.get_selected() + 1
        year_str = year_dd.get_model().get_string(year_dd.get_selected())
        if not year_str:
            return None
        try:
            return date(int(year_str), month, day)
        except ValueError:
            return None

    def _on_custom_apply(self, _button):
        start = self._get_dropdown_date(self.start_day, self.start_month, self.start_year)
        end = self._get_dropdown_date(self.end_day, self.end_month, self.end_year)
        if start is None or end is None:
            self.show_toast(_("Invalid date selected."))
            return
        if start > end:
            self.show_toast(_("End date must be after start date."))
            return
        self._custom_start = start
        self._custom_end = end
        self._mode = 'custom'
        self.custom_toggle.set_active(False)
        self._apply_filter_change()

    def _on_custom_clear(self, _button):
        self._custom_start = None
        self._custom_end = None
        self._mode = 'all'
        self.custom_toggle.set_active(False)
        self._apply_filter_change()

    def _apply_filter_change(self):
        self._update_button_labels()
        self._build_filter_menu()
        self._reset_scroll()
        self._rebuild_list()

    def _update_button_labels(self):
        for preset in self._FILTER_PRESETS:
            if preset['mode'] == self._mode:
                self.filter_button.set_label(_(preset['label']))
                break
        else:
            self.filter_button.set_label(_("All"))

        if self._mode == 'custom' and self._custom_start and self._custom_end:
            self.custom_toggle.set_label('%s \u2013 %s' % (
                self._custom_start.strftime('%b %d'),
                self._custom_end.strftime('%b %d')))
        else:
            self.custom_toggle.set_label(_("Custom Range…"))

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
            self.empty_status_page.set_title(_("No Previous Scans"))
            self.empty_status_page.set_description(_("Your scan history will appear here."))
            self.history_stack.set_visible_child_name('empty')
            return

        if not filtered:
            self.empty_status_page.set_title(_("No Scans Found"))
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
        deep_suffix = " · " + _("Deep") if scan.get("deep_scan", False) else ""
        row.set_subtitle(_("{time} · {count} devices{deep}").format(
            time=time_str, count=device_count, deep=deep_suffix))
        row.set_activatable(True)
        row.scan_data = scan

        delete_button = Gtk.Button()
        delete_button.set_icon_name('user-trash-symbolic')
        delete_button.set_tooltip_text(_("Delete this scan"))
        delete_button.set_valign(Gtk.Align.CENTER)
        delete_button.add_css_class('flat')
        delete_button.connect('clicked', self._on_delete_clicked, row)
        row.add_suffix(delete_button)

        row.add_suffix(Gtk.Image.new_from_icon_name('go-next-symbolic'))
        return row

    def _on_delete_clicked(self, button, row):
        scan_data = getattr(row, 'scan_data', None)
        if not scan_data:
            return

        confirmation = Adw.AlertDialog.new(
            _("Delete Scan?"),
            _("This scan will be permanently removed from your history."),
        )
        confirmation.add_response("cancel", _("Cancel"))
        confirmation.add_response("delete", _("Delete"))
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
        storage.delete_scan(scan_data.get('timestamp', ''))
        self._rebuild_list()
        self.show_toast(_("Scan deleted"))

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
