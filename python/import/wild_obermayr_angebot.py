import pandas as pd
import hashlib
import string
import re

debug = False


# --- producer specific settings

xlsx = "Downloads/Frankkistl 2026.xlsx"
# sheets: ['Oktober-November2026', 'Pflanzen 2026', 'Säfte 2026']

# change unit from 1 kg to "Stück" with specified weight in kg
piece_units = { # key must fit full original article name (before name_changes are applied and prefix is added) 
    "Zuckerhut": 0.7,
    "Chinakohl": 1.0,
    "Radicchio": 0.5,
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

# change unit from 1 kg to specified weight in kg
var_units = { # key must fit full original article name (before name_changes are applied and prefix is added)
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
    "Gelbe Zwiebeln": "Zwiebeln gelb",
    "Rote Zwiebeln": "Zwiebeln rot",
    "Schalottenzw.": "Zwiebeln Schalotten",
    "Gemüsezwiebeln": "Zwiebeln Gemüsezwiebeln",
    "Pepino": "Pepino Melonenbirne",
    "Weißkraut/flach": "Weißkraut flach",
    "Weißkraut/rund": "Weißkraut rund",
}

add_prefix = { # if any of the list strings is found in the article name, add prefix to name
    "Salat": ["Häuptelsalat", "Romanasalat", "Eissalat",
        "Batavia", "Lollo", "Eichblatt", "Endivie", "Zuckerhut", "Chinakohl"],
    "Tomaten": ["paradeiser"],
    "Pilze": ["Shitake", "seitling", "Champignon"],
    "Gurken": ["gurken"],
    #"Zwiebel": ["zwiebel", "Schalotten"], # moved to name_changes
    "Kürbis": ["Patison", "Hokkaido", "Butternu", "Crown prince", "Longe de Nice"],
}

split_articles = { # split article with variants to individual articles
    "Paprika grün,weiß, lila": {"base": "Paprika", "vars": ["grün", "weiß", "lila"]},
    "Grünkohl Grün/Rot": {"base": "Grünkohl", "vars": ["grün", "rot"]},
    "Pfefferoni": {"base": "Pfefferoni", "vars": ["mild", "scharf"]},
    # "template": {"base": "", "vars": ["", "", ""]},
}

categories = { # if any of the list strings is found in the article name, apply category specified in key
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

notes = { # if key is found in article name, add note to article
    "Gemüsezwiebel":  "etwas süß, kann roh gegessen werden",
    "Pimientos de Padron": "kleine grüne Paprika",
}

ignore_articles = [ # if any of the strings is found in the article name, make it unavailable
    "Erdäpfel",
]



# --- helper functions ----

def is_item_in_str(items, string, lowercase=False):
    if isinstance(items, str): items = [items]
    if lowercase: string = string.lower()
    for item in items:
        citem = item.lower() if lowercase else item
        if citem in string: 
            return item
    return False


def article_number(name, length=6, name_chars=2):
    # generate an order number for the article based on its name with length characters
    # use first name_chars of the name for the first order number characters 
    # so that articles appear in alphabetical order in order lists
    # test if order numbers are unique has to be performed after all numbers were generated
    # increase length if this test fails?
    
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
    
    length -= name_chars
    return name[:name_chars].upper() + result.zfill(length)[-length:]


def str_join(s1, s2):
    return s1 + (" " if s1 and s2 else "") + s2


def weight_str(weight_in_kg):
    if weight_in_kg < 1.0:
        return "%.0f g" % (weight_in_kg*1000)
    else:
        return ("%g kg" % (weight_in_kg)).replace(".",",")
        
        
        
# --- import Excel sheet data and save CSV table --------

article_numbers = []
foodsoft_table = []
for sheet, cols in [
    [0, "B:D"], # Gemüse Spalte 1
    [0, "G:I"], # Gemüse Spalte 2
    [1, "A,C"], # Pflanzen
    [2, "A,D,E,F"],  # Säfte, Brot
]:
    header = 1 # row number of row headers, row counting starts with 0; set to None of table has no headers
    skip_rows = 0 # number of rows to be skipped before data starts, only to be set if header is None
    price_set = None # für Artikel, wo der Preis nur einmal vorab und nicht einzeln bei jedem Artikel angegeben ist, z.B. Brote
    # wenn price_set auf eine Zahl gesetzt wird, wird für den Artikelpreis dieser Wert verwendet statt row["price"]. 
    prefix = "" # wird dem Artikelnamen vorangestellt
    producer = ""        
    
    if sheet==0: # Gemüse
        row_names = ["unit", "name", "price"]
    
    elif sheet==1: # Pflanzen
        row_names = ["name", "price"]
        category = "Pflanze"
        prefix = "Pflanze "
    
    elif sheet==2: # Säfte, Brot
        row_names = ["name", "unit", "price", "status"]    
        header = None
        skip_rows = 2
        
    d = pd.read_excel(xlsx, sheet_name=sheet, header=header, usecols=cols,
        names=row_names, skiprows=skip_rows) 
    
    # --- loop over rows in table ---
    for index, row in d.iterrows():
        note = "" 
        origin = ""
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
            if isinstance(row["unit"], str): 
                unit = row["unit"].strip()
                unit = re.sub(r'(\d)Liter\b', r'\1 Liter', unit)
                if "Bio-Brote" in row["name"]:
                    # Bio-Brote von Strasser Barbara 			kg	€ 6,80
                    price_set = row["price"]
                    producer = row["name"].strip()
                    continue             
            else: # no unit specified
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

            outofstock = row["status"] if isinstance(row["status"], str) else ""
            deposit =  0.50 if category!="Brot" else 0 

        # --- end of sheet-specific actions ---------------------------------- 
                       
        # --- article price ---
        if price_set is None: 
            price = row["price"]
        else:
            price = price_set
            
        
        # --- article name ---
        try:
            name = row["name"].strip()
        except:
            # if row["name"] is unexpectedly empty, its type is float and applying .strip() raises an error
            print(d) # helps debugging: show whole imported table data
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
             
        # add deposit to article name as it is not displayed in the foodsoft order form for ordergroups
        if deposit>0: name += " inkl. %.0f ct Pfand" % (deposit*100)

        # --- article not available? ---
        if not debug:
            not_available =  (
                pd.isna(price) or 
                is_item_in_str(ignore_articles, name) or
                outofstock != ""
            )
        else: # debug: show conditions why article is not available
            not_available = ""
            if pd.isna(price): not_available += "x-noprice "
            if is_item_in_str(ignore_articles, name): not_available += "x-ignore "
            if outofstock != "": not_available += "x-" + outofstock
        
        # --- article unit ---
        has_piece_unit = name in piece_units
        has_var_unit = name in var_units
        if has_piece_unit or has_var_unit:
            if unit.lower()!="kg": raise Exception(f"{name} Einheit {unit} != kg") 
            kg_per_piece = piece_units.get(name, var_units.get(name))
            price_per_kg = price
            #name = name + (" (%.2f €/kg)" % price).replace(".",",")  # moved to note 
            note = ("%.2f €/kg" % price).replace(".",",")
            unit = (("Stück " if has_piece_unit else "") + weight_str(kg_per_piece))
            price = price_per_kg * kg_per_piece              
        if unit.lower()=="kg": unit="1 kg"
        if unit.lower()=="stk": unit="Stück"
        if unit.lower()=="bd": unit="Bund"

        # --- article name changes ----
        for s,r in name_changes.items():
            if s in name: name = r

        # --- article name add prefix, set article category ---
        if sheet==0: # Gemüse
            for prefix,items in add_prefix.items():
                item = is_item_in_str(items, name, lowercase=True)
                if item:
                    name = prefix + " " + name
                    break                     
            category = "Gemüse" # set default 
            for c,items in categories.items():
                item = is_item_in_str(items, name, lowercase=True)
                if item:
                    category = c
                    break

        # --- generate article order number from article name ---
        n = article_number(name)
        article_numbers.append(n)
        
        # --- article note ---
        for note_key, note_text in notes.items():
            if note_key in name:
                note = str_join(note_text, note)
                break
        
        # --- split article in different variants ---
        if name in split_articles:
            name_base = split_articles[name]["base"] + " "
            name_vars = split_articles[name]["vars"]
        else:
            name_base = name
            name_vars = [""]
        
        # --- prepare CSV table row(s) for article/article variants
        for i,name_var in enumerate(name_vars):
            fs_name = name_base + name_var 
            if has_piece_unit: fs_name += "*"
            if len(fs_name)>60:
                raise Exception(f"zu langer Name: {fs_name} {len(fs_name)}>60")
            foodsoft_article = {
                "Status": ("x" if not_available else "") if not debug else not_available,
                "Bestellnummer":  n + ("%d"%i if len(name_vars)>1 else ""),
                "Name":  fs_name,
                "Notiz":  note,
                "Produzent":  producer,
                "Herkunft":  origin,
                "Einheit":  unit,
                "Nettopreis":  "%.2f" % (0 if not_available else price),
                "MwSt":  "0",
                "Pfand":  "%.2f" % deposit,
                "Gebindegröße":  "1",
                "(geschützt1)":  "",
                "(geschützt2)":  "",
                "Kategorie":  category,
            }
            foodsoft_table.append(";".join(foodsoft_article.values()))   
        # end for variants of article
    # end for row in sheet
# end for sheet in Excel-file-sheets

# --- ensure unique article numbers ---
print("Bestellnummern gesamt:",len(article_numbers), "davon eindeutig;", len(set(article_numbers)))
if len(article_numbers) != len(set(article_numbers)):
    raise ValueError("Duplicate article numbers detected!")

# --- export article CSV table ---
foodsoft_table = (
    ";".join(foodsoft_article.keys()) + # Kopfzeile
    "\n" + "\n".join(foodsoft_table) # Artikel-Daten
)
print("---- CSV for foodsoft import ---")
print(foodsoft_table)

filename = "wild-obermayr.csv"
print("... writing to",filename)
with open(filename, mode='wt', encoding='utf-8') as file:
    file.write(foodsoft_table)
