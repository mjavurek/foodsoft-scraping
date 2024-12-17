filename='Downloads/Angebotsliste 2024-10 LIEFERUNG OÖ.txt'
# pdftotext -layout Angebotsliste\ 2024-08\ LIEFERUNG\ OÖ.pdf

categories = { # Foodsoft-Kategorien aus Überschriften der Liste
  "BIO-WEISSWEINE": "Weisswein", 
  "BIO-ROTWEINE": "Rotwein",
  "BIO-SCHAUMWEINE, BIO-SEKT": "Sekt und Prosecco",
  "BIO-SÄFTE": "Säfte, Getränke",
  "ORANGE-WEIN": "Weisswein",
  "VINOTHEKWEINE": "Weisswein",
  }
  
category_exceptions = { # Ausnahmen für Kategorien: Ausnahmeregel nur anwenden, wenn "exclude" nicht in der Artikelbezeichnung vorkommt
  "Grüner Veltliner": {"category": "Weisswein"}, 
  "Zweigelt": {"category": "Rotwein", "exclude": "Weißer"},
  "Rosé": {"category": "Rosé-Wein", "exclude": "Biosecco"},
}

exclude = ["Karton", "pfand"] # Zeilen, die € Zeichen enthalten, aber keine Artikel sind
exclude_small_cat = ["Sekt und Prosecco", "Säfte, Getränke"] # kleine Gebinde in diesen Kategorien ausschließen

producer_deposits = {1.0: 0.10} # Produzent*innen-Pfand 10 Cent auf 1 Liter Flaschen
no_deposit_categories = ["Sekt und Prosecco"] # kein FC Pfand in diesen Kategorien
no_deposit_names = ["Origin"] # kein FC Pfand wenn einer dieser Begriffe in der Artikelbezeichnung vorkommt

replace_in_line = {
    "1l":    "1 l",
    "0,75l": "0,75 l",
}
delete_from_name = ["QW", "SW", "W", "LW", "RW"] # diese Kürzel nicht übernehmen

max_name_len = 60 
shortcuts = { # Abkürzen falls Artikelbezeichnung sonst zu lange wäre (> max_name_len)
   "Weinviertel": "Weinv.", 
   "vom" : "v.",
}

# aus foodsoft > Artikel hochladen
foodsoft_columns = "Status 	Bestellnummer 	Name 	Notiz 	Produzent 	Herkunft 	Einheit 	Nettopreis 	MwSt 	Pfand 	Gebindegröße 	(geschützt1) 	(geschützt2) 	Kategorie".split("\t")
#for c in foodsoft_columns: # generiere Python-Code für dictionary 
#    print(f'        "{c.strip()}":  article[""],')

fc_discount = 0.1 # 10 % Rabatt für FC

def replace_multiple(string, replace_items, separator=""):
    if isinstance(replace_items, list):
        replace_items = { key: "" for key in replace_items }
    for search,replace in replace_items.items():
        string = string.replace(separator+search+separator, separator+replace)
    return string

def is_item_in_str(items, string):
    for item in items:
        if item in string: 
            return item
    return False


with open(filename) as file:
    lines = [line.rstrip() for line in file]
category = ""
foodsoft_table = []
excluded_articles = []
excluded_lines = []
for line in lines:

    # get artile categories from headings
    is_heading = False
    for key,cat in categories.items():
    	if key in line:
            category = cat
            is_heading = True
            break
    if is_heading: continue
    this_category = category
    for key,cat in category_exceptions.items():
        if key in line:
           if "exclude" in cat:
               if cat["exclude"] in line: continue
           this_category = cat["category"]            
    
    # filter articles
    if not "€" in line or is_item_in_str(exclude, line): 
        if len(line)>0: excluded_lines.append(line)
        continue    
    
    # correct text
    line = replace_multiple(line, replace_in_line)
    
    # decompose line into single items
    s = line.split()
    if not "l" in s: # e.g. ..., "0,75", "l", ...
        print(s)
        raise Exception("'l' nicht als eigenes Wort gefunden: "+line)

    # get article details
    article = dict(
        category = this_category,
        name = " ".join(s[:s.index("l")-1]),        
        description = " ".join(s[s.index("l")+1 : -2]),
        volume = float(s[s.index("l")-1].replace(",",".")),
        price = float(s[-1].replace(",",".")),
        deposit = 0.50,
    )
    
    if (this_category in no_deposit_categories or 
        is_item_in_str(no_deposit_names, article["name"])): 
        article["deposit"] = 0
        
    producer_deposit = producer_deposits.get(article["volume"], 0)
    article["price-foodcoop"] = (article["price"] - producer_deposit) * (1 - fc_discount)
    
    if article["volume"]<0.4 and this_category in exclude_small_cat: 
        excluded_articles.append(article)
        continue
    
    # add deposit info to article name (otherwise not visible for foodsoft users)
    foodsoft_name = article["name"]
    if article["deposit"]>0:
        #foodsoft_name += " %4.2f€ Pfand" % article["deposit"]
        foodsoft_name += " %2.0fct Pfand" % (100*article["deposit"])
    else:
        foodsoft_name += " Einwegflasche"
    foodsoft_name = replace_multiple(foodsoft_name, delete_from_name, separator=" ")
    if len(foodsoft_name)>max_name_len:
       foodsoft_name = replace_multiple(foodsoft_name, shortcuts)
 
    print(len(foodsoft_name), "%-20s" % (this_category+":"), "%-60s" % foodsoft_name, 
          "| %5.2f €" % article["price"], "=>", 
          "%5.2f €" % (article["price-foodcoop"]),
          "%5.2f €" % (article["price-foodcoop"] + article["deposit"]),
          article["volume"],"L", 
          "Prd.Pfand: %4.2f €" %  producer_deposit if producer_deposit else "",
          article["description"]) 
 
    # prepare import table for foodsoft
    foodsoft_article = {
        "Status":  "",
        "Bestellnummer":  "",
        "Name":  foodsoft_name,
        "Notiz":  article["description"],
        "Produzent":  "BIO-Weingut HuM Hofer",
        "Herkunft":  "AT Weinviertel",
        "Einheit":  ("%g" % article["volume"]).replace(".",",")+" l",
        "Nettopreis":  "%g" % article["price-foodcoop"],
        "MwSt":  "0",
        "Pfand":  "%g" % article["deposit"],
        "Gebindegröße":  "1",
        "(geschützt1)":  "",
        "(geschützt2)":  "",
        "Kategorie":  article["category"],
    }
    foodsoft_table.append(";".join(foodsoft_article.values()))    

foodsoft_table = "\n".join(foodsoft_table)
print("---- import CSV: ---")
print(foodsoft_table)

filename = "hofer.csv"
print("... writing to",filename)
with open(filename, mode='wt', encoding='utf-8') as file:
    file.write(foodsoft_table)
    
print("--- übersprungene Zeilen: ---")
print("\n".join(excluded_lines))

print("--- ausgeschlossene Artikel: ---")
for a in excluded_articles:
    print(a)    
    
