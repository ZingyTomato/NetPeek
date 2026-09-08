import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk, GLib

from .helpers import parse_scan_dt


@Gtk.Template(resource_path='/io/github/zingytomato/netpeek/gtk/scan_metadata_dialog.ui')
class ScanMetadataDialog(Adw.Dialog):
    __gtype_name__ = 'ScanMetadataDialog'

    timestamp_row = Gtk.Template.Child()
    ip_range_row = Gtk.Template.Child()
    ip_copy_button = Gtk.Template.Child()
    scan_type_row = Gtk.Template.Child()
    duration_row = Gtk.Template.Child()
    new_count_row = Gtk.Template.Child()
    known_count_row = Gtk.Template.Child()

    def __init__(self, scan, **kwargs):
        super().__init__(**kwargs)
        ip_range = scan.get('ip_range', '')
        self._ip_range = ip_range
        if ip_range:
            self.ip_range_row.set_subtitle(ip_range)
        else:
            self.ip_range_row.set_visible(False)
        ts = scan.get('timestamp', '')
        dt = parse_scan_dt(ts)
        if dt:
            local = dt.astimezone()
            gdt = GLib.DateTime.new_local(
                local.year, local.month, local.day, local.hour, local.minute, local.second
            )
            self.timestamp_row.set_subtitle(gdt.format('%A, %B %d, %Y · %H:%M') or ts)
        else:
            self.timestamp_row.set_subtitle(ts)
        self.scan_type_row.set_subtitle(_("Deep") if scan.get('deep_scan', False) else _("Standard"))
        duration = scan.get('duration_seconds') or 0
        if duration:
            self.duration_row.set_visible(True)
            self.duration_row.set_subtitle(self._format_duration(duration))
        devices = scan.get('devices', [])
        self.new_count_row.set_subtitle(str(sum(1 for d in devices if not d.get('known', False))))
        self.known_count_row.set_subtitle(str(sum(1 for d in devices if d.get('known', False))))

    @Gtk.Template.Callback()
    def on_ip_range_copy_clicked(self, button):
        if not self._ip_range:
            return
        display = Gdk.Display.get_default()
        if display is None:
            return
        display.get_clipboard().set(self._ip_range)

    @staticmethod
    def _format_duration(seconds):
        seconds = int(seconds)
        minutes, secs = divmod(seconds, 60)
        if minutes < 60:
            if minutes:
                return _("{minutes} {seconds}").format(
                    minutes=ngettext(
                        "{n} minute", "{n} minutes", minutes).format(n=minutes),
                    seconds=ngettext(
                        "{n} second", "{n} seconds", secs).format(n=secs))
            return ngettext("{n} second", "{n} seconds", secs).format(n=secs)
        hours, minutes = divmod(minutes, 60)
        return _("{hours} {minutes}").format(
            hours=ngettext("{n} hour", "{n} hours", hours).format(n=hours),
            minutes=ngettext("{n} minute", "{n} minutes", minutes).format(
                n=minutes))
