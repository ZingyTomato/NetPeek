<p align="center">
  <img src="data/icons/hicolor/scalable/apps/io.github.zingytomato.netpeek.svg" width="100" alt="NetPeek icon"/>
</p>

<h1 align="center">NetPeek</h1>

<p align="center">
  A modern libadwaita-based network scanner for GNOME that helps you discover devices on your local network.
</p>

<p align="center">
  <a href="https://flathub.org/apps/io.github.zingytomato.netpeek">
    <img width="140" alt="Download on Flathub" src="https://flathub.org/api/badge?svg&locale=en"/>
  </a>
  <a href="https://github.com/ZingyTomato/NetPeek/blob/master/LICENSE">
    <img alt="License: GPL v3" src="https://img.shields.io/badge/License-GPLv3-blue.svg"/>
  </a>
  <a href="https://hosted.weblate.org/engage/netpeek/">
    <img src="https://hosted.weblate.org/widgets/netpeek/-/netpeek/svg-badge.svg" alt="Translation status" />
  </a>
</p>

## 📖 Table of Contents

- [📷 Screenshots](#-screenshots)
- [⭐ Features](#-features)
- [🔧 Installation](#-installation)
- [🔨 Local Development](#-local-development)
- [🙌 Help Translate](#-help-translate)
- [❓ Support](#-support)
- [📙 License](#-license)

## 📷 Screenshots

<p align="center">
  <img src="https://github.com/ZingyTomato/NetPeek/blob/master/data/screenshots/1.png?raw=true" alt="Home Page" width="700"/>
</p>

<p align="center">
  <img src="https://github.com/ZingyTomato/NetPeek/blob/master/data/screenshots/2.png?raw=true" alt="Scanning in Progress" width="700"/>
</p>

<p align="center">
  <img src="https://github.com/ZingyTomato/NetPeek/blob/master/data/screenshots/3.png?raw=true" alt="Results Page" width="700"/>
</p>

<p align="center">
  <img src="https://github.com/ZingyTomato/NetPeek/blob/master/data/screenshots/4.png?raw=true" alt="List View" width="700"/>
</p>

<p align="center">
  <img src="https://github.com/ZingyTomato/NetPeek/blob/master/data/screenshots/5.png?raw=true" alt="Deep Scan" width="700"/>
</p>

<p align="center">
  <img src="https://github.com/ZingyTomato/NetPeek/blob/master/data/screenshots/6.png?raw=true" alt="Previous Scans" width="700"/>
</p>

## ⭐ Features

- **Fast Network Scanning** -- Discover active devices on your network
- **Port Scanning** -- Shows open ports on discovered devices
- **Service Detection** -- Automatically identifies common services (SMB, Cockpit, MySQL, PostgreSQL, Plex, Home Assistant, and more)
- **Deep Scan Mode** -- Attempts OS detection and service version identification
- **Custom Names and History** -- Rename devices, browse and reload previous scans
- **Scan Info Dialog** -- View detailed scan metadata for current and previous scans
- **Dark Mode** -- Follow system theme, or force light/dark
- **Sortable Results** -- Sort by known status, IP, hostname, custom name, ports, services, or OS
- **Searchable Results** -- Search and filter devices on scan pages
- **Modern UI** -- Built with GTK4 and libadwaita
- **Multi-threaded** -- Fast concurrent scanning with a configurable thread count
- **Flexible Input** -- Supports CIDR notation (`192.168.1.0/24`), IP ranges (`192.168.1.1-254`), and single IPs
- **Automatic IP Detection** -- Instantly finds your local IP range
- **CSV Export** -- Export scan results for use elsewhere

## 🔧 Installation

### 👍 Flathub (Recommended)

<a href="https://flathub.org/apps/io.github.zingytomato.netpeek">
    <img width="240" alt="Get it on Flathub" src="https://flathub.org/api/badge?svg&locale=en"/>
</a>

Or install via the command line:

```sh
flatpak install flathub io.github.zingytomato.netpeek
```

### 👨🏻‍🔧 Unofficial Community Packages

[![Packaging status](https://repology.org/badge/vertical-allrepos/netpeek.svg)](https://repology.org/project/netpeek/versions)

**Fedora COPR:** https://copr.fedorainfracloud.org/coprs/infiniti151/flatpak-apps/package/netpeek/

### 🔨 Building from Source

**Dependencies:**

- **Python 3** with **PyGObject** (GTK4 bindings)
- **[python-nmap](https://pypi.org/project/python-nmap/)** -- nmap library for network scanning
- **GTK4** and **libadwaita** (>= 1.6)
- **[nmap](https://nmap.org/)**

## 🔨 Local Development

[GNOME Builder](https://flathub.org/apps/org.gnome.Builder) is the recommended development environment. It uses Flatpak manifests to provide a consistent build environment across distributions.

1. Download GNOME Builder.
2. In Builder, click the "Clone Repository" button at the bottom, using `https://github.com/zingytomato/netpeek.git` as the URL.
3. Click the build button at the top once the project is loaded.

## 🙌 Help Translate

[![Translation status](https://hosted.weblate.org/widgets/netpeek/-/netpeek/multi-auto.svg)](https://hosted.weblate.org/engage/netpeek/)

Translations to your native language are very much appreciated.

[Translate on Weblate](https://hosted.weblate.org/engage/netpeek/)

## ❓ Support

If you encounter any issues or have feature requests, please [open an issue](https://github.com/zingytomato/netpeek/issues).

## 📙 License

This project is licensed under the GPL-3.0 License. See the [LICENSE](https://github.com/ZingyTomato/NetPeek/blob/master/LICENSE) file for details.
