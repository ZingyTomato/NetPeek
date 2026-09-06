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
from gi.repository import Adw, Gio


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

    def __init__(self, settings, scanner, **kwargs):
        super().__init__(**kwargs)
        self._settings = settings
        self._scanner = scanner

        # Single group — no search needed yet.
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
        # Preserve previous SpinButton increments (10 step / 50 page).
        adjustment = self.thread_row.get_adjustment()
        if adjustment is not None:
            adjustment.set_page_increment(self.PAGE_INCREMENT)
        # Int key <-> double SpinRow value is bridged by the default
        # GIO mapping (a custom get_mapping cannot return a converted
        # value through PyGObject). The scanner side-effect rides on the
        # key so external changes (e.g. dconf) apply too.
        self._settings.bind('thread-count', self.thread_row, 'value',
                            Gio.SettingsBindFlags.DEFAULT)
        self._settings.connect(
            'changed::thread-count', self._on_thread_count_setting)
        group.add(self.thread_row)

    def _on_thread_count_setting(self, settings, _key):
        self._scanner.set_max_workers(settings.get_int('thread-count'))
