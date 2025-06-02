# python miesenberger.py Downloads/RE000230_FRANCK_Kistl.pdf


import sys
import os
if len(sys.argv)==1:
    raise Exception("Als Argument muss der PDF oder TXT Dateiname der Rechnung angegeben werden.") 
filename = sys.argv[1]
if ".pdf" in filename:
    print("Konvertiere PDF in TXT:", filename)
    os.system("pdftotext -layout " + filename)
    filename = filename.replace(".pdf", ".txt")

# Miesenberger: ['15', 'Bio', 'Apfel', 'AT-BIO-401', '€', '3,30', '€', '49,50']
pos = {"amount": 0, "name-start": 1, "name-end": -4, "price-per-unit": -3,  "price": -1}

if "FRAN" in filename:
    # Lang:         
    # 4,00 Liter           Rohmilch                                                1,30     13,00           5,20
    pos = {"amount": 0, "unit": 1, "name-start": 2, "name-end": -3, "price-per-unit": -3, "tax": -2, "price": -1}
    print("Lang Rechnung:", filename)
else
    print("Miesenberger Rechnung:", filename)


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

with open(filename) as file:
    lines = [line.rstrip() for line in file]
excluded_lines = []
table = []
parsing = False
total = 0
for line in lines:
    #print(is_item_in_str(["Menge", "Einheiten"], line), line)
    if not line: continue
    if is_item_in_str(["Menge", "Einheiten"], line): 
        parsing = True
        continue
    if is_item_in_str(["Miesenberger", "Zwischensumme"], line):
        parsing = False
    if is_item_in_str(["Rechnungsbetrag", "Nettowarenwert"],  line): 
        print("-"*100 + "\n" + line)
        if "Nettowarenwert" in line: parsing = False
    if not parsing: 
        continue
    print(line)
    
    line = line.replace("€- ", "€ -")
    line = replace_multiple(line, {
        " ml Glas": "_ml_Glas",
        })
    items = line.split()
    #print(items)
    if items[0] == "0,00": continue

    article = dict(
        n = _float(items[pos["amount"]]),
        unit = items[pos["unit"]] if "unit" in pos else "",
        article_name = " ".join(items[pos["name-start"]:pos["name-end"]]),
        price_per_unit = _float(items[pos["price-per-unit"]]),
        price_total = _float(items[pos["price"]]),
        tax = _float(items[pos["tax"]] if "tax" in pos else "")/100,
    )
    table.append(";".join([str(v) for v in article.values()]))
    total += article["price_total"]
    
print("-"*100)
print("  gesamt verarbeitet: %.2f €" % total)
table = "\n".join(table)
print("---- CSV: ---")
print(table)

filename = filename.replace(".txt", ".csv")
print("... writing to",filename)
with open(filename, mode='wt', encoding='utf-8') as file:
    file.write(table)
    
#print("--- übersprungene Zeilen: ---")
#print("\n".join(excluded_lines))

    
