import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio

from .widgets import DeviceCard
from .scanner import NetworkScanner
from .pages import HomePage, ResultsPage

class NetworkScannerWindow(Adw.ApplicationWindow):
    """Main application window"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_title("NetPeek")
        self.set_default_size(900, 700)

        # Create toast overlay for notifications
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        # Create navigation view for page management
        self.navigation_view = Adw.NavigationView()
        self.toast_overlay.set_child(self.navigation_view)

        # Initialize scanner
        self.scanner = NetworkScanner()

        # Create and add pages
        self.setup_pages()

        # Add actions
        self.create_actions()

    def create_actions(self):
        """Create application actions"""
        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about_action)
        self.get_application().add_action(about_action)

        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self.on_quit_action)
        self.get_application().add_action(quit_action)

    def on_about_action(self, action, param):
        """Show about dialog"""
        about = Adw.AboutDialog()
        about.set_application_name("NetPeek")
        about.set_version("0.1")
        about.set_developer_name("ZingyTomato")
        about.set_license_type(Gtk.License.GPL_3_0)
        about.set_comments("Discover devices on your local network.")
        about.set_website("https://github.com/zingytomato/netpeek")
        about.set_issue_url("https://github.com/zingytomato/netpeek/issues")
        about.set_application_icon("io.github.zingytomato.netpeek")
        about.add_credit_section("Contributors", ["ZingyTomato"])
        about.present(self)

    def on_quit_action(self, action, param):
        """Quit the application"""
        self.get_application().quit()

    def setup_pages(self):
        """Setup the main pages"""
        self.home_page = HomePage(
            navigation_view=self.navigation_view,
            toast_overlay=self.toast_overlay,
            scanner=self.scanner
        )

        self.results_page = ResultsPage(
            navigation_view=self.navigation_view,
            toast_overlay=self.toast_overlay,
            scanner=self.scanner
        )

        # Connect pages
        self.home_page.connect_results_page(self.results_page)
        self.results_page.connect_home_page(self.home_page)

        self.navigation_view.add(self.home_page.page)

    def show_toast(self, message, timeout=3):
        """Show a toast notification"""
        toast = Adw.Toast(title=message)
        toast.set_timeout(timeout)
        self.toast_overlay.add_toast(toast)
