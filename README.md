# install_fail2ban

Ansible-Rolle für Debian/Ubuntu-Webserver: installiert Fail2Ban, schützt SSH und Apache/Moodle, prüft die Konfiguration und aktiviert den Dienst erst danach.

## Wichtig

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
│   └── templates/
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

## Konkrete Jail-Empfehlung

Standardmäßig aktiv:

- `sshd`: SSH-Bruteforce-Schutz, konservativ und progressiv
- `apache-malicious-paths`: eindeutige Exploit-/Fremdsystem-Pfade, sofort permanent
- `apache-scanner-useragents`: explizit benannte Scanner, sofort permanent
- `apache-scanburst`: viele 400/403/404/405/408/414 in kurzer Zeit, temporär und progressiv
- `apache-overflows`: eingebauter Apache-Overflow-Filter, permanent nach zwei Treffern
- `apache-shellshock`: eingebauter Shellshock-Filter, sofort permanent
- `recidive`: Wiederholungstäter, permanent auf allen Ports

Vorbereitet, aber default `false`:

- `apache-auth`: nur Apache Basic/Digest Auth, nicht Moodle-Formularlogin
- `apache-badbots`: breite User-Agent-Liste, erst gegen echte Logs prüfen
- `apache-botsearch`: kann sich mit eigenen Pfadfiltern überschneiden, erst gegen echte Logs prüfen

Bewusst nicht eingebaut:

- `apache-fakegooglebot`: DNS-abhängig und unnötig komplex
- `apache-noscript`: für PHP/Moodle schnell zu breit
- `apache-modsecurity*`: ModSecurity ist nicht Teil dieser Rolle

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

Keine großen privaten Netze wie `10.0.0.0/8` pauschal freistellen, wenn dort nicht wirklich alle Quellen vertrauenswürdig sind.

## Whitelist aus nftables importieren

Kurzfassung: Ja, technisch möglich — aber nur sicher, wenn die Sets eindeutig als Allow-/Monitoring-/Management-Sets benannt sind.

Die Rolle liest nicht blind alle IPs aus dem nftables-Ruleset aus. In nftables können erlaubte IPs, Blocklisten, Fail2Ban-Sets und Routing-/Policy-Sets gleichzeitig stehen. Ein pauschaler Import könnte versehentlich Angreifer whitelisten.

Deshalb ist der Import opt-in und auf Set-Namen beschränkt:

```yaml
install_fail2ban_nft_whitelist_import_enabled: true
install_fail2ban_nft_whitelist_set_names:
  - monitoring_ips
  - management_ips
  - mgmt_ips
  - admin_ips
  - trusted_ips
  - fail2ban_ignore
```

Die Rolle führt dann `nft -j list ruleset` aus, liest nur diese Sets aus und übernimmt gültige IP-/CIDR-Einträge in `ignoreip`.

Empfehlung: Wenn möglich ein eigenes nftables-Set für Fail2Ban-Ausnahmen pflegen, z.B. `fail2ban_ignore`.

## Scanner-User-Agent-Liste erweitern

Der eigene Filter `apache-scanner-useragents` ist jetzt templated und über Variablen steuerbar.

Basisliste:

```yaml
install_fail2ban_scanner_useragents:
  - sqlmap
  - nikto
  - nuclei
  - wpscan
  - gobuster
  - ffuf
```

Zusätzliche lokale Scanner ergänzen:

```yaml
install_fail2ban_scanner_useragents_extra:
  - eigener-scanner-name
  - CompanySecurityScanner
```

Bestimmte autorisierte User-Agents trotz Match ignorieren:

```yaml
install_fail2ban_scanner_useragents_ignore:
  - CompanySecurityScanner
```

Die Einträge werden als Literale behandelt und im Template regex-escaped. Generische Clients wie `curl`, `wget`, `python-requests` oder `Go-http-client` sind absichtlich nicht enthalten.

## Jail-Tuning

Wichtige Werte sind einzeln überschreibbar:

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

Wenn SSH nicht über systemd-journal, sondern über `/var/log/auth.log` ausgewertet werden soll:

```yaml
install_fail2ban_sshd_backend: auto
install_fail2ban_sshd_logpath: /var/log/auth.log
```

Optionales Apache-Auth-Jail aktivieren:

```yaml
install_fail2ban_apache_auth_enabled: true
install_fail2ban_apache_auth_maxretry: 5
install_fail2ban_apache_auth_findtime: 10m
install_fail2ban_apache_auth_bantime: 1d
```

## node_exporter Textfile-Metriken

Optional kann die Rolle Fail2Ban-Metriken für den node_exporter Textfile Collector bereitstellen.

Default ist aus:

```yaml
install_fail2ban_node_exporter_textfile_enabled: false
```

Aktivieren, wenn node_exporter bereits mit Textfile Collector läuft:

```yaml
install_fail2ban_node_exporter_textfile_enabled: true
install_fail2ban_node_exporter_textfile_dir: /var/lib/prometheus/node-exporter
```

Optional auch das Debian/Ubuntu-Paket installieren:

```yaml
install_fail2ban_node_exporter_install_package: true
install_fail2ban_node_exporter_package: prometheus-node-exporter
```

Die Rolle installiert dann:

```text
/usr/local/sbin/fail2ban-node-exporter-textfile.sh
/etc/cron.d/fail2ban-node-exporter-textfile
/var/lib/prometheus/node-exporter/fail2ban.prom
```

Erzeugte Metriken:

```text
fail2ban_up
fail2ban_jails
fail2ban_jail_currently_banned{jail="sshd"}
fail2ban_jail_total_banned{jail="sshd"}
```

Das Skript schreibt atomar über eine temporäre Datei. Wenn `fail2ban-client` nicht erreichbar ist, wird `fail2ban_up 0` geschrieben statt einen kaputten Cronjob zu erzeugen.

## Idempotenz und Aktivierungsreihenfolge

Die Rolle kann mehrfach laufen:

- Paketinstallation, Verzeichnisse, Dateien und Templates sind idempotent.
- Das initiale Backup wird nur einmal erstellt und über `install_fail2ban_backup_marker` markiert.
- Aktivierte eingebaute Filter werden vor dem Rendern geprüft.
- `fail2ban-client -t` läuft nach dem Rendern der verwalteten Dateien.
- Fail2Ban wird erst nach erfolgreicher Prüfung gestartet bzw. aktiviert.
- Ein Restart passiert nur, wenn verwaltete Konfigurationsdateien wirklich geändert wurden.
- Wenn die Prüfung fehlschlägt, wird nicht aktiviert/restarted.

## Aktive Konfiguration nur auslesen

Für eine reine Bestandsaufnahme ohne Installation und ohne Dateischreibungen:

```bash
ansible-playbook -i inventories/example/hosts.ini playbooks/install_fail2ban.yml \
  -e install_fail2ban_report_only=true
```

Dabei werden ausgeführt:

- `fail2ban-client status`
- `fail2ban-client -d`

Danach beendet die Rolle den Host per `meta: end_host`. Es wird nichts installiert und keine verwaltete Datei geschrieben.

Optional vor und/oder nach einem normalen Lauf reporten:

```yaml
install_fail2ban_report_before: true
install_fail2ban_report_after: true
```

## Abbruchbedingungen

Die Rolle bricht ab, wenn:

- das Zielsystem nicht Debian/Ubuntu ist
- die Ansible-Version kleiner als 2.10 ist
- `nft` nicht an einem üblichen Systempfad vorhanden ist
- `/var/log/apache2` fehlt, solange `install_fail2ban_require_apache_log_dir: true` gesetzt ist
- Whitelist-Einträge nicht wie IPs oder CIDRs aussehen
- ein aktivierter eingebauter Fail2Ban-Filter auf dem Zielsystem fehlt
- `fail2ban-client -t` nach dem Rendern fehlschlägt
- der Dienst nach Aktivierung nicht aktiv ist

## Rollback

Die Rolle erstellt vor Änderungen an `/etc/fail2ban` optional ein initiales Backup:

```yaml
install_fail2ban_backup_existing_config: true
install_fail2ban_backup_dir: /root/fail2ban-backup
install_fail2ban_backup_marker: /root/fail2ban-backup/.install_fail2ban_initial_backup_done
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
