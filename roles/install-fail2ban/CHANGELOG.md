# CHANGELOG

Alle relevanten Änderungen an dieser Rolle werden hier dokumentiert.

---

## [Unreleased]

### Fixed

- Die Rolle legt `/var/log/fail2ban.log` vor dem Konfigurationstest an, wenn `recidive` aktiv ist. Dadurch endet eine frische Installation nicht mehr mit Exit-Code 255, nur weil Fail2Ban seine eigene Logdatei noch nicht erzeugen konnte. Eine vorhandene Logdatei wird nicht überschrieben.
- Eine fehlende `/etc/fail2ban/jail.conf` wird aus der installierten Fail2Ban-Paketversion wiederhergestellt. Die Rolle pflegt weiterhin nur ihre eigene Datei unter `jail.d`.
- Die Wiederherstellung der `jail.conf` unterdrückt Paket-Serviceaktionen über eine temporäre `policy-rc.d`. Eine vorhandene Policy wird anschließend unverändert wiederhergestellt.

### Changed

- README-Überschriften und Jail-Kommentare gestrafft. Die technischen Hinweise bleiben erhalten, ohne jede Sektion dekorativ aufzublähen.
- Der IPv6-Modus ist explizit auf `auto` gesetzt; damit entfällt die gleichnamige Fail2Ban-Standardwert-Warnung.

---

## [2.0.0] - 2026-08-11

### Migration

- Der nftables-Whitelist-Import verwendet standardmäßig explizite Set-Kommentare statt beliebiger direkter `accept`-Regeln. Vertrauenswürdige Sets können mit `fail2ban-ignore` beziehungsweise `fail2ban-admin` markiert oder im Modus `explicit` über genaue `family/table/set`-Identitäten angegeben werden; Firewallregeln werden nicht mehr als Vertrauen interpretiert.
- Solange die echten Ausnahmen noch nicht feststehen, deaktiviert `fail2ban_whitelist_safety_checks_enabled: false` die neuen Marker-, Set-, IP/CIDR- und SSH-Admin-Preflight-Prüfungen. Der Schalter erzeugt keine Ausnahme und muss nach der Migration wieder aktiviert werden.
- `ansible.utils.ipaddr` sowie `netaddr` werden nur für die aktivierten semantischen Whitelist-Prüfungen benötigt.

### Added

- Sichere, comment-basierte Trennung zwischen allgemeinen Monitoring-Ausnahmen und SSH-Admin-Quellen.
- Reine Ansible-Vertragstests für nftables-Set-Auswahl sowie gültige und ungültige IPv4-/IPv6-Werte.
- Reine Ansible-Regex-Matrix mit 19 exakten Attack-, Clean- und Ignore-Prüfungen.
- GitHub-Actions-Workflow für ansible-core 2.12.10, ansible-core 2.21.2 und das Production-Profil von `ansible-lint`.
- MIT-Lizenzdatei und neutrale Beispielinventare.

### Fixed

- Bei aktivierten Whitelist-Sicherheitschecks werden ungültige IPv4-Oktette, IPv4-Präfixe über `/32`, IPv6-Präfixe über `/128` und fehlerhafte IPv6-Syntax bereits im Preflight abgelehnt.
- README-Aufruf mit fehlendem `-e`, fehlerhafte Tabelle, falscher Filterpfad und beschädigter Markdown-Codeblock korrigiert.
- Lokale VM-Adressen und SSH-Pfade werden nicht mehr im Repository versioniert.
- Inkonsistente Versionsangaben und veraltete Dokumentation bereinigt.

### Changed

- CI-Testlogik aus Python-Helfern in ausführbare Ansible-Playbooks überführt; das Repository enthält keine Python- oder Shell-Testskripte.
- GitLab-CI dedupliziert und an dieselben zentralen Ansible-Testplaybooks wie GitHub Actions angebunden.
- README um Schnellstart, Abhängigkeiten, Whitelist-Migration, lokale Prüfungen, Inventarbeispiele und Lizenzangaben ergänzt.

### Testing

- Syntaxchecks mit ansible-core 2.12.10 und 2.21.2.
- `ansible-lint` mit Production-Profil.
- Exakte Fail2Ban-Regex-Matrix und Security-Contract-Tests in beiden unterstützten Ansible-Versionen.

---

## [1.4.0]

### Added

- Handler-Datei `install-fail2ban/handlers/main.yml` ergänzt.
- Funktionales Jail `apache-unusual-useragents` für fehlende, leere, überlange und explizite Scanner-User-Agents ergänzt.
- `moodle-badbots` als eigenes Moodle-Jail ergänzt.
- Funktionale Jails `moodle-webservice-abuse` und `moodle-password-reset-abuse` ergänzt, um Webservice-Volumen und Passwort-Reset-Enumeration threshold-basiert zu erkennen.
- Default-off Jail `apache-infra-admin-exposure` ergänzt, um versehentlich öffentlich erreichbare Solr-Admin- und HAProxy-Stats-Pfade high-confidence zu erkennen.
- `apache-infra-admin-exposure` unterstützt eine jail-spezifische `ignoreip` für eng definierte Monitoring-/Admin-Quellen.
- Default-off Built-in Jail `apache-fakegooglebot` ergänzt; Aktivierung prüft den vorhandenen Fail2Ban-Filter und dokumentiert die DNS-Lookup-Abweichung.
- Funktionales Jail `moodle-behat-access` ergänzt: überwacht Behat-bezogene Moodle-Pfade bei HTTP 200 und 404.
- Optionales Jail `apache-slow-scan` ergänzt, um geduldige 4xx-Scans über längere Zeiträume zu erfassen; standardmäßig deaktiviert wegen False-Positive-Risiko bei NAT-/Campus-Netzen.
- Ausführlicher Kommentar-Header (Regex-Breakdown) in allen Filter-Dateien (`apache-malicious-paths.conf`, `apache-scanburst.conf`, `moodle-badbots.conf`, `moodle-behat-access.conf`, `moodle-webservice-abuse.conf`, `moodle-password-reset-abuse.conf`, `apache-infra-admin-exposure.conf`, `apache-scanner-useragents.conf.j2`, `apache-unusual-useragents.conf.j2`) ergänzt, um Aufbau und Zweck jeder Regex-Zeile nachvollziehbar zu dokumentieren.
- `Config | flush pending Fail2Ban handlers` (`meta: flush_handlers`) nach dem letzten Config-Render-Task ergänzt, um sicherzustellen, dass Validierung und Reload/Restart innerhalb desselben Rollenlaufs erfolgen, bevor nachfolgende Tasks oder Rollen greifen.
- Hinweis-Kommentar in `moodle-badbots.conf` zu `login/token.php` ergänzt: Dokumentiert das Risiko von Sammel-Bans bei geteilten IPs (Schul-/Campus-NAT, CGNAT) durch die Moodle Mobile App sowie mögliche Gegenmaßnahmen (Jail-Tuning, `ignoreip`, Moodle-eigener Konto-Lockout).

### Changed

- Paketinstallation prüft installierte Pakete vorab und überspringt `apt`, wenn `fail2ban` bereits installiert ist.
- Scanner-Templates filtern leere Werte, deduplizieren Listen und bleiben auch bei leeren Scanner-Listen valide.
- Regex-Filter für Web-Pfade, Moodle-Login/Token-Endpunkte und Scanbursts geprüft und präzisiert.
- Anker aller Custom-Filter (`apache-malicious-paths`, `apache-scanburst`, `moodle-badbots`, `apache-scanner-useragents`, `apache-unusual-useragents`) von einer generischen `.*"`-Suche auf eine feldgenaue Verankerung direkt hinter dem Zeitstempel (`\[[^\]]*\]\s+"`) umgestellt. Verhindert, dass ein präparierter User-Agent- oder Referer-Wert mit eingebettetem, gefälschtem Request-String (`"GET ... HTTP/1.1"`) den eigentlichen Match verfälscht oder Fehlzählungen in den verhaltensbasierten Jails (`moodle-badbots`, `apache-scanburst`) verursacht.
- Feld für die Antwortgröße (`size`) in `apache-scanner-useragents` und `apache-unusual-useragents` von optional auf verpflichtend geändert.
- Scanner-Namen-Erkennung (`sqlmap`, `nikto`, etc.) aus `apache-unusual-useragents` entfernt, da sie sich mit `apache-scanner-useragents` überschnitt und pro Vorfall zwei unabhängige Ban-Events statt eines erzeugte. `apache-unusual-useragents` ist jetzt ausschließlich für fehlende/leere und überlange User-Agents zuständig; die Zählung gegenüber `recidive` ist damit wieder eindeutig einem Ereignis pro Vorfall zugeordnet.
- README erklärt kurz, wie Scanner-User-Agents und verdächtige Pfade erweitert werden.
- Template-Rendering prüft jetzt auch leere Scanner-Listen, das Jail-Template und die Exporter-Unit.
- Fail2Ban-Regex-Checks prüfen jetzt konkrete Trefferzahlen für Attack-, Clean- und Ignore-Fixtures, damit ein 0-Treffer-Filter die CI nicht mehr grün passieren kann.
- CI deckt jetzt auch Moodle-Webservice-, Passwort-Reset- und Infra-Admin-Exposure-Filter mit Attack- und Clean-Fixtures ab.
- Behat-Zugriffe mit HTTP 200 werden als öffentliche Exposition gewertet und mit `maxretry: 1` sofort über die konfigurierte nftables-Aktion gedroppt; HTTP 404 bleibt als Probe-Erkennung enthalten.
- `moodle-behat-access` eskaliert Wiederholungstäter jetzt progressiv, damit Scanner nach der ersten temporären Sperre nicht stündlich weitermachen können.
- README dokumentiert die Low-and-Slow-Grenze kurzer Schwellwert-Jails und die optionale Gegenmaßnahme `apache-slow-scan`.
- DateDetector-Root-Cause direkt in den Filter-Kommentaren dokumentiert: Fail2Ban entfernt den Timestamp vor `failregex`, daher muss das Timestamp-Feld `[^\]]*` statt `[^\]]+` erlauben.
- Adminer-Erkennung in `apache-malicious-paths` auf sinnvolle Boundary-Fälle begrenzt, inklusive `adminer_*.php`, ohne breite Teilstring-Treffer.
- Preflight-Erkennung der Apache-Log-Anforderung um alle neueren Apache-/Moodle-Jails ergänzt.
- ConfigParser-Interpolationsfalle in `apache-infra-admin-exposure` behoben: literal kodierte Solr-UI-Pfade mit Prozentzeichen werden Fail2Ban-konform escaped.
- Jail-spezifische `ignoreip`-Variablen für Behat-, Webservice- und Infra-Admin-Ausnahmen ergänzt, damit Ausnahmen nicht global auf alle Jails wirken.
- Wiederholbare QA-Skripte für ungenutzte Defaults, ungesicherte Jinja-Referenzen und Prozentzeichen-Interpolation unter `tests/scripts/` ergänzt.
- `MANUELL.md` als bewusst schlanken Basis-/Notfall-Auszug gekennzeichnet; die vollständige Jail-Matrix bleibt im README, um parallele Wahrheiten zu vermeiden.
- Repository der eLeDia-Konvention und für Infra angepasst.

### Testing

- Rolle gegen Debian 13 Server getestet.
- Idempotent sichergestellt.
- ansible-core 2.12.10 Support.
- ansible-core 2.21.2 Support.
---

## [1.2.0]

### Changed

- Lint-Policy an die eLeDia-Konvention mit kurzen Modulnamen angepasst.

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
