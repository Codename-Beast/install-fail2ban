<p align="center">
  <img src="assets/elediav2.png" alt="eLeDia" width="720">
</p>

# install-fail2ban

Ansible-Rolle für eLeDia Webserver mit Apache/Moodle. Sie installiert Fail2Ban, richtet die verwalteten Jails ein und prüft die Konfiguration, bevor der Service neu geladen oder gestartet wird.

Status prüfen, ohne etwas zu ändern (`run_role` ist der produktive Wrapper; das Repo-Playbook ist nur ein CI-/Test-Harness):
```bash
run_role install-fail2ban -e 'hosts=hustensaft' -e 'report_only=true'
```
Rolle ausführen:

```bash
run_role install-fail2ban -e 'hosts=hc-hustensaft'
```

Abhängigkeiten für lokale Tests:

```bash
ansible-galaxy collection install -r collections/requirements.yml
python3 -m pip install -r requirements-test.txt
```

---

## Kurzüberblick

| Punkt | Wert |
|---|---|
| Zielsystem | Debian / Ubuntu |
| Firewall | nftables muss vorhanden sein |
| SSH | systemd-journal, Ports `22` und `3333` |
| Apache-Logs | unter `/var/log/apache2` |

Die Rolle schreibt keine globale `[DEFAULT]`-Jail-Konfiguration. Alle verwalteten Jails bekommen ihre eigene `ignoreip`, damit bestehende fremde Jails nicht ungewollt verändert werden.

---

## Was die Rolle macht

- installiert nur die Pakete, die noch fehlen
- lässt die paketverwaltete `/etc/fail2ban/jail.conf` unverändert und stellt sie per Paket-Reinstallation wieder her, falls sie fehlt; Paket-Skripte dürfen Fail2Ban dabei nicht vor der Konfigurationsprüfung neu starten
- legt optional ein einmaliges Backup von `/etc/fail2ban` an
- schreibt eigene Jails nach `/etc/fail2ban/jail.d/99-apache-moodle-bots.local` sowie Filter und Daemon-Konfiguration
- rendert Scanner- und User-Agent-Filter aus Variablen
- prüft mit `fail2ban-client -t`, bevor Fail2Ban neu geladen oder gestartet wird
- prüft nach der Aktivierung den Fail2Ban Service und aktive Jails
- kann optional den offiziellen Fail2Ban Prometheus Exporter installieren

---

## Aktive Jails

Standardmäßig aktiv:

- `sshd`
- `apache-malicious-paths`
- `moodle-badbots`
- `moodle-webservice-abuse`
- `moodle-pwreset-abuse`
- `moodle-form-abuse`
- `moodle-behat-access`
- `apache-scanner-useragents`
- `apache-unusual-useragents`
- `apache-scanburst`
- `apache-overflows`
- `apache-shellshock`
- `apache-badbots`
- `recidive`

Default-off, bewusst nur nach Topologie-/Logprüfung aktivieren:

- `apache-infra-admin-exposure`
- `apache-fakegooglebot`
- `apache-slow-scan`
- `apache-auth`
- `apache-botsearch`

Hinweis: `apache-badbots` ist in dieser Rolle aktiv, sollte aber wie alle breiteren Bot-Filter gegen echte Logs geprüft werden.

---

## Whitelist und nftables

Loopback ist immer freigestellt:

```yaml
fail2ban_base_ignoreip:
  - 127.0.0.1/8
  - "::1"
```

Die Rolle liest keine nftables-Sets mehr als Whitelist ein. Das war in gemischten Firewall-Setups zu fragil: ein falsch markiertes oder wiederverwendetes Set kann sonst unbeabsichtigt globale Fail2Ban-Ausnahmen erzeugen.

Zusätzliche Ausnahmen werden nur noch explizit per Inventory gesetzt:

```yaml
fail2ban_admin_ips:
  - 203.0.113.55

fail2ban_trusted_ips:
  - 203.0.113.56

fail2ban_allowed_ips:
  - 198.51.100.0/24
```

`fail2ban_admin_ips` ist für Admin-, VPN- oder Jump-Host-Adressen gedacht. Die Werte landen in den verwalteten `ignoreip`-Zeilen. Optional kann die Rolle daraus eine eigene nftables-Fragmentdatei bauen. Das ist standardmäßig aus:

```yaml
fail2ban_nft_allow_sets_enabled: false
fail2ban_nft_allow_sets_file: /etc/nftables.d/90-fail2ban-allowsets.nft
fail2ban_nft_allow_sets_overwrite: false
fail2ban_nft_allow_sets_apply: false
```

Wenn `fail2ban_nft_allow_sets_enabled: true` gesetzt ist, rendert die Rolle nur Sets aus den expliziten Variablen `fail2ban_admin_ips`, `fail2ban_trusted_ips` und `fail2ban_allowed_ips`. Sie liest weiterhin keine vorhandenen nftables-Sets ein.

Schutz gegen versehentliches Überschreiben:

- Existiert `fail2ban_nft_allow_sets_file` bereits, bricht die Rolle ab.
- Überschreiben gibt es nur mit `fail2ban_nft_allow_sets_overwrite: true`.
- Vor dem Schreiben prüft `nft -c -f` die gerenderte Datei.
- Anwenden ist getrennt und bleibt aus, solange `fail2ban_nft_allow_sets_apply: false` gesetzt ist.

Jail-spezifische Ausnahmen bleiben für bekannte Monitoring-, Campus-, Helpdesk- oder Integrationsquellen der bessere Weg, wenn die IP nur bei einem bestimmten Signal ausgenommen werden soll.

---

## User-Agent-Schutz

`apache-scanner-useragents` erkennt klar benannte Scanner. Die Liste kann pro Umgebung ergänzt werden:

```yaml
fail2ban_scanner_useragents_extra:
  - eLeDiaSecurityScanner
```

Autorisierte Scanner können ausgenommen werden:

```yaml
fail2ban_scanner_useragents_ignore:
  - eLeDiaSecurityScanner
```

`apache-unusual-useragents` bannt sofort bei:

- fehlendem User-Agent `"-"`
- leerem oder nur aus Leerzeichen bestehendem User-Agent
- User-Agent ab `fail2ban_unusual_useragents_max_length`, standardmäßig `256`

Generische Clients wie `curl`, `wget`, `python-requests` und `Go-http-client` sind nicht pauschal enthalten. Die können in Monitoring, APIs oder Cronjobs legitim sein.


`moodle-webservice-abuse` zählt GET/POST-Aufrufe auf die echten Moodle-Webservice-Ausführungsendpunkte (`webservice/rest/server.php`, `webservice/xmlrpc/server.php`, `webservice/soap/server.php`). Das Jail ist bewusst threshold-basiert: Mobile Apps und Integrationen erzeugen legitime API-Last, deshalb liegt `maxretry` mit Standard `60` höher als bei `moodle-badbots`. Bekannte Integrations-Backends können jail-spezifisch über `fail2ban_moodle_webservice_abuse_ignoreip` ausgenommen werden, ohne sie global aus allen Jails herauszunehmen.

`moodle-badbots`, `moodle-pwreset-abuse` und `moodle-form-abuse` besitzen ebenfalls jail-spezifische `ignoreip`-Variablen. Diese sind für bekannte Campus-/NAT-/Helpdesk-/Monitoring-Quellen gedacht und vermeiden False Positives, ohne die IP global gegen High-Confidence-Probes wie `.env` oder Scanner-User-Agents blind zu machen.

`moodle-pwreset-abuse` zählt POSTs auf `login/forgot_password.php`, um Account-Enumeration über viele Reset-Versuche zu erkennen. Es ist ebenfalls threshold-basiert, aber mit niedrigerem Standard `maxretry: 8`, weil ein echter Nutzer dieses Formular normalerweise nicht mehrfach in kurzer Zeit absendet. Einzelne legitime Reset-Requests zählen als Ereignis, lösen allein aber keinen Ban aus.

`moodle-form-abuse` zählt POSTs auf öffentliche Moodle-Formulare, die häufig für Spam oder automatisierte Account-Erzeugung missbraucht werden: `login/signup.php` und `user/contactsitesupport.php`. Das Jail ist aktiv und streng feldgebunden, aber threshold-basiert (`maxretry: 5`), damit ein einzelner legitimer Formularversand nicht sperrt.

`moodle-behat-access` überwacht Behat-bezogene Moodle-Pfade bei `200` und `404`. Ein `200` ist ein starkes Signal für öffentlich erreichbare Behat-Dateien und wird mit `maxretry: 1` sofort über die konfigurierte nftables-Aktion gedroppt. `404` bleibt enthalten, um Scans nach versteckten oder übrig gebliebenen Behat-Pfaden ebenfalls zu erfassen. Die erste Sperre bleibt bewusst temporär, weil dieses Jail auch 404-Probes enthält; Wiederholungstäter eskalieren über `bantime.increment` bis maximal `fail2ban_moodle_behat_access_maxtime`. Die HTTP-Antwort selbst muss Apache/Moodle liefern; Fail2Ban reagiert erst auf den Logeintrag.


`apache-infra-admin-exposure` ist eine default-off Zusatzabsicherung gegen versehentlich öffentlich erreichbare Solr-Admin- und HAProxy-Stats-Pfade auf demselben Apache/Moodle-Reverse-Proxy. Sie ersetzt keine Netzwerksegmentierung: Solr Admin und HAProxy Stats gehören auf interne Interfaces, geschützte VHosts oder separate Logpfade. Aktivieren nur nach Prüfung der echten Access-Logs mit `fail2ban-regex` und nur, wenn Monitoring-Zugriffe wie `/haproxy?stats` nicht über denselben überwachten Logpfad laufen oder sauber per IP ausgenommen sind. Bekannte interne Monitoring-/Admin-Quellen können nur für diese Jail über `fail2ban_infra_admin_exposure_ignoreip` ausgenommen werden; diese Ausnahme muss eng bleiben und ersetzt den Logtest nicht. Generische Solr-Select-Endpunkte werden bewusst nicht gematcht, um Search-Proxy-False-Positives zu vermeiden.

`apache-fakegooglebot` nutzt den Fail2Ban-Built-in-Filter samt `ignorecommand` für Reverse-DNS-Double-Check. Die Jail ist default-off, weil sie DNS-Lookups benötigt und damit bewusst vom sonstigen Rollenstandard `fail2ban_usedns: "no"` abweicht. DNS-Lookups können Log-Scanning verlangsamen oder bei Resolver-Problemen Latenz erzeugen. Aktivieren nur, wenn der Built-in-Filter und das Ignorecommand auf dem Zielhost vorhanden sind; die Rolle prüft das bei aktivierter Jail vor dem Rendern.

Low-and-Slow-Scanning ist die Grenze jedes kurzen Schwellwert-Fensters: Wer z.B. nur wenige 4xx-Requests pro Tag sendet, bleibt unter `apache-scanburst` und erzeugt damit auch keine `recidive`-Eskalation. Dafür gibt es optional `apache-slow-scan`. Das Jail nutzt denselben Filter wie `apache-scanburst`, aber mit langem Zeitraum (`fail2ban_slow_scan_findtime`, Standard `14d`) und niedriger Schwelle (`fail2ban_slow_scan_maxretry`, Standard `7`). Es ist bewusst default-off, weil lange Fenster bei NAT-/Campus-IP-Adressen schneller False Positives erzeugen können.

---

## Filter erweitern

Neue Scanner-User-Agents gehören nicht direkt ins Regex. Nutze dafür Variablen:

```yaml
fail2ban_scanner_useragents_extra:
  - MyBadScanner
```

Autorisierte Scanner kommen in die Ignore-Liste:

```yaml
fail2ban_scanner_useragents_ignore:
  - eLeDiaSecurityScanner
```

Neue verdächtige Pfade ergänzt du im Filter:

```text
roles/install-fail2ban/files/apache-malicious-paths.conf
```

Beispiel: `/.env` und `/public_html/.env` sind bereits abgedeckt, weil der Filter nach `/.env` an jeder Stelle im Request-Pfad sucht. Für einen neuen Pfad ergänzt du die passende Gruppe, zum Beispiel:

```regex
|backup\.zip|database\.sql
```

Faustregel: Nur Dinge aufnehmen, die normale Moodle-Nutzer nie abrufen sollten. Sonst kommt es zu False Positives.

---

## Lokale Prüfungen

Zusätzliche Repo-Checks für bekannte Fehlerklassen:

```bash
ANSIBLE_COLLECTIONS_PATH=.cache/collections ANSIBLE_ROLES_PATH=roles \
  ansible-playbook -i tests/inventory.ini install_fail2ban.yml --syntax-check

ANSIBLE_COLLECTIONS_PATH=.cache/collections ANSIBLE_ROLES_PATH=roles \
  ansible-playbook -i tests/inventory.ini tests/security_contract.yml

ANSIBLE_COLLECTIONS_PATH=.cache/collections ANSIBLE_ROLES_PATH=roles \
  ansible-playbook -i tests/inventory.ini tests/regex.yml

ANSIBLE_COLLECTIONS_PATH=.cache/collections ANSIBLE_ROLES_PATH=roles \
  ansible-lint .
```

Die Checks prüfen Syntax, Whitelist-Vertrag, IPv4/IPv6-Werte und die exakten Trefferzahlen aller Regex-Fixtures. GitHub Actions führt sie automatisch aus. `.gitlab-ci.yml` enthält die gleiche Matrix für einen vorhandenen GitLab-Runner.

---

## Jail-Überblick

| Jail | Konfidenz/Signal | Default | Standard-Verhalten |
|---|---|---:|---|
| `sshd` | Auth/Behavioral | enabled | progressiv `1h` bis `7d` |
| `apache-malicious-paths` | High-Confidence Path | enabled | permanent |
| `moodle-badbots` | Behavioral/Threshold | enabled | progressiv `2h` bis `7d` |
| `moodle-webservice-abuse` | Behavioral/Threshold | enabled | progressiv `2h` bis `7d` |
| `moodle-pwreset-abuse` | Behavioral/Threshold | enabled | progressiv `4h` bis `14d` |
| `moodle-form-abuse` | Behavioral/Threshold | enabled | progressiv `4h` bis `14d` |
| `moodle-behat-access` | High-Confidence/Probe gemischt | enabled | progressiv `1h` bis `30d` |
| `apache-scanner-useragents` | High-Confidence UA | enabled | permanent |
| `apache-unusual-useragents` | UA-Anomalie | enabled | fix `1h`, Wiederholung über `recidive` |
| `apache-scanburst` | Behavioral/Burst | enabled | progressiv `12h` bis `90d` |
| `apache-slow-scan` | Behavioral/Low-and-Slow | disabled | progressiv `7d` bis `90d` |
| `apache-infra-admin-exposure` | High-Confidence Infra-Pfad | disabled | permanent |
| `apache-overflows` | Built-in High-Confidence | enabled | permanent |
| `apache-shellshock` | Built-in High-Confidence | enabled | permanent |
| `apache-auth` | Built-in Auth | disabled | fix `1d` |
| `apache-fakegooglebot` | Built-in High-Confidence DNS | disabled | permanent |
| `apache-badbots` | Built-in Bot-Liste | enabled | permanent |
| `apache-botsearch` | Built-in Bot/Search | disabled | fix `1d` |
| `recidive` | Wiederholungstäter | enabled | permanent all-ports |

---

## Wichtige Variablen

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

fail2ban_moodle_webservice_abuse_maxretry: 60
fail2ban_moodle_webservice_abuse_findtime: 10m
fail2ban_moodle_webservice_abuse_bantime: 2h
fail2ban_moodle_webservice_abuse_ignoreip: []

fail2ban_moodle_password_reset_abuse_maxretry: 8
fail2ban_moodle_password_reset_abuse_findtime: 10m
fail2ban_moodle_password_reset_abuse_bantime: 4h
fail2ban_moodle_password_reset_abuse_ignoreip: []

fail2ban_moodle_form_abuse_enabled: true
fail2ban_moodle_form_abuse_maxretry: 5
fail2ban_moodle_form_abuse_findtime: 10m
fail2ban_moodle_form_abuse_bantime: 4h
fail2ban_moodle_form_abuse_ignoreip: []

fail2ban_infra_admin_exposure_enabled: false
fail2ban_infra_admin_exposure_maxretry: 1
fail2ban_infra_admin_exposure_findtime: 1d
fail2ban_infra_admin_exposure_bantime: -1
fail2ban_infra_admin_exposure_ignoreip: []

fail2ban_apache_fakegooglebot_enabled: false
fail2ban_apache_fakegooglebot_maxretry: 1
fail2ban_apache_fakegooglebot_findtime: 1d
fail2ban_apache_fakegooglebot_bantime: -1
fail2ban_apache_fakegooglebot_usedns: "warn"

fail2ban_slow_scan_enabled: false
fail2ban_slow_scan_maxretry: 7
fail2ban_slow_scan_findtime: 14d
fail2ban_slow_scan_bantime: 7d

fail2ban_moodle_behat_access_maxretry: 1
fail2ban_moodle_behat_access_findtime: 10m
fail2ban_moodle_behat_access_bantime: 1h
fail2ban_moodle_behat_access_bantime_increment: true
fail2ban_moodle_behat_access_multipliers: "1 6 24 168"
fail2ban_moodle_behat_access_maxtime: 30d
fail2ban_moodle_behat_access_rndtime: 10m
fail2ban_moodle_behat_access_ignoreip: []

fail2ban_recidive_maxretry: 3
fail2ban_recidive_findtime: 7d
fail2ban_recidive_bantime: -1
```

## Fail2Ban Prometheus Exporter

Optional:

```yaml
fail2ban_exporter_enabled: true
fail2ban_exporter_listen_address: "127.0.0.1:9191"
fail2ban_exporter_health_url: "http://127.0.0.1:9191/metrics"
```

Der Exporter läuft nach `fail2ban.service`, liest `/var/run/fail2ban/fail2ban.sock` und bindet standardmäßig nur auf localhost.

---

## Rollback

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
  /etc/fail2ban/filter.d/apache-infra-admin-exposure.conf \
  /etc/fail2ban/filter.d/moodle-badbots.conf \
  /etc/fail2ban/filter.d/moodle-webservice-abuse.conf \
  /etc/fail2ban/filter.d/moodle-password-reset-abuse.conf \
  /etc/fail2ban/filter.d/moodle-form-abuse.conf \
  /etc/fail2ban/filter.d/moodle-behat-access.conf \
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

## Weitere Dokumente

- `MANUELL.md`: bewusst schlanker Basis-/Notfall-Auszug; vollständige Jail-Übersicht bleibt hier im README
- `CHANGELOG.md`: Änderungen und Versionen
- `inventory/vm-hosts.example`: Beispiel für lokale VM-Tests
- `inventory/group_vars/fail2ban_vm_all.yml.example`: Beispielvariablen ohne lokale Zugangsdaten

Die echten VM-Inventare bleiben lokal und werden über `.gitignore` ausgeschlossen.

## Unterstützte Ansible-Versionen

- Rollen-Version `2.0.0`
- ansible-core 2.12.10
- ansible-core 2.21.2
- MIT-Lizenz, siehe `LICENSE`

##
Made with ☕ and ❤️ by **Bernd Schreistetter**
