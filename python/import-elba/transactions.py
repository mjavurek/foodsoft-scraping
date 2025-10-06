# Diese Datei im Home-Verzeichnis ablegen
elba_transactions_file = "Downloads/bank_transactions.json"
database_export_file = "Downloads/bank_transactions.csv"
database_import_file = "Downloads/bank_transactions_import.csv"

import csv
import json

def quote(s):
    if s=="NULL": return s
    return '"'+s+'"'


print("--- lade", elba_transactions_file, "---------------------------")
with open(elba_transactions_file) as f:
    transactions = f.read()
transactions = json.loads(transactions)
for t in transactions[:5]:
   print(t,"\n")
print("   ...\n")

print("--- lade", database_export_file, "---------------------------")
with open(database_export_file) as f:
    fs_bank_transactions = [fst for fst in csv.reader(f, delimiter=",", quotechar='"')] 
keys = fs_bank_transactions[0]
index = {key:i for i,key in enumerate(keys)}
print(keys)
print(fs_bank_transactions[1])
print(fs_bank_transactions[2])
print("   ...")
print(fs_bank_transactions[-3])
print(fs_bank_transactions[-2])
print(fs_bank_transactions[-1])
print("------------------------------")

fs_ids = [t[index["external_id"]] for t in fs_bank_transactions]
last = fs_bank_transactions[-1]
ba_id = last[index["bank_account_id"]]
last_fs_id = int(last[index["id"]])

transactions_to_import = []
fs_id = last_fs_id + 1
for t in reversed(transactions):
    zr = "?"
    for key in ["zahlungsreferenz", "verwendungszweckZeile1"]:
        if key in t:
            zr = t[key]
            break
    text = t.get("transaktionsteilnehmerZeile1", "NULL")
    iban = t.get("auftraggeberIban", "NULL")
    betrag = t["betrag"]["amount"]
    if isinstance(betrag, dict):
        betrag = betrag["source"]
    betrag = float(betrag)
    transaction_str = " ".join(["%11s" % t["id"], t["buchungstag"], "%8.2f €" % betrag, zr, text])
    if t["id"] in fs_ids: 
        print("#", end="")
        print(transaction_str)
    else: 
        print(transaction_str) 
        transactions_to_import.append({
            "id": str(fs_id),
            "bank_account_id": ba_id,
            "external_id": t["id"],
            "date": t["buchungstag"],
            "amount": "%.2f" % betrag,
            "iban": iban,
            "reference": quote(zr),
            "text": quote(text),
            "receipt": "NULL",
            "financial_link_id": "NULL"
        })
        fs_id += 1        
print("------------------------------")
if len(transactions_to_import)==0:
    print("keine neuen Transaktionen.")
else:
    with open(database_import_file, "w") as f:
        for t in transactions_to_import:
            line = ",".join(t.values())
            print(line)
            # print("  ",t,"\n")
            f.write(line+"\n")
    print("zu importierende Bankdaten geschrieben in", database_import_file)    
  
