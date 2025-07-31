import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw

from .window import NetworkScannerWindow

class NetworkScannerApp(Adw.Application):
    """Main application class for NetPeek"""

    def __init__(self):
        super().__init__(application_id='io.github.zingytomato.netpeek')
        self.devices = []

    def do_activate(self):
        """Called when the application is activated"""
        self.window = NetworkScannerWindow(application=self)
        self.window.present()
