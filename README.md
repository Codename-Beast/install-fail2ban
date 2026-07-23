# install_fail2ban

Ansible-Rolle für Debian/Ubuntu-Webserver. Sie installiert Fail2Ban, schützt SSH und typische Apache/Moodle-Angriffsflächen, prüft die Konfiguration und schaltet den Dienst erst danach aktiv.

Die Rolle ist absichtlich schlicht gehalten: klare Defaults, keine Magie, keine Änderungen an Apache, PHP, Moodle oder Reverse-Proxys.

---

## Schnellstart

Inventory anlegen:

```yaml
# inventory/hosts
fail2ban_targets:
  hosts:
    web01:
      ansible_host: 192.0.2.10
      ansible_user: root
```

Ausführen:

```bash
ansible-playbook -i inventory/hosts install_fail2ban.yml
```

Nutze die vorhandene zentrale Ansible-Konfiguration der Umgebung.

Weitere Inventories funktionieren genauso:

```bash
ansible-playbook -i prod install_fail2ban.yml
ansible-playbook -i hc-moodle install_fail2ban.yml
ansible-playbook -i . install_fail2ban.yml
```


Anderen Host oder Gruppe wählen:

```bash
ansible-playbook install_fail2ban.yml -i inventory/hosts -e hosts=web01
ansible-playbook install_fail2ban.yml -i inventory/hosts -e hosts=fail2ban_targets
```

Mehrere Hosts oder Gruppen gehen als Ansible-Pattern:

```bash
ansible-playbook install_fail2ban.yml -i inventory/hosts -e 'hosts=web01:web02'
ansible-playbook install_fail2ban.yml -i inventory/hosts -e 'hosts=web01,web02'
ansible-playbook install_fail2ban.yml -i hc-moodle -e 'hosts=moodle_web:&debian'
```

Zusatzargumente kommen einfach als weitere Extra-Vars dazu:

```bash
ansible-playbook install_fail2ban.yml -i inventory/hosts \
  -e hosts=hc-testmaschine \
  -e install_fail2ban_report_only=true

ansible-playbook install_fail2ban.yml -i prod \
  -e 'hosts=web01:web02' \
  -e install_fail2ban_exporter_enabled=true
```

Alternativ bleibt auch der nicht reservierte Variablenname möglich:

```bash
ansible-playbook install_fail2ban.yml -i inventory/hosts -e install_fail2ban_hosts=web01
```

Vorher prüfen:

```bash
ansible-playbook -i inventory/hosts install_fail2ban.yml --syntax-check
ansible-playbook -i inventory/hosts install_fail2ban.yml --check --diff
```

---

## Was die Rolle macht

- prüft Debian/Ubuntu und Ansible-Version
- bricht ab, wenn `nft` fehlt
- installiert `fail2ban`
- legt ein einmaliges Backup von `/etc/fail2ban` an
- installiert eigene Filter für Apache/Moodle-Scans
- rendert SSH-, Apache- und Recidive-Jails
- prüft die Fail2Ban-Konfiguration mit `fail2ban-client -t`
- bricht bei ungültiger Konfiguration mit stdout/stderr ab
- startet oder restartet Fail2Ban erst nach erfolgreicher Prüfung
- gibt danach Service-Status, aktive Jails und Ban-Zähler aus
- kann optional den Fail2Ban Prometheus Exporter installieren

---

## Anforderungen

| Thema | Erwartung |
|---|---|
| OS | Debian/Ubuntu |
| Ansible | ansible-core >= 2.12.10 |
| Firewall | nftables muss vorhanden sein |
| Logs | Apache-Dateilogs unter `/var/log/apache2` |
| SSH-Logs | nur systemd-journal |

`nftables` wird nicht automatisch installiert. Wenn `nft` fehlt, beendet die Rolle den Lauf vor Änderungen. Der optionale nftables-Whitelist-Import nutzt `nft -j list ruleset` und Ansible-Filter, keinen Inline-Python-Code.

SSH wird nur über systemd-journal ausgewertet. Es gibt keinen Datei-Log-Fallback.

---

## Aktive Jails

Standardmäßig aktiv:

- `sshd`
- `apache-malicious-paths`
- `apache-scanner-useragents`
- `apache-scanburst`
- `apache-overflows`
- `apache-shellshock`
- `recidive`

Optional vorbereitet, aber nicht automatisch aktiv:

- `apache-auth`
- `apache-badbots`
- `apache-botsearch`

Diese optionalen Jails sollten erst gegen echte Logs getestet werden.

---

## Whitelist

Loopback ist immer freigestellt:

```yaml
install_fail2ban_base_ignoreip:
  - 127.0.0.1/8
  - "::1"
```

Die gemeinsame VPN- oder Jump-Host-IP muss explizit rein. Sonst bricht die Rolle ab, solange `sshd` aktiv ist:

```yaml
install_fail2ban_trusted_ips:
  - 203.0.113.55        # gemeinsame VPN- oder Jump-Host-IP

install_fail2ban_allowed_ips:
  - 198.51.100.0/24     # weiteres Monitoring-Netz
```

Die Rolle schreibt die Whitelist je Jail als `ignoreip`. Dadurch werden fremde Fail2Ban-Jails nicht global verändert.

Wichtig: Fail2Ban sperrt IPs, keine SSH-Benutzer. Erfolgreiche SSH-Key-Logins werden vom `sshd`-Filter nicht gebannt. Damit eure gemeinsame VPN-IP trotzdem nie durch Fehlversuche blockiert wird, steht sie in `install_fail2ban_trusted_ips`.

Große Netze nur eintragen, wenn alle Quellen darin wirklich vertrauenswürdig sind.

---

## Whitelist aus nftables

Die Rolle kann IPs aus nftables-Sets übernehmen. Das ist ausgeschaltet und muss bewusst aktiviert werden:

```yaml
install_fail2ban_nft_whitelist_import_enabled: true
install_fail2ban_nft_whitelist_set_names:
  - monitoring_ips
  - management_ips
  - trusted_ips
  - fail2ban_ignore
```

Es werden nur Sets mit diesen Namen gelesen. Das ist wichtig, weil im nftables-Ruleset auch Blocklisten oder Fail2Ban-Ban-Sets stehen können.

Praktisch ist ein eigenes Set wie `fail2ban_ignore`.

---

## Scanner-User-Agents erweitern

Der Filter `apache-scanner-useragents` ist ein Template. Die Liste kann pro Umgebung ergänzt werden:

```yaml
install_fail2ban_scanner_useragents_extra:
  - CompanySecurityScanner
```

Wenn ein autorisierter Scanner trotz Treffer nicht gebannt werden soll:

```yaml
install_fail2ban_scanner_useragents_ignore:
  - CompanySecurityScanner
```

Die Einträge werden automatisch für Regex escaped. Generische Tools wie `curl`, `wget` oder `python-requests` sind nicht in der Standardliste.

---

## Wichtige Variablen

```yaml
install_fail2ban_sshd_enabled: true
install_fail2ban_sshd_port: ssh
install_fail2ban_sshd_backend: systemd
install_fail2ban_sshd_maxretry: 5
install_fail2ban_sshd_findtime: 10m
install_fail2ban_sshd_bantime: 1h

install_fail2ban_scanburst_maxretry: 80
install_fail2ban_scanburst_findtime: 5m
install_fail2ban_scanburst_bantime: 12h

install_fail2ban_recidive_maxretry: 3
install_fail2ban_recidive_findtime: 7d
install_fail2ban_recidive_bantime: -1
```

Optionales Apache-Auth-Jail:

```yaml
install_fail2ban_apache_auth_enabled: true
install_fail2ban_apache_auth_maxretry: 5
install_fail2ban_apache_auth_findtime: 10m
install_fail2ban_apache_auth_bantime: 1d
```

---

## Fail2Ban Prometheus Exporter

Optional kann die Rolle den offiziellen Fail2Ban Prometheus Exporter installieren:

https://gitlab.com/hctrdev/fail2ban-prometheus-exporter

```yaml
install_fail2ban_exporter_enabled: true
install_fail2ban_exporter_listen_address: "127.0.0.1:9191"
install_fail2ban_exporter_health_url: "http://127.0.0.1:9191/metrics"
```

Default ist bewusst localhost. Wenn Prometheus direkt von einem anderen Host scraped, entweder Reverse Proxy/Firewall sauber setzen oder die Adresse gezielt öffnen.

```yaml
install_fail2ban_exporter_listen_address: "0.0.0.0:9191"
```

Die Rolle legt dann an:

```text
/usr/local/bin/fail2ban_exporter
/etc/systemd/system/fail2ban-exporter.service
```

Metriken:

```text
f2b_up
f2b_jail_count
f2b_jail_banned_current{jail="sshd"}
f2b_jail_banned_total{jail="sshd"}
```

Der Exporter liest den Fail2Ban-Socket `/var/run/fail2ban/fail2ban.sock` und läuft erst nach `fail2ban.service`.

---

## Aktive Konfiguration nur auslesen

Für eine reine Bestandsaufnahme ohne Installation und ohne Dateischreibungen:

```bash
ansible-playbook -i inventory/hosts install_fail2ban.yml -e install_fail2ban_report_only=true
```

Dabei werden nur Statusdaten gelesen:

```text
Service state/status
Active jail count
Active jail list
Currently banned je Jail
Total banned je Jail
```

Danach beendet die Rolle den Host mit `meta: end_host`. Nach erfolgreicher Installation wird derselbe Bericht automatisch ausgegeben.

---

## Idempotenz

Die Rolle kann mehrfach laufen:

- Dateien werden nur geändert, wenn sich der Inhalt unterscheidet
- das initiale Backup wird nur einmal erstellt
- `fail2ban-client -t` läuft vor Start/Restart
- Restart passiert nur bei geänderter verwalteter Konfiguration


---

## Rollback

Die Rolle legt vor Änderungen optional ein Backup an:

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
  /etc/fail2ban/jail.d/99-apache-moodle-bots.local \
  /etc/systemd/system/fail2ban-exporter.service \
  /usr/local/bin/fail2ban_exporter

sudo tar --extract --gzip --file=/root/fail2ban-backup/fail2ban-YYYYMMDD-HHMMSS.tar.gz --directory=/
sudo fail2ban-client -t
sudo systemctl restart fail2ban
```

---

## Lokal geprüfte Versionen

- ansible-core 2.12.10
- ansible-core 2.21.2
- ansible-lint mit ansible-core 2.21.2 im Profil `shared`
