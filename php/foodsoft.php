<?php

require_once "simplehtmldom/simple_html_dom.php";

class Foodcoop
{
  public $host;
  public $name;
  public $real_name;

  public function __construct($host, $name)
  {
    $this->host = $host; # "https://app.foodcoops.at"
    $this->name = $name; # "franckkistl"
    $this->real_name = ucwords($name); #  "Franckkistl"
  }

  public function set_real_name($name)
  {
    $this->real_name = $name;
  }


  public function url($url = ""): string
  {
    if (strpos($url, $this->name) === false) { # "orders" => "http.../foodcoop/orders"
      $url = "/" . $this->name . "/" . $url;
    }
    if (strpos($url, $this->host) === false) {
      $url = $this->host . $url;
    }
    return $url;
  }

  public function relative_url($url): string
  {
    return "/" . $this->name . "/" . $url;
  }

  public function html_ahref($url, $linktext, $target = "_blank")
  {
    return "<a href='" . $this->url($url) . "' target='$target'>$linktext</a>";
  }

}

class Foodsoft_User
{
  public $foodcoop;
  public $username;
  public $password;

  public function __construct($foodcoop, $username, $password)
  {
    $this->foodcoop = $foodcoop;
    $this->username = $username;
    $this->password = $password;
  }
}

class Foodsoft
{
  private $fs_url, $fs_fc_url;
  private $login_url, $login_action_url;
  private $is_localhost, $do_post;
  private $channel;
  private $url, $page, $html, $csfr_token;
  private $foodsoft_user, $foodcoop_name;
  public $orders;

  private $debug = FALSE;

  public function __construct($foodsoft_user) #$host, $foodcoop, $user, $password)
  {
    $this->fs_url = $foodsoft_user->foodcoop->host; # "https://app.foodcoops.at";
    $this->fs_fc_url = $this->fs_url . "/" . $foodsoft_user->foodcoop->name;
    $this->login_url = $this->fs_fc_url . "/login"; //
    $this->login_action_url = $this->fs_fc_url . "/sessions"; // submit $fs_urlurl from the login form
    $this->is_localhost = strpos($_SERVER['HTTP_HOST'], "localhost") === 0;
    $this->do_post = !$this->is_localhost;
    $this->login($foodsoft_user->username, $foodsoft_user->password);
    $this->foodsoft_user = $foodsoft_user;
    $this->foodcoop_name = $foodsoft_user->foodcoop->name;
  }

  public function get_username()
  {
    return $this->foodsoft_user->username;
  }

  public function get_foodcoop_name()
  {
    return $this->foodsoft_user->foodcoop->name;
  }
  public function get_foodcoop_real_name()
  {
    return $this->foodsoft_user->foodcoop->real_name;
  }

  public function set_post($active)
  {
    $this->do_post = $active;
  }

  private function header($array = array())
  {
    $array = array(
      "Content-Type" => "application/x-www-form-urlencoded",
      "Upgrade-Insecure-Requests" => 1,
      'Accept' => 'text/html' # if not specified, for some pages like fincance/.../bank_transcations 
      # GET ends up with 422 Unprocessable Entity 
      # ActionController::InvalidCrossOriginRequest (Security warning: an embedded <script> tag on 
      # another site requested protected JavaScript. If you know what you're doing, go ahead and 
      # disable forgery protection on this action to permit cross-origin JavaScript embedding.)
    ) + $array;
    $result = array();
    foreach ($array as $key => $value) {
      $result[] = $key . ": " . $value;
    }
    return $result;
  }

  public function fc_url($url) # e.g. "/orders" => "http.../foodcoop/orders"
  {
    return $this->fs_fc_url . $url;
  }

  public function fs_url($url)  # e.g. "/foodcoop/orders" => "http.../foodcoop/orders"
  {
    return $this->fs_url . $url;
  }

  public function url($url): string
  {
    if (strpos($url, $this->foodcoop_name) === false) {
      return $this->fc_url($url);
    }
    if (strpos($url, $this->fs_url) === false) {
      return $this->fs_url($url);
    }
    return $url;
  }

  public function html_ahref($url, $linktext, $target = "_blank")
  {
    return "<a href='" . $this->url($url) . "' target='$target'>$linktext</a>";
  }

  private function login($user, $password)
  {
    $loginFields = array(
      'nick' => $user,
      'password' => $password,
      "utf8" => "&#x2713;",
      'commit' => 'Anmelden',
      "authenticity_token" => ""
    ); //login form field names and values
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.2309.372 Safari/537.36');
    curl_setopt($ch, CURLOPT_HTTPHEADER, $this->header());
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, 0);
    curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, false);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_COOKIEJAR, realpath('./cookie.txt'));
    curl_setopt($ch, CURLOPT_COOKIEFILE, realpath('./cookie.txt'));
    curl_setopt($ch, CURLOPT_URL, $this->login_url);
    $p = curl_exec($ch);
    if (!$p) {
      print "konnte $this->login_url nicht erreichen.";
      $this->channel = NULL;
      return;
    }

    /* ...
    <input type="hidden" 
      name="authenticity_token" 
      value="tDVoz6jVZsVPULTJiVFr6fiolcW-GbJJFCUwTrmT2GvqrF6RR-DKhmrltMQaHqx9__geuOfCHvzWQIcHCgF3jg" 
      autocomplete="off" />
    ... */
    $loginFields["authenticity_token"] = str_get_html($p)->find('input[name=authenticity_token]', 0)->value;
    //print "token: ".$loginFields["authenticity_token"];

    curl_setopt($ch, CURLOPT_POST, 1);
    curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query($loginFields));
    curl_setopt($ch, CURLOPT_URL, $this->login_action_url);
    curl_setopt($ch, CURLOPT_REFERER, $this->login_url);
    curl_exec($ch);

    $this->channel = $ch;
  }

  public function has_connection()
  {
    return $this->channel !== NULL;
  }

  function get_page($url): string
  {
    $this->url = $url;
    curl_setopt($this->channel, CURLOPT_URL, $url);
    curl_setopt($this->channel, CURLOPT_POST, 0);
    $this->page = curl_exec($this->channel);
    return $this->page;
  }

  function get_html($url)
  {
    $this->html = str_get_html($this->get_page($url));
    # print "<pre>" . $url . "\n" . $this->page . "</pre>";
    $this->csfr_token = $this->html->find("meta[name=csrf-token]", 0)->content;
    return $this->html;
  }

  function post($url, $data)
  {
    curl_setopt($this->channel, CURLOPT_URL, $url);
    curl_setopt($this->channel, CURLOPT_POST, 1);
    curl_setopt($this->channel, CURLOPT_POSTFIELDS, http_build_query($data));
    curl_setopt($this->channel, CURLOPT_REFERER, $this->url);
    curl_setopt(
      $this->channel,
      CURLOPT_HTTPHEADER,
      $this->header(array("X-CSRF-Token" => $this->csfr_token))
    );
    if ($this->do_post) {
      curl_exec($this->channel);
    }
  }


  function get_orders_admin($n_pages_balanced = 3, $key = "index")
  {
    // scrape order infos from foodsoft order administration page /orders
    // result: array[][order-property] if $key="index" or
    //         array[key][order-property] else; e.g. $key="id" 
    $html = $this->get_html($this->fc_url("/orders"));// Bestellungen verwalten
    #print $this->fc_url("/orders");
    $orders = array();

    # --- beendete Bestellungen -----------------
    $html_order = $html->find("h2", 1)->parent()->parent()->next_sibling(); # h2: Beendet -> td -> tr -> next tr
    $i = 0;
    while ($html_order) {
      $td = $html_order->find("td");
      $order = array(
        "producer" => $td[0]->plaintext,
        "pickup" => $td[1]->plaintext,
        "end" => $td[2]->plaintext,
        "url" => $td[5]->children(1)->href,
        # <td> children(0) <a class="btn btn-small" href="/franckkistl/orders/5555/edit">Bearbeiten</a>
        #      children(1) <a class="btn btn-small" href="/franckkistl/orders/5555">Anzeigen</a>
        #      children(2) <a data-confirm="Willst Du wirklich die Bestellung löschen?" class="btn btn-small btn-danger" rel="nofollow" data-method="delete" href="/franckkistl/orders/5555">Löschen</a>     
        "id" => explode("/", $td[5]->children(2)->href)[3],
        "status" => "beendet",
        "balanced" => FALSE,
        "updated-by" => "",
      );
      #print $order["url"] . "<br>";

      if ($key == "index") {
        $orders[] = $order;
      } else { // key=="id"
        $orders[$order[$key]] = $order;
      }

      $html_order = $html_order->next_sibling();
      if ($i++ > 500)
        break; # this should never happen, because after last table entry, $html_order = null
    }

    # --- abgerechnete Bestellungen -----------------------
    for ($page = 1; $page <= $n_pages_balanced; $page++) {
      if ($page > 1) {
        $html = $this->get_html($this->fc_url("/orders?page=$page&per_page=15"));
      }
      foreach ($html->find("table", 1)->find("tbody tr") as $tr) {
        $td = $tr->find("td");
        #print $td[5]->children(1) . "<br>";
        $order = array(
          "producer" => $td[0]->plaintext,
          "pickup" => $td[1]->plaintext,
          "end" => $td[3]->plaintext,
          "url" => $td[5]->children(1)->href,
          "id" => explode("/", $td[5]->children(1)->href)[3],
        );
        #print $order["url"] . "<br>";

        if ($key == "index") {
          $orders[] = $order;
        } else {
          $orders[$order[$key]] = $order;
        }
      }
    }
    $this->orders = $orders;
    return $orders;
  }

  function get_articles_order_admin($order)
  {
    $html = $this->get_html($this->fc_url("/orders/" . $order["id"] . "?view=articles"));
    $articles = array();
    foreach ($html->find("table tbody") as $tbody) {
      $tr_a = $tbody->find("tr");
      # Asiasalate  (ca 250g, 3,60 €  )
      #    print count($tr_a)."=>";
      $a = array_shift($tr_a)->children(0)->children(0)->innertext;
      #    print count($tr_a)." ".$a."\n";
      $j1 = strpos($a, "<small>");
      $j2 = strpos($a, ", ", $j1);
      $j3 = strpos($a, "</small>");
      if ($j1 === FALSE) {
        continue;
      }
      $article = array(
        "id" => substr($tbody->id, 3),  # <tbody id='oa_127975'>               
        "name" => cleanup_str(trim(substr_abspos($a, 0, $j1))),
        "unit" => trim(substr_abspos($a, $j1 + 9, $j2)),
        "price" => loc_floatval(substr_abspos($a, $j2 + 2, $j3 - 6)),
        "ordergroups" => array(),
      );
      foreach ($tr_a as $tr) {
        # print "    tr\n";
        #    print "#[".$tr."]#\n";        
        $td_a = $tr->find("td");
        if (count($td_a) < 3) {
          continue;
        }
        $article["ordergroups"][] = array(
          "id" => substr($tr->id, 4), #  <tr id='goa_1856853'>  
          "name" => $td_a[0]->plaintext,
          "ordered" => intval(explode("+", $td_a[1]->plaintext)[0]), // 2+0 = bestellt+Toleranz
          //"tolerance" => intval(explode("+",$td_a[1]->plaintext)[1]), // 2+0 = bestellt+Toleranz
          "received" => loc_floatval($td_a[2]->innertext), #find("input",1),
        );
      }
      $articles[] = $article;
    }
    return $articles;
  }

  function get_orders($n_pages = 1, $n_orders_per_page = 500, $pickup_dates = FALSE, $until_date = "")
  {
    // scrape order infos from foodsoft order overview page /finance/balancing
    // result: array[id][order-property]

    if ($this->debug)
      print "<pre>";
    $orders = array();
    for ($i = 1; $i <= $n_pages; $i++) {
      if ($this->debug)
        print "order page " . $i . "\n";
      $html = $this->get_html($this->fc_url("/finance/balancing?page=$i&per_page=$n_orders_per_page")); // Create a DOM object from a string
      foreach ($html->find("table tbody tr") as $tr) {
        #print $tr;
        $td = $tr->find("td");
        // Lieferantin 	Ende 	Status 	Zuletzt geändert von
        $url = $td[0]->children(0)->href;
        $id = explode("=", $url)[1];
        $orders[$id] = array(
          "producer" => $td[0]->plaintext,
          "url" => $url, // /franckkistl/finance/balancing/new?order_id=4095
          "id" => $id,
          "end" => $td[1]->plaintext,
          "pickup" => "",
          "status" => $td[2]->plaintext,
          "balanced" => strpos($td[2]->plaintext, "abgerechnet") === 0,
          "updated-by" => $td[3]->plaintext,
        );
        if ($this->debug)
          print "  " . $orders[$id]["end"] . " " . $orders[$id]["producer"] . "\n";
      }
      if ($this->debug)
        print "    " . $orders[$id]["end"] . " < " . $until_date . ": " .
          (date_create($orders[$id]["end"]) < date_create($until_date)) . "\n";
      if ($until_date && date_create($orders[$id]["end"]) < date_create($until_date)) {
        break;
      }
    }
    if ($this->debug)
      print "</pre>";

    if ($pickup_dates) {
      $orders_pickup = $this->get_orders_admin(0, "id");
      foreach ($orders_pickup as $id => $order_p) {
        if (array_key_exists($id, $orders)) {
          $orders[$id]["pickup"] = $order_p["pickup"];
        } else {
          $orders[$id] = $order_p;
        }
      }
    }
    return $orders;
  }

  function get_order($url)
  {
    // scrape order article infos from foodsoft specific order balance page 
    // like e.g. /franckkistl/finance/balancing/new?order_id=5533
    // returns: array("url" => $url, "page" => $page, "articles" => $articles, ...)
    $url = $this->fs_url(url: $url);
    $html = $this->get_html($url); // Create a DOM object from a string
    if (!$html) {
      return false;
    }

    // get note for order
    $note = $html->find('div[id=note] p', 0);
    if ($note) {
      $note = $note->plaintext;
      if (strpos($note, "Hier kannst Du") === 0)
        $note = "";
    } else {
      $note = "";
    }

    // get invioce id and url for order
    $invoice_url = $html->find('div[id=invoice] a', 0);
    $invoice_id = "";
    if ($invoice_url) {
      $invoice_url = $invoice_url->href;
      // /franckkistl/finance/invoices/new?order_id=4095&amp;supplier_id=8  -- no invoice yet
      // /franckkistl/finance/invoices/2306/edit"  -- invoice exists
      $invoice_url_parts = explode("/", $invoice_url);
      if (count($invoice_url_parts) == 6 && $invoice_url_parts[5] == "edit") {
        $invoice_id = $invoice_url_parts[4];
      }
    }


    // loop over order articles 
    $articles = array();
    # print "<pre>";
    foreach ($html->find('table tbody[id=result_table] tr[class=order_article]') as $tr) {
      $td = $tr->find("td");
      $received = explode("×", $td[2]->plaintext); #  "3" oder "1 × 4"
      if (count($received) == 2) {
        $received = floatval($received[0]) * floatval($received[1]); #  z.B. 	1 × 4
      } else {
        $received = floatval($received[0]);
      }
      $article = array(
        "name" => $td[0]->plaintext,
        "item-number" => $td[1]->plaintext, // Artikelnummer
        "received-total" => $received, # floatval($td[2]->plaintext), // Anzahl der bestellten Artikel ohne Lager-Bestellungen!
        "unit" => $td[3]->plaintext,
        "price-excl-tax" => loc_floatval(explode("/", $td[4]->plaintext)[0]),
        "price-incl-tax" => loc_floatval(explode("/", $td[5]->plaintext)[0]),
        "tax" => loc_floatval($td[6]->plaintext),
        "deposit" => loc_floatval($td[7]->plaintext),
        "edit-url" => ""
      );
      # print $url . " " . $article["name"] . " " . $td[2]->plaintext . " => " . $received . "\n";
      $a = $td[8]->find("a", 0);
      if ($a) {
        $article["edit-url"] = substr($a->href, 0, -strlen("/edit"));
      } // else: Bestellung schon abgerechnet, kein Link zum Bearbeiten des Artikels

      /*
      0 Name
      1 <th>Bestellnummer</th>
      2 <th>Menge</th>
      3 <th>Einheit</th>
      4 <th>Netto</th>
      5 <th>Brutto</th>
      6 <th>MwSt</th>
      7 <th>Pfand</th>
      */

      #print "<pre>";
      #print_r($article);
      #print "</pre>";

      $td = $tr->next_sibling()->find('table tfoot tr td');  // Summe (FC-Preis) -> bekommen     
      $article["received-total"] = loc_floatval($td[2]->plaintext);
      # printf("  received-total: %g\n", $article["received-total"]);
      # der Wert sollte identisch mit dem oben bestimmten sein, wenn die gesamt erhaltene Zahl 
      # mit der Summe der Zahlen der Bestellgruppen übereinstimmt. 
      # Teilweise wurden erhaltene Mengen von Artikeln wo Einheit>1 ist, falsch eingegeben (Menge statt Menge/Einheit)
      # Mitglieder-Guthaben abgebucht wird jedenfalls nur für diesen Wert.


      // <tr class='group_order_article' id='group_order_article_2321601'>
      //     0 <td></td>
      //     1 <td style='width:50%'>Claudia L</td>
      //     2 <td class='center'>
      //          <form class="simple_form delta-input" id="edit_group_order_article_2321601" 
      //                data-submit-onchange="changed" action="/franckkistl/group_order_articles/2321601" 
      //                accept-charset="UTF-8" data-remote="true" method="post">
      //             <input type="hidden" name="_method" value="patch" autocomplete="off" />
      //             <div class="delta-input input-prepend input-append">
      //                 <button name="delta" type="button" value="-1" data-decrement="r_2321601" tabindex="-1" class="btn"><i class="icon icon-minus"></i></button>
      //                 <input class="delta optional input-nano" data-min="0" data-delta="1" 
      //                        id="r_2321601" value="1" type="text" autocomplete="off" name="group_order_article[result]" />
      //                 <button name="delta" type="button" value="1" data-increment="r_2321601" tabindex="-1" class="btn"><i class="icon icon-plus"></i></button>
      //             </div>
      //         </form></td>
      //     3 <td class='numeric'>4,95 € </td>
      //     4 <td class='actions' style='width:1em'>
      //         <a class="btn btn-mini btn-danger" data-remote="true" rel="nofollow" data-method="delete" 
      //            href="/franckkistl/group_order_articles/2321601">Löschen</a></td>
      //     5 <td></td>
      // </tr>

      // loop over ordergroups who orderd this article
      $received_total = 0;
      $updated_received_total = 0;
      $ordergroups = array();
      $update_article = FALSE;
      foreach ($tr->next_sibling()->find('table tbody tr[class=group_order_article]') as $tr) {
        $td = $tr->find("td");
        $ordergroup = trim($td[1]->plaintext);
        $input = $td[2]->find("form div input", 0);
        if ($input) {
          $id = substr($input->id, 2);
          $received = loc_floatval($input->value);
        } else {
          $id = $tr->id; # e.g. group_order_article_2166348
          $id = explode("_", $id)[3];
          $received = loc_floatval($td[2]->plaintext);
        }
        $ordergroups[$id] = array(
          "name" => $ordergroup,
          "received" => $received,
        );
        $received_total += $received;
      }
      $article["ordergroups"] = $ordergroups;
      $articles[] = $article;
    }
    # print "</pre>";


    $transport_fees = 0;
    foreach ($html->find('table tbody[id=result_table] tr') as $tr) {
      $td = $tr->find("td");
      if (strpos($td[0]->plaintext, "Transportkosten") === 0) {
        $transport_fees += loc_floatval(explode(" ", $td[1]->plaintext)[0]);	 	# 6,60 € 
      }
    }

    $stock_order = 0;
    foreach ($html->find('table tbody[id=result_table] tr[class=group_order_article]') as $tr) {
      $td = $tr->find("td");
      if (strpos($td[1]->plaintext, "Lager (") === 0) {
        //print $td[1]->plaintext." ".$td[3]->plaintext."\n";	
        $stock_order += loc_floatval(explode(" ", $td[3]->plaintext)[0]);	 	# 6,60 € 
      }
    }


    return array(
      "url" => $url,
      "note" => $note,
      "invoice-url" => $invoice_url,
      "invoice-id" => $invoice_id,
      "articles" => $articles,
      "transport-fees" => $transport_fees,
      "stock-order" => $stock_order
    );
  }




  function update_group_order($id, $received)
  {
    // update the received units of a group order article
    $url = $this->fc_url("/group_order_articles/" . $id);
    if ($this->is_localhost)
      printf(
        "POST %s %s group_order_article[result]=%.2f\n",
        $this->do_post ? "active" : "inactive",
        $url,
        $received
      );
    $this->post(
      $url,
      array(
        "_method" => "patch",
        "group_order_article[result]" => sprintf("%.2f", $received),
      )
    );
  }

  function update_article($article, $received)
  {
    // update the totally received units of an article in an order
    $url = $this->fs_url($article["edit-url"]);
    if ($this->is_localhost)
      printf(
        "POST %s %s order_article[units_received]=%.2f\n",
        $this->do_post ? "active" : "inactive",
        $url,
        $received
      );
    $this->post(
      $url,
      array(
        "utf8" => "✓",
        "_method" => "patch",
        #"order_article[units_to_order]"=> "2",
        "order_article[units_received]" => sprintf("%.2f", $received),
        #"article[name]"=> "apfel",
        #"article_price[unit_quantity]"=> "1",
        #"article[unit]"=> "kg",
        #"article_price[price]"=> "11.0",
        #"article_price[tax]"=> "7.0",
        #"article_price[deposit]"=> "0.0",
        "order_article[update_global_price]" => "0",
        "article[order_number]" => $article["item-number"], // diese Eigenschaft 
        // wird nur deshalb übertragen, weil der Request sonst in der Foodsoft 
        // erfolglos ist (ROLLBACK). Es kann auch stattdessen eine andere Eigenschaft  
        // übergeben werden, anscheinend gibt es eine Mindestanzahl an Eigenschaften,
        // die übergeben werden muss. 
        "commit" => "Bestell-Artikel+aktualisieren"
      ),
    );
  }


  function get_group_order($group_order_url)
  {
    // get the article details of a group order by scraping
    // group_order_url: e.g. "/franckkistl/group_orders/34105"
    // depricated!
    $group_order_articles = array();
    if (strlen($group_order_url) == 0) {
      return $group_order_articles;
    }
    $order_id = get_order_id($group_order_url);
    $order_url = $this->fs_url($group_order_url);
    $order = $this->get_html($order_url);
    $article_id = 0; // no access to the foodsoft-id, so lets create our own
    foreach ($order->find('table', 0)->find('tr') as $tr) {
      $article = array();
      $tr_class = $tr->class;
      if ($tr_class == 'article-category') {
        // $category="<h2>".$tr->find("td",0)->plaintext."</h2>\n";                
      } elseif (strpos($tr_class, "success") !== false || strpos($tr_class, "ignore") !== false || strpos($tr_class, "failed") !== false) {
        $td = $tr->find("td");
        $i = 0;
        $article["name"] = $td[$i++]->plaintext; // $article 
        $article["unit"] = $td[$i++]->plaintext;
        $article["price"] = $td[$i++]->plaintext;
        $article["ordered"] = $td[$i++]->plaintext;
        $article["received"] = $td[$i++]->plaintext;
        $article["id"] = "$order_id-$article_id";
        if (intval($article["ordered"]) > 0 || intval($article["received"]) > 0) {
          $group_order_articles[] = $article;
        }
        $article_id++;
      }
    }
    return $group_order_articles;
  }








  function get_invoice($invoice_id)
  {
    $html = $this->get_html($this->fc_url("/finance/invoices/" . $invoice_id));
    $invoice = array();
    foreach ($html->find("dl dt") as $dt) {
      #print $dt->plaintext." ".$dt->find("dd",0)->plaintext."<br>";
      $key = strtr($dt->plaintext, array(":" => ""));
      if ($key == "Bestellung") {
        $order_ids = array();
        foreach ($dt->find("dd a") as $a) {
          $href = $a->href;
          // https://app.foodcoops.at/franckkistl/finance/balancing/new?order_id=4037
          $href_parts = explode("=", $href);
          if (count($href_parts) == 2) {
            $order_ids[] = [1];
          }
        }
        $invoice[$key] = $order_ids;
      } elseif ($key == "Lager-Lieferung") {
        $delivery_urls = array();
        foreach ($dt->find("dd a") as $a) {
          $delivery_urls[] = $a->href;
        }
        $invoice[$key] = $delivery_urls;
      } elseif ($key == "Anhang") {
        #print "<pre>";
        #print_r($dt->find("dd"));
        $dd = $dt->next_sibling(); #$i=1;
        $invoice[$key] = array();
        while ($dd->tag == "dd") {
          $a = $dd->find("a", 0);
          #print $i++.": ".$a->plaintext." ".$a->href."\n";
          $invoice[$key][] = $a->href;
          $dd = $dd->next_sibling();
        }
        #print "</pre>";   
      } elseif ($key == "Finanzlink") {
        $invoice[$key] = $dt->find("dd a", 0)->href;
      } else {
        $value = $dt->find("dd", 0)->plaintext;
        if ($key != "Notiz" && strpos($value, "€") > 0)
          $value = loc_floatval($value);
        $invoice[$key] = $value;
      }
    }
    $invoice["Gewinn"] = $invoice["Total"] - $invoice["Pfandbereinigter Betrag"];
    return $invoice;
  }



  function get_user_details()
  {
    $html = $this->get_html($this->fc_url("/home/ordergroup"));
    if (strlen($html) == 0 || strpos($html, "redirected") > 0)
      return FALSE;
    return array(
      "name" => $html->find("a", 0)->plaintext,
      "ordergroup" => $html->find("h2", 0)->plaintext,
      "total_credit" => $html->find("p")[0]->plaintext,
      "available_credit" => $html->find("p")[1]->plaintext,
    );
  }

  function get_users()
  {
    $html = $this->get_html($this->fc_url("/foodcoop?per_page=500"));
    $users = array();
    foreach ($html->find("table tbody tr") as $tr) {
      $td = $tr->find("td");
      if (count($td) >= 2) {
        $users[] = array(
          "name" => $td[0]->plaintext,
          "email" => $td[1]->plaintext,
        );
      }
    }
    /*
    0 <th>Name</th>
    1 <th>E-Mail</th>
    2 <th>Telefon</th>
    3 <th>Bestellgruppe</th>
    4 <th>Arbeitsgruppen</th>
    */
    return $users;
  }

  function get_ordergroups()
  {
    $html = $this->get_html($this->fc_url("/foodcoop/ordergroups?per_page=500"));
    $ordergroups = array();
    foreach ($html->find("table tbody tr") as $tr) {
      $td = $tr->find("td");
      if (count($td) >= 2) {
        $members = explode(", ", $td[1]->plaintext);
        foreach ($members as $i => $member) {
          $members[$i] = trim($member);
        }
        $ordergroups[] = array(
          "name" => $td[0]->plaintext,
          "members" => $members,
        );
      }
    }

    $members = array();
    foreach ($ordergroups as $ordergroup) {
      foreach ($ordergroup["members"] as $member) {
        if (strlen($member) > 0)
          $members[$member] = $ordergroup["name"];
      }
    }
    ksort($members);

    return array("ordergroups" => $ordergroups, "members" => $members);
  }


  function get_ordergroup_name($id)
  {
    $html = $this->get_html($this->fc_url("/admin/ordergroups/$id"));
    // print($html);
    $title = $html->find("h1", 0)->plaintext; // Bestellgruppe Anne J.
    // print $title;
    strtok($title, " "); // remove "Bestellgruppe "
    return strtok(";");
  }

  function get_user_name($id)
  {
    $html = $this->get_html($this->fc_url("/admin/users/$id"));
    // print($html);
    $title = $html->find("h1", 0)->plaintext; // Anne J.
    return $title;
  }



  function close()
  {
    curl_close($this->channel);
  }

  function __destruct()
  {
    $this->close();
  }

}







function get_order_href($href)
{
  // $href can be:
  //  /franckkistl/group$group_order_articles/new?order_id=3929 -- open order without ordering
  //  /franckkistl/group$group_order_articles/25566/edit?order_id=3920 -- open order with ordering
  //  /franckkistl/group$group_order_articles/25566 -- closed order

  $href_elements = explode("/", $href); // 
  if (is_numeric($href_elements[3])) {  //  /franckkistl/group$group_order_articles/25566 <= 3rd element
    return implode("/", array_slice($href_elements, 0, 4)); // first element is empty!
  } else { //  /franckkistl/group$group_order_articles/new?order_id=3929 
    return "";
  }
}

function get_order_id($href)
{
  $href_elements = explode("/", $href); // 
  $id = $href_elements[3];  //  /franckkistl/group$group_order_articles/25566 <= element 3 (0 = "")
  if (is_numeric($id)) {
    return intval($id);
  } else { // z.B. /franckkistl/group$group_order_articles/new?order_id=3929 
    return 0;
  }
}


function char_is_blank($c)
{
  return $c == " ";
}

function char_is_number($c)
{
  return is_numeric($c) || $c == ",";
}

function get_unit_weight($unit)
{
  // return unit weight (weight of one article entity) in gram from foodsoft unit-string
  $unit = " " . $unit;
  $i1 = strpos($unit, "kg");
  if ($i1 > 0) {
    $factor = 1000.;
  } else {
    $i1 = strpos($unit, "g");
    if ($i1 > 0) {
      $factor = 1.0;
    } else {
      $factor = 0;
    }
  }
  if ($factor > 0) {
    $i0 = $i1;
    while (char_is_blank($unit[--$i0]) && $i0 > 0)
      ;
    while (char_is_number($unit[--$i0]) && $i0 > 0)
      ;
    $unit_weight = floatval(str_replace(",", ".", substr($unit, $i0 + 1, $i1 - $i0 - 1))) * $factor;
  } else {
    $unit_weight = 0;
  }
  return $unit_weight;
}








