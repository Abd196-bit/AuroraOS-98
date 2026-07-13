project('auroraos', 'c',
  version: '0.1.0',
  default_options: [
    'warning_level=2',
    'c_std=c11'
  ]
)

executable('aurora-compositor',
  'src/aurora-compositor/main.c',
  install: true
)

executable('aurora-shell',
  'src/aurora-shell/main.c',
  include_directories: include_directories('src/aurora-shell'),
  install: true
)

executable('aurora-pi-hardwared',
  'src/aurora-pi-hardwared/main.c',
  install: true,
  install_dir: get_option('libexecdir') / 'aurora'
)

install_data(
  'assets/manifest.json',
  install_dir: get_option('datadir') / 'aurora' / 'assets'
)

install_data(
  'MSW98UI-Regular copy.ttf',
  rename: 'MSW98UI-Regular.ttf',
  install_dir: get_option('datadir') / 'aurora' / 'assets' / 'fonts'
)

install_data(
  'MSW98UI-Bold copy.ttf',
  rename: 'MSW98UI-Bold.ttf',
  install_dir: get_option('datadir') / 'aurora' / 'assets' / 'fonts'
)

install_data(
  'click.wav',
  install_dir: get_option('datadir') / 'aurora' / 'assets' / 'sounds'
)

install_data(
  'systemd/system/aurora-pi-hardwared.service',
  install_dir: get_option('prefix') / 'lib' / 'systemd' / 'system'
)

install_data(
  'systemd/user/aurora-session.target',
  'systemd/user/aurora-compositor.service',
  'systemd/user/aurora-shell.service',
  install_dir: get_option('prefix') / 'lib' / 'systemd' / 'user'
)
