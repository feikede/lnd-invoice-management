# LND Invoice Management

2024 by Rainer Feike -
V0.9 - not to use in production

Creating lightning invoices on your lnd instance is simple with lncli. rest or gRPC. But subscribing to updates with
observables is pain in the ass,
and most of the time it's not your apps business to keep streaming connections open.
That's what this service is about. It wraps lightning invoicing with lnd in kind of PayPal like interface.

Or how ChatGPT describes it: "Streamlining lightning invoice creation on your lnd instance is a breeze with lncli,
whether through REST or gRPC. However, staying updated with observables can be a cumbersome process, often diverting
attention from your application's core functions. Enter our service: designed to simplify lightning invoicing with lnd,
it offers a user-friendly interface reminiscent of PayPal, eliminating the need for constant streaming connections and
allowing you to focus on your app's essential tasks."

# Create invoice request

```
POST http://localhost:8080/v1/invoice
```

with POST body like

```
{
    "amount_msat": 6000, 
    "callback_uri": "http://localhost:3246", 
    "remittance_info": "hallo 2323", 
    "magic_code": "6545", 
    "secret": "not_to_know"
}
```

# Invoice created notification

This is sent to your callback_uri when the invoice is created by lnd. Show the 'lnd_invoice_data.payment_request' to
your payee (as QR Code or whatever).

```
POST / HTTP/1.1
Host: localhost:3246
User-Agent: python-requests/2.31.0
Accept-Encoding: gzip, deflate
Accept: */*
Connection: keep-alive
Content-Type: application/json; charset=utf-8
Content-Length: 1350

{
  "remittance_info": "hallo 2323",
  "amount_msat": 6000,
  "magic_code": "6545",
  "timestamp": 1712506538,
  "lnd_invoice_data": "{'memo': '', 'r_preimage': 'Sxxxxxxxxxs=', 'r_hash': 'GUxxxxxxxxx8o=', 'value': '6', 'value_msat': '6000', 'settled': False, 'creation_date': '1712506538', 'settle_date': '0', 'payment_request': 'lnbc60nxxxxxxxxxxxxxxxxxxxmwvq', 'description_hash': 'mo2xxxxxxxxxU=', 'expiry': '86400', 'fallback_addr': '', 'cltv_expiry': '80', 'route_hints': [], 'private': False, 'add_index': '883', 'settle_index': '0', 'amt_paid': '0', 'amt_paid_sat': '0', 'amt_paid_msat': '0', 'state': 'OPEN', 'htlcs': [], 'features': {'9': {'name': 'tlv-onion', 'is_required': False, 'is_known': True}, '14': {'name': 'payment-addr', 'is_required': True, 'is_known': True}, '17': {'name': 'multi-path-payments', 'is_required': False, 'is_known': True}}, 'is_keysend': False, 'payment_addr': 'BTxxxxxxxxxQ=', 'is_amp': False, 'amp_invoice_state': {}}"
}
```

# Invoice settled notification

This is sent to your callback_uri when the invoice is paid.

```
POST / HTTP/1.1
Host: localhost:3246
User-Agent: python-requests/2.31.0
Accept-Encoding: gzip, deflate
Accept: */*
Connection: keep-alive
Content-Type: application/json; charset=utf-8
Content-Length: 1637

{
  "remittance_info": "hallo 2323",
  "amount_msat": 6000,
  "magic_code": "6545",
  "timestamp": 1712506538,
  "lnd_invoice_data": "{'memo': '', 'r_preimage': 'S3+apxxxxxxxxxAcs=', 'r_hash': 'GUxxxxxxxxx48o=', 'value': '6', 'value_msat': '6000', 'settled': True, 'creation_date': '1712506538', 'settle_date': '1712506581', 'payment_request': 'lnbc60xxxxxxxxxzsqzxmwvq', 'description_hash': 'mo2ZU9xxxxxxxxxekuDU=', 'expiry': '86400', 'fallback_addr': '', 'cltv_expiry': '80', 'route_hints': [], 'private': False, 'add_index': '883', 'settle_index': '353', 'amt_paid': '6000', 'amt_paid_sat': '6', 'amt_paid_msat': '6000', 'state': 'SETTLED', 'htlcs': [{'chan_id': '7xxxxxxxxxx', 'htlc_index': '418', 'amt_msat': '6000', 'accept_height': 838157, 'accept_time': '1712506581', 'resolve_time': '1712506581', 'expiry_height': 838240, 'state': 'SETTLED', 'custom_records': {}, 'mpp_total_amt_msat': '6000', 'amp': None}], 'features': {'9': {'name': 'tlv-onion', 'is_required': False, 'is_known': True}, '14': {'name': 'payment-addr', 'is_required': True, 'is_known': True}, '17': {'name': 'multi-path-payments', 'is_required': False, 'is_known': True}}, 'is_keysend': False, 'payment_addr': 'BTxxxxxxxxxQ=', 'is_amp': False, 'amp_invoice_state': {}}"
}
```
