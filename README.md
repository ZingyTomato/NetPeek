# 🔎 NetPeek

A modern libadwaita-based network scanner for GNOME that helps you discover devices on your local network.

## 📖 Table Of Contents

* [`📷 Screenshots`](#-screenshots)
* [`⭐ Features`](#-features)
* [`🔧 Installation`](#-installation)
* [`🔨 Local Development`](#-local-development)
* [`👨🏻‍💻 Requirements`](#-requirements)
* [`🙌 Help translate!`](#-help-translate!)
* [`❓ Support`](#-support)

## 📷 Screenshots


![Home Page](https://github.com/ZingyTomato/NetPeek/blob/master/data/screenshots/1.png?raw=true)

![Results Page](https://github.com/ZingyTomato/NetPeek/blob/master/data/screenshots/2.png?raw=true)

![No Devices Found](https://github.com/ZingyTomato/NetPeek/blob/master/data/screenshots/3.png?raw=true)

## ⭐ Features

- 🔍 **Fast Network Scanning** - Discover active devices on your network
- 🎯 **Port Scanning** - Shows open ports on discovered devices
- 📱 **Modern UI** - Built with GTK4 and Libadwaita
- ⚡ **Multi-threaded** - Fast concurrent scanning
- 🔧 **Flexible Input** - Supports CIDR notation, IP ranges, and single IPs
- 🤖 **Automatic IP Detection** - Instantly finds your local IP range

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

### Python Dependencies

- `socket` - Network operations
- `ipaddress` - IP address validation
- `threading` - Concurrent scanning
- `python-nmap` - Find active hosts using nmap

## 🙌 Help translate!

Translations to your native language are very much appreciated.
Currently supported languages:
* Dutch
* Russian
* Spanish
* Italian
* French
* Polish
* Ukranian
* Slovakian

## 📙 License

This project is licensed under the GPL-3.0 License - see the [LICENSE](https://github.com/ZingyTomato/NetPeek/blob/master/LICENSE) file for details.

## ❓ Support

If you encounter any issues or have feature requests, please [open an issue](https://github.com/zingytomato/netpeek/issues).
