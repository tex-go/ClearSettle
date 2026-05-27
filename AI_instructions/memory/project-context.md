# Project Context

## What is ClearSettle
ClearSettle is a production SaaS for Indian eCommerce marketplace sellers.
It surfaces settlement discrepancies, automates dispute filing, and recovers
owed amounts (commission overcharges, GST/TCS, missing payouts, return fraud).

## Core Product Pillars
- Settlement intelligence (discrepancy detection across Amazon, Flipkart, Meesho, Myntra, etc.)
- Dispute automation (raise and track disputes against platforms)
- GST / TCS recovery (cross-reference marketplace deductions with GST filings)
- Bank reconciliation (match bank credits against platform payouts)
- Seller analytics (revenue, fees, refunds, profitability per SKU)

## Technical Profile
- API-first, multi-tenant, enterprise-ready
- Security-sensitive (fintech-grade: JWT, bcrypt, JTI revocation, CORS, HSTS)
- Scaling-focused (async architecture, company_id isolation, no shared state)
- Observability: structured logging via Python logging module
- Deployment: Docker Compose on Linux VMs; staging (dev branch) + production (tagged releases)

## Active Marketplaces
Amazon, Flipkart, Meesho, Myntra, Ajio, Nykaa, Snapdeal, JioMart, IndiaMART

## Data Sensitivity
- Seller PII (name, email, phone, GSTIN, PAN, address)
- Financial data (settlements, payouts, commissions)
- Marketplace API credentials (per-tenant, encrypted at rest)
- All data is company-scoped — zero cross-tenant leakage tolerance

## Team / Ownership
- Owner: Ranjith (sudo.ranjith@gmail.com)
- Git user: tex-go
- Repo: github.com/tex-go/ClearSettle
- Main branch: main (production-gated)
- Dev branch: dev (CI + staging auto-deploy)

## Current Version
1.0.0 (see VERSION file at repo root)
