# install_fail2ban

Ansible-Rolle für Debian/Ubuntu-Webserver: installiert Fail2Ban, spielt eine Apache/Moodle-Bot-Schutzkonfiguration ein, prüft die Konfiguration kurz und schaltet Fail2Ban aktiv.

Wichtig:

- `nftables` muss auf dem Zielserver bereits vorhanden sein.
- Wenn `nft` fehlt, bricht die Rolle vor Änderungen ab.
- Die Rolle installiert bewusst nur `fail2ban`, nicht `nftables`.
- Standard-Logpfade sind Apache-Datei-Logs unter `/var/log/apache2/`.
- Die Rolle verändert keine Apache-, PHP-, Moodle-, Reverse-Proxy- oder CDN-Konfiguration.

## Getestete Ansible-Versionen

Lokale Syntax-Checks wurden mit diesen Versionen ausgeführt:

- ansible-base / Ansible 2.10.12
- ansible-core 2.12.10
- ansible-core 2.21.2

Stand laut `pip index`: `ansible-core` aktuell 2.21.2, das Meta-Paket `ansible` aktuell 14.2.0. Eine 2.22-Version war nicht als aktuelles Release sichtbar.

## Struktur

```text
install_fail2ban/
├── ansible.cfg
├── inventories/example/hosts.ini
├── playbooks/install_fail2ban.yml
├── roles/install_fail2ban/
│   ├── defaults/main.yml
│   ├── files/
│   ├── handlers/main.yml
│   ├── meta/main.yml
│   ├── tasks/main.yml
│   └── templates/99-apache-moodle-bots.local.j2
└── tests/
    ├── inventory.ini
    └── syntax.yml
```

## Schnellstart

Inventory anpassen:

```ini
[fail2ban_targets]
server1 ansible_host=192.0.2.10 ansible_user=root
```

Syntax prüfen:

```bash
ansible-playbook -i inventories/example/hosts.ini playbooks/install_fail2ban.yml --syntax-check
```

Dry-run, soweit von Modulen unterstützt:

```bash
ansible-playbook -i inventories/example/hosts.ini playbooks/install_fail2ban.yml --check --diff
```

Produktiv ausführen:

```bash
ansible-playbook -i inventories/example/hosts.ini playbooks/install_fail2ban.yml
```

## Wichtige Variablen

```yaml
install_fail2ban_ignoreip:
  - 127.0.0.1/8
  - "::1"

install_fail2ban_access_log: /var/log/apache2/*access.log
install_fail2ban_error_log: /var/log/apache2/*error.log

install_fail2ban_run_nft_test_ban: true
install_fail2ban_test_ban_ip: 192.0.2.123
```

Management-/Monitoring-IP ergänzen:

```yaml
install_fail2ban_ignoreip:
  - 127.0.0.1/8
  - "::1"
  - 203.0.113.55
```

## Was installiert und aktiviert wird

Aktive Jails:

- `apache-malicious-paths`
- `apache-scanner-useragents`
- `apache-scanburst`
- `apache-overflows`
- `apache-shellshock`
- `recidive`

Alle Jails nutzen nftables-Actions. `recidive` sperrt Wiederholungstäter dauerhaft auf allen Ports.

## Abbruchbedingungen

Die Rolle bricht ab, wenn:

- das Zielsystem nicht Debian/Ubuntu ist
- `nft` nicht im PATH vorhanden ist
- `/var/log/apache2` fehlt, solange `install_fail2ban_require_apache_log_dir: true` gesetzt ist
- `fail2ban-client -t` nach dem Rendern fehlschlägt
- der Dienst nach Aktivierung nicht aktiv ist

## Rollback

Die Rolle erstellt vor Änderungen an `/etc/fail2ban` optional ein Backup:

```yaml
install_fail2ban_backup_existing_config: true
install_fail2ban_backup_dir: /root/fail2ban-backup
```

Manuell zurückrollen:

```bash
sudo rm -f \
  /etc/fail2ban/fail2ban.d/99-web-protection.local \
  /etc/fail2ban/filter.d/apache-malicious-paths.conf \
  /etc/fail2ban/filter.d/apache-scanner-useragents.conf \
  /etc/fail2ban/filter.d/apache-scanburst.conf \
  /etc/fail2ban/jail.d/99-apache-moodle-bots.local

sudo tar --extract --gzip --file=/root/fail2ban-backup/fail2ban-YYYYMMDD-HHMMSS.tar.gz --directory=/
sudo fail2ban-client -t
sudo systemctl restart fail2ban
```
