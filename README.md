# install_fail2ban

Ansible-Rolle für Debian/Ubuntu-Webserver: installiert Fail2Ban, spielt eine Apache/Moodle-Bot-Schutzkonfiguration ein, prüft die Konfiguration kurz und schaltet Fail2Ban aktiv.

Wichtig:

- `nftables` muss auf dem Zielserver bereits vorhanden sein.
- Wenn `nft` fehlt, bricht die Rolle vor Änderungen ab.
- Die Rolle installiert bewusst nur `fail2ban`, nicht `nftables`.
- Standard-Logpfade sind Apache-Datei-Logs unter `/var/log/apache2/`.
- Die Rolle verändert keine Apache-, PHP-, Moodle-, Reverse-Proxy- oder CDN-Konfiguration.
- Whitelisting läuft über `ignoreip` pro verwaltetem Jail, nicht über einen globalen `[DEFAULT]`-Block.
- Die Rolle ist idempotent ausgelegt: erneute Läufe schreiben nur bei Abweichungen und restarten nur nach erfolgreicher Prüfung.

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
install_fail2ban_access_log: /var/log/apache2/*access.log
install_fail2ban_error_log: /var/log/apache2/*error.log

install_fail2ban_sshd_enabled: true
install_fail2ban_sshd_backend: systemd

install_fail2ban_run_nft_test_ban: true
install_fail2ban_test_ban_ip: 192.0.2.123
```

## IP-Whitelisting

Loopback ist immer freigestellt:

```yaml
install_fail2ban_base_ignoreip:
  - 127.0.0.1/8
  - "::1"
```

Eigene erlaubte IPs und Netze kommen in `install_fail2ban_allowed_ips`:

```yaml
install_fail2ban_ip_whitelist_enabled: true
install_fail2ban_allowed_ips:
  - 203.0.113.55        # Management-IP
  - 198.51.100.0/24     # Monitoring/VPN-Netz
```

Die Rolle rendert daraus je Jail:

```ini
ignoreip = 127.0.0.1/8 ::1 203.0.113.55 198.51.100.0/24
```

Hinweis: Keine großen privaten Netze wie `10.0.0.0/8` pauschal freistellen, wenn dort nicht wirklich alle Quellen vertrauenswürdig sind.

## Jails

Aktivierte Standard-Jails:

- `sshd`: SSH-Bruteforce-Schutz, konservativ und progressiv
- `apache-malicious-paths`: eindeutige Exploit-/Fremdsystem-Pfade, sofort permanent
- `apache-scanner-useragents`: explizit benannte Scanner, sofort permanent
- `apache-scanburst`: viele 400/403/404/405/408/414 in kurzer Zeit, temporär und progressiv
- `apache-overflows`: mitgelieferter Apache-Overflow-Filter, permanent nach zwei Treffern
- `apache-shellshock`: mitgelieferter Shellshock-Filter, sofort permanent
- `recidive`: Wiederholungstäter, permanent auf allen Ports

Optional vorhanden, aber absichtlich deaktiviert:

- `apache-auth`: nur Apache Basic/Digest Auth, nicht Moodle-Formularlogin
- `apache-badbots`: breite User-Agent-Liste, erst gegen reale Logs prüfen
- `apache-botsearch`: kann sich mit eigenen Pfadfiltern überschneiden, erst gegen reale Logs prüfen

Alle Jails nutzen nftables-Actions. `recidive` sperrt Wiederholungstäter dauerhaft auf allen Ports.

## Jail-Tuning

Die wichtigsten Werte sind einzeln überschreibbar:

```yaml
install_fail2ban_sshd_enabled: true
install_fail2ban_sshd_port: ssh
install_fail2ban_sshd_backend: systemd
install_fail2ban_sshd_logpath: ""
install_fail2ban_sshd_maxretry: 5
install_fail2ban_sshd_findtime: 10m
install_fail2ban_sshd_bantime: 1h
install_fail2ban_sshd_bantime_increment: true

install_fail2ban_malicious_paths_maxretry: 1
install_fail2ban_malicious_paths_findtime: 1d
install_fail2ban_malicious_paths_bantime: -1

install_fail2ban_scanburst_maxretry: 80
install_fail2ban_scanburst_findtime: 5m
install_fail2ban_scanburst_bantime: 12h
install_fail2ban_scanburst_maxtime: 90d
install_fail2ban_scanburst_multipliers: "1 2 6 14 60 180"

install_fail2ban_recidive_maxretry: 3
install_fail2ban_recidive_findtime: 7d
install_fail2ban_recidive_bantime: -1
```

Optionales Jail aktivieren:

```yaml
install_fail2ban_apache_auth_enabled: true
install_fail2ban_apache_auth_maxretry: 5
install_fail2ban_apache_auth_findtime: 10m
install_fail2ban_apache_auth_bantime: 1d
```

Wenn ein Zielserver SSH nicht über systemd-journal, sondern nur über `/var/log/auth.log` auswerten soll:

```yaml
install_fail2ban_sshd_backend: auto
install_fail2ban_sshd_logpath: /var/log/auth.log
```

## Idempotenz und Aktivierungsreihenfolge

Die Rolle kann mehrfach laufen:

- Paketinstallation, Verzeichnisse, Dateien und Templates sind idempotent.
- Das initiale Backup wird nur einmal erstellt und über `install_fail2ban_backup_marker` markiert.
- `fail2ban-client -t` läuft nach dem Rendern der verwalteten Dateien.
- Fail2Ban wird erst nach erfolgreicher Prüfung gestartet bzw. aktiviert.
- Ein Restart passiert nur, wenn verwaltete Konfigurationsdateien wirklich geändert wurden.
- Wenn die Prüfung fehlschlägt, wird nicht aktiviert/restarted.

## Abbruchbedingungen

Die Rolle bricht ab, wenn:

- das Zielsystem nicht Debian/Ubuntu ist
- die Ansible-Version kleiner als 2.10 ist
- `nft` nicht an einem üblichen Systempfad vorhanden ist
- `/var/log/apache2` fehlt, solange `install_fail2ban_require_apache_log_dir: true` gesetzt ist
- Whitelist-Einträge nicht wie IPs oder CIDRs aussehen
- `fail2ban-client -t` nach dem Rendern fehlschlägt
- der Dienst nach Aktivierung nicht aktiv ist

## Rollback

Die Rolle erstellt vor Änderungen an `/etc/fail2ban` optional ein Backup:

```yaml
install_fail2ban_backup_existing_config: true
install_fail2ban_backup_dir: /root/fail2ban-backup
install_fail2ban_backup_marker: /root/fail2ban-backup/.install_fail2ban_initial_backup_done
```

Das Backup ist bewusst ein initiales Sicherheitsbackup. Es wird bei weiteren idempotenten Läufen nicht jedes Mal neu erzeugt.

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
