# CHANGELOG

Alle relevanten Änderungen an dieser Rolle werden hier dokumentiert.

Die Labels `Added`, `Changed` und `Fixed` bleiben bewusst Englisch.

---

## [1.1.0] - 2026-07-24

### Added

- `report_only` als kurze Variable für reine Statusabfragen ohne Installation und ohne Dateischreibungen.
- Formatierter Fail2Ban-Statusbericht mit Service-Status, aktiven Jails und Ban-Zählern pro Jail.
- `MANUELL.md` als Tutorial für die händische Absicherung eines Servers ohne Ansible.
- Hinweis in der README zur Ansible-2.21.2-Warnung bei `-e hosts=...`.

### Changed

- README-Beispiele zeigen den gewünschten Aufrufstil: erst `-e hosts=...`, am Ende `-i inventory`.
- Der korrekte, nicht reservierte Zielhost-Parameter ist zusätzlich dokumentiert: `install_fail2ban_hosts`.

---

## [1.0.0] - 2026-07-24

### Added

- Formatierter Statusbericht nach erfolgreicher Installation.
- Reiner Info-Modus am Anfang des Laufs.
- Inventory-Beispiel auf `inventory/hosts` vereinheitlicht.

### Changed

- Alte Report-Varianten entfernt und durch eine zentrale Report-Task-Datei ersetzt.
- Die Rolle bleibt ohne mitgelieferte `ansible.cfg` und ohne `.ansible-lint`.

---

## [0.9.0] - 2026-07-24

### Added

- Expliziter Fail2Ban-Konfigurationstest mit `fail2ban-client -t` vor Start oder Restart.
- Klare Fehlerausgabe mit Exit-Code, stdout und stderr, wenn die Konfiguration ungültig ist.

### Changed

- Start und Restart des Dienstes wurden vereinfacht.

---

## [0.8.0] - 2026-07-24

### Changed

- Inline-Python für den nftables-Whitelist-Import entfernt.
- nftables-Import läuft über `nft -j list ruleset` und Ansible-Filter.
- Kurzmodule bleiben erhalten, keine `ansible.builtin.*`-Schreibweise in der Rolle.

---

## [0.7.0] - 2026-07-24

### Added

- Offizieller Fail2Ban Prometheus Exporter als optionale Komponente.
- VPN-/Jump-Host-Whitelist über `install_fail2ban_trusted_ips`.

### Changed

- `admin_ips`-Benennung entfernt.
- SSH wird ausschließlich über systemd-journal ausgewertet.
