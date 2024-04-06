# LND Invoice Management

2024 by Rainer Feike

Creating lightning invoices on your lnd instance is simple with lncli. rest or gRPC. But subscribing to updates with
observables is pain in the ass,
and most of the time it's not your apps business to keep streaming connections open.
That's what this service is about. It wraps lightning invoicing with lnd in kind of PayPal like interface.

Or how ChatGPT describes it: "Streamlining lightning invoice creation on your lnd instance is a breeze with lncli,
whether through REST or gRPC. However, staying updated with observables can be a cumbersome process, often diverting
attention from your application's core functions. Enter our service: designed to simplify lightning invoicing with lnd,
it offers a user-friendly interface reminiscent of PayPal, eliminating the need for constant streaming connections and
allowing you to focus on your app's essential tasks."