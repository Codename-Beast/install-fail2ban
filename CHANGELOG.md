# CHANGELOG

Alle relevanten Änderungen an dieser Rolle werden hier dokumentiert.

---

## [1.3.0]

### Added

- Handler-Datei `install-fail2ban/handlers/main.yml` ergänzt.
- Funktionales Jail `apache-unusual-useragents` für fehlende, leere, überlange und explizite Scanner-User-Agents ergänzt.
- `moodle-badbots` als eigenes Moodle-Jail ergänzt.
- Projektkonfiguration für `ansible-lint` ergänzt.

### Changed

- Paketinstallation prüft installierte Pakete vorab und überspringt `apt`, wenn `fail2ban` bereits installiert ist.
- Scanner-Templates filtern leere Werte, deduplizieren Listen und bleiben auch bei leeren Scanner-Listen valide.
- Regex-Filter für Web-Pfade, Moodle-Login/Token-Endpunkte und Scanbursts geprüft und präzisiert.
- README erklärt kurz, wie Scanner-User-Agents und verdächtige Pfade erweitert werden.
- Template-Rendering prüft jetzt auch leere Scanner-Listen, das Jail-Template und die Exporter-Unit.
- Repository bereinigt

### Testing
- Rolle gegen Debian 13 Server Getestet.
- idempotent Sichergestellt.
- ansible-core 2.12.10 Support 
- ansible-core 2.21.2 Support

---

## [1.2.0]

### Changed

- Lint-Policy an die eLeDia konvention mit kurzen Modulnamen angepasst.

---

## [1.1.0]

### Added

- `report_only` als kurze Variable für reine Statusabfragen ohne Installation.
- Formatierter Fail2Ban-Statusbericht mit Service-Status, aktiven Jails und Ban-Zählern pro Jail.
- `MANUELL.md` als Anleitung für die händische Absicherung eines Servers ohne Ansible.
---

## [1.0.0]

### Added

- Formatierter Statusbericht nach erfolgreicher Installation.
- Reiner Info-Modus.

---

## [0.9.0]

### Added

- Expliziter Fail2Ban-Konfigurationstest mit `fail2ban-client -t` vor Start oder Restart.
- Klare Fehlerausgabe mit Exit-Code, stdout und stderr, wenn die Konfiguration ungültig ist.

### Changed

- Start und Restart des Fail2Ban Service vereinfacht.

---

## [0.8.0]

### Changed
- nftables-Import läuft über `nft -j list ruleset` und Ansible-Filter.

---

## [0.7.0]

### Added

- Offizieller Fail2Ban Prometheus Exporter als optionale Komponente.
- VPN-/Jump-Host-Whitelist über `fail2ban_trusted_ips`.

### Changed

- SSH wird ausschließlich über systemd-journal ausgewertet.

---

## [0.6.0]

### Added

- Offizieller Fail2Ban Prometheus Exporter als optionale Komponente.

---

## [0.5.0]

### Added

- Optionale selbst geschriebene Metrik-Datei für Fail2Ban-Zähler.
- Lokale Render- und Shell-Prüfungen für die damalige Metrik-Ausgabe.

---

## [0.4.0]

### Added

- Zusätzliche Apache-/Moodle-Jails für Scanner, bösartige Pfade und wiederholte Treffer.
- Opt-in-Import von Whitelist-Adressen aus explizit benannten nftables-Sets.
- Erste Status-/Reporting-Ausgaben für konfigurierte Fail2Ban-Jails.

---

## [0.3.0]

### Added

- SSH-Jail mit systemd-journal als Backend.
- Aktivierungsfluss, der Fail2Ban erst nach erfolgreicher Konfiguration startet.

---

## [0.2.0]

### Added

- Erste Defaults für Jails, Whitelist und Apache-Logpfade.
- IP-Whitelist je verwaltetem Jail.

### Changed

- Fail2Ban-Jail-Defaults und Whitelist-Handling geschärft.

---

## [0.1.0]

### Added

- Initiale Ansible-Rolle `install-fail2ban`.
- Grundstruktur mit Rolle, Playbook, Defaults, Templates und Tests.
- Installation von Fail2Ban auf Debian.
