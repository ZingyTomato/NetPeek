# preferences.py
#
# Copyright 2026 ZingyTomato
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gio, Gtk

from .. import models



class PreferencesDialog(Adw.PreferencesDialog):
    """App preferences following GNOME HIG boxed-lists pattern.

    Currently hosts the scan thread count as an
    :class:`Adw.SpinRow` with instant-apply to GSettings + scanner.
    """
    __gtype_name__ = 'PreferencesDialog'

    MIN_THREADS = 1
    MAX_THREADS = 500
    STEP = 10
    PAGE_INCREMENT = 50
    # savig old ports in case the edit is invalid
    OLD_PORTS = models.BASE_PORTS

    def __init__(self, settings, scanner, toast_overlay, **kwargs):
        super().__init__(**kwargs)
        self._settings = settings
        self._scanner = scanner
        self._toast_overlay = toast_overlay
        # formatting BASE_PORTS for input box
        ports_string = ", ".join(str(port) for port in models.BASE_PORTS)

        self.set_search_enabled(False)

        page = Adw.PreferencesPage()
        page.set_title(_("General"))
        page.set_icon_name("emblem-system-symbolic")
        self.add(page)

        group = Adw.PreferencesGroup()
        group.set_title(_("Scanning"))
        group.set_description(_(
            "Tune how aggressively NetPeek scans your network."
        ))
        page.add(group)

        self.thread_row = Adw.SpinRow.new_with_range(
            self.MIN_THREADS, self.MAX_THREADS, self.STEP)
        self.thread_row.set_title(_("Threads"))
        self.thread_row.set_subtitle(_(
            "Concurrent workers. Higher is faster but uses more resources."
        ))
        adjustment = self.thread_row.get_adjustment()
        if adjustment is not None:
            adjustment.set_page_increment(self.PAGE_INCREMENT)
        self._settings.bind('thread-count', self.thread_row, 'value',
                            Gio.SettingsBindFlags.DEFAULT)
        self._settings.connect(
            'changed::thread-count', self._on_thread_count_setting)
        group.add(self.thread_row)

        # Adjusting Ports
        # Ports group
        ports_group = Adw.PreferencesGroup()
        ports_group.set_title(_("Ports List"))
        ports_group.set_description(_("Add or remove ports that get scanned, seperated by commas.\nChanges are only saved for the current session!"))
        page.add(ports_group)

        # Ports entry
        self.port_entry = Gtk.Entry()
        # self.port_entry.set_placeholder_text(_("e.g. 8080"))
        self.port_entry.set_text(ports_string)
        self.port_entry.set_hexpand(True)

        # Add focus controller for saving on focus leave
        focus_controller = Gtk.EventControllerFocus()
        focus_controller.connect("leave", self._on_ports_setting)
        self.port_entry.add_controller(focus_controller)
        ports_group.add(self.port_entry)

    def _on_thread_count_setting(self, settings, _key):
        self._scanner.set_max_workers(settings.get_int('thread-count'))

    def _on_ports_setting(self, _key):
        try:
            models.BASE_PORTS = [int(port) for port in self.port_entry.get_text().split(", ")]
        except ValueError:
            self._toast_overlay.add_toast(
                Adw.Toast(
                    title=_("Invalid ports list, edits not saved"),
                    timeout=3,
                    priority=Adw.ToastPriority.HIGH,
                )
            )
            models.BASE_PORTS = self.OLD_PORTS

        return False
