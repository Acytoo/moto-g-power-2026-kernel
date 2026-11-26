"""Configure the newly bootstrapped native Debian root; never edits partitions."""
from pathlib import Path
import json
import argparse
import re
import os
import shutil
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--build-dir', type=Path, required=True)
parser.add_argument('--hostname', default='moto-server')
args = parser.parse_args()
BASE = args.build_dir.resolve()
ROOT = BASE / 'debian-root'
INPUT = BASE / 'rootfs-input'
assert re.fullmatch(r'[a-z0-9][a-z0-9-]{0,62}', args.hostname)
assert BASE != Path('/') and ROOT.resolve() == ROOT and INPUT.resolve() == INPUT
assert os.geteuid() == 0



def run(*args, **kw):
    return subprocess.run([str(a) for a in args], check=True, **kw)


def write(name, text, mode=0o644):
    p = ROOT / name.lstrip('/'); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text); p.chmod(mode)


def install(source, target, mode=0o644):
    p = ROOT / target.lstrip('/'); p.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, p); p.chmod(mode)


assert (ROOT / 'etc/debian_version').read_text().startswith('13.')
assert not (ROOT / 'etc/vegas/native-setup-complete').exists()
overlay = INPUT / 'overlay'
for p in overlay.rglob('*'):
    if p.is_file():
        install(p, str(p.relative_to(overlay)), p.stat().st_mode & 0o777)
write('/etc/hostname', args.hostname + '\n')
write('/etc/hosts', '127.0.0.1 localhost\n127.0.1.1 ' + args.hostname + '\n::1 localhost ip6-localhost ip6-loopback\n')
write('/etc/apt/sources.list', 'deb https://deb.debian.org/debian trixie main\ndeb https://deb.debian.org/debian trixie-updates main\ndeb https://security.debian.org/debian-security trixie-security main\n')
write('/etc/ssh/sshd_config.d/vegas.conf', 'Port 22\nPort 8022\nPermitRootLogin prohibit-password\nPasswordAuthentication no\nKbdInteractiveAuthentication no\nSetEnv LANG=C.UTF-8\n')
account = json.loads((INPUT / 'capture/account.private.json').read_text())
fields = account['passwd'].split(':'); uid, gid, home, shell = fields[2], fields[3], fields[5], fields[6]
user = fields[0]
assert re.fullmatch(r'[a-z_][a-z0-9_-]*', user) and int(uid) > 0 and int(gid) > 0
assert home == '/home/' + user and shell in ('/bin/zsh', '/bin/bash')
run('chroot', ROOT, 'groupadd', '-g', gid, user)
run('chroot', ROOT, 'useradd', '-u', uid, '-g', gid, '-m', '-s', shell, user)
run('chroot', ROOT, 'usermod', '-aG', 'sudo', user)
shadow = account['shadow'].split(':'); assert shadow[0] == user and shadow[1].startswith('$')
run('chroot', ROOT, 'chpasswd', '-e', input=(user + ':' + shadow[1] + '\n').encode())
run('tar', '-xf', INPUT / 'capture/user-home.private.tar', '-C', ROOT)
run('chown', '-R', uid + ':' + gid, ROOT / 'home' / user)
install(INPUT / 'login-authorized_keys', home + '/.ssh/authorized_keys', 0o600)
run('chown', '-R', uid + ':' + gid, ROOT / 'home' / user / '.ssh')
(ROOT / 'home' / user / '.ssh').chmod(0o700)
install(INPUT / 'login-authorized_keys', '/root/.ssh/authorized_keys', 0o600)
(ROOT / 'root/.ssh').chmod(0o700)
run('chroot', ROOT, 'passwd', '-l', 'root', stdout=subprocess.DEVNULL)
for p in (INPUT / 'capture/ssh').iterdir():
    install(p, '/etc/ssh/' + p.name, 0o644 if p.suffix == '.pub' else 0o600)
for p in (INPUT / 'capture/runtime/apex').rglob('*'):
    if p.is_file(): install(p, '/apex/' + str(p.relative_to(INPUT / 'capture/runtime/apex')), 0o755 if p.name == 'linker64' else 0o644)
install(INPUT / 'capture/runtime/ld.config.android.txt', '/linkerconfig/ld.config.txt')
install(BASE / 'out/libpropshim.so', '/odm/lib64/libpropshim.so')
for name in ['vendor', 'vendor_dlkm', 'android/system', 'config', 'mnt/vendor/nvcfg/fg', 'mnt/vendor/nvdata/APCFG/APRDEB']:
    (ROOT / name).mkdir(parents=True, exist_ok=True)
assert not (ROOT / 'system').exists()
(ROOT / 'system').symlink_to('/android/system/system')
for p in (INPUT / 'capture/nvcfg_fg').iterdir(): install(p, '/mnt/vendor/nvcfg/fg/' + p.name, 0o600)
for p in (INPUT / 'capture/nvram').iterdir(): install(p, '/mnt/vendor/nvdata/APCFG/APRDEB/' + p.name, 0o640)
release = (INPUT / 'kernel.release').read_text().strip()
modules = ROOT / 'lib/modules' / release / 'vendor'; modules.mkdir(parents=True, exist_ok=True)
for sub in ['vendor_dlkm', 'vendor_ramdisk00']:
    for p in (INPUT / 'modules' / sub).rglob('*.ko'): shutil.copyfile(p, modules / p.name)
run('depmod', '-b', ROOT, release)
install(INPUT / 'capture/wpa_supplicant-wlan0.conf', '/etc/wpa_supplicant/wpa_supplicant-wlan0.conf', 0o600)
server = INPUT / 'capture/server'
run('chroot', ROOT, 'useradd', '--system', '--home-dir', '/var/lib/xray', '--create-home', '--shell', '/usr/sbin/nologin', 'xray')
install(server / 'usr/local/bin/xray', '/usr/local/bin/xray', 0o755)
install(server / 'etc/xray/config.json', '/etc/xray/config.json', 0o640)
run('chroot', ROOT, 'chown', 'root:xray', '/etc/xray/config.json')
run('chroot', ROOT, '/usr/local/bin/xray', 'run', '-test', '-config', '/etc/xray/config.json', stdout=subprocess.DEVNULL)
run('chroot', ROOT, 'useradd', '--system', '--home-dir', '/var/lib/moto-tunnel', '--create-home', '--shell', '/usr/sbin/nologin', 'moto-tunnel')
install(server / 'root/.ssh/moto_tunnel_ed25519', '/etc/moto-tunnel/identity', 0o600)
install(server / 'root/.ssh/moto_vps_known_hosts', '/etc/moto-tunnel/known_hosts', 0o600)
config = (server / 'root/.ssh/moto_tunnel_config').read_text()
config = config.replace('/root/.ssh/moto_tunnel_ed25519', '/etc/moto-tunnel/identity').replace('/root/.ssh/moto_vps_known_hosts', '/etc/moto-tunnel/known_hosts')
assert 'SessionType none' in config and 'RemoteForward' in config
write('/etc/moto-tunnel/ssh_config', config, 0o600)
run('chroot', ROOT, 'chown', '-R', 'moto-tunnel:moto-tunnel', '/etc/moto-tunnel')
write('/etc/systemd/system/xray.service', '''[Unit]
Description=Xray client proxy
After=network.target
[Service]
User=xray
Group=xray
ExecStart=/usr/local/bin/xray run -config /etc/xray/config.json
Restart=always
RestartSec=5
NoNewPrivileges=yes
CapabilityBoundingSet=
[Install]
WantedBy=multi-user.target
''')
write('/etc/systemd/system/moto-tunnel.service', '''[Unit]
Description=Phone reverse SSH tunnel
After=network.target ssh.service xray.service
Wants=xray.service
[Service]
User=moto-tunnel
Group=moto-tunnel
Environment=AUTOSSH_GATETIME=0 AUTOSSH_POLL=30
ExecStart=/usr/bin/autossh -M 0 -NT -F /etc/moto-tunnel/ssh_config moto-vps
Restart=always
RestartSec=5
NoNewPrivileges=yes
[Install]
WantedBy=multi-user.target
''')
generator = ROOT / 'etc/systemd/system-generators/systemd-gpt-auto-generator'
generator.parent.mkdir(parents=True, exist_ok=True); generator.symlink_to('/dev/null')
run('systemctl', '--root=' + str(ROOT), 'enable', 'systemd-networkd', 'systemd-resolved', 'systemd-timesyncd',
    'ssh', 'vegas-modules', 'vegas-fuelgauged', 'vegas-chargeguard.timer', 'vegas-thermal', 'vegas-wifi',
    'xray', 'moto-tunnel')
run('systemctl', '--root=' + str(ROOT), 'mask', 'systemd-networkd-wait-online', 'systemd-pstore')
run('systemctl', '--root=' + str(ROOT), 'set-default', 'multi-user.target')
resolv = ROOT / 'etc/resolv.conf'
resolv.unlink(missing_ok=True); resolv.symlink_to('/run/systemd/resolve/stub-resolv.conf')
# Do not preserve a build-host machine identity.
write('/etc/machine-id', '')
(ROOT / 'var/lib/dbus/machine-id').unlink(missing_ok=True)
write('/etc/vegas/root-role', 'standalone\n')
write('/etc/vegas/native-setup-complete', 'native Debian 13; see private build manifest\n')
run('chroot', ROOT, 'visudo', '-cf', '/etc/sudoers')
print('Native Debian configuration complete; user account, Wi-Fi, power services, Xray and reverse tunnel installed.')
