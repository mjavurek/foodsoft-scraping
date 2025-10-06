## ELBA Import

This is a workaround if https://github.com/bankproxy/bankproxy/blob/main/src/tasks/MeinElba.ts gets outdated due to changes in the data communication in the ELBA web bank interface.

Run `bash transaction` in a Linux terminal to get instructions.

Ergänzungen:
- Das Shell-Skript ```transactions``` muss nicht ausgeführt werden. Es geht auch, manuell die Zwischenablage mit den kopierten Bankdaten in die Datei ```banktransactions.json``` einzufügen und dann nur das Python Skript mit ```python transactions.py``` zu starten. Dazu die Beschreibung hier.

### Beschreibung ohne Bash-Skript 
- Im Webbrowser (Firefox) ins ELBA einloggen und dabei *Extras > Browser-Werkzeuge > Werkzeuge für Web Entwickler* öffnen (Strg+Shift+I).
- Unter *Netzwerkanalyse* im Filterfeld (*Adressen durchsuchen*) ```kontou``` (für kontoumsaetze) eingeben
- Im rechten Kasten auf *Antwort* gehen, dort rechte Maustaste: alles kopieren:
<img width="1517" height="963" alt="grafik" src="https://github.com/user-attachments/assets/93d28b17-82e5-4821-8323-fe4730ca4953" />

- Ein neue Textdatei in einem Texteditor öffnen und den kopierten Text einfügen, Datei speichern unter ```Downloads/bank_transactions.json```
- In der MySQL Foodsoft Datenbank über phpMyAdmin auf die Tabelle ```bank_transactions``` gehen und dort exportieren als CSV in ```Downloads/bank_transactions.csv```
- ```python transactions.py``` in einem Terminal ausführen
- Falls neue Transaktionen vorhanden, in der MySQL Foodsoft Datenbank über phpMyAdmin in der Tabelle ```bank_transactions``` Import von ```Downloads/bank_transactions_import.csv``` durchführen.


