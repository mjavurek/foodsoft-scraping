# Biogast Text aus PDF für Google Tabelle
# aufbereiten.
# Mirko Javurek 2022-02

# Aufruf aus biogast bash-Skript oder mit TXT files der Auftragsbestätigung(en) als Argumente:
# python3.8 biogast.py Downloads/Auftragsbestaetigung_ZT_20241202_113006_023.txt

import sys

taxes = {"(1)": 0.1, "(2)": 0.2, "(13)": 0.13}
skip_lines_containing = ["Liefer", "Besorgung", "ACHTUNG", "Ursprung", "Summe"]
units = ["kg", "ml", "St", "g", "l"]
units_translation = {
    "2lg24/200" : {"number": 200,  "unit": "Stück", "circa": ""},
}
circa = ["c.", "ca.", "ca", "c"]

def skip_line(line):
    for s in skip_lines_containing: 
        if s in line: return True; break
    return False

def fnum(amount, fmt="%.1f"):
    return (fmt % amount).replace(".", ",")

def euro(amount):
    return fnum(amount, fmt="%.2f")

def col(i):
    return chr(ord('A') + i) 
       
def is_item_in_str(items, string):
    for item in items:
        if item in string: 
            return item
    return False
    
def find_first_number_position(s):
    for index, char in enumerate(s):
        if char.isdigit():
            return index  # Return the index of the first numeric character
    return -1  # Return -1 if no numeric characters are found

def split_num_unit(s, ca):
    index = find_first_number_position(s)
    s1 = s[:index]
    s2 = s[index:]
    result = dict(name="", number=0, unit="", circa=len(ca)>0)
    for ca in circa:
        index = s1.find(ca) 
        if index>=0 and index == len(s1) - len(ca): # ca muss am Ende von s1 sein
            result["circa"]=True
            break
    if not result["circa"]: result["name"] = s1

    factor = 1
    if "x" in s2:
        s = s2.split("x")
        factor = int(s[0])
        s2 = s[1]

    for unit in units:
        index = s2.find(unit)
        if index>0:
            try: 
                result["number"] = float(s2[:index].replace(",",".")) * factor
                result["unit"] = s2[index:]
                break
            except ValueError:
                continue
    return result

#umlaute = {"ˆ": "ö", "‰": "ä"}
umlaute = {"ˆ": "oe", "‰": "ae", "¸": "ue"}
hline = "-"*70
dhline = "="*70
colend = dict(H="\n", N="\n")

csv_filename = "biogast.csv"  # filename.replace(".txt",".csv")
nf = []
with open(csv_filename, "w") as fout:
    i = 0
    # for i,filename in enumerate(sys.argv[1:]):
    for j, filename in enumerate(sys.argv[1:]):
        print(f"\nDatei {j+1}: {filename}")
        print(dhline)
        with open(filename, "r") as f:
            lines = f.readlines()

        delivery = ""
        date = ""
        s = ""
        n_lines = 0
        paging = False
        for line in lines:
            for us, ur in umlaute.items():
                line = line.replace(us, ur)
            if "Lieferdatum" in line:
                date = line.split()[-1]
            if "Best.Nr" in line:
                delivery = line.split()[2]
                continue
            if "Übertrag" in line:
                paging = True
                continue
            if paging:
                if "Artikelbezeichnung" in line:
                    paging = False
                continue
            if delivery:
                # 301609 2.00 ST PLA Sennk‰se 200g BA bio 1.00 ST 2.450 4.90 (1)
                # 255203 1.00 ST BOM Heubauernk‰se ca.1,6kg BA bio 1.60 KG 15.230 24.37 (1)

                items = line.split()

                # for i, item in enumerate(items):
                #    print("  %d #%s#" % (i, item))
                # if len(items) == 1 and len(s) > 0 and not items[0].isnumeric():
                # print("<"+line+">")
                # print(
                #     f"len(s)={len(s)}, line[0]={line[0]} == ' ': {line[0] == ' '}")

                if len(s) > 0 and line[0] == " ":
                    if skip_line(line): continue
                    s += " ".join(items)  # Name BestellerIn(nen)
                if len(s) > 0:
                    #print(s+"\n")  # .replace("\t","#\n#"))
                    for j,d in enumerate(s.split("\t")):
                        c = col(j)
                        print("["+c+"]:", d, end=colend.get(c, "   "))
                    print("\n")
                    # print("--------------------")
                    fout.write(s+"\n")
                    s = ""
                if len(items) > 0 and items[0].isnumeric() and line[0] != ' ' and items[0] != '4030':
                    i += 1
                    n_lines += 1
                    number = items[0]
                    order_amount = float(items[1])
                    order_unit = items[2]
                    producer = items[3]
                    if items[-1][0] == "(": # Spalte USt: (1), ...
                        tax = taxes[items[-1]]
                        price_total = float(items[-2])
                        n = -3
                        if not items[n][0].isnumeric():
                            n -= 1
                        price = float(items[n])
                        content_unit = items[n-1]
                        content_amount = float(items[n-2])

                        # trenne Artikelbezeichnung und Gewichtsangabe, z.B.;
                        #  Camember.Nuß DD ca200g   DD bio
                        #  Altern. Sauerrahm 200g   C% bio
                        #  Tiroler Stangl c.1,6kg   BA bio
                        name = ""
                        ca = ""
                        r = dict(number=1, unit="", circa="")
                        for item in items[4:(n-2)]:
                            if item in circa:
                               ca = item
                               continue 
                            if item in units_translation:
                               r = units_translation[item]
                               name += " " + item
                               continue
                            if is_item_in_str(units, item): 
                               index = find_first_number_position(item)
                               if index>=0: #print("  ",index, item[:index], item[index:])
                                   r = split_num_unit(item, ca)
                                   if r["name"]:
                                       if name: name += " "
                                       name += r["name"]
                                   continue
                            if name: name += " "
                            name += item
                        #name = ";".join([name, "ca." if r["circa"] else "", fnum(r["number"], fmt="%g"), r["unit"]])
                        #print("   ", name)
                        amount = order_amount * content_amount
                    else:
                        tax = 0
                        price_total = 0
                        price = 0
                        content_unit = ""
                        content_amount = 0
                        name = " ".join(items[4:-1])
                        amount = 0

                    # print(f"{date} {delivery} {number}  {name} {price} €/{content_unit} {order_amount} {order_unit} x {content_amount} {content_unit}/{order_unit} {price_total} €")
                    s = (date +  # A
                         "\t".join(["",
                                   delivery,  # B
                                   str(i),  # C
                                   number,  # D
                                   fnum(order_amount),  # E
                                   order_unit,  # F
                                   fnum(content_amount, fmt="%g"), # G
                                   content_unit,  # H
                                   fnum(r["number"], fmt="%g"), # I
                                   r["unit"] + ("*" if r["circa"] else ""), # J
                                   producer,  # K
                                   name,  # L
                                   euro(price),  # M
                                   '=INDIREKT("M"&ZEILE()) *  INDIREKT("R"&ZEILE())',  # N
                                   "%.0f%%" % (tax*100),  # O 
                                   '=INDIREKT("N"&ZEILE()) * (1 + INDIREKT("O"&ZEILE()))', # P
                                   fnum(amount, fmt="%g"),  # Q
                                   fnum(amount, fmt="%g"),  # R
                                   ""])) 
        nf.append(n_lines)
print("Zeilen pro File: " + ",".join(map(str, nf))+" gesamt: "+str(sum(nf)))
