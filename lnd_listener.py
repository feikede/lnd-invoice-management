import base64
import hashlib
import json
import logging
import os
import threading
import time
import requests
import urllib3
from requests.exceptions import ChunkedEncodingError
from typing import Callable, Any


class LndListener:
    SOCKS5H_PROXY = os.environ.get("SOCKS5H_PROXY", "")
    LND_RESTADDR = os.environ.get("LND_RESTADDR", "https://your.lnd-server.org")
    INVOICE_MACAROON = os.environ.get("INVOICE_MACAROON", "xxxxxxxxx-xxxx-xxxx")
    TLS_VERIFY = os.environ.get("TLS_VERIFY", "./tls.cert")

    def __init__(self, mutex: threading.Lock, logger: logging.Logger,
                 event_callback: Callable[[logging.Logger, Any], None]):
        self._event_callback = event_callback
        self._logger = logger
        self._mutex = mutex
        self._listener = False
        self._is_healthy = False
        if self.TLS_VERIFY.lower() == "false":
            self.TLS_VERIFY = False
        if not self.TLS_VERIFY:
            urllib3.disable_warnings()

    def start_invoice_listener(self):
        if self._listener:
            self._logger.warning("LND invoice listener already started")
            return
        self._logger.info("Starting LND invoice listener thread")
        self._listener = threading.Thread(target=self._listen_for_invoices)
        self._listener.start()

    def set_healthy(self, ok: bool) -> None:
        with self._mutex:
            self._is_healthy = ok

    def get_healthy(self) -> bool:
        with self._mutex:
            ok = self._is_healthy
        return ok

    def create_invoice(self, amount_msat: int, remittance_info: str, expiry: int = 86400):
        with requests.Session() as session:
            session.proxies = {'http': self.SOCKS5H_PROXY, 'https': self.SOCKS5H_PROXY}
            description = remittance_info
            d_hasher = hashlib.sha256(description.encode('UTF-8'))
            description_hashed = base64.b64encode(d_hasher.digest())
            headers = {"Content-Type": "application/json; charset=utf-8",
                       "Grpc-Metadata-macaroon": self.INVOICE_MACAROON}
            data = {"value_msat": amount_msat,
                    "memo": description,
                    "description_hash": description_hashed.decode("UTF-8"),
                    "expiry": expiry}
            json_data = json.dumps(data)
            self._logger.debug("Sending to LND: ")
            self._logger.debug(json_data)
            response = session.post(self.LND_RESTADDR + "/v1/invoices", headers=headers, data=json_data,
                                    verify=self.TLS_VERIFY)
            self._logger.debug("LND response " + str(response.json()))
        if response.status_code != 200:
            self._logger.error("No 200 from lnd: ")
            self._logger.error(response.json())
            self._logger.error(response.headers)
            return ""

        return response.json()

    def _listen_for_invoices(self):
        retry_secs = 1
        # start endless loop
        while True:
            url = self.LND_RESTADDR + '/v1/invoices/subscribe'
            retry_secs = 2 * retry_secs
            session = requests.Session()
            session.proxies = {'http': self.SOCKS5H_PROXY, 'https': self.SOCKS5H_PROXY}
            headers = {'Grpc-Metadata-macaroon': self.INVOICE_MACAROON}
            self._logger.debug("Sending invoice subscribe to LND")
            try:
                self.set_healthy(True)
                self._response_stream = session.get(url, headers=headers, stream=True, verify=self.TLS_VERIFY)
                try:
                    for raw_response in self._response_stream.iter_lines():
                        json_response = json.loads(raw_response)
                        if 'error' in json_response:
                            self._logger.error(f"ERROR from LND: {json_response['error']}")
                            self.set_healthy(False)
                        else:
                            retry_secs = 1
                            self.set_healthy(True)
                            with self._mutex:
                                self._event_callback(self._logger, json_response)
                            self._logger.debug(f"Got streamed from LND: {raw_response}")
                except ChunkedEncodingError:
                    self._logger.warning("LND ChunkedEncodingError closed subscription")
            except requests.exceptions.InvalidSchema:
                self._logger.error(f"LND not reachable at {self.LND_RESTADDR}")
            except requests.exceptions.SSLError:
                self._logger.error("LND certificate verify failed")

            self._logger.info(f"LND hung up, retrying in {retry_secs} seconds")
            self.set_healthy(False)
            time.sleep(retry_secs)
