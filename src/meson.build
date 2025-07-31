pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'netpeek'
gnome = import('gnome')

gnome.compile_resources('netpeek',
  'netpeek.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'netpeek.in',
  output: 'netpeek',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'r-xr-xr-x'
)

netpeek_sources = [
  '__init__.py',
  'netpeek.py',
  'window.py',
  'pages.py',
  'app.py',
  'scanner.py',
  'widgets.py'
]

install_data(netpeek_sources, install_dir: moduledir)
