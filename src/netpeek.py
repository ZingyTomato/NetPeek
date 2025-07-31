#!/usr/bin/env python3

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

import sys
from .app import NetworkScannerApp

def main(version="0.1.0"):
    """Main entry point for NetPeek application"""
    app = NetworkScannerApp()
    app.version = version
    return app.run(sys.argv)

if __name__ == '__main__':
    main()
