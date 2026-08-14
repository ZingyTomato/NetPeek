# 🔎 NetPeek

A modern libadwaita-based network scanner for GNOME that helps you discover devices on your local network.

## 📖 Table Of Contents

* [`📷 Screenshots`](#-screenshots)
* [`⭐ Features`](#-features)
* [`🔧 Installation`](#-installation)
* [`🙌 Help translate!`](#-help-translate)
* [`🔨 Local Development`](#-local-development)
* [`👨🏻‍💻 Requirements`](#%E2%80%8D-requirements)
* [`❓ Support`](#-support)

## 📷 Screenshots


![Home Page](https://github.com/ZingyTomato/NetPeek/blob/master/data/screenshots/1.png?raw=true)

![Scanning](https://github.com/ZingyTomato/NetPeek/blob/master/data/screenshots/2.png?raw=true)

![Results Page](https://github.com/ZingyTomato/NetPeek/blob/master/data/screenshots/3.png?raw=true)

![List View](https://github.com/ZingyTomato/NetPeek/blob/master/data/screenshots/4.png?raw=true)

![Deep Scan](https://github.com/ZingyTomato/NetPeek/blob/master/data/screenshots/5.png?raw=true)

![Previous Scans](https://github.com/ZingyTomato/NetPeek/blob/master/data/screenshots/6.png?raw=true)

## ⭐ Features

- 🔍 **Fast Network Scanning** - Discover active devices on your network
- 🎯 **Port Scanning** - Shows open ports on discovered devices
- 🖥️ **Service Detection** - Automatically identifies common services (SMB, Cockpit, MySQL, PostgreSQL, Plex, Home Assistant, and more)
- 🔬 **Deep Scan Mode** - Attempts OS detection & service version identification.
- 📇 **Custom Names & History** - Rename devices, browse and reload previous scans
- ℹ️ **Scan Info Dialog** - View detailed scan metadata for current and previous scans
- 🌗 **Dark Mode** - Follow system, or force light/dark
- ↕️ **Sortable Results** - Sort by known status, IP, hostname, custom name, ports, services, or OS
- 🔎 **Searchable Results** - Search and filter devices across all scan pages
- 📱 **Modern UI** - Built with GTK4 and Libadwaita
- ⚡ **Multi-threaded** - Fast concurrent scanning with a configurable thread count
- 🔧 **Flexible Input** - Supports CIDR notation, IP ranges, and single IPs
- 🤖 **Automatic IP Detection** - Instantly finds your local IP range
- 📤 **CSV Export** - Export scan results for use elsewhere

## 🔧 Installation

### 👍 Flathub (Recommended)
<a href='https://flathub.org/apps/io.github.zingytomato.netpeek'>
    <img width='240' alt='Get it on Flathub' src='https://flathub.org/api/badge?svg&locale=en'/>
</a>

Or install via the command line:
```sh
flatpak install flathub io.github.zingytomato.netpeek
```

### 👨🏻‍🔧 Unofficial Community Packages

[![Packaging status](https://repology.org/badge/vertical-allrepos/netpeek.svg)](https://repology.org/project/netpeek/versions)

Fedora COPR: https://copr.fedorainfracloud.org/coprs/infiniti151/flatpak-apps/package/netpeek/

## 🙌 Help translate!

[![Translation status](https://hosted.weblate.org/widgets/netpeek/-/netpeek/multi-auto.svg)](https://hosted.weblate.org/engage/netpeek/)

Translations to your native language are very much appreciated.

[Translate on Weblate](https://hosted.weblate.org/engage/netpeek/)

## 🔨 Local Development

### GNOME Builder

GNOME Builder is the environment used for developing this application.
It can use Flatpak manifests to create a consistent building and running
environment cross-distro. Thus, it is highly recommended you use it.

1. Download GNOME Builder.
2. In Builder, click the "Clone Repository" button at the bottom, using https://github.com/zingytomato/netpeek.git as the URL.
3. Click the build button at the top once the project is loaded.

### Supported Formats

- **CIDR**: `192.168.1.0/24`, `10.0.0.0/16`
- **Range**: `192.168.1.1-254`, `10.0.0.1-50`
- **Single IP**: `192.168.1.1`

## 👨🏻‍💻 Requirements

- **Python 3** with **PyGObject** (GTK4 bindings)
- **[python-nmap](https://pypi.org/project/python-nmap/)** — nmap library for network scanning
- **GTK4** and **libadwaita** (>= 1.6)
- **[nmap](https://nmap.org/)**

## 📙 License

This project is licensed under the GPL-3.0 License - see the [LICENSE](https://github.com/ZingyTomato/NetPeek/blob/master/LICENSE) file for details.

## ❓ Support

If you encounter any issues or have feature requests, please [open an issue](https://github.com/zingytomato/netpeek/issues).
