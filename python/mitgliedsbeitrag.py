# ------------------------------------------------------------------------------------
#
#    Foodsoft Daten zu Mitgliedsbeiträgen auslesen und darstellen
#
#    2024-12 Mirko Javurek
#
# ------------------------------------------------------------------------------------

import foodsoft_login_data_mirko as foodsoft_login
import foodsoft as fs
from foodsoft import negative_red

foodsoft = fs.FSConnector(login=foodsoft_login)

# Liste aller Mitglieder mit Beiträgen
members = foodsoft.get_ordergroups_csv()

# Kontostand aller Mitglieder
accounts = foodsoft.get_ordergroup_accounts()
for id in members:
    members[id].update(accounts[id])

# Kontotransaktionen: Überweisungen für Guthaben Mitgliedsbeitrag
transactions = foodsoft.get_transactions(n=3000)
for transaction in transactions:
    if transaction["Kontotransaktionstyp"]=="Überweisung Mitgliedsbeitrag":
        id = transaction["Id"]
        members[id].setdefault("Überweisungen", {})[transaction["Datum"]] = transaction["Guthaben Mitgliedsbeitrag"]

foodsoft.logout()

# Daten darstellen
for id, m in members.items():
    b = m["Mitgliedsbeitrag"]
    print("%-30s" % m["Name"], 
        negative_red("%6.2f", m['Guthaben Mitgliedsbeitrag']), 
        "%3.0f" % b if b<0 else "- 0", "=>", 
        negative_red("%6.2f", m['Guthaben Mitgliedsbeitrag'] + m["Mitgliedsbeitrag"], positive_green=True))
    for date,amount in m.get("Überweisungen", {}).items():
        print("  ",date[:10],"%5.2f" % amount)
