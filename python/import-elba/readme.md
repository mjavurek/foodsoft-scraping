## ELBA Import

This is a workaround if https://github.com/bankproxy/bankproxy/blob/main/src/tasks/MeinElba.ts gets outdated due to changes in the data communication in the ELBA web bank interface.

Run `bash transaction` in a Linux terminal to get instructions.

Ergänzungen:
- Das Shell-Skript ```transactions``` muss nicht ausgeführt werden. Es geht auch, manuell die Zwischenablage mit den kopierten Bankdaten in die Datei ```banktransactions.json``` einzufügen und dann nur das Python Skript mit ```python transactions.py``` zu starten.
- Es geht auch (besser?), vor dem Kopieren der Bankdaten nicht auf "unformatiert" umzustellen, und dann mit rechte Maustaste "alles Kopieren" auszuwählen
