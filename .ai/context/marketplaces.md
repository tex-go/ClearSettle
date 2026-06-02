# Marketplace Context

Current marketplace: Flipkart

Planned marketplaces: Amazon, Meesho, Myntra, Ajio, Shopify, WooCommerce

Per-marketplace notes
- Flipkart: existing parsers live in repo; reports include payment-ledger, settlement, order-exports.
- Amazon: SP API integrations planned (credentials, reports) — backend has `sp_api` router placeholder.

Normalization
- Agents must convert marketplace fields into canonical models: `Order`, `Settlement`, `Fee`, `Tax`, `Refund`, `Adjustment`.
