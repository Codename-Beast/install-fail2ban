# MANUELL.md

Händische Fail2Ban-Absicherung für Debian/Ubuntu-Webserver, falls Ansible nicht verfügbar ist.

Dieses Tutorial übersetzt die Rolle `install_fail2ban` in manuelle Arbeitsschritte. Es ist für Sysadmins gedacht, die einen Server absichern müssen, auch wenn Ansible gerade nicht zur Verfügung steht.

---

## Zielbild

Nach der Umsetzung gilt:

- Fail2Ban ist installiert und aktiviert.
- SSH wird nur über systemd-journal ausgewertet.
- Es gibt keinen `/var/log/auth.log`-Fallback.
- Apache/Moodle-Scanner werden über eigene Filter gebannt.
- nftables muss vorhanden sein.
- Die gemeinsame VPN- oder Jump-Host-IP steht in jedem `ignoreip`.
- Die Konfiguration wird vor dem Start mit `fail2ban-client -t` geprüft.
- Nach dem Start werden Service-Status, aktive Jails und Ban-Zähler kontrolliert.

---

## 1. Werte festlegen

Lege vor dem Kopieren der Dateien fest:

```text
TRUSTED_IPS="127.0.0.1/8 ::1 203.0.113.55"
APACHE_ACCESS_LOG="/var/log/apache2/*access.log"
APACHE_ERROR_LOG="/var/log/apache2/*error.log"
```

`203.0.113.55` ist ein Platzhalter. Ersetze ihn durch die gemeinsame VPN- oder Jump-Host-IP. Ohne diese Whitelist kann ein legitimer SSH-Zugang über eine gemeinsame Quell-IP ausgesperrt werden.

---

## 2. Vorbedingungen prüfen

```bash
cat /etc/os-release
command -v nft
systemctl status nftables --no-pager
test -d /var/log/apache2 && echo "Apache log dir exists"
```

Wenn `nft` fehlt, hier stoppen. Erst nftables sauber bereitstellen, dann Fail2Ban konfigurieren.

---

## 3. Fail2Ban installieren

```bash
sudo apt update
sudo apt install fail2ban
```

Noch nicht blind starten. Erst konfigurieren und testen.

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

---

## 5. Verzeichnisse vorbereiten

```bash
sudo install -d -o root -g root -m 0755 /etc/fail2ban/fail2ban.d
sudo install -d -o root -g root -m 0755 /etc/fail2ban/filter.d
sudo install -d -o root -g root -m 0755 /etc/fail2ban/jail.d
```

---

## 6. Fail2Ban-Grundkonfiguration

Datei anlegen:

```text
/etc/fail2ban/fail2ban.d/99-web-protection.local
```

Inhalt:

```ini
[DEFAULT]
loglevel = INFO
logtarget = /var/log/fail2ban.log
dbfile = /var/lib/fail2ban/fail2ban.sqlite3
dbpurgeage = 2592000
dbmaxmatches = 20
```

Rechte:

```bash
sudo chown root:root /etc/fail2ban/fail2ban.d/99-web-protection.local
sudo chmod 0644 /etc/fail2ban/fail2ban.d/99-web-protection.local
```

---

## 7. Filter anlegen

### 7.1 apache-malicious-paths

Datei:

```text
/etc/fail2ban/filter.d/apache-malicious-paths.conf
```

Inhalt:

```ini
[Definition]
failregex = ^(?:\S+:\d+\s+)?<HOST>\s+\S+\s+\S+\s+\[[^\]]+\]\s+"(?:GET|POST|HEAD|OPTIONS|PUT|DELETE|PATCH|PROPFIND|CONNECT)\s+(?:https?://[^/\s"]+)?[^\s"?]*(?i:/(?:\.env(?:\.[A-Za-z0-9_-]+)?|\.git|\.svn|\.hg|\.aws|\.ssh))(?=[/?#\s"])[^\s"]*\s+HTTP/\d(?:\.\d)?"\s+\d{3}(?:\s+.*)?$
            ^(?:\S+:\d+\s+)?<HOST>\s+\S+\s+\S+\s+\[[^\]]+\]\s+"(?:GET|POST|HEAD|OPTIONS|PUT|DELETE|PATCH|PROPFIND|CONNECT)\s+(?:https?://[^/\s"]+)?[^\s"?]*(?i:/(?:wp-login\.php|xmlrpc\.php|wp-admin|phpmyadmin|pma|adminer(?:\.php)?|vendor/phpunit|eval-stdin\.php|cgi-bin|actuator|boaform|hnap1))(?=[/?#\s"])[^\s"]*\s+HTTP/\d(?:\.\d)?"\s+\d{3}(?:\s+.*)?$
            ^(?:\S+:\d+\s+)?<HOST>\s+\S+\s+\S+\s+\[[^\]]+\]\s+"(?:GET|POST|HEAD|OPTIONS|PUT|DELETE|PATCH|PROPFIND|CONNECT)\s+(?:https?://[^/\s"]+)?[^\s"?]*(?i:/(?:config\.php|composer\.(?:json|lock)|phpinfo\.php|info\.php|(?:shell|cmd|webshell|wso|c99|r57|alfa|b374k)\.php))(?=[/?#\s"])[^\s"]*\s+HTTP/\d(?:\.\d)?"\s+\d{3}(?:\s+.*)?$
            ^(?:\S+:\d+\s+)?<HOST>\s+\S+\s+\S+\s+\[[^\]]+\]\s+"(?:GET|POST|HEAD|OPTIONS|PUT|DELETE|PATCH|PROPFIND|CONNECT)\s+(?:https?://[^/\s"]+)?[^\s"?]*(?i:/(?:etc/passwd|proc/self/environ))(?=[/?#\s"])[^\s"]*\s+HTTP/\d(?:\.\d)?"\s+\d{3}(?:\s+.*)?$
ignoreregex =
```

### 7.2 apache-scanburst

Datei:

```text
/etc/fail2ban/filter.d/apache-scanburst.conf
```

Inhalt:

```ini
[Definition]
failregex = ^(?:\S+:\d+\s+)?<HOST>\s+\S+\s+\S+\s+\[[^\]]+\]\s+"[^"]*"\s+(?:400|403|404|405|408|414)(?:\s+.*)?$
ignoreregex =
```

### 7.3 apache-scanner-useragents

Datei:

```text
/etc/fail2ban/filter.d/apache-scanner-useragents.conf
```

Inhalt:

```ini
[Definition]
failregex = ^(?:\S+:\d+\s+)?<HOST>\s+\S+\s+\S+\s+\[[^\]]+\]\s+"[^"]*"\s+\d{3}(?:\s+\S+)?\s+"[^"]*"\s+"[^"]*(?i:sqlmap|nikto|nmap\ scripting\ engine|masscan|zgrab|zmap|gobuster|dirbuster|dirsearch|feroxbuster|ffuf|wpscan|nuclei|acunetix|nessus|openvas|havij|whatweb|censysinspect|internetmeasurement|jaeles|arachni|wapiti|skipfish)[^"]*"(?:\s+.*)?$
ignoreregex =
```

Rechte:

```bash
sudo chown root:root /etc/fail2ban/filter.d/apache-malicious-paths.conf \
  /etc/fail2ban/filter.d/apache-scanburst.conf \
  /etc/fail2ban/filter.d/apache-scanner-useragents.conf
sudo chmod 0644 /etc/fail2ban/filter.d/apache-malicious-paths.conf \
  /etc/fail2ban/filter.d/apache-scanburst.conf \
  /etc/fail2ban/filter.d/apache-scanner-useragents.conf
```

---

## 8. Jails anlegen

Datei:

```text
/etc/fail2ban/jail.d/99-apache-moodle-bots.local
```

Inhalt. Ersetze `127.0.0.1/8 ::1 203.0.113.55` durch deine echte Whitelist:

```ini
[sshd]
enabled = true
filter = sshd
port = ssh
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
protocol = tcp
ignoreip = 127.0.0.1/8 ::1 203.0.113.55
ignoreself = true
usedns = no
backend = auto
banaction = nftables
action = %(action_)s
logpath = /var/log/apache2/*access.log
maxretry = 1
findtime = 1d
bantime = -1
bantime.increment = false
bantime.rndtime = 0

[apache-scanner-useragents]
enabled = true
filter = apache-scanner-useragents
port = http,https
protocol = tcp
ignoreip = 127.0.0.1/8 ::1 203.0.113.55
ignoreself = true
usedns = no
backend = auto
banaction = nftables
action = %(action_)s
logpath = /var/log/apache2/*access.log
maxretry = 1
findtime = 1d
bantime = -1
bantime.increment = false
bantime.rndtime = 0

[apache-scanburst]
enabled = true
filter = apache-scanburst
port = http,https
protocol = tcp
ignoreip = 127.0.0.1/8 ::1 203.0.113.55
ignoreself = true
usedns = no
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
bantime.overalljails = false

[apache-overflows]
enabled = true
filter = apache-overflows
port = http,https
protocol = tcp
ignoreip = 127.0.0.1/8 ::1 203.0.113.55
ignoreself = true
usedns = no
backend = auto
banaction = nftables
action = %(action_)s
logpath = /var/log/apache2/*error.log
maxretry = 2
findtime = 1d
bantime = -1
bantime.increment = false
bantime.rndtime = 0

[apache-shellshock]
enabled = true
filter = apache-shellshock
port = http,https
protocol = tcp
ignoreip = 127.0.0.1/8 ::1 203.0.113.55
ignoreself = true
usedns = no
backend = auto
banaction = nftables
action = %(action_)s
logpath = /var/log/apache2/*error.log
maxretry = 1
findtime = 1d
bantime = -1
bantime.increment = false
bantime.rndtime = 0

[recidive]
enabled = true
filter = recidive
logpath = /var/log/fail2ban.log
protocol = tcp,udp
ignoreip = 127.0.0.1/8 ::1 203.0.113.55
ignoreself = true
usedns = no
backend = auto
banaction = nftables[type=allports]
action = %(action_)s
maxretry = 3
findtime = 7d
bantime = -1
bantime.increment = false
bantime.rndtime = 0
```

Rechte:

```bash
sudo chown root:root /etc/fail2ban/jail.d/99-apache-moodle-bots.local
sudo chmod 0644 /etc/fail2ban/jail.d/99-apache-moodle-bots.local
```

---

## 9. Konfiguration testen

```bash
sudo fail2ban-client -t
```

Nur wenn dieser Befehl erfolgreich ist, weitermachen. Bei Fehlern nicht starten, sondern die gemeldete Datei korrigieren und erneut testen.

---

## 10. Dienst starten oder neu laden

```bash
sudo systemctl enable fail2ban
sudo systemctl restart fail2ban
sudo systemctl status fail2ban --no-pager
```

---

## 11. Status kontrollieren

Aktive Jails anzeigen:

```bash
sudo fail2ban-client status
```

Details pro Jail:

```bash
sudo fail2ban-client status sshd
sudo fail2ban-client status apache-malicious-paths
sudo fail2ban-client status apache-scanner-useragents
sudo fail2ban-client status apache-scanburst
sudo fail2ban-client status apache-overflows
sudo fail2ban-client status apache-shellshock
sudo fail2ban-client status recidive
```

Achte pro Jail auf:

```text
Currently banned
Total banned
File list
```

---

## 12. nftables prüfen

```bash
sudo nft list ruleset
```

Nach echten Treffern sollten Fail2Ban-Sets oder Regeln sichtbar sein. Einen Test-Ban nur in einem Wartungsfenster setzen.

---

## 13. Rollback

Wenn etwas schiefgeht:

```bash
sudo systemctl stop fail2ban
sudo rm -f \
  /etc/fail2ban/fail2ban.d/99-web-protection.local \
  /etc/fail2ban/filter.d/apache-malicious-paths.conf \
  /etc/fail2ban/filter.d/apache-scanner-useragents.conf \
  /etc/fail2ban/filter.d/apache-scanburst.conf \
  /etc/fail2ban/jail.d/99-apache-moodle-bots.local
sudo tar --extract --gzip \
  --file=/root/fail2ban-backup/fail2ban-before-web-protection.tar.gz \
  --directory=/
sudo fail2ban-client -t
sudo systemctl restart fail2ban
```

Wenn `fail2ban-client -t` nach dem Restore fehlschlägt, Dienst nicht starten und zuerst die gemeldete Datei prüfen.

---

## 14. Minimaler Notfallmodus

Wenn nur SSH sofort geschützt werden muss, lege vorübergehend nur dieses Jail an:

```ini
[sshd]
enabled = true
filter = sshd
backend = systemd
port = ssh
ignoreip = 127.0.0.1/8 ::1 203.0.113.55
banaction = nftables
maxretry = 5
findtime = 10m
bantime = 1h
```

Danach immer:

```bash
sudo fail2ban-client -t
sudo systemctl restart fail2ban
sudo fail2ban-client status sshd
```
