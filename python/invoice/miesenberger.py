# python miesenberger.py Downloads/RE000230_FRANCK_Kistl.pdf


import sys
import os
if len(sys.argv)==1:
    raise Exception("Als Argument muss der PDF Dateiname der Rechnung angegeben werden.") 
filename = sys.argv[1]
os.system("pdftotext -layout " + filename)

def replace_multiple(string, replace_items, separator=""):
    if isinstance(replace_items, list):
        replace_items = { key: "" for key in replace_items }
    for search,replace in replace_items.items():
        string = string.replace(separator+search+separator, separator+replace)
    return string

def is_item_in_str(items, string):
    if isinstance(items, str): items = [items]
    for item in items:
        if item in string: 
            return item
    return False

def _float(string):
    return float(string.replace(",","."))

with open(filename.replace(".pdf", ".txt")) as file:
    lines = [line.rstrip() for line in file]
excluded_lines = []
table = []
parsing = False
total = 0
for line in lines:
    if not line: continue
    if "Menge" in line: 
        parsing = True
        continue
    if is_item_in_str(["Miesenberger", "Zwischensumme"], line):
        parsing = False
    if "Rechnungsbetrag" in line: print("-"*100 + "\n" + line)
    if not parsing:
     
        continue
    print(line)
    
    line = line.replace("€- ", "€ -")
    items = line.split()
    # print(items)
    # ['15', 'Bio', 'Apfel', 'AT-BIO-401', '€', '3,30', '€', '49,50']
    article = dict(
        n = _float(items[0]),
        article_name = " ".join(items[1:-4]),
        price_per_unit = _float(items[-3]),
        price_total = _float(items[-1]),
    )
    table.append(";".join([str(v) for v in article.values()]))
    total += article["price_total"]
    
print("-"*100)
print("  gesamt verarbeitet: %.2f €" % total)
table = "\n".join(table)
print("---- CSV: ---")
print(table)

filename = filename.replace(".pdf", ".csv")
print("... writing to",filename)
with open(filename, mode='wt', encoding='utf-8') as file:
    file.write(table)
    
#print("--- übersprungene Zeilen: ---")
#print("\n".join(excluded_lines))

    
