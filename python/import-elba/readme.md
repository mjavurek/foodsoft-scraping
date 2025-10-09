## ELBA Import

This is a workaround if https://github.com/bankproxy/bankproxy/blob/main/src/tasks/MeinElba.ts gets outdated due to changes in the data communication in the ELBA web bank interface.

### Voraussetzungen
- Zugriff aufs ELBA über Webbrowser am PC (nicht über Android Smartphone, Tablet o.ä.)
- Zugriff auf MySQL Datenbank der Foodsoft über myPhpAdmin (bei IGF anfordern)
- Firefox (oder Chrome?) Webbrowser
- Texteditor (Windows: Notepad, Notepad++; Apple: ...?; Linux: gedit, ...)
- Python Interpretor: https://www.python.org/downloads/ (Linux: bereits im System integriert)

### Beschreibung mit Bash-Skript unter Linux
`bash transaction` in einem Linux Terminal starten und den Anweisungen folgen.

### Beschreibung ohne Bash-Skript 
- Im Webbrowser (Firefox) ins ELBA einloggen und dabei *Extras > Browser-Werkzeuge > Werkzeuge für Web Entwickler* öffnen (Strg+Shift+I).
- Unter *Netzwerkanalyse* im Filterfeld (*Adressen durchsuchen*) ```kontou``` (für kontoumsaetze) eingeben
- Im rechten Kasten auf *Antwort* gehen, dort rechte Maustaste: alles kopieren.  Es ist egal, wenn auch Buchungen dabei sind, die schon in der Foodsoft vorhanden sind, weil später nur die neuen Buchungen vom Skript heraus gesucht werden.
<img width="1517" height="963" alt="grafik" src="https://github.com/user-attachments/assets/93d28b17-82e5-4821-8323-fe4730ca4953" />

- Ein neue Textdatei in einem Texteditor öffnen und den kopierten Text einfügen, Datei speichern unter ```Downloads/bank_transactions.json```
- In der MySQL Foodsoft Datenbank über phpMyAdmin auf die Tabelle ```bank_transactions``` gehen und dort exportieren als CSV in ```Downloads/bank_transactions.csv```
- ```python transactions.py``` in einem Terminal ausführen
- Falls neue Transaktionen vorhanden, in der MySQL Foodsoft Datenbank über phpMyAdmin in der Tabelle ```bank_transactions``` Import von ```Downloads/bank_transactions_import.csv``` durchführen.


