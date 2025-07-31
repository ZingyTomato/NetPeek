import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio

from .widgets import DeviceCard, PresetButton

class HomePage:
    """Home page with IP input functionality"""

    def __init__(self, navigation_view, toast_overlay, scanner):
        self.navigation_view = navigation_view
        self.toast_overlay = toast_overlay
        self.scanner = scanner
        self.results_page = None

        self.page = self.create_page()

    def connect_results_page(self, results_page):
        """Connect the results page for navigation"""
        self.results_page = results_page

    def create_page(self):
        """Create the home page"""
        page = Adw.NavigationPage()
        page.set_title("NetPeek")

        toolbar_view = Adw.ToolbarView()
        page.set_child(toolbar_view)

        header_bar = Adw.HeaderBar()
        toolbar_view.add_top_bar(header_bar)

        window_title = Adw.WindowTitle()
        window_title.set_title("NetPeek")
        header_bar.set_title_widget(window_title)

        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_tooltip_text("Main Menu")

        menu_model = Gio.Menu()
        menu_model.append("About", "app.about")
        menu_model.append("Quit", "app.quit")
        menu_button.set_menu_model(menu_model)
        header_bar.pack_end(menu_button)

        main_content = self.create_content()
        toolbar_view.set_content(main_content)

        return page

    def create_content(self):
        """Create the home page content"""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.set_spacing(24)
        main_box.set_margin_top(48)
        main_box.set_margin_bottom(48)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)
        main_box.set_halign(Gtk.Align.CENTER)
        main_box.set_valign(Gtk.Align.CENTER)

        # Welcome section
        welcome_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        welcome_box.set_spacing(12)
        welcome_box.set_halign(Gtk.Align.CENTER)

        app_icon = Gtk.Image()
        app_icon.set_from_icon_name("network-wireless-symbolic")
        app_icon.set_pixel_size(64)
        app_icon.add_css_class("accent")
        welcome_box.append(app_icon)

        welcome_title = Gtk.Label()
        welcome_title.set_markup("<span size='x-large' weight='bold'>Discover devices on your local network.</span>")
        welcome_title.set_halign(Gtk.Align.CENTER)
        welcome_box.append(welcome_title)

        main_box.append(welcome_box)

        # IP input section
        self.setup_ip_input_section(main_box)

        # Scan button
        self.scan_button = Gtk.Button(label="Scan my Network")
        self.scan_button.add_css_class("suggested-action")
        self.scan_button.add_css_class("pill")
        self.scan_button.set_size_request(200, 48)
        self.scan_button.set_halign(Gtk.Align.CENTER)
        self.scan_button.connect('clicked', self.on_scan_clicked)
        main_box.append(self.scan_button)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(main_box)

        return scrolled

    def setup_ip_input_section(self, parent_box):
        """Create the IP range input section"""
        self.ip_group = Adw.PreferencesGroup()
        self.ip_group.set_title("IP Range Configuration")
        self.ip_group.set_description("Enter the IP range you want to scan:")

        self.ip_entry_row = Adw.EntryRow()
        self.ip_entry_row.set_title("IP Range")
        self.ip_entry_row.set_text("192.168.1.0/24")
        self.ip_entry_row.set_show_apply_button(True)
        self.ip_entry_row.connect('apply', self.on_ip_range_apply)
        self.ip_entry_row.connect('entry-activated', self.on_ip_range_apply)

        help_label = Gtk.Label()
        help_label.set_markup('<small><i>Examples: 192.168.1.0/24, 10.0.0.1-50, 172.16.1.100-200</i></small>')
        help_label.set_halign(Gtk.Align.START)
        help_label.set_margin_top(6)
        help_label.add_css_class("dim-label")

        # Preset buttons
        preset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        preset_box.set_spacing(6)
        preset_box.set_halign(Gtk.Align.CENTER)
        preset_box.set_margin_top(12)

        presets = [
            ("192.168.1.0/24", "Home Network (192.168.1.x)"),
            ("192.168.0.0/24", "Home Network (192.168.0.x)"),
            ("10.0.0.0/24", "Corporate (10.0.0.x)"),
            ("172.16.0.0/24", "Private (172.16.0.x)")
        ]

        for preset_range, tooltip in presets:
            preset_button = PresetButton(preset_range, tooltip, self.on_preset_clicked)
            preset_box.append(preset_button)

        auto_button = Gtk.Button(label="Auto-Detect")
        auto_button.set_tooltip_text("Try to automatically detect your network range.")
        auto_button.add_css_class("pill")
        auto_button.connect('clicked', self.on_auto_detect_clicked)
        preset_box.append(auto_button)

        self.ip_group.add(self.ip_entry_row)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(600)

        input_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        input_box.set_spacing(12)
        input_box.append(self.ip_group)
        input_box.append(help_label)
        input_box.append(preset_box)

        clamp.set_child(input_box)
        parent_box.append(clamp)

        # Auto-detect on startup
        self.auto_detect_network()

    def auto_detect_network(self):
        """Auto-detect network range"""
        network, message = self.scanner.auto_detect_network()
        self.ip_entry_row.set_text(network)
        self.show_toast(message)

    def on_scan_clicked(self, button):
        """Handle scan button click"""
        if not self.validate_ip_range():
            return

        ip_range = self.ip_entry_row.get_text().strip()

        if self.results_page:
            self.navigation_view.push(self.results_page.page)
            self.results_page.start_scan(ip_range)

    def on_ip_range_apply(self, entry_row):
        """Handle IP range apply button"""
        if self.validate_ip_range():
            self.show_toast("Valid IP range!", 2)

    def on_preset_clicked(self, button, preset_range):
        """Handle preset button click"""
        self.ip_entry_row.set_text(preset_range)
        self.show_toast(f"Set IP range to: {preset_range}", 2)

    def on_auto_detect_clicked(self, button):
        """Handle auto-detect button click"""
        self.auto_detect_network()

    def validate_ip_range(self):
        """Validate the IP range input"""
        ip_range = self.ip_entry_row.get_text().strip()
        is_valid, message = self.scanner.validate_ip_range(ip_range)

        if not is_valid:
            self.show_toast(message)

        return is_valid

    def show_toast(self, message, timeout=3):
        """Show a toast notification"""
        toast = Adw.Toast(title=message)
        toast.set_timeout(timeout)
        self.toast_overlay.add_toast(toast)


class ResultsPage:
    """Results page for displaying scan results"""

    def __init__(self, navigation_view, toast_overlay, scanner):
        self.navigation_view = navigation_view
        self.toast_overlay = toast_overlay
        self.scanner = scanner
        self.home_page = None

        self.page = self.create_page()

    def connect_home_page(self, home_page):
        """Connect the home page for navigation"""
        self.home_page = home_page

    def create_page(self):
        """Create the results page"""
        page = Adw.NavigationPage()
        page.set_title("Scanning in progress...")

        toolbar_view = Adw.ToolbarView()
        page.set_child(toolbar_view)

        header_bar = Adw.HeaderBar()
        toolbar_view.add_top_bar(header_bar)

        self.results_title = Adw.WindowTitle()
        self.results_title.set_title("Scan Results")
        self.results_title.set_subtitle("Devices found on your network:")
        header_bar.set_title_widget(self.results_title)

        self.rescan_button = Gtk.Button(label="Scan Again")
        self.rescan_button.add_css_class("suggested-action")
        self.rescan_button.connect('clicked', self.on_rescan_clicked)
        header_bar.pack_end(self.rescan_button)

        self.results_content = self.create_content()
        toolbar_view.set_content(self.results_content)

        return page

    def create_content(self):
        """Create the results page content"""
        self.results_stack = Gtk.Stack()
        self.results_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.results_stack.set_transition_duration(200)

        # Loading page
        loading_page = Adw.StatusPage()
        loading_page.set_title("Scanning Network")
        loading_page.set_description("Discovering devices on your network... (this may take a while!)")
        loading_page.set_icon_name("network-wireless-acquiring-symbolic")

        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(48, 48)
        self.spinner.add_css_class("large")
        loading_page.set_child(self.spinner)

        # Results scroll view
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_vexpand(True)

        self.flow_box = Gtk.FlowBox()
        self.flow_box.set_valign(Gtk.Align.START)
        self.flow_box.set_max_children_per_line(3)
        self.flow_box.set_min_children_per_line(1)
        self.flow_box.set_row_spacing(12)
        self.flow_box.set_column_spacing(12)
        self.flow_box.set_margin_top(24)
        self.flow_box.set_margin_bottom(24)
        self.flow_box.set_margin_start(24)
        self.flow_box.set_margin_end(24)
        self.flow_box.set_selection_mode(Gtk.SelectionMode.NONE)

        scrolled_window.set_child(self.flow_box)

        # Empty page
        self.empty_page = Adw.StatusPage()
        self.empty_page.set_title("No Devices Found")
        self.empty_page.set_description("No devices were found in the specified range!")
        self.empty_page.set_icon_name("network-wireless-offline-symbolic")

        # Error page
        self.error_page = Adw.StatusPage()
        self.error_page.set_title("Scan Error")
        self.error_page.set_description("An error occurred while scanning the network!")
        self.error_page.set_icon_name("dialog-error-symbolic")

        # Add pages to stack
        self.results_stack.add_named(loading_page, "loading")
        self.results_stack.add_named(scrolled_window, "devices")
        self.results_stack.add_named(self.empty_page, "empty")
        self.results_stack.add_named(self.error_page, "error")

        self.results_stack.set_visible_child_name("loading")

        return self.results_stack

    def start_scan(self, ip_range):
        """Start network scan"""
        self.rescan_button.set_sensitive(False)
        self.rescan_button.set_label("Scanning...")

        # Clear previous results
        self.clear_results()

        self.results_stack.set_visible_child_name("loading")
        self.spinner.start()

        self.results_title.set_subtitle(f"Scanning {ip_range}...")

        # Start scan
        self.scanner.scan_network(
            ip_range,
            self.on_scan_complete,
            self.on_scan_error
        )

    def clear_results(self):
        """Clear previous scan results"""
        child = self.flow_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.flow_box.remove(child)
            child = next_child

    def on_rescan_clicked(self, button):
        """Handle rescan button click"""
        if self.home_page:
            ip_range = self.home_page.ip_entry_row.get_text().strip()
            if ip_range and self.home_page.validate_ip_range():
                self.start_scan(ip_range)
            else:
                self.navigation_view.pop()

    def on_scan_complete(self, devices):
        """Handle scan completion"""
        self.spinner.stop()
        self.rescan_button.set_sensitive(True)
        self.rescan_button.set_label("Scan Again")

        if devices:
            for device in devices:
                card = DeviceCard(device)
                self.flow_box.append(card)

            self.results_stack.set_visible_child_name("devices")
            self.results_title.set_subtitle(f"Found {len(devices)} devices")

            self.show_toast(f"Found {len(devices)} devices on the network.")
        else:
            self.results_stack.set_visible_child_name("empty")
            self.results_title.set_subtitle("No devices found")
            self.show_toast("No devices found in the specified range")

    def on_scan_error(self, error_message):
        """Handle scan error"""
        self.spinner.stop()
        self.rescan_button.set_sensitive(True)
        self.rescan_button.set_label("Scan Again")

        self.results_stack.set_visible_child_name("error")
        self.error_page.set_description(f"Error: {error_message}")
        self.results_title.set_subtitle("An error occurred!")

        self.show_toast(f"Error: {error_message}", 5)

    def show_toast(self, message, timeout=3):
        """Show a toast notification"""
        toast = Adw.Toast(title=message)
        toast.set_timeout(timeout)
        self.toast_overlay.add_toast(toast)
