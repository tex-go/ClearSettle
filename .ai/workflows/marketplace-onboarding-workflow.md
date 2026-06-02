# Marketplace Onboarding Workflow

Purpose: Onboard a new marketplace (e.g., Amazon, Meesho, Myntra).

Steps
1. `ecommerce-agent` requests sample reports and mapping documentation.
2. `parser-agent` creates detection rules and extractors.
3. `reconciliation-agent` validates calculations using normalization.
4. `database-agent` updates schema if needed (new fields) with migration plan.
5. `qa-agent` runs exploratory tests on representative datasets.
6. `devops-agent` deploys parser to staging and monitors for errors.

Acceptance
- Parity with marketplace reports and signed-off test corpus.
