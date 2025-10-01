import csv
import json

NULL = ""

def quote(s):
    if s=="NULL": return s
    return '"'+s+'"'


filename = "bank_transactions.json"
print("--- lade", filename, "---------------------------")
with open(filename) as f:
    transactions = f.read()
transactions = json.loads(transactions)
for t in transactions[:5]:
   print(t,"\n")
print("   ...\n")

filename = "Downloads/bank_transactions.csv"
print("--- lade", filename, "---------------------------")
with open(filename) as f:
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
    if t["id"] in fs_ids: 
        print("#", end="")
        print("%11s" % t["id"], t["buchungstag"],"%8.2f €" % t["betrag"]["amount"], zr, text)
    else: 
        print("%11s" % t["id"], t["buchungstag"],"%8.2f €" % t["betrag"]["amount"], zr, text) 
        transactions_to_import.append({
            "id": str(fs_id),
            "bank_account_id": ba_id,
            "external_id": t["id"],
            "date": t["buchungstag"],
            "amount": str(t["betrag"]["amount"]),
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
    filename = "Downloads/bank_transactions_import.csv"
    with open(filename, "w") as f:
        for t in transactions_to_import:
            line = ",".join(t.values())
            print(line)
            # print("  ",t,"\n")
            f.write(line+"\n")
    print("zu importierende Bankdaten geschrieben in", filename)    
  
