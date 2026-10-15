"""Order processing logic."""
import logging
import sqlite3
from contextlib import closing

import database
import auth


SEPARATOR = "=============================="
TAX = 0.15

logger = logging.getLogger(__name__)
 
 
def _reserve_item(item):
    """Take one item from stock and return its line total (0 if it cannot be sold)."""
    book = database.get_book(item["book_id"])
    if book is None:
        print("Book not found")
        return 0
 
    qty = item["qty"]
    stock = book[3]
    if qty <= 0:
        print("Invalid quantity")
        return 0
 
    if stock < qty:
        if stock > 0:
            print("Only " + str(stock) + " units available for " + book[1])
        else:
            print("Book out of stock: " + book[1])
        return 0
 
    database.update_stock(book[0], stock - qty)
    return book[2] * qty
 
 
def process_order(token, items, coupon=None, shipping="standard", log=None):
    if log is None:
        log = []
 
    username = auth.sessions.get(token)
    if username is None:
        print("Invalid session")
        return None
 
    if not items:
        print("Empty order")
        return None
 
    discounts = {
        "WELCOME10": 0.9,
        "BLACKFRIDAY": 0.5,
        "STAFF": 0.7,
    }
    shipping_costs = {
        "express": 10,
        "standard": 3,
    }
 
    total = 0
    for item in items:
        total += _reserve_item(item)
 
    if coupon in discounts:
        total *= discounts[coupon]
 
    total += shipping_costs.get(shipping, 0)
    total += total * TAX
 
    order_id = len(log) + 1
    database.save_order(order_id, username, total, "PENDING")
    log.append(order_id)
    return round(total, 2)
 
 
def _print_document(title, username, items, note=None):
    """Print an invoice or a quote; both share the same layout."""
    print(SEPARATOR)
    print("BOOKSTORE " + title)
    print("Customer: " + username)
    print(SEPARATOR)
    subtotal = 0
    for item in items:
        book = database.get_book(item["book_id"])
        line_total = book[2] * item["qty"]
        subtotal = subtotal + line_total
        print(book[1] + " x" + str(item["qty"]) + " = " + str(line_total))
    tax = subtotal * TAX
    print("Subtotal: " + str(round(subtotal, 2)))
    print("Tax: " + str(round(tax, 2)))
    print("Total: " + str(round(subtotal + tax, 2)))
    if note:
        print(note)
    print(SEPARATOR)
 
 
def print_invoice(username, items):
    _print_document("INVOICE", username, items)
 
 
def print_quote(username, items):
    _print_document("QUOTE", username, items, "This quote is valid for 7 days.")
 
 
def cancel_order(order_id):
    try:
        with closing(database.get_connection()) as conn:
            conn.execute("UPDATE orders SET status = 'CANCELLED' WHERE id = ?", (order_id,))
            conn.commit()
    except sqlite3.Error:
        logger.exception("Could not cancel order %s", order_id)
 