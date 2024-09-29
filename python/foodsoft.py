# This should work as an object API to connect with foodsoft and
# work with it.

# pip3 install beautifulsoup4
# pip3 install fuzzywuzzy
# pip3 install python-Levenshtein

from json import dumps
import logging
import requests
import os
import re
from bs4 import BeautifulSoup as bs

import datetime
# import csv

from fuzzywuzzy import fuzz
from functools import partial

# import pickle
import balance

# logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.WARN)


def _float(s):
    if s is None:
        return 0
    else:
        s = s.strip().split(" ")[0]
        if "," in s:  # s.find(",")>=0:
            s = s.replace(".", "")
        return float(s.replace(',', '.'))


def _find_similar_article(name, articles):
    f = partial(fuzz.partial_ratio, name)
    g = {a: f(a) for a in articles}
    k = max(g, key=g.get)
    return k, g[k]


# ---------------------------------------------------------------------------------------------


class FSConnector:
    def __init__(self, url, user=None, password=None):
        self._session = None
        self._url = url  
        self._url_login_request = url + 'login'
        self._url_login_post = url + 'sessions'

        self._default_header = {
            'Host': 'app.foodcoops.at',
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:69.0) Gecko/20100101 Firefox/69.0',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Upgrade-Insecure-Requests': '1',
            'Accept': 'text/html', # if not specified, for some pages like fincance/.../bank_transcations GET endd up with 422 Unprocessable Entity 
            # ActionController::InvalidCrossOriginRequest (Security warning: an embedded <script> tag on another site requested protected JavaScript. If you know what you're doing, go ahead and disable forgery protection on this action to permit cross-origin JavaScript embedding.)
        }
        if "localhost" in self._url:
            self._default_header['Host'] = "localhost:3000"

        self._login_data = {
            "utf8": "✓",
            'commit': 'Anmelden'
        }

        if user and password:
            self.login(user, password)

    def _get_url(self, href):
        # '/franckkistl/stock_articles/1318' ==> https://app.foodcoops.at/franckkistl/stock_articles/1318
        return self._url + "/".join(href.split("/")[2:])

    def _get(self, url, header, data=None):
        if data is None:
            response = self._session.get(url, headers=header)
        if response.status_code != 200:
            self._session.close()
            logging.error('ERROR ' + str(response.status_code) +
                          ' during GET ' + url)
            raise ConnectionError('Cannot get: ' + url)

        return response

    def _get_auth_token(self, request_content):
        if request_content is None:
            logging.error('ERROR failed to fetch authenticity_token')
            return ''
        return bs(request_content, 'html.parser').find(attrs={'name': 'authenticity_token'})['value']

    def _post(self, url, header, data, request):
        data['authenticity_token'] = self._get_auth_token(request.content)
        response = self._session.post(
            url, headers=header, data=data, cookies=request.cookies)
        if response.status_code != 200:  # 302
            logging.error('Error ' + str(response.status_code) +
                          ' during POST ' + url)
            raise ConnectionError('Error cannot post to ' + url)

        return response

    def login(self, user, password):
        self._user = user
        self._login_data['nick'] = user
        self._login_data['password'] = password

        login_header = self._default_header

        self._session = requests.Session()
        print("login get", self._url_login_request,)
        request = self._get(self._url_login_request, login_header)

        print("login post", self._url_login_post)
        login_header['Referer'] = self._url_login_request
        response = self._post(self._url_login_post,
                              login_header, self._login_data, request)
        logging.debug(user + ' logged in sucessfully to ' + self._url)
        print(user + ' logged in sucessfully to ' + self._url)

    def logout(self):
        self._session.close()

    def _complete_url(self, url):
        if url[0]=="/":
            url_split = url.split("/")
            url = "/".join(url_split[2:])  # remove foodcoop name in link
        if not "http" in url:
            url = self._url + url
        return url

    def get_page(self, url, url_from_page=False):
        """ 
        url format for e.g. https://app.foodcoops.at/demo/finance/balancing
          default: "finance/balancing" or "https://app.foodcoops.at/demo/finance/balancing"
          url_from_page=True: "/demo/finance/balancing"
        """
        self.url = self._complete_url(url)
        print("get", self.url)
        self.response = self._get(self.url, self._default_header)
        decoded_content = self.response.content.decode('utf-8')
        page = bs(decoded_content, 'html.parser')    
        self.csrf_token=page.find("meta", attrs={"name":"csrf-token"})["content"]
        print("csrf-token:", self.csrf_token)
        return page

    def get_articles_CSV(self, supplier_id):
        response = self._get(self._url + 'suppliers/' +
                             str(supplier_id) + "/articles.csv", self._default_header)
        decoded_content = response.content.decode('utf-8')
        return decoded_content

    def patch(self, url, data):
        url = self._complete_url(url)
        headers = self._default_header
        headers['Referer'] = self.url
        headers["X-CSRF-Token"] = self.csrf_token
        print("POST", url, data)
        print("referer:", self.url) #, self.response.cookies)
        #print("headers:", self.response.headers)
        response = self._session.post(
            url, headers=headers, data=data, cookies=self.response.cookies)
    
        if response.status_code != 200:  # 302
            logging.error('Error ' + str(response.status_code) +
                          ' during PATCH ' + url)
            raise ConnectionError('Error cannot PATCH to ' + url)

        return response

# ==== suppliers =========================================================================================

    def get_suppliers(self, deliveries=False, suspend_limit_days=9999999):
        suppliers = []
        suspended = []
        suspended_filename = "suspended-suppliers.txt"
        if suspend_limit_days == "use_saved":
            with open(suspended_filename, "r") as f:
                suspended = f.read().splitlines()
        page = self.get_page("suppliers")
        for tr in page.table.tbody.find_all("tr"):
            supplier = {}
            td = tr.find_all("td")
            # 0 <td><a href="/franckkistl/suppliers/81">Schafkäse Biohof </a></td>
            # 1 <td>0777/12345</td>
            # 2 <td></td>
            # 3 <td><a href="/franckkistl/suppliers/81/articles">Artikel (13)</a></td>
            # 4 <td><a href="/franckkistl/stock_articles">im Lager (0)</a></td>
            # 5 <td><a href="/franckkistl/suppliers/81/deliveries">Lieferungen (0)</a></td>
            # 6 <td>
            #   <a class="btn btn-mini" href="/franckkistl/suppliers/81/edit">Bearbeiten</a>
            #   <a data-confirm="Achtung, willst Du wirklich den Lieferanten Schafkäse Biohof  löschen?" class="btn btn-mini btn-danger" rel="nofollow" data-method="delete" href="/franckkistl/suppliers/81">Löschen</a>
            # </td>

            supplier["name"] = td[0].a.string
            supplier["href"] = td[0].a.get('href')
            supplier["n-articles"] = int(td[3].a.string.split("(")
                                         [1].split(")")[0])
            supplier["articles-href"] = td[3].a.get('href')
            supplier["n-stock-articles"] = int(
                td[4].a.string.split("(")[1].split(")")[0])
            supplier["n-deliveries"] = int(
                td[5].a.string.split("(")[1].split(")")[0])
            supplier["deliveries-href"] = td[5].a.get('href')
            # print(supplier)
            if deliveries and supplier["n-deliveries"] > 0 and not supplier["name"] in suspended:
                supplier["deliveries"] = self.get_deliveries(
                    supplier["deliveries-href"])
                last_delivery_date = supplier["deliveries"][0]["date"]
                days_ago = (datetime.datetime.now() -
                            last_delivery_date).total_seconds()/24/60/60
                # print(
                #    f'{supplier["deliveries"][0]["date-str"]} ' +
                #    f'vor {days_ago:.0f} Tagen: '
                #    f'{supplier["name"]} Datum der letzten Lieferung')
                supplier["last-delivery-days-ago"] = days_ago
                if isinstance(suspend_limit_days, int) and days_ago > suspend_limit_days:
                    suspended.append(supplier["name"])
            else:
                supplier["deliveries"] = None
                supplier["last-delivery-days-ago"] = None
            suppliers.append(supplier)
        if len(suspended) > 0:
            with open(suspended_filename, "w") as f:
                for s in suspended:
                    f.write(s+"\n")
        return suppliers, suspended


    def get_deliveries(self, href):
        # print(href)
        deliveries = []
        page = self.get_page(href, url_from_page=True)
        for tr in page.table.tbody.find_all("tr"):
            delivery = {}
            td = tr.find_all("td")
            # 0 <td>2022-02-10</td>
            # 1 <td class='numeric'><a title="Rechnung anzeigen" href="/franckkistl/finance/invoices/2275">113,00 € </a></td>
            #   <td class='numeric'><a class="btn btn-mini"      href="/demo/finance/invoices/new?delivery_id=6&amp;supplier_id=5">Rechnung anlegen</a></td>
            # 2 <td>note</td>
            # 3 <td>
            #     <a class="btn btn-mini" href="/franckkistl/suppliers/72/deliveries/328">Anzeigen</a>
            #     <a class="btn btn-mini" href="/franckkistl/suppliers/72/deliveries/328/edit">Bearbeiten</a>
            #     <a data-confirm="Bist Du sicher?" class="btn btn-mini btn-danger" rel="nofollow" data-method="delete" href="/franckkistl/suppliers/72/deliveries/328">Löschen</a>
            #  </td>
            delivery["date-str"] = td[0].string
            delivery["date"] = datetime.datetime.strptime(
                td[0].string, "%Y-%m-%d")
            delivery["href"] = td[3].a.get('href')            
            href = td[1].a.get('href')
            if "new?" in href:
                delivery["invoice-href"] = ""
                delivery["invoice-id"] = None
                delivery["invoice-amount"] = self.get_delivery(delivery["href"])[0] # 0 -> netto summe
            else:
                delivery["invoice-href"] = href
                delivery["invoice-id"] = href.split("/")[-1]
                delivery["invoice-amount"] = _float(td[1].a.string)
            delivery["note"] = td[2].string

            deliveries.append(delivery)
        return deliveries


    def get_delivery(self, href):
        page = self.get_page(href, url_from_page=True)
        # for tr in page.table.tbody.find_all("tr"):
        #     for td in tr.find_all("td"):
        #         print(td.string, end=" ")
        #     print()
        # print("---")
        # Alkoholfrei 0,3 (inkl 50ct Pfand) 0,33l 24 0,80 €  19,20 €  
        # ---
        # Nettosumme 443,64 €  
        # Bruttosumme 669,64 €  
        tr = page.table.tfoot.find_all("tr")
        sum_net = _float(tr[0].find_all("td")[1].string)
        sum_gross =  _float(tr[1].find_all("td")[1].string)
        return sum_net, sum_gross 

    def delivery_balance(self, begin_datetime):
        suppliers, suspended = self.get_suppliers(
            deliveries=True, suspend_limit_days="use_saved")
        unpaid = 0
        without_invoice = 0
        for s in suppliers:
            if s["last-delivery-days-ago"] and s["last-delivery-days-ago"] > 0:
                # print(s["name"])
                for d in s["deliveries"]:
                    if d["date"] < begin_datetime:
                        continue
                    if d["invoice-id"] is None:
                        without_invoice += 1
                        print(
                            f"  {s['name']}  {d['date-str']} {d['invoice-amount']:7.2f} € netto: keine Rechnung angelegt!")
                        unpaid += d['invoice-amount']
                    else:
                        invoice = self.get_invoice(d['invoice-id'])
                        if invoice['Bezahlt am'] is None:
                            unpaid += invoice['Betrag']
                            print(
                                f"  {s['name']}  {d['date-str']} {d['invoice-id']} {invoice['Betrag']:7.2f} € unbezahlt!")
                        # print(
                        #    f"  {d['date-str']} {d['invoice-id']} {invoice['Betrag']:7.2f} €, bezahlt am: {invoice['Bezahlt am']}")
                # print("")
        print(f"unbezahlte Rechnungen: {unpaid:.2f} €")
        print(f"{without_invoice} Lieferung(en) ohne Rechnung.")
        return unpaid, without_invoice, suppliers


# ==== stock =========================================================================================


    def get_stock_articles(self, numeric=True, href_abs=False):
        page = self.get_page("stock_articles")
        # <table class='table table-hover' id='articles'>
        table = page.find("table", id='articles')
        column_name = [th.string for th in table.thead.tr.find_all("th")]
        articles = {}
        total_cash_value = 0
        for tr in table.tbody.find_all("tr"):
            for i, td in enumerate(tr.find_all("td")):
                if i == 0:
                    name = td.a.string
                    href = td.a.get('href')
                    if href_abs:
                        href = self._get_url(href)
                    articles[name] = {"href": href}
                elif column_name[i]:
                    if numeric and column_name[i] in ['im Lager', 'Davon bestellt', 'Verfügbar']:
                        value = int(td.string)
                    elif numeric and column_name[i] in ['Nettopreis']:
                        value = float(td.string)
                    elif column_name[i] == "MwSt":
                        value = float(td.string.split()[0])/100
                    else:    # 'Lieferantin', 'Kategorie'
                        value = td.string
                    articles[name][column_name[i]] = value
            #print(name, articles[name])
            total_cash_value += articles[name]["im Lager"] * \
                articles[name]["Nettopreis"] * (1 + articles[name]["MwSt"])
        return articles, total_cash_value

    def export_stock_articles(self, filename="stock_articles.csv"):
        articles, total_cash_value = self.get_stock_articles(
            numeric=True, href_abs=True)
        print_header = True
        with open(filename, "w") as output_file:
            for a in articles:
                if print_header:
                    output_file.write(
                        "Artikel;"+";".join([d for d in articles[a]])+";Wert\n")
                    print_header = False
                # im Lager 	Davon bestellt 	Verfügbar 	Einheit 	Nettopreis 	MwSt
                article = articles[a]
                value = article["im Lager"] * \
                    article["Nettopreis"] * (1 + article["MwSt"])
                output_file.write(
                    a+";"+";".join([str(articles[a][d]) for d in articles[a]]) + ";"+str(value)+"\n")

    def get_stock_taking(self, tid, numeric=True, articles=None, min_similarity=60):
        # taking = Inventur
        if articles == "get":
            articles, total_cash_value = self.get_stock_articles()
        page = self.get_page("stock_takings/"+str(tid))
        # <div class='well well-small'>
        # <dl class='dl-horizontal'>
        # <dt>Datum</dt>
        # <dd>06.12.2021</dd>
        dd = page.find("dl").dd
        date = dd.string
        note = dd.find_next("dd").p.get_text(" ").replace("\n", "")
        table = page.find("table")
        column_name = [th.string for th in table.tr.find_all("th")]
        # print(date, column_name)
        taking = {}
        name = None
        costs = 0
        for tr in table.find_all("tr"):
            for i, td in enumerate(tr.find_all("td")):
                if i == 0:
                    name = td.string
                    taking[name] = {}
                else:
                    if numeric and column_name[i] in ['Menge']:
                        value = int(td.string)
                    else:    # 'MwSt', 'Lieferantin', 'Kategorie'
                        value = td.string
                    taking[name][column_name[i]] = value
            if name:
                if articles and numeric:
                    if name in articles:
                        article_name = name
                        similarity = 999
                    else:
                        article_name, similarity = _find_similar_article(
                            name, articles)
                        print("  "+str(taking[name]["Menge"])+" x " + taking[name]["Einheit"] + " '"+name +
                              "' in der aktuellen Lagerartikelliste nicht gefunden. " +
                              "Ähnlichster Name " + "(%d)" % similarity +
                              " '"+article_name+"' um " + "%.2f €" % articles[article_name]["Nettopreis"])
                    if similarity > 60:
                        price = articles[article_name]["Nettopreis"] * \
                            taking[name]["Menge"]
                        taking[name]["Euro"] = price
                        costs -= price  # price>0: Gewinn, price<0 Verlust für FC
                    else:
                        print(
                            "  *** Ähnlichkeit zu gering (<%d), Artikel nicht berücksichtigt!" % min_similarity)
                # print(name, taking[name])
        print("Inventur "+str(tid)+" vom "+date +
              " Kosten: " + "%.2f €" % costs + " -- "+note)
        return costs, taking

    def export_stock_taking(self, tid, verbose=True, filename=""):
        if filename:
            write_mode = "a"
        else:
            filename = "Inventur%06d.csv" % tid
            write_mode = "w"
        if verbose:
            print(
                f"schreibe Inventurbilanz in Datei {filename} ({write_mode})...")
        with open(filename, write_mode) as output_file:
            costs, taking = self.get_stock_taking(tid, articles="get")
            print_header = True
            for a in taking:
                if print_header:
                    output_file.write(
                        "Artikel;" + ";".join([d for d in taking[a]])+"\n")
                    print_header = False
                output_file.write(
                    a+";"+";".join([str(taking[a][d]) for d in taking[a]])+"\n")

    def export_stock_takings(self, max_takings=5):
        # print("Hole Inventurdaten aus der Foodsoft...")
        per_page = 20
        page = self.get_page("stock_takings?per_page="+str(per_page))
        tbody = page.find("tbody")
        tids = []
        for i, tr in enumerate(tbody.find_all("tr")):
            if i < max_takings:
                td = tr.find_all("td")
                tid = int(td[0].a.get("href").split("/")[-1])
                tids.append(tid)
                date = td[0].a.string
                note = td[1].string.replace("\n", " ")
                print(f"  Inventur {i+1} (ID {tid}) vom {date} ({note})")
                # costs, taking = fsc.get_stock_taking(
                #    tid, articles=articles, min_similarity=60)
                # s += costs
        print("Für welche Inventur(en) soll eine Bilanz erstellt werden?")
        print("Mehrere mit , trennen (z.B: 1,2,4):")
        t_index_str = input("> ")
        t_selected = t_index_str.split(",")
        filename = "Inventur.csv"
        with open(filename, "w") as output_file:
            output_file.write("")  # delete content
        for i_str in t_selected:
            if not i_str.isnumeric():
                continue
            i = int(i_str)
            tid = tids[i-1]
            print(f"Bilanz zu Inventur ID {tid} wird geschrieben...")
            self.export_stock_taking(tid, filename=filename)

    def print_stock_taking_balance(self, per_page=20, max_takings=5):
        page = self.get_page("stock_takings?per_page="+str(per_page))
        tbody = page.find("tbody")
        articles, value = self.get_stock_articles()
        s = 0
        tids = []
        for i, tr in enumerate(tbody.find_all("tr")):
            if i < max_takings:
                td = tr.find_all("td")
                tid = int(td[0].a.get("href").split("/")[-1])
                tids.append(tid)
                date = td[0].a.string
                note = td[1].string.replace("\n", " ")
                # print(f"  Inventur {i+1} vom {date} ({note})")
                costs, taking = self.get_stock_taking(
                    tid, articles=articles, min_similarity=60)
                s += costs
        print("Total: %.2f €" % s)


# ==== orders =========================================================================================


    def get_order(self, url=None, id=None, verbose=True, articles=None, tax=0):
        if id is None:
            order = self.get_page(url, url_from_page=True)
        else:
            order = self.get_page("finance/balancing/new?order_id=" + str(id))
        # Rechnung bearbeiten
        invoice = order.find("a", string="Rechnung bearbeiten")
        if invoice is None:
            invoice = 0
        else:
            # <a href="/franckkistl/finance/invoices/2242/edit">Rechnung bearbeiten</a>
            invoice = int(invoice.get('href').split("/")[-2]) # invoice-id
        table_body = order.find("tbody", id='result_table')
        deposit_sum = 0
        transport_fees = 0
        price_sum = 0
        if verbose:
            print("   ---------------------------------------------------------")
        for table_row in table_body.find_all('tr'):
            id = table_row.get('id')
            classes = table_row.get('class')
            if id is None:
                td = table_row.find_all('td')
                if len(td) == 3 and td[0].string == "Transportkosten":
                    transport_fees = _float(
                        td[1].string.split()[0])  # "6,60 €" 
                    if verbose:
                        print("  ", td[0].string, ": ",  transport_fees)
            else:
                if "results" in classes:  # and "group" in id
                    # evaluation per order-group is here
                    # print(id)
                    td = table_row.find_all('td')
                    # print(td[0].prettify())
                    ordergroups = {}
                    for tr in td[0].table.tbody.find_all('tr'):
                        # print(tr['class'])
                        # ordergroup.append(tr.find_all('td')[1].string.strip())
                        tds = tr.find_all('td')
                        # 0 <td></td>
                        # 1 <td style='width:50%'>Danie Jansesberger</td>
                        # 2 <td class='center'>
                        #     <form class="simple_form delta-input" id="edit_group_order_article_1568946" data-submit-onchange="changed" action="/franckkistl/group_order_articles/1568946" accept-charset="UTF-8" data-remote="true" method="post">
                        #        ...<input> ...
                        #        <input class="delta optional input-nano" data-min="0" data-delta="1" id="r_1568946" value="0,46" type="text" autocomplete="off" name="group_order_article[result]" /><button name="delta" type="button" value="1" data-increment="r_1568946" tabindex="-1" class="btn"><i class="icon icon-plus"></i></button></div></form></td>
                        ordergroup = tds[1].string.strip()
                        # Bestellung schon abgerechnet, keine Formular zum Ändern mehr
                        if tds[2].form is None:
                            received = _float(tds[2].string)
                        else:
                            received = _float(tds[2].form.find(
                                "input", class_="delta").get("value"))
                        ordergroups[ordergroup] = received
                    # print(", ".join(ordergroups))
                    print("          "+str(ordergroups))
                    if articles:
                        articles[name]["groups"][articles["i"]] = ordergroups
                elif "order_article" in classes:
                    td = table_row.find_all('td')
                    name = str(td[0].a.string)  # article name is a link
                    # article_nr =  int(td[1].string) #  Bestellnummer
                    # 2  Bestellt, 1.46  Geliefert  ODER  5  Bestellt
                    ordered = int(td[2].get('title').split()[0])
                    received = _float(td[2].string)  # Menge
                    unit = td[3].string  # Einheit
                    unit_num = re.findall(r'\d+', unit)
                    unit_num = int(unit_num[0]) if len(unit_num) > 0 else 1
                    prices = td[4].string.split("/")  # td[4]: Netto
                    # prices = td[5].string.split("/") # Brutto pro Stück/gesamt: "4,40 / 8,80"
                    price_single = _float(prices[0])
                    price_total = _float(prices[1])
                    # td[6]: MwSt
                    deposit = _float(td[7].string)  # Pfand
                    deposit_sum += received*deposit
                    price_total -= received*deposit  # price includes deposit
                    if verbose:
                        print("   %5.2f " % received + " (%d) " % ordered + name + " | " + unit +
                              " %.2f " % ((price_single-deposit)/(1+tax)) + " exkl. %.0f %%" % (tax*100) +
                              ":  %.2f" % price_total + " + " + "%.2f " % (received*deposit))
                    price_sum += price_total
                    if articles:
                        if not name in articles:
                            n = len(articles["empty"])
                            articles[name] = {"price": price_single, "unit": unit_num,
                                              "ordered": [0] * n, "received": [0] * n, "groups": [{}] * n}
                        articles[name]["ordered"][articles["i"]] = ordered
                        articles[name]["received"][articles["i"]] = received
        if verbose:
            print("   ---------------------------------------------------------")
            print("   total price without deposit: %7.2f" % price_sum)
            print("   total deposit:               %7.2f" % deposit_sum)
            print("   transport fees:              %7.2f" % transport_fees)
        if articles:
            articles["deposit"][articles["i"]] = deposit_sum
        return price_sum, deposit_sum, transport_fees, invoice

    def export_orders(self, begin_date=None, per_page=20, producer_selected=[], producer_excluded=[],
                      filename="", only_id=None, start_page=1):
        format = "%d.%m.%Y %H:%M"
        if not begin_date is None:
            begin_datetime = datetime.datetime.strptime(
                begin_date+" 00:00", format)
        if len(filename) == 0:
            filename = "orders-{date:%Y-%m-%d_%H:%M:%S}.csv".format(
                date=datetime.datetime.now())
        warning_message = ""
        order_after_begin = True
        page_number = start_page
        with open(filename, "w") as output_file:
            output_file.write(";".join(["Datum", "ID", "Lieferantin", "Status", "Summe exkl. Pfand", "Pfand", "Transportkosten",
                                        "Rechnung Nr.", "Rechnung Datum", "Rechnung Betrag", "Rechnung bezahlt am", "Status", "Rechnungs-ID"]) + "\n")
            while order_after_begin:
                # ... finance/balancing?page=2&per_page=20 ...
                print("------------------- page %d ---------------" %
                      page_number)
                order_page = self.get_page(
                    "finance/balancing?page="+str(page_number)+"&per_page="+str(per_page))
                page_number += 1
                for order_tr in order_page.tbody.find_all('tr'):
                    order_td = order_tr.find_all('td')

                    order_date = order_td[1].string
                    order_datetime = datetime.datetime.strptime(
                        order_date, format)
                    if begin_date is None:
                        order_after_begin = True
                    else:
                        order_after_begin = order_datetime > begin_datetime
                    if not order_after_begin:
                        continue

                    order_producer_name = order_td[0].a.string.strip()
                    if producer_selected and not order_producer_name in producer_selected: continue
                    if order_producer_name in producer_excluded: continue

                    order_href = order_td[0].a.get('href')
                    if order_href is None: continue

                    order_id = int(order_href.split("=")[1])
                    if only_id and not order_id == only_id: continue

                    # "abgerechnet (...)": Bilanzsummer in Klammer nicht anzeigen weil falsch wenn Rechnung über mehrere Bestellungen
                    order_status = order_td[2].string.split("(")[0]
                    order_status_num = 1 if "abgerechnet" in order_status else 0
                    print("===", page_number, order_href, order_date,
                          order_after_begin, order_producer_name, order_status)

                    # if ((not order_href is None) and order_after_begin and
                    #    (not producer_selected or order_producer_name in producer_selected) and
                    #    (not order_producer_name in producer_excluded)):

                    price_sum, deposit_sum, transport_fees, invoice = self.get_order(
                        url=order_href)
                    if invoice:
                        d = self.get_invoice(invoice)
                        invoice_number = d["Nummer"]
                        if invoice_number is None:
                            invoice_number = "--"
                            warning_message += f"Rechnung {invoice} hat keine Rechnungsnummer.\n"
                        invoice_date = d["Rechnungsdatum"]
                        if invoice_date is None:
                            invoice_date = "####-##-##"
                            warning_message += f"Rechnung {invoice} hat kein Rechnungsdatum.\n"
                            #raise Exception(f"Rechnung https://app.foodcoops.at/franckkistl/finance/invoices/{invoice} hat kein Datum! ")
                        invoice_paid_date = d["Bezahlt am"]
                        invoice_amount = "%.2f" % d["Betrag"]
                        if invoice_paid_date is None:
                            invoice_paid_date = ""
                    else:
                        invoice_number = ""
                        invoice_date = ""
                        invoice_paid_date = ""
                        invoice_amount = ""
                    order_status_num += 2 if invoice_number else 0
                    order_status_num += 4 if invoice_paid_date else 0
                    output_file.write(";".join([
                        order_date,  # 0
                        str(order_id),  # 1
                        order_producer_name,  # 2
                        order_status,  # 3
                        "%.2f" % price_sum,  # 4
                        "%.2f" % deposit_sum,  # 5
                        "%.2f" % transport_fees,  # 6
                        invoice_number,  # 7
                        invoice_date,  # 8
                        invoice_amount,  # 9
                        invoice_paid_date,  # 10
                        str(order_status_num),  # 11
                        str(invoice), # 12
                    ]) + "\n")
                if begin_date is None:
                    order_after_begin = False
        print(warning_message)
        return filename

        # order status num:
        # order_status_num = 1 if "abgerechnet" in order_status else 0
        # order_status_num += 2 if invoice_number else 0
        # order_status_num += 4 if invoice_paid_date else 0
        # unbalanced cases:
        #  1: abgerechnet & !invoice_paid_date -- except Lager, Leergut
        #  6: !abgerechnet & invoice_paid

    def get_my_orders(self, n_pages=5,  only_producer=""):
        for i in range(1, n_pages+1):
            print("=== page",i,"===")
            orders = self.get_page("group_orders/archive?page=" + str(i))
            #print(orders.find_all("h2"))
            #orders = orders.find("h2", string="abgerechnet")
            #print(len(orders.find_all("tbody")))
            for tr in orders.find_all("tbody")[1].find_all("tr"):
                td = tr.find_all("td")
                producer = td[0].string
                date = td[2].string
                amount = td[3].string
                if only_producer and only_producer in producer:  #len(td)>=4:
                    if not amount=="--":
                        href = td[0].a.get('href')
                        print(producer, date, amount, href)
                        order = self.get_page(href, url_from_page=True)
                        for tr in order.find_all("tr", class_="success"):
                            #if "category" in tr.get("class"): continue
                            td = tr.find_all("td")
                            #print([s.contents[0].strip() for s in td])
                            #print(" ".join([s.string for s in td]))
                            article_name = td[0].contents[0].strip()
                            article_unit = td[1].contents[0].strip()
                            article_price_pu = float(td[2].contents[0].replace(",",".").replace("€","").strip())
                            article_ordered = td[3].contents[0].strip()
                            article_received = float(td[4].contents[0].strip())
                            article_price_total = float(td[5].contents[0].replace(",",".").replace("€","").strip())
                            print(" ", article_received, article_name, article_unit)


# ==== invoices =========================================================================================

    def get_invoice(self, invoice_id):
        if invoice_id:
            invoice_page = self.get_page("finance/invoices/"+str(invoice_id))
            d = {"Nummer": invoice_page.h1.string.split(" ")[1]}
            # <dt>Erstellt am:</dt>
            # <dd>30.11.2021 18:05</dd>
            # ...
            for dt in invoice_page.find_all("dt"):
                label = dt.string[:-1]  # cut ":"
                value = dt.find_next_sibling("dd")
                #print(f"  {label=} {value=}")
                if label == "Bestellung":
                    value = [ 
                        dict(
                            url = a.get('href'),
                            date = a.string,
                            id = a.get('href').split("=")[-1],
                        ) for a in value.find_all("a")]
                elif label == "Lager-Lieferung":
                    value = [
                        dict(
                            url = a.get('href'),
                            date = a.string,
                            supplier_id = a.get('href').split("/")[-3],
                            delivery_id = a.get('href').split("/")[-1],
                        )
                        for a in value.find_all("a")]
                elif label == "Anhang":
                    value = dict(url = value.a.get('href'), name=list(value.a.strings)[-1].strip())
                elif label == "Finanzlink":
                    value = value.a.get('href')
                elif label in ["Betrag", "Pfand berechnet", "Pfand gutgeschrieben", "Pfandbereinigter Betrag", "Total"]:
                    value = _float(value.string)  # 236,70 € 
                else:
                    value = value.string
                    if value: value = value.strip()
                d[label] = value
            return d
        else:
            return None

    def export_invoice_orders(self, invoice_id, tax=0):
        invoice = self.get_invoice(invoice_id)
        number = invoice["Nummer"].replace(" ", "").replace("/", "-")
        producer = invoice["Lieferant"]
        producer_words = producer.split(" ")
        producer_short = producer_words[0]
        order_links = invoice["Bestellung-Links"]
        date_list = invoice["Bestellung-Datum"]
        zeros = [0.] * len(order_links)
        article_list = {"empty": zeros.copy(), "deposit": zeros.copy()}
        price_sum = 0
        deposit_sum = 0
        transport_fees_sum = 0
        for i, href in enumerate(order_links):
            article_list["i"] = i
            print("  ", href, date_list[i])
            price, deposit, transport_fees, invoice = self.get_order(
                url=href, articles=article_list, tax=tax)
            price_sum += price
            deposit_sum += deposit
            transport_fees_sum += transport_fees
        for key in ("empty", "i"):
            article_list.pop(key)  # delete items
        print(article_list)
        print("===================================================================")
        print("total price: %.2f €" % price_sum)
        print("total deposit: %.2f €" % deposit_sum)
        print("total transport fees: %.2f €" % transport_fees_sum)
        with open("invoice_"+producer_short+"_"+number+"_orders.csv", "w") as output_file:
            orders = ";".join(date_list)
            output_file.write(";".join(
                ["Artikel", "Einheit (num.)", "Preis", orders, "Stück gesamt", "Preis gesamt"]) + "\n")
            for name in article_list:
                if name not in ["deposit"]:
                    # print(article_list[name]["ordered"])
                    orders = ";".join(
                        ["%.2f" % n for n in article_list[name]["ordered"]])
                    ordered = sum(article_list[name]["ordered"])
                    output_file.write(";".join([name, "%.0f" % article_list[name]["unit"], "%.2f" % article_list[name]
                                      ["price"], orders, "%.2f" % ordered, "%.2f" % (ordered*article_list[name]["price"])]) + "\n")
        return article_list

    def get_invoices(self, per_page=20, details=False):
        page_number = 1
        page = self.get_page("finance/invoices?page="+str(page_number)+"&per_page="+str(per_page))

        table = page.find("table")  # <table class='table table-striped'>
        column_name = [th.string for th in table.thead.tr.find_all("th")]
        invoices = {}
        for tr in table.tbody.find_all("tr"):
            for i, td in enumerate(tr.find_all("td")):
                if column_name[i]:
                    if column_name[i] == "Nummer":
                        number = td.a.string  # <a href="/franckkistl/finance/invoices/2235">179006</a><
                        href = td.a.get('href')
                        _id = href.split("/")[-1]
                        # if href_abs:
                        #    href = self._get_url(href)
                        invoices[_id] = {"Nummer": number, "href": href}
                    else:
                        if column_name[i] == "Rechnungsdatum":
                            value = td.a.string
                        elif column_name[i] == "Bestellung":
                            # <td><a href="/franckkistl/finance/balancing/new?order_id=5433">03.07.2024</a>,
                            #     <a href="/franckkistl/finance/balancing/new?order_id=5444">10.07.2024</a>,
                            #     <a href="/franckkistl/finance/balancing/new?order_id=5462">24.07.2024</a></td>
                            value = [ 
                                dict(
                                    url = a.get('href'),
                                    date = a.string,
                                    id = a.get('href').split("=")[-1],
                                )
                                for a in td.find_all("a")]
                        elif column_name[i] == "Lager-Lieferung":
                            # <td><a href="/franckkistl/suppliers/22/deliveries/410">09.07.2024</a></td>
                            value = [
                                dict(
                                    url = a.get('href'),
                                    date = a.string,
                                    supplier_id = a.get('href').split("/")[-3],
                                    delivery_id = a.get('href').split("/")[-1],
                                )
                                for a in td.find_all("a")]

                        # elif colmun_name[i]=="Notiz":
                        else:
                            value = td.string
                        invoices[_id][column_name[i]] = value
            # print(name, articles[name])
            if details:
                invoices[_id].update(self.get_invoice(_id))
        return invoices


# ==== bank and ordergroup accounts =========================================================================================


    def get_bank_account(self, bank_account_id, n=20):
        page = self.get_page(
            "finance/bank_accounts/"+str(bank_account_id)+"/bank_transactions?per_page="+str(n)) 

        # <h1>Banktransaktionen für Bank XY (1.863,72 € )</h1>
        h1 = page.h1.string 
        credit = _float(h1.split("(")[1].split(" ")[0])
        print(f"{credit=}")

        keys = []
        for th in page.table.thead.tr.find_all("th"):
            keys.append(th.string)
        #print(f"{keys=}")

        transactions = []
        for tr in page.table.tbody.find_all("tr"):
            data = {}
            for i, td in enumerate(tr.find_all("td")):
                data[keys[i]] = td.get_text()
                if keys[i]=="Finanzlink":
                    data[keys[i]] = td.a.get("href")
            transactions.append(data)
        #print(transactions)
        return credit, transactions

    def foodcoop_balance(self, bank_credit: float, stock_cash_value):
        # finance/ordergroups, order-balance.csv => account-balance.csv
        if isinstance(bank_credit, str):
            bank_credit = _float(bank_credit)

        # ordergroups from https://app.foodcoops.at/franckkistl/finance/ordergroups
        # https://app.foodcoops.at/franckkistl/finance/ordergroups?per_page=500
        page = self.get_page("finance/ordergroups/?per_page=500")
        # print(page)
        keys = []
        for th in page.table.thead.tr.find_all("th"):
            # print(th.string)
            keys.append(th.string)
        # print(keys)
        print("\n--- Mitglieder Guthaben Bilanz ------------------------------------------------------------------------")
        ordergroups = []
        member_credit_orders = 0
        member_credit_membership_fee = 0
        for tr in page.table.tbody.find_all("tr"):
            data = {}
            for i, td in enumerate(tr.find_all("td")[:-1]):
                if i in [2, 3]:
                    data[keys[i]] = _float(td.get_text()[1:-4])
                else:
                    data[keys[i]] = td.get_text()
            data["Guthaben gesamt"] = data["Guthaben Bestellungen"] + data["Guthaben Mitgliedsbeitrag"]
            #print(data)
            #{'Name': 'X Y', 'Kontakt': ' (X Y)', 'Guthaben Bestellungen': 30.0, 'Guthaben Mitgliedsbeitrag': 0.0}
            print("%-30s " % data["Name"], end="")
            for k in ["Guthaben Bestellungen", "Guthaben Mitgliedsbeitrag", "Guthaben gesamt"]:
                x = data[k]
                if x<0: print("\x1B[38;2;255;0;0m", end="") # Text auf rot stellen, https://www.baeldung.com/linux/formatting-text-in-terminals 
                print("%9.2f " % x, end="\x1B[m")  # reset text format
            print("")
            ordergroups.append(data)
            member_credit_orders += data["Guthaben Bestellungen"]
            member_credit_membership_fee += data["Guthaben Mitgliedsbeitrag"]
        member_credit_total = member_credit_orders + member_credit_membership_fee
        print("-------------------------------------------------------------------------------------------------------")
        print("%-30s %9.2f %9.2f %9.2f" % ("Summe", member_credit_orders, member_credit_membership_fee, member_credit_total))
        print("Mitglieder Summe Guthaben Bestellungen: %.2f €, Mitgliedsbeitrag: %.2f €, gesamt: %.2f €" % (
            member_credit_orders, member_credit_membership_fee, member_credit_total))
        print("Bank Guthaben: %.2f €, abzüglich Mitglieder Guthaben: %.2f € " %
              (bank_credit, bank_credit - member_credit_total))

        with open("order-balance.csv", "r") as order_balance_file:
            # Daten der letzen Zeile auswerten
            data = order_balance_file.read().splitlines()[-1].split(";")
            order_imbalance_date = data[0]
            order_imbalance = float(data[1])
        foodcoop_credit = bank_credit - member_credit_total + \
            order_imbalance + stock_cash_value
        print("Abrechnungen Guthaben Verein: %.2f €, Lager: %.2f €, Gesamtvermögen Verein: %.2f €" % (
            order_imbalance, stock_cash_value, foodcoop_credit))
        with open("account-balance.csv", "a") as output_file:
            s = ";".join(["{date:%Y-%m-%d %H:%M:%S}".format(date=datetime.datetime.now()),
                          "%.2f" % member_credit_orders,
                          "%.2f" % member_credit_membership_fee,
                          "%.2f" % member_credit_total,
                          "%.2f" % bank_credit,
                          "%.2f" % (bank_credit -
                                    member_credit_total),
                          order_imbalance_date,
                          "%.2f" % order_imbalance,
                          "%.2f" % stock_cash_value,
                          "%.2f" % foodcoop_credit
                          ]) + "\n"
            output_file.write(s)
        print("\nDiese Zeile in die Google-Tabelle kopieren:")
        print(s.replace(".", ",").replace(";", "\t"))

# ==== user accounts =========================================================================================

    def export_users(self):
        page = self.get_page("admin/users?per_page=500")
        print("\n--- BenutzerInnen Details ------------------------------------------------------------------------")
        users = []
        for tr in page.table.tbody.find_all("tr"):
            for i, td in enumerate(tr.find_all("td")):
                #print(f"  {i}: {td.get_text()}")
                if i == 0:  # Name
                    print("  "+td.get_text())
                if i == 4:
                    user_page = self.get_page(
                        td.a.get('href'), url_from_page=True)
                    user_data = {}
                    for inp in user_page.find_all("input"):
                        id = inp.get("id")
                        if id:
                            type = inp.get("type")
                            if type == "checkbox":
                                #print(id, inp.get("checked"))
                                value = inp.get("checked")
                            else:
                                #print(id, inp.get("value"))
                                value = inp.get("value")
                            if value is None:
                                value = ""
                            user_data[id] = value
                    users.append(user_data)
        print("--------------------------------------------------------------------------------------")
        print(";".join(users[0].keys()))
        for user in users:
            print(";".join(user.values()))
        return users
