import logging
import sys
import time
import threading
from typing import Any

import os
from lnd_listener import LndListener
from flask import Flask
from flask import request
from flask_cors import CORS
from waitress import serve
from urllib.parse import urlparse
import sqlite3


def lnd_response(response: Any) -> None:
    print(str(response))


def insert_row(idx: int, remittance_info: str, amount_msat: int, magic_code: str, callback_uri: str):
    connection = sqlite3.connect(SQ3_DATABASE)
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO invoices (idx, remittance_info, amount_msat, magic_code, callback_uri, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (idx, remittance_info, amount_msat, magic_code, callback_uri, int(time.time())))
    connection.commit()
    connection.close()


def get_row(idx: int):
    connection = sqlite3.connect(SQ3_DATABASE)
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM invoices WHERE idx=?", (idx,))
    row = cursor.fetchone()
    connection.close()
    return row


def delete_row(idx: int):
    connection = sqlite3.connect(SQ3_DATABASE)
    cursor = connection.cursor()
    cursor.execute("DELETE FROM invoices WHERE idx=?", (idx,))
    connection.commit()
    connection.close()


def check_for_valid_url(url: str) -> bool:
    parsed_uri = urlparse(url)
    if not all([parsed_uri.scheme, parsed_uri.netloc]):
        return False
    return True


if __name__ == '__main__':
    SERVER_PORT = os.environ.get("SERVER_PORT", "8080")
    ENDPOINT_SECRET = os.environ.get("ENDPOINT_SECRET", "YouShouldChangeThis")
    SQ3_DATABASE = os.environ.get("SQ3_DATABASE", "./data.db")
    SERVER_VERSION = "LNDIMS V0.9.0"
    API_VERSION = "v1"
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format="[%(asctime)s - %(levelname)s] %(message)s")
    logging.getLogger().setLevel(logging.DEBUG)
    app_logger = logging.getLogger("LNDInvoiceMgmt")
    # mutex
    mutex = threading.Lock()
    # database
    sq3_connection = sqlite3.connect(SQ3_DATABASE)
    sq3_cursor = sq3_connection.cursor()
    sq3_cursor.execute(
        "CREATE TABLE IF NOT EXISTS invoices (idx INTEGER PRIMARY KEY, remittance_info TEXT, "
        "amount_msat INTEGER, magic_code TEXT, callback_uri TEXT, timestamp INTEGER)")
    sq3_connection.close()

    # listener thread
    lnd_listener = LndListener(logger=app_logger, event_callback=lnd_response, mutex=mutex)
    lnd_listener.start_invoice_listener()
    # flask
    app = Flask("LNDInvoiceMgmtServer")
    CORS(app)


    @app.route(f"/{API_VERSION}/invoice", methods=["POST"])
    def create_invoice():
        try:
            amount_msat = request.json['amount_msat']
            callback_uri = request.json['callback_uri']
            remittance_info = request.json['remittance_info']
            magic_code = request.json['magic_code']
            secret = request.json['secret']
        except KeyError:
            app_logger.debug("Illegal request body")
            return "Missing fields in body", 400
        if secret != ENDPOINT_SECRET:
            return "Missing or wrong auth-secret", 401
        if not check_for_valid_url(callback_uri):
            return "Invalid callback_uri", 400

        app_logger.debug(
            f"Got invoice request: remittance_info={remittance_info}, amount_msat={amount_msat}, "
            f"callback_uri={callback_uri}, magic_code={magic_code}")
        bech32_invoice = lnd_listener.create_invoice(amount_msat, remittance_info)
        if bech32_invoice == "":
            return {"status": "ERROR", "reason": "LND did not provide an invoice"}, 500
        insert_row(idx=int(bech32_invoice["add_index"]), callback_uri=callback_uri, magic_code=magic_code,
                   remittance_info=remittance_info, amount_msat=int(amount_msat))

        return {}, 204


    app_logger.info(f"LNDInvoiceMgmtServer {SERVER_VERSION} starting on port {SERVER_PORT}")
    app_logger.info("GitHub: https://github.com/feikede")
    app_logger.info("A server to simplify LND invoicing.")
    app_logger.info("This software is provided AS IS without any warranty. Use it at your own risk.")
    app_logger.info("API version: " + API_VERSION)
    app_logger.info("SQLite3 database file: " + SQ3_DATABASE)
    app_logger.info("Config SOCKS5H_PROXY: " + str(lnd_listener.SOCKS5H_PROXY))
    app_logger.info("Config LND_RESTADDR: " + str(lnd_listener.LND_RESTADDR)[:16] + "...")
    app_logger.info("Config INVOICE_MACAROON: " + str(lnd_listener.INVOICE_MACAROON)[:14] + "...")
    app_logger.info("Config TLS_VERIFY: " + str(lnd_listener.TLS_VERIFY))

    serve(app, host="0.0.0.0", port=SERVER_PORT)
