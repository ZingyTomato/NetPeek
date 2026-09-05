import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

from .helpers import parse_scan_dt


@Gtk.Template(resource_path='/io/github/zingytomato/netpeek/gtk/scan_metadata_dialog.ui')
class ScanMetadataDialog(Adw.Dialog):
    __gtype_name__ = 'ScanMetadataDialog'

    timestamp_row = Gtk.Template.Child()
    scan_type_row = Gtk.Template.Child()
    duration_row = Gtk.Template.Child()
    new_count_row = Gtk.Template.Child()
    known_count_row = Gtk.Template.Child()

    def __init__(self, scan, **kwargs):
        super().__init__(**kwargs)
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

    @staticmethod
    def _format_duration(seconds):
        seconds = int(seconds)
        minutes, secs = divmod(seconds, 60)
        if minutes < 60:
            if minutes:
                return _("{minutes} min {seconds} s").format(minutes=minutes, seconds=secs)
            return _("{seconds} s").format(seconds=secs)
        hours, minutes = divmod(minutes, 60)
        return _("{hours} h {minutes} min").format(hours=hours, minutes=minutes)
