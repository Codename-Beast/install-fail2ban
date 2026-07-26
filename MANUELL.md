# 🛠️ Manuelle Fail2Ban-Absicherung

Diese Anleitung beschreibt die händische Variante der Rolle `install-fail2ban` für Debian- und Ubuntu-Webserver. Sie ist für Fälle gedacht, in denen ein Server ohne Ansible vorbereitet, geprüft oder im Notfall nachvollziehbar abgesichert werden soll.

Die Ansible-Rolle bleibt der bevorzugte Weg. Manuell arbeitest du nur, wenn du bewusst jede Datei selbst setzen und prüfen willst.

> Kurz gesagt: Erst absichern, dann schreiben, dann testen, dann neu laden.
> Wenn `fail2ban-client -t` fehlschlägt, bleibt der Dienst unverändert.

## Inhalt

- [Zielbild](#-zielbild)
- [Vorbereitung](#1-werte-festlegen)
- [Filter und Jails](#7-filter-installieren)
- [Test und Aktivierung](#10-konfiguration-testen)
- [Rollback und Notfallmodus](#16-rollback)

---

## ✅ Zielbild

Am Ende soll der Server so stehen:

- Fail2Ban ist installiert und aktiv.
- Bans laufen über nftables.
- SSH ist über das systemd-Journal geschützt.
- Die SSH-Ports `22` und `3333` sind abgedeckt.
- Apache/Moodle-Scans werden über eigene Jails erkannt.
- Ungewöhnliche oder eindeutig verdächtige User-Agents werden sofort gebannt.
- Wiederholungstäter landen über `recidive` im Allports-Drop.
- Admin-, VPN- oder Jump-Host-Adressen stehen in `ignoreip`.
- Vor Start, Reload oder Restart wird immer `fail2ban-client -t` ausgeführt.

Wichtig: Fail2Ban sperrt IP-Adressen, keine Benutzer. Auch ein Admin mit SSH-Key kann sich aussperren, wenn die eigene Quell-IP nicht in der Whitelist steht.

---

## 1. Werte festlegen

Passe diese Werte vor dem Kopieren an:

```text
TRUSTED_IPS="127.0.0.1/8 ::1 203.0.113.55"
APACHE_ACCESS_LOG="/var/log/apache2/*access.log"
APACHE_ERROR_LOG="/var/log/apache2/*error.log"
SSH_PORTS="22,3333"
```

`203.0.113.55` ist nur ein Platzhalter. Verwende hier echte Admin-, VPN- oder Jump-Host-Adressen.

Wenn du unsicher bist, nimm lieber zuerst nur SSH in Betrieb und prüfe danach die Web-Jails gegen echte Logs.

---

## 2. Vorbedingungen prüfen

```bash
cat /etc/os-release
command -v nft
systemctl status nftables --no-pager
test -d /var/log/apache2 && echo "Apache log dir exists"
```

Wenn `nft` fehlt, installiere und aktiviere nftables zuerst. Diese Anleitung installiert nftables nicht automatisch, weil die Firewall-Policy bewusst gesetzt werden muss.

---

## 3. Fail2Ban installieren

```bash
sudo apt update
sudo apt install fail2ban
```

Das Paket kann den Dienst direkt starten. Das ist okay. Wichtig ist nur: neue Dateien erst schreiben, danach `fail2ban-client -t` ausführen und erst dann Reload oder Restart machen.

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

Die statischen Filter liegen in der Rolle unter `roles/install-fail2ban/files/`.

```bash
sudo install -m 0644 -o root -g root \
  roles/install-fail2ban/files/apache-malicious-paths.conf \
  /etc/fail2ban/filter.d/apache-malicious-paths.conf

sudo install -m 0644 -o root -g root \
  roles/install-fail2ban/files/moodle-badbots.conf \
  /etc/fail2ban/filter.d/moodle-badbots.conf

sudo install -m 0644 -o root -g root \
  roles/install-fail2ban/files/apache-scanburst.conf \
  /etc/fail2ban/filter.d/apache-scanburst.conf
```

Kurz zur Einordnung:

- `apache-malicious-paths` erkennt eindeutige Scans auf `.env`, `.git`, phpMyAdmin, WordPress, PHPUnit, Webshells und ähnliche Pfade.
- `moodle-badbots` erkennt wiederholte POST-Zugriffe auf Moodle-Login- und Token-Endpunkte. Einzelne Fehlversuche werden nicht sofort gebannt.
- `apache-scanburst` zählt viele Fehlerantworten wie `400`, `403`, `404`, `405`, `408` und `414`.

---

## 8. User-Agent-Filter setzen

Die Rolle rendert diese Filter normalerweise aus Templates. Wenn du manuell arbeitest, legst du sie direkt an.

Datei:

```text
/etc/fail2ban/filter.d/apache-scanner-useragents.conf
```

```ini
[Definition]
failregex = ^(?:\S+:\d+\s+)?<HOST>.*"[^"]*"\s+\d{3}(?:\s+\S+)?\s+"[^"]*"\s+"[^"]*(?i:sqlmap|nikto|nmap\ scripting\ engine|masscan|zgrab|zmap|gobuster|dirbuster|dirsearch|feroxbuster|ffuf|wpscan|nuclei|acunetix|nessus|openvas|havij|whatweb|censysinspect|internetmeasurement|jaeles|arachni|wapiti|skipfish)[^"]*"(?:\s+.*)?$
ignoreregex =
```

Datei:

```text
/etc/fail2ban/filter.d/apache-unusual-useragents.conf
```

```ini
[Definition]
failregex = ^(?:\S+:\d+\s+)?<HOST>\s+.*"[^"]*"\s+\d{3}(?:\s+\S+)?\s+"[^"]*"\s+"(?:-|\s*)"(?:\s+.*)?$
            ^(?:\S+:\d+\s+)?<HOST>\s+.*"[^"]*"\s+\d{3}(?:\s+\S+)?\s+"[^"]*"\s+"[^"]{256,}"(?:\s+.*)?$
            ^(?:\S+:\d+\s+)?<HOST>\s+.*"[^"]*"\s+\d{3}(?:\s+\S+)?\s+"[^"]*"\s+"[^"]*(?i:sqlmap|nikto|nmap\ scripting\ engine|masscan|zgrab|zmap|gobuster|dirbuster|dirsearch|feroxbuster|ffuf|wpscan|nuclei|acunetix|nessus|openvas|havij|whatweb|censysinspect|internetmeasurement|jaeles|arachni|wapiti|skipfish)[^"]*"(?:\s+.*)?$
ignoreregex =
```

`apache-unusual-useragents` bannt sofort bei fehlendem, leerem, überlangem oder eindeutigem Scanner-User-Agent.

Generische Clients wie `curl`, `wget`, `python-requests` und `Go-http-client` sind bewusst nicht pauschal enthalten. Solche Clients können in Monitoring, APIs oder Cronjobs legitim sein.

Rechte setzen:

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

Ersetze `127.0.0.1/8 ::1 203.0.113.55` durch deine echte Whitelist.

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

## 11. Dienst starten oder neu laden

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

Details pro Jail:

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

## 13. Filter gegen echte Logs testen

```bash
sudo fail2ban-regex /var/log/apache2/access.log /etc/fail2ban/filter.d/apache-malicious-paths.conf
sudo fail2ban-regex /var/log/apache2/access.log /etc/fail2ban/filter.d/moodle-badbots.conf
sudo fail2ban-regex /var/log/apache2/access.log /etc/fail2ban/filter.d/apache-scanner-useragents.conf
sudo fail2ban-regex /var/log/apache2/access.log /etc/fail2ban/filter.d/apache-unusual-useragents.conf
sudo fail2ban-regex /var/log/apache2/access.log /etc/fail2ban/filter.d/apache-scanburst.conf
```

Bei False Positives wird der Filter enger gemacht oder ein autorisierter Scanner über `ignoreregex` ausgenommen. Große Netze gehören nicht aus Bequemlichkeit in `ignoreip`.

---

## 14. nftables prüfen

```bash
sudo nft list ruleset
```

Nach echten Treffern sollten Fail2Ban-Tabellen, Chains oder Sets sichtbar sein. Test-Bans nur in einem Wartungsfenster setzen, damit du dich nicht selbst aussperrst.

---

## 15. IP entbannen

```bash
sudo fail2ban-client set apache-unusual-useragents unbanip 203.0.113.10
sudo fail2ban-client set recidive unbanip 203.0.113.10
```

---

## 16. Rollback

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

Wenn `fail2ban-client -t` nach dem Restore fehlschlägt, Dienst nicht starten. Erst die gemeldete Datei prüfen.

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

Das ist nur der Notfallmodus. Für den vollständigen Webschutz nimm die Jails oben oder, sauberer, direkt die Ansible-Rolle.
