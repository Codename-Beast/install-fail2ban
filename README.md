<p align="center">
  <img src="assets/elediav2.png" alt="eLeDia" width="720">
</p>

# 🛡️ install-fail2ban

Ansible-Rolle für Debian- und Ubuntu-Webserver mit Apache/Moodle. Sie installiert Fail2Ban, richtet die verwalteten Jails ein und prüft die Konfiguration, bevor der Dienst neu geladen oder gestartet wird.

Der Standardlauf nutzt die Inventory-Gruppe `fail2ban_targets`:

```bash
ansible-playbook -i inventory/hosts install_fail2ban.yml
```

---

## ✅ Kurzfassung

| Bereich | Stand |
|---|---|
| Zielsysteme | Debian/Ubuntu |
| Firewall | nftables, muss vorhanden sein |
| SSH | systemd-journal, Ports `22` und `3333` |
| Webserver | Apache-Logs unter `/var/log/apache2` |
| Prüfungen | Syntax, Template-Rendering, Regex-Fixtures, ansible-lint |

Die Rolle schreibt keine globale `[DEFAULT]`-Jail-Konfiguration. Alle verwalteten Jails bekommen ihre eigene `ignoreip`-Zeile, damit bestehende fremde Jails nicht ungewollt verändert werden.

---

## ⚙️ Was die Rolle macht

- prüft Betriebssystem, Ansible-Version, nftables und Apache-Logpfad
- installiert `fail2ban`, wenn das Paket fehlt
- überspringt `apt`, wenn alle benötigten Pakete bereits vorhanden sind
- legt optional ein einmaliges Backup von `/etc/fail2ban` an
- installiert Filter, Jails und Daemon-Konfiguration
- rendert Scanner- und User-Agent-Filter aus Variablen
- prüft mit `fail2ban-client -t`, bevor Fail2Ban neu geladen oder gestartet wird
- nutzt Handler für Validate, Reload und Restart
- prüft nach der Aktivierung Dienststatus und aktive Jails
- kann optional den offiziellen Fail2Ban Prometheus Exporter installieren

---

## 🔒 Aktive Jails

Standardmäßig aktiv:

- `sshd`
- `apache-malicious-paths`
- `moodle-badbots`
- `apache-scanner-useragents`
- `apache-unusual-useragents`
- `apache-scanburst`
- `apache-overflows`
- `apache-shellshock`
- `recidive`

Vorbereitet, aber nicht automatisch aktiv:

- `apache-auth`
- `apache-botsearch`

Hinweis: `apache-badbots` ist in dieser Rolle aktiv, sollte aber wie alle breiteren Bot-Filter gegen echte Logs geprüft werden.

---

## 🧱 Whitelist und nftables

Loopback ist immer freigestellt:

```yaml
fail2ban_base_ignoreip:
  - 127.0.0.1/8
  - "::1"
```

Die Rolle liest `nft -j list ruleset` und übernimmt nur Adress-Sets, die in direkten `accept`-Regeln als Quelladresse verwendet werden. Sets aus `drop`-/`reject`-Regeln und nicht referenzierte Sets werden nicht übernommen.

Für SSH gibt es eine zusätzliche Lockout-Sicherung. Wenn `sshd` aktiv ist, muss eine Admin-, VPN- oder Jump-Host-Adresse über nftables oder `fail2ban_trusted_ips` ermittelt werden. Reine Monitoring-Adressen reichen dafür nicht.

Zusätzliche Adressen:

```yaml
fail2ban_trusted_ips:
  - 203.0.113.55

fail2ban_allowed_ips:
  - 198.51.100.0/24
```

---

## 🕵️ User-Agent-Schutz

`apache-scanner-useragents` erkennt klar benannte Scanner. Die Liste kann pro Umgebung ergänzt werden:

```yaml
fail2ban_scanner_useragents_extra:
  - CompanySecurityScanner
```

Autorisierte Scanner können ausgenommen werden:

```yaml
fail2ban_scanner_useragents_ignore:
  - CompanySecurityScanner
```

`apache-unusual-useragents` bannt sofort bei:

- fehlendem User-Agent `"-"`
- leerem oder nur aus Leerzeichen bestehendem User-Agent
- User-Agent ab `fail2ban_unusual_useragents_max_length`, standardmäßig `256`
- Scanner-User-Agents aus den konfigurierten Listen

Generische Clients wie `curl`, `wget`, `python-requests` und `Go-http-client` sind nicht pauschal enthalten. Die können in Monitoring, APIs oder Cronjobs legitim sein.

---

## 🧰 Filter erweitern

Neue Scanner-User-Agents gehören nicht direkt ins Regex. Nutze dafür Variablen:

```yaml
fail2ban_scanner_useragents_extra:
  - MyBadScanner
```

Autorisierte Scanner kommen in die Ignore-Liste:

```yaml
fail2ban_scanner_useragents_ignore:
  - CompanySecurityScanner
```

Neue verdächtige Pfade ergänzt du im Filter:

```text
roles/install-fail2ban/files/apache-malicious-paths.conf
```

Beispiel: `/.env` und `/public_html/.env` sind bereits abgedeckt, weil der Filter nach `/.env` an jeder Stelle im Request-Pfad sucht. Für einen neuen Pfad ergänzt du die passende Gruppe, zum Beispiel:

```regex
|backup\.zip|database\.sql
```

Danach immer gegen Attack- und Clean-Logs testen:

```bash
fail2ban-regex tests/fixtures/apache-malicious-attack.log roles/install-fail2ban/files/apache-malicious-paths.conf
fail2ban-regex tests/fixtures/apache-clean.log roles/install-fail2ban/files/apache-malicious-paths.conf
```

Faustregel: Nur Dinge aufnehmen, die normale Moodle-Nutzer nie abrufen sollten. Sonst lieber erst Logs sammeln.

---

## 🧩 Wichtige Variablen

```yaml
fail2ban_sshd_enabled: true
fail2ban_sshd_port: "22,3333"
fail2ban_sshd_backend: systemd
fail2ban_sshd_maxretry: 5
fail2ban_sshd_findtime: 10m
fail2ban_sshd_bantime: 1h

fail2ban_scanburst_maxretry: 80
fail2ban_scanburst_findtime: 5m
fail2ban_scanburst_bantime: 12h

fail2ban_recidive_maxretry: 3
fail2ban_recidive_findtime: 7d
fail2ban_recidive_bantime: -1
```

Reine Statusabfrage ohne Installation und ohne Dateischreibungen:

```bash
ansible-playbook -i inventory/hosts install_fail2ban.yml -e report_only=true
```

---

## 🧪 Lokale Prüfung

Syntax-Check:

```bash
ANSIBLE_ROLES_PATH=/home/bernd/Downloads/install_fail2ban/roles \
  ansible-playbook -i tests/inventory.ini install_fail2ban.yml --syntax-check
```

Templates rendern:

```bash
ANSIBLE_ROLES_PATH=/home/bernd/Downloads/install_fail2ban/roles \
  ansible-playbook -i tests/inventory.ini tests/render_filters.yml
```

Lint:

```bash
ansible-lint .
```

Regex-Beispiele:

```bash
fail2ban-regex tests/fixtures/apache-malicious-attack.log roles/install-fail2ban/files/apache-malicious-paths.conf
fail2ban-regex tests/fixtures/apache-moodle-badbots-attack.log roles/install-fail2ban/files/moodle-badbots.conf
fail2ban-regex tests/fixtures/apache-scanburst-attack.log roles/install-fail2ban/files/apache-scanburst.conf
fail2ban-regex tests/fixtures/apache-scanner-attack.log /tmp/install-fail2ban-rendered-filters/apache-scanner-useragents.conf
fail2ban-regex tests/fixtures/apache-unusual-useragents-attack.log /tmp/install-fail2ban-rendered-filters/apache-unusual-useragents.conf
```

Die Fixture-Logs prüfen Angriffe und saubere Zugriffe für Moodle, API, Monitoring, Browser und autorisierte Scanner-Ausnahmen. Gerenderte Testdateien landen unter `/tmp`, nicht im Repository.

`--check` ist für diese Rolle nicht geeignet, weil nftables- und Fail2Ban-Laufzeitprüfungen einen vorbereiteten Zielhost brauchen.

---

## 📈 Fail2Ban Prometheus Exporter

Optional:

```yaml
fail2ban_exporter_enabled: true
fail2ban_exporter_listen_address: "127.0.0.1:9191"
fail2ban_exporter_health_url: "http://127.0.0.1:9191/metrics"
```

Der Exporter läuft nach `fail2ban.service`, liest `/var/run/fail2ban/fail2ban.sock` und bindet standardmäßig nur auf localhost.

---

## 🧯 Rollback

Die Rolle kann vor ihren Änderungen ein einmaliges Backup anlegen:

```yaml
fail2ban_backup_existing_config: true
fail2ban_backup_dir: /root/fail2ban-backup
fail2ban_backup_marker: /root/fail2ban-backup/.fail2ban_initial_backup_done
```

Manuell zurückrollen:

```bash
sudo rm -f \
  /etc/fail2ban/fail2ban.d/99-web-protection.local \
  /etc/fail2ban/filter.d/apache-malicious-paths.conf \
  /etc/fail2ban/filter.d/apache-scanner-useragents.conf \
  /etc/fail2ban/filter.d/apache-unusual-useragents.conf \
  /etc/fail2ban/filter.d/apache-scanburst.conf \
  /etc/fail2ban/jail.d/99-apache-moodle-bots.local \
  /etc/systemd/system/fail2ban-exporter.service \
  /usr/local/bin/fail2ban_exporter

sudo tar --extract --gzip --file=/root/fail2ban-backup/fail2ban-YYYYMMDD-HHMMSS.tar.gz --directory=/
sudo fail2ban-client -t
sudo systemctl restart fail2ban
```

---

## 📚 Weitere Dokumente

- `MANUELL.md`: händische Absicherung eines Servers
- `CHANGELOG.md`: Änderungen und Versionen

## 🧾 Unterstützte Ansible-Versionen

- ansible-core 2.12.10
- ansible-core 2.21.2
