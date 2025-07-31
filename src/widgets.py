import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

class DeviceCard(Adw.Bin):
    """Custom widget for displaying device information in a card format"""

    def __init__(self, device_info):
        super().__init__()

        # Create the main card using Adw.Clamp for proper sizing
        self.clamp = Adw.Clamp()
        self.clamp.set_maximum_size(320)
        self.clamp.set_tightening_threshold(280)

        # Create content group
        self.content_group = Adw.PreferencesGroup()
        self.content_group.set_margin_top(8)
        self.content_group.set_margin_bottom(8)
        self.content_group.set_margin_start(8)
        self.content_group.set_margin_end(8)

        # Create action rows for device information
        ip_address = device_info.get('ip', 'Unknown IP')
        self.ip_row = Adw.ActionRow()
        self.ip_row.set_title(ip_address)

        # Status indicator
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        status_box.set_spacing(6)
        status_box.set_valign(Gtk.Align.CENTER)

        status_indicator = Gtk.Image()
        status_indicator.set_from_icon_name("network-wireless-signal-excellent-symbolic")
        status_indicator.add_css_class("success")

        status_box.append(status_indicator)
        self.ip_row.add_suffix(status_box)

        # Hostname row
        hostname = device_info.get('hostname', 'Unknown')
        if hostname == ip_address:
            hostname = "Unknown"

        self.hostname_row = Adw.ActionRow()
        self.hostname_row.set_title("Hostname")
        self.hostname_row.set_subtitle(hostname)

        hostname_icon = Gtk.Image()
        hostname_icon.set_from_icon_name("computer-symbolic")
        self.hostname_row.add_prefix(hostname_icon)

        # Ports open row
        ports = device_info.get('ports', 'No Ports Open')
        self.ports_row = Adw.ActionRow()
        self.ports_row.set_title("Ports Open")
        self.ports_row.set_subtitle(ports)

        ports_icon = Gtk.Image()
        ports_icon.set_from_icon_name("network-wired-symbolic")
        self.ports_row.add_prefix(ports_icon)

        # Add rows to group
        self.content_group.add(self.ip_row)
        self.content_group.add(self.hostname_row)
        self.content_group.add(self.ports_row)

        self.clamp.set_child(self.content_group)
        self.set_child(self.clamp)

class PresetButton(Gtk.Button):
    """Custom preset button for IP ranges"""

    def __init__(self, preset_range, tooltip_text, callback=None):
        super().__init__()

        # Extract display text (e.g., "192.168.1.x" from "192.168.1.0/24")
        display_text = preset_range.split('/')[0].replace('.0', '.x')
        self.set_label(display_text)
        self.set_tooltip_text(tooltip_text)
        self.add_css_class("pill")

        self.preset_range = preset_range

        if callback:
            self.connect('clicked', callback, preset_range)

class StatusIndicator(Gtk.Box):
    """Custom status indicator widget"""

    def __init__(self, status="online"):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_spacing(6)
        self.set_valign(Gtk.Align.CENTER)

        self.indicator = Gtk.Image()
        self.set_status(status)

        self.append(self.indicator)

    def set_status(self, status):
        """Set the status indicator"""
        if status == "online":
            self.indicator.set_from_icon_name("network-wireless-signal-excellent-symbolic")
            self.indicator.add_css_class("success")
        elif status == "offline":
            self.indicator.set_from_icon_name("network-wireless-offline-symbolic")
            self.indicator.add_css_class("error")
        elif status == "scanning":
            self.indicator.set_from_icon_name("network-wireless-acquiring-symbolic")
            self.indicator.add_css_class("warning")
