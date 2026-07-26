# Manuelle Absicherung

Diese Anleitung beschreibt die händische Variante der Rolle `install-fail2ban` für eLeDia Webserver.


> **Hinweis:** Diese Anleitung ist bewusst ein Basis-/Notfall-Auszug. Sie deckt
> den stabilen Kernbestand ab (SSH, ursprüngliche Apache-/Moodle-Webschutz-Jails,
> `recidive`) und ersetzt nicht die vollständige Rollenreferenz. Für die aktuelle
> komplette Jail-Übersicht inklusive Moodle-Webservice/Password-Reset, Behat,
> Low-and-Slow, Infra-Admin-Exposure und Fake-Googlebot siehe `README.md`,
> Abschnitt "Jail-Überblick". Neue optionale oder spezialisierte Jails werden
> nicht automatisch hier nachgezogen, damit es keine zweite vollständige Wahrheit
> neben der Rolle/README gibt.


---

## Ziel Zustand

Am Ende soll der Server so stehen:

- Fail2Ban ist installiert und aktiv.
- Bans laufen über nftables.
- SSH ist über das systemd-Journal geschützt.
- Die SSH-Ports `22` und `3333` sind abgedeckt.
- Apache/Moodle-Scans werden über den hier dokumentierten Kernbestand eigener Jails erkannt.
- Wiederholungstäter landen über `recidive` im Allports-Drop.
- Admin-, VPN- oder Jump-Host-Adressen stehen in `ignoreip`.
- Vor Start, Reload oder Restart wird immer `fail2ban-client -t` ausgeführt.

Wichtig: Fail2Ban sperrt IP-Adressen. Auch ein Admin mit SSH-Key kann sich aussperren, wenn die eigene Quell-IP nicht in der Whitelist steht.

---

## 1. Werte festlegen

Passe diese Werte vor dem Kopieren an:

```text
TRUSTED_IPS="127.0.0.1/8 ::1 203.0.113.55"
APACHE_ACCESS_LOG="/var/log/apache2/*access.log"
APACHE_ERROR_LOG="/var/log/apache2/*error.log"
SSH_PORTS="22,3333"
```

`203.0.113.55` ist nur ein Platzhalter. Verwende die eLeDia-IP

Wenn du unsicher bist, nimm lieber zuerst nur SSH in Betrieb und prüfe danach die Web-Jails gegen Logs.

---

## 2. Vorbedingungen prüfen

```bash
cat /etc/os-release
command -v nft
systemctl status nftables --no-pager
test -d /var/log/apache2 && echo "Apache log dir exists"
```

Wenn `nft` fehlt, installiere und aktiviere nftables zuerst, weil die Firewall-Policy bewusst gesetzt werden muss.

---

## 3. Fail2Ban installieren

```bash
sudo apt update
sudo apt install fail2ban
```

Das Paket kann den Service direkt starten. Das ist nicht schlimm, aber danach gilt: erst neue Dateien schreiben, dann `fail2ban-client -t`, dann Reload oder Restart.

---

## 4. Ausgangszustand sichern

```bash
sudo mkdir -p /root/fail2ban-backup
sudo chmod 0700 /root/fail2ban-backup
sudo tar --create --gzip \
  --file=/root/fail2ban-backup/fail2ban-before-web-protection.tar.gz \
  /etc/fail2ban
sudo chmod 0600 /root/fail2ban-backup/fail2ban-before-web-protection.tar.gz
```

Das Backup ist bewusst einfach gehalten. Es soll im Fehlerfall schnell genug sein, um den alten Stand wiederherzustellen.

---

## 5. Verzeichnisse vorbereiten

```bash
sudo install -d -o root -g root -m 0755 /etc/fail2ban/fail2ban.d
sudo install -d -o root -g root -m 0755 /etc/fail2ban/filter.d
sudo install -d -o root -g root -m 0755 /etc/fail2ban/jail.d
```

---

## 6. Fail2Ban-Grundkonfiguration setzen

Datei:

```text
/etc/fail2ban/fail2ban.d/99-web-protection.local
```

Inhalt:

```ini
[Definition]
loglevel = INFO
logtarget = /var/log/fail2ban.log
dbfile = /var/lib/fail2ban/fail2ban.sqlite3
dbpurgeage = 2592000
dbmaxmatches = 20
```

Rechte setzen:

```bash
sudo chown root:root /etc/fail2ban/fail2ban.d/99-web-protection.local
sudo chmod 0644 /etc/fail2ban/fail2ban.d/99-web-protection.local
```

---

## 7. Filter installieren

Die statischen Kernfilter liegen in der Rolle unter `install-fail2ban/files/`. Für alle weiteren Filter ist die Rolle/README maßgeblich.

```bash
sudo install -m 0644 -o root -g root \
  install-fail2ban/files/apache-malicious-paths.conf \
  /etc/fail2ban/filter.d/apache-malicious-paths.conf

sudo install -m 0644 -o root -g root \
  install-fail2ban/files/moodle-badbots.conf \
  /etc/fail2ban/filter.d/moodle-badbots.conf

sudo install -m 0644 -o root -g root \
  install-fail2ban/files/apache-scanburst.conf \
  /etc/fail2ban/filter.d/apache-scanburst.conf
```

Kurz zur Einordnung:

- `apache-malicious-paths` erkennt eindeutige Scans auf `.env`, `.git`, phpMyAdmin, WordPress, PHPUnit, Webshells und ähnliche Pfade.
- `moodle-badbots` erkennt wiederholte POST-Zugriffe auf Moodle-Login- und Token-Endpunkte. Einzelne Fehlversuche werden nicht sofort gebannt.
- `apache-scanburst` zählt viele Fehlerantworten wie `400`, `403`, `404`, `405`, `408` und `414`.

---

## 8. User-Agent-Filter setzen

Die Rolle rendert diese Filter aus Templates. Damit diese Notfallanleitung keine zweite, veraltende Regex-Wahrheit enthält, werden die Regex-Zeilen hier nicht mehr ausgeschrieben. Für manuelle Arbeit gilt:

1. Wenn das Repo verfügbar ist, rendere die Rolle lokal oder auf einem sicheren Admin-System und kopiere die gerenderten Dateien nach `/etc/fail2ban/filter.d/`:
   - `apache-scanner-useragents.conf`
   - `apache-unusual-useragents.conf`
2. Wenn kein Render möglich ist, lasse diese beiden UA-Jails im Notfall weg und nutze zuerst SSH plus die statischen Kernfilter. Ziehe danach die Ansible-Rolle oder `README.md` nach.

`apache-scanner-useragents` erkennt klar benannte Scanner. `apache-unusual-useragents` bannt bei fehlendem, leerem oder überlangem User-Agent. Generische Clients wie `curl`, `wget`, `python-requests` und `Go-http-client` sind bewusst nicht pauschal enthalten.

Rechte setzen, nachdem die Dateien korrekt gerendert/kopiert wurden:

```bash
sudo chown root:root /etc/fail2ban/filter.d/apache-scanner-useragents.conf /etc/fail2ban/filter.d/apache-unusual-useragents.conf
sudo chmod 0644 /etc/fail2ban/filter.d/apache-scanner-useragents.conf /etc/fail2ban/filter.d/apache-unusual-useragents.conf
```

---

## 9. Jails anlegen

Datei:

```text
/etc/fail2ban/jail.d/99-apache-moodle-bots.local
```

Ersetze `127.0.0.1/8 ::1 203.0.113.55` durch deine echte Whitelist. Der folgende Block ist der bewusst schlanke Kernbestand; die vollständige Jail-Matrix bleibt in der Rolle/README.

```ini
[sshd]
enabled = true
filter = sshd
port = 22,3333
protocol = tcp
ignoreip = 127.0.0.1/8 ::1 203.0.113.55
ignoreself = true
usedns = no
backend = systemd
banaction = nftables
action = %(action_)s
maxretry = 5
findtime = 10m
bantime = 1h
bantime.increment = true
bantime.multipliers = 1 2 6 24 72
bantime.maxtime = 7d
bantime.rndtime = 5m

[apache-malicious-paths]
enabled = true
filter = apache-malicious-paths
port = http,https
ignoreip = 127.0.0.1/8 ::1 203.0.113.55
backend = auto
banaction = nftables
action = %(action_)s
logpath = /var/log/apache2/*access.log
maxretry = 1
findtime = 1d
bantime = -1

[moodle-badbots]
enabled = true
filter = moodle-badbots
port = http,https
ignoreip = 127.0.0.1/8 ::1 203.0.113.55
backend = auto
banaction = nftables
action = %(action_)s
logpath = /var/log/apache2/*access.log
maxretry = 25
findtime = 10m
bantime = 2h
bantime.increment = true
bantime.multipliers = 1 2 6 24
bantime.maxtime = 7d
bantime.rndtime = 5m

[apache-scanner-useragents]
enabled = true
filter = apache-scanner-useragents
port = http,https
ignoreip = 127.0.0.1/8 ::1 203.0.113.55
backend = auto
banaction = nftables
action = %(action_)s
logpath = /var/log/apache2/*access.log
maxretry = 1
findtime = 1d
bantime = -1

[apache-unusual-useragents]
enabled = true
filter = apache-unusual-useragents
port = http,https
ignoreip = 127.0.0.1/8 ::1 203.0.113.55
backend = auto
banaction = nftables
action = %(action_)s
logpath = /var/log/apache2/*access.log
maxretry = 1
findtime = 10m
bantime = 1h

[apache-scanburst]
enabled = true
filter = apache-scanburst
port = http,https
ignoreip = 127.0.0.1/8 ::1 203.0.113.55
backend = auto
banaction = nftables
action = %(action_)s
logpath = /var/log/apache2/*access.log
maxretry = 80
findtime = 5m
bantime = 12h
bantime.increment = true
bantime.multipliers = 1 2 6 14 60 180
bantime.maxtime = 90d
bantime.rndtime = 10m

[apache-overflows]
enabled = true
filter = apache-overflows
port = http,https
ignoreip = 127.0.0.1/8 ::1 203.0.113.55
backend = auto
banaction = nftables
action = %(action_)s
logpath = /var/log/apache2/*error.log
maxretry = 2
findtime = 1d
bantime = -1

[apache-shellshock]
enabled = true
filter = apache-shellshock
port = http,https
ignoreip = 127.0.0.1/8 ::1 203.0.113.55
backend = auto
banaction = nftables
action = %(action_)s
logpath = /var/log/apache2/*error.log
maxretry = 1
findtime = 1d
bantime = -1

[recidive]
enabled = true
filter = recidive
logpath = /var/log/fail2ban.log
protocol = tcp,udp
ignoreip = 127.0.0.1/8 ::1 203.0.113.55
backend = auto
banaction = nftables[type=allports]
action = %(action_)s
maxretry = 3
findtime = 7d
bantime = -1
```

Rechte setzen:

```bash
sudo chown root:root /etc/fail2ban/jail.d/99-apache-moodle-bots.local
sudo chmod 0644 /etc/fail2ban/jail.d/99-apache-moodle-bots.local
```

---

## 10. Konfiguration testen

```bash
sudo fail2ban-client -t
```

Nur wenn diese Prüfung erfolgreich ist, darfst du den Dienst starten, neu laden oder neu starten. Bei Fehlern erst die gemeldete Datei korrigieren und erneut testen.

---

## 11. Service starten oder neu laden

Erstaktivierung:

```bash
sudo systemctl enable --now fail2ban
sudo systemctl status fail2ban --no-pager
```

Spätere Jail- oder Filter-Änderungen:

```bash
sudo fail2ban-client -t
sudo fail2ban-client reload
```

Änderungen unter `/etc/fail2ban/fail2ban.d/` brauchen einen Restart:

```bash
sudo fail2ban-client -t
sudo systemctl restart fail2ban
```

---

## 12. Status prüfen

```bash
sudo fail2ban-client status
```

Details pro hier dokumentierter Kern-Jail:

```bash
sudo fail2ban-client status sshd
sudo fail2ban-client status apache-malicious-paths
sudo fail2ban-client status moodle-badbots
sudo fail2ban-client status apache-scanner-useragents
sudo fail2ban-client status apache-unusual-useragents
sudo fail2ban-client status apache-scanburst
sudo fail2ban-client status apache-overflows
sudo fail2ban-client status apache-shellshock
sudo fail2ban-client status recidive
```

Achte besonders auf:

```text
Currently banned
Total banned
File list
```

Wenn eine erwartete Jail fehlt, nicht weiterarbeiten, sondern zuerst die Konfiguration prüfen.

---

## 13. Kernfilter gegen Logs testen

```bash
sudo fail2ban-regex /var/log/apache2/access.log /etc/fail2ban/filter.d/apache-malicious-paths.conf
sudo fail2ban-regex /var/log/apache2/access.log /etc/fail2ban/filter.d/moodle-badbots.conf
sudo fail2ban-regex /var/log/apache2/access.log /etc/fail2ban/filter.d/apache-scanner-useragents.conf
sudo fail2ban-regex /var/log/apache2/access.log /etc/fail2ban/filter.d/apache-unusual-useragents.conf
sudo fail2ban-regex /var/log/apache2/access.log /etc/fail2ban/filter.d/apache-scanburst.conf
```

Bei False Positives: Filter enger machen oder autorisierte Scanner über `ignoreregex` ausnehmen. Nicht aus Bequemlichkeit große Netze in `ignoreip` aufnehmen. Für neue/spezialisierte Filter wie Webservice, Password-Reset, Behat, Slow-Scan oder Infra-Admin-Exposure siehe README.md und die Rollen-Fixtures.

---

## 14. nftables prüfen

```bash
sudo nft list ruleset
```

Nach Treffern sollten Fail2Ban-Tabellen, Chains oder Sets sichtbar sein. Test-Bans nur in einem Wartungsfenster setzen, damit du dich nicht selbst aussperrst.

---

## 15. IP entbannen

```bash
sudo fail2ban-client set apache-unusual-useragents unbanip 203.0.113.10
sudo fail2ban-client set recidive unbanip 203.0.113.10
```

---

## 16. Rollback

Dieser Rollback entfernt nur den in dieser Datei dokumentierten Kernbestand. Falls die vollständige Rolle mit weiteren Jails ausgerollt wurde, nutze die Rollback-Liste aus README.md.

```bash
sudo systemctl stop fail2ban
sudo rm -f \
  /etc/fail2ban/fail2ban.d/99-web-protection.local \
  /etc/fail2ban/filter.d/apache-malicious-paths.conf \
  /etc/fail2ban/filter.d/moodle-badbots.conf \
  /etc/fail2ban/filter.d/apache-scanner-useragents.conf \
  /etc/fail2ban/filter.d/apache-unusual-useragents.conf \
  /etc/fail2ban/filter.d/apache-scanburst.conf \
  /etc/fail2ban/jail.d/99-apache-moodle-bots.local

sudo tar --extract --gzip \
  --file=/root/fail2ban-backup/fail2ban-before-web-protection.tar.gz \
  --directory=/

sudo fail2ban-client -t
sudo systemctl restart fail2ban
```

Wenn `fail2ban-client -t` nach dem Restore fehlschlägt, Service nicht starten. Erst die gemeldete Datei prüfen.

---

## 17. Minimaler Notfallmodus nur für SSH

Wenn nur SSH sofort geschützt werden muss, reicht vorübergehend diese Jail:

```ini
[sshd]
enabled = true
filter = sshd
backend = systemd
port = 22,3333
ignoreip = 127.0.0.1/8 ::1 203.0.113.55
banaction = nftables
maxretry = 5
findtime = 10m
bantime = 1h
```

Danach:

```bash
sudo fail2ban-client -t
sudo systemctl restart fail2ban
sudo fail2ban-client status sshd
```

Das ist nur ein Notfallmodus. Für den vollständigen Webschutz nutze die Ansible-Rolle und die Jail-Übersicht in README.md.
