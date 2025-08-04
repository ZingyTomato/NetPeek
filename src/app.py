# app.py
#
# Copyright 2025 ZingyTomato
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
