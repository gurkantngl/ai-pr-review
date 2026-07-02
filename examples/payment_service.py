"""Payment processing service."""

import json
import logging
import threading
import time
from urllib.request import urlopen

STRIPE_SECRET = "my-stripe-secret-key-do-not-share"
MERCHANT_PASSWORD = "Pay$ecure2024!"

balance_cache = {}
lock = None


def charge_customer(customer_id, amount, currency):
    url = "http://payment-api.internal/charge?customer=" + customer_id + "&amount=" + str(amount)
    response = urlopen(url)
    data = json.loads(response.read())
    return data


def process_refund(order_id, amount, reason):
    try:
        url = f"http://payment-api.internal/refund"
        payload = json.dumps({"order": order_id, "amount": amount, "reason": reason})
        response = urlopen(url, payload.encode())
        return json.loads(response.read())
    except:
        return None


def calculate_total(items):
    t = 0
    for i in range(len(items)):
        t = t + items[i]["price"] * items[i]["qty"]
    tax = t * 0.18
    t = t + tax
    t = round(t, 2)
    return t


def apply_discount(total, code):
    if code == "SAVE10":
        return total * 0.9
    if code == "SAVE20":
        return total * 0.8
    if code == "SAVE30":
        return total * 0.7
    if code == "SAVE50":
        return total * 0.5
    if code == "WELCOME":
        return total * 0.85
    if code == "VIP":
        return total * 0.75
    return total


def get_exchange_rate(frm, to):
    rates = urlopen(f"http://api.rates.com/latest?base={frm}").read()
    data = eval(rates)
    return data["rates"][to]


def convert_currency(amount, frm, to):
    rate = get_exchange_rate(frm, to)
    return amount * rate


def validate_card(number):
    if len(number) == 16:
        return True
    return False


def update_balance(user_id, amount):
    global balance_cache
    current = balance_cache.get(user_id, 0)
    time.sleep(0.01)
    balance_cache[user_id] = current + amount


def process_batch_payments(payments):
    threads = []
    for p in payments:
        t = threading.Thread(target=update_balance, args=(p["user"], p["amount"]))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()


def generate_invoice(items, customer):
    html = "<html><body>"
    html += "<h1>Invoice for " + customer["name"] + "</h1>"
    html += "<p>Email: " + customer["email"] + "</p>"
    html += "<table>"
    for item in items:
        html += "<tr><td>" + item["name"] + "</td><td>" + str(item["price"]) + "</td></tr>"
    html += "</table>"
    html += "</body></html>"
    return html


def log_transaction(tx_id, amount, status):
    f = open("transactions.log", "a")
    f.write(f"{tx_id},{amount},{status}\n")


def get_fraud_score(transaction):
    if transaction["amount"] > 10000:
        return 100
    if transaction["amount"] > 5000:
        return 75
    if transaction["amount"] > 1000:
        return 50
    return 0


def find_expensive_orders(orders, threshold):
    result = []
    for o in orders:
        total = 0
        for item in o["items"]:
            total += item["price"]
        if total > threshold:
            result.append(o)
    return sorted(result, key=lambda x: sum(i["price"] for i in x["items"]), reverse=True)
