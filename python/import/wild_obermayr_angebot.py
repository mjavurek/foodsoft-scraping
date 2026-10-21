import pandas as pd
import hashlib
import string
import re

xlsx = "Downloads/Frankkistl 2026.xlsx"
# sheets: ['Oktober-November2026', 'Pflanzen 2026', 'Säfte 2026']




piece_units = {
    "Zuckerhut": 0.7,
    "Chinakohl": 1.0,
    "Radicchio": 0.25,
    "Treviso": 0.5,
    "Schmelzkohlrabi": 0.5,
    "Frühkraut": 1.3,
    "Weißkraut/flach": 1.3,
    "Weißkraut/rund": 1.3,
    "Spitzkraut": 1.3,
    "Blaukraut": 1.3,
     #"Karfiol": 1.0,
     #"Karfiol bunt": 1.0,
     #"Romanesco": 1.0,
     #"Brokkoli": 0.5,
    "Zuckermelonen": 1.0,
    "Wassermelonen": 2.0,
    "Hokkaido": 1.3,
    "Butternuß": 1.3,
    "Crown prince": 1.3,
    "Longe de Nice": 1.3,
     # "Kiwano": 1.0,
    "Sellerie": 1.1,
} 

var_units ={
    "Herbstrübe": 0.5,
    "Kohlrübe": 0.5, 
    "Schwarzer Rettich": 0.5, 
    "Daikonrettich": 0.5, 
    "Knoblauch": 0.1,    
    "Mispeln": 0.5,  
}

name_changes = {
    "Treviso": "Radicchio di Treviso",
    "Bataten": "Süßkartoffel (Bataten)",
    "Gelbe Rüben": "Karotten gelb",
    "Bunte Karotten": "Karotten bunt",
    "Schnittsalat -mix" : "Schnittsalat-Mix",
}

add_prefix = {
    "Salat": ["Häuptelsalat", "Romanasalat", "Eissalat",
        "Batavia", "Lollo", "Eichblatt", "Endivie", "Zuckerhut"],
    "Tomaten": ["paradeiser"],
    "Pilze": ["Shitake", "seitling", "Champignon"],
    "Gurken": ["gurken"],
    "Zwiebel": ["zwiebel", "Schalotten"],
    "Kürbis": ["Patison", "Hokkaido", "Butternu", "Crown prince", "Longe de Nice"],
}

split_articles = {
    "Paprika grün,weiß, lila": {"base": "Paprika", "vars": ["grün", "weiß", "lila"]},
    "Grünkohl Grün/Rot": {"base": "Grünkohl", "vars": ["grün", "rot"]},
    # "template": {"base": "", "vars": ["", "", ""]}
}

categories = {
    "Gemüse": ["Erdäpfel"],
    "Pilze": ["Champignon", "seitling", "Shitake"],
    "Obst": ["Äpfel", 'Mispeln', 'Birnen', 'beeren', 'Kirschen', 'Kriecherl', 'Marillen', 
        'melone', 'Paw Paw', 'Pfirsich', 'Physalis', 'Quitten', 'Ribisel', 
        'Weichseln ', 'Weintrauben', 'Zwetschken'],
    "Ölsaaten": ["sonnenblumen"],
    "Kräuter": ["Basilikum", 'Bohnenkraut', 'Dill', 'Koriander', 
        'Liebstöckel', 'Petersiliengrün', 
        'Rosmarin', 'Schnittknoblauch', 'Schnittlauch', 'Thymian'], 
    "Nüsse": ["nüsse"],
    
}

ignore_articles = [
    "Erdäpfel",
]


def is_item_in_str(items, string, lowercase=False):
    if isinstance(items, str): items = [items]
    if lowercase: string = string.lower()
    for item in items:
        citem = item.lower() if lowercase else item
        if citem in string: 
            return item
    return False

def article_number(name, length=6, name_chars=2):
    name = name.strip().lower()

    # Generate a 64-bit hash
    value = int.from_bytes(
        hashlib.sha256(name.encode('utf-8')).digest()[:8],
        byteorder='big'
    )

    # Convert to base n
    chars = string.digits + string.ascii_uppercase + string.ascii_lowercase
    n = len(chars)

    result = ''
    while value:
        value, remainder = divmod(value, n)
        result = chars[remainder] + result
    
    #print(name, result, len(result))
    
    #return result.zfill(10)[-10:]
    # return result.zfill(length)[-length:]
    length -= name_chars
    return name[:name_chars].upper() + result.zfill(length)[-length:]

article_numbers = []
foodsoft_table = []
for sheet, cols in zip([0,0,1,2], ["B:D", "G:I", "A,C", "A,D,E,F"]):
    prefix = ""
    h=1
    skip_rows=0
    if sheet==0: # Gemüse
        names = ["unit", "name", "price"]
    elif sheet==1: # Pflanzen
        names=["name", "price"]
        category = "Pflanze"
        prefix = "Pflanze "
    elif sheet==2: # Säfte, Brot
        names=["name", "unit", "price", "status"]    
        h=None
        skip_rows=2
        

    d = pd.read_excel(xlsx, sheet_name=sheet, header=h, usecols=cols,
        names=names, skiprows=skip_rows) 
    price_set = None
    producer = ""        
    origin = ""
    for index, row in d.iterrows():
        outofstock = ""
        deposit = 0
        if sheet==0: # Gemüse
            unit = row["unit"]
            if not isinstance(unit, str): continue
            unit = unit.strip()
            unit = re.sub(r'(\d)g\b', r'\1 g', unit) # "500g" => "500 g"
            prefix = ""
        elif sheet==1: # Pflanzen
            unit = "Stück"
        elif sheet==2: # Säfte, Brot
            prefix = ""
            if not isinstance(row["unit"], str): 
                # print("--", row["name"])
                name = row["name"].strip() if isinstance(row["name"], str) else ""
                if "Brot" == name: 
                    category = "Brot"
                    continue
                elif "brot" in name: 
                    row["name"] = row["name"].replace("gerste","Gerste")
                    row["name"] = row["name"].replace("weizen","Weizen")
                    row["name"] = "Brot " + row["name"].replace("brot","")
                    # row["name"] = row["name"].replace("","")
                    pass
                else: 
                    continue
            else:
                unit = row["unit"].strip()
                unit = re.sub(r'(\d)Liter\b', r'\1 Liter', unit)
                if "Bio-Brote" in row["name"]:
                    # Bio-Brote von Strasser Barbara 			kg	€ 6,80
                    price_set = row["price"]
                    producer= row["name"]
                    continue 
            outofstock = row["status"] if isinstance(row["status"], str) else ""
            deposit = 0 if category=="Brot" else 0.50 
            # print(row["name"], outofstock!="", type(outofstock))
                       
        if price_set is None: 
            price = row["price"]
        else:
            price = price_set
            
        try:
            name = row["name"].strip()
        except:
            print(d)
            raise
        name = prefix + name
        if sheet==2: # Säfte, Brot
            name = name.replace("  ", " ")
            name = name.replace("-saft", "saft")
            name = name.replace("-most", "most")
            name = name.replace("-essig", "essig")
            name = name.replace("mit Sonnenblumenkörnern", "m. Sonnenblumk.")
            if "essig" in name: 
                category="Essig" 
            elif category!="Brot": 
                category = "Säfte, Getränke"
             
        #n = article_number(name)
        #article_numbers.append(n)

        if deposit>0: name += " inkl. %.0f ct Pfand" % (deposit*100)


        na =  (
            pd.isna(price) or 
            is_item_in_str(ignore_articles, name) or
            outofstock != ""
        )
        
        note = ""
        if name in piece_units or name in var_units:
            if unit.lower()!="kg": raise Exception(f"{name} Einheit {unit} != kg") 
            kg_per_piece = piece_units.get(name, var_units.get(name))
            price_per_kg = price
            #name = name + (" (%.2f €/kg)" % price).replace(".",",")
            note = ("%.2f €/kg" % price).replace(".",",")
            unit = (("Stück " if name in piece_units else "") + 
                ("%.0f g" % (kg_per_piece*1000)))
            price = price_per_kg * kg_per_piece
            if name in piece_units: name += "*"

        for s,r in name_changes.items():
            if s in name: name = r
              

        if unit.lower()=="kg": unit="1 kg"
        if unit.lower()=="stk": unit="Stück"
        if unit.lower()=="bd": unit="Bund"
        

        if sheet==0:
            for prefix,items in add_prefix.items():
                item = is_item_in_str(items, name, lowercase=True)
                if item:
                    name = prefix + " " + name
                    break                     
            category = "Gemüse"
            for c,items in categories.items():
                item = is_item_in_str(items, name, lowercase=True)
                if item:
                    # print(name, c)
                    category = c
                    break

        n = article_number(name)
        article_numbers.append(n)
        
        if name in split_articles:
            name_base = split_articles[name]["base"] + " "
            name_vars = split_articles[name]["vars"]
        else:
            name_base = name
            name_vars = [""]
        for i,name_var in enumerate(name_vars):
            fs_name = name_base + name_var
            if len(fs_name)>60:
                raise Exception(f"zu langer Name: {fs_name} {len(fs_name)}>60")
            foodsoft_article = {
                "Status":  "x" if na else "",
                "Bestellnummer":  n + ("%d"%i if len(name_vars)>1 else ""),
                "Name":  fs_name,
                "Notiz":  note,
                "Produzent":  producer,
                "Herkunft":  origin,
                "Einheit":  unit,
                "Nettopreis":  "%.2f" % (0 if na else price),
                "MwSt":  "0",
                "Pfand":  "%.2f" % deposit,
                "Gebindegröße":  "1",
                "(geschützt1)":  "",
                "(geschützt2)":  "",
                "Kategorie":  category,
            }
            foodsoft_table.append(";".join(foodsoft_article.values()))   

print("Bestellnummern gesamt:",len(article_numbers), "davon eindeutig;", len(set(article_numbers)))
if len(article_numbers) != len(set(article_numbers)):
    raise ValueError("Duplicate article numbers detected!")

foodsoft_table = (
    ";".join(foodsoft_article.keys()) + # Kopfzeile
    "\n" + "\n".join(foodsoft_table) # Artikel-Daten
)
print("---- import CSV: ---")
print(foodsoft_table)

filename = "wild-obermayr.csv"
print("... writing to",filename)
with open(filename, mode='wt', encoding='utf-8') as file:
    file.write(foodsoft_table)


