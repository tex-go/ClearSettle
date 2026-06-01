# Parser Development Workflow

Purpose: Build robust parsers for new marketplaces and report formats.

Steps
1. `ecommerce-agent` and `product-manager-agent` collect sample reports and schema expectations.
2. `parser-agent` implements autodetection and parsing with provenance metadata.
3. `reconciliation-agent` validates parsed outputs against business rules and produces parity tests.
4. `qa-agent` runs edge-case and fuzz tests; `database-agent` verifies storage schema compatibility.
5. `documentation-agent` publishes parser contract and sample files.

Acceptance
- Parsers must pass parity tests and provide a confidence score; unknown formats trigger manual review flows.
