year_and_months = {2024: [1,2,3, 4,5,6]}

import os

month_names = ["Jänner", "Februar", "März", "April", "Mai", "Juni", 
    "Juli", "August", "September", "Oktober", "November", "Dezember"]

for year, months in year_and_months.items(): 
    for month in months:
        month_name = month_names[month-1]
        print(f"=== {month_name} {year} ===============================================================")
        filename=f'Downloads/Franckkistl {month_name} {year}.txt'
        if not os.path.isfile(filename):
            cmd = f"pdftotext -layout '"+filename.replace(".txt", ".PDF")+"'"
            print("executing:", cmd)
            os.system(cmd)
        with open(filename) as file: # 'latin-1', encoding='utf-8'
            lines = [line.rstrip() for line in file]
        articles = {}
        total = 0
        for line in lines:
            items = line.split()
            if len(items)==0: continue
            if items[0]=="KW":
                week = items[1]
                if article["name"] in articles:
                    while week in articles[article["name"]]:
                        week+="*" # manchmal mehrfach gleiche Artikelnamen für Artikel mit unterschiedlichem 
                        # kg-Preis in der selben KW; z.B. Kohl (Kopf) und Kohl (Palmkohl) 
                    articles[article["name"]][week] = article
                else:
                    articles[article["name"]] = {week: article}
            #articles.setdefault(article["name"], {})[week] = article
            
            n = len(items)
            if n<6: continue
            if items[0] in ["Pos", 'wildobermayr@gmx.at', 'Rechnung', 'Alle', 'Wir', 'Die','Zahlungskondition:', 'Bankverbindung:']: continue
            
            article = dict(
            	pos = items[0],
            	name = " ".join(items[1:n-4]),
            	amount = float(items[n-4].replace(",",".")),
            	unit = items[n-3], # Einheit von "amount"
            	price_per_unit = float(items[n-2].replace(",",".")),
            	price = float(items[n-1].replace(",",".")) # = amount * price_per_unit
            )
            total += article["price"]
            #print(n, items, "\n  ", article)

        for view in ["summary", "details"]:
            articles = dict(sorted(articles.items()))
            total_a = 0
            for article,deliveries in articles.items():
                if view=="details": print(article)
                price_sum = 0
                for week,delivery in deliveries.items():
                    if view=="details": print("  ", week, delivery)
                    price_sum += delivery["price"]
                if view=="details": print("  ", "%.2f €" % price_sum)    
                if view=="summary": print(article+"\t"+"%.2f" % price_sum)
                total_a += price_sum    
            print("gesamt:", "%.2f" % total, "%.2f" % total_a)
            print(f"--- {month_name} {year} --------------------------------------------------------------------")
        print("\n\n")

