# ClearSettle — Amazon SP-API Test Harness

A standalone developer utility to validate Amazon SP-API integration
before production deployment. Tests credentials, OAuth, Sellers API,
Reports API, and sandbox connectivity.

---

## Files

| File | Purpose |
|---|---|
| `amazon_health_check.py` | **Start here** — one-command readiness summary |
| `amazon_credentials_validator.py` | Validate every credential with detailed diagnostics |
| `amazon_oauth_test.py` | Test LWA token exchange and token metadata |
| `amazon_seller_test.py` | Call getMarketplaceParticipations and show results |
| `amazon_reports_test.py` | Test createReport / getReport / settlement types |
| `amazon_sandbox_test.py` | Probe all sandbox regions for connectivity and latency |
| `amazon_sp_api_test.py` | Full pytest-compatible integration test suite |
| `_sp_client.py` | Shared client (LWA exchange, SigV4 signing, logging) |
| `.env.example` | Environment variable template |

---

## 1. How to Obtain Amazon SP-API Credentials

### Step 1 — Create or locate your SP-API app

1. Log in to **Seller Central** at https://sellercentral.amazon.in
2. Navigate to **Apps & Services → Develop Apps**
3. You will see `clear_settle_test` and `clear_settle_prod` apps
4. Click **Edit App** on the app you want to test

### Step 2 — Get LWA credentials

In the app detail page, under **Credentials**:

| Field | Where to find |
|---|---|
| `LWA_CLIENT_ID` | Listed as "App client ID" — format `amzn1.application-oa2-client.*` |
| `LWA_CLIENT_SECRET` | Click **Show** next to Client Secret |

### Step 3 — Authorise the app (get refresh token)

**For `clear_settle_test` (your own seller account):**
1. In the app page, click **Authorise** (self-authorisation)
2. Complete the OAuth flow
3. The resulting **refresh token** starts with `Atzr|`

**For `clear_settle_prod` (third-party sellers):**
Sellers authorise via the OAuth redirect flow:
```
https://sellercentral.amazon.in/apps/authorize/consent
  ?application_id=<APP_ID>
  &state=<STATE>
  &redirect_uri=https://clearsettle.in/api/sp-api/callback
  &version=beta
```
The callback receives `spapi_oauth_code` — exchange it for a refresh token.

### Step 4 — Create an IAM user / policy

1. Open **AWS Console → IAM → Users → Create user**
2. Attach the following inline policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "execute-api:Invoke",
      "Resource": "arn:aws:execute-api:*:*:*"
    }
  ]
}
```

3. Under **Security credentials**, create an **Access key**
4. Save the `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`

---

## 2. How to Configure `.env`

```bash
# Copy the template
cp .env.example .env

# Edit with your values
nano .env
```

Minimum required fields:

```env
LWA_CLIENT_ID=amzn1.application-oa2-client.<32hex>
LWA_CLIENT_SECRET=amzn1.oa2-cs.v1.<...>
LWA_REFRESH_TOKEN=Atzr|IwEB...
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=<secret>
SP_API_ENDPOINT=https://sandbox.sellingpartnerapi-eu.amazon.com
```

**Start with the sandbox endpoint** — change to production only after all
sandbox tests pass.

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. How to Run Sandbox Tests

Always test against sandbox first. Sandbox uses real credentials but
returns static, predictable data.

```bash
# Ensure SP_API_ENDPOINT points to sandbox in .env
# SP_API_ENDPOINT=https://sandbox.sellingpartnerapi-eu.amazon.com

# Run the health check first
python amazon_health_check.py

# Run individual tests
python amazon_credentials_validator.py
python amazon_oauth_test.py
python amazon_seller_test.py
python amazon_reports_test.py
python amazon_sandbox_test.py

# Run the full suite
python amazon_sp_api_test.py

# Or with pytest for detailed output
pytest amazon_sp_api_test.py -v --tb=short
```

### Expected sandbox health check output

```
═════════════════════════════════════════════════════════════════
  ClearSettle  Amazon SP-API — Health Check
═════════════════════════════════════════════════════════════════
  ✅  Environment variables       all set  [SANDBOX: https://sandbox...]
  ✅  AWS credentials (STS)       Account=123456789012  (234ms)
  ✅  OAuth / LWA token           obtained  expires in 3600s  (412ms)
  ✅  Sellers API                 1 marketplace(s)  (389ms)
  ✅  Reports API                 accessible  (201ms)
  ✅  Sandbox (EU)                HTTP 200  (341ms)
─────────────────────────────────────────────────────────────────
  Checks passed  6/6
  Total time     1.8s
─────────────────────────────────────────────────────────────────
  ALL CHECKS PASSED ✅  ClearSettle SP-API integration is ready.
═════════════════════════════════════════════════════════════════
```

---

## 5. How to Run Production Tests

After all sandbox tests pass:

1. Update `.env`:

```env
SP_API_ENDPOINT=https://sellingpartnerapi-eu.amazon.com
```

2. Ensure the SP-API app is **published** (not in Draft state):
   - Seller Central → Develop Apps → Edit App → **Submit for review** / Publish

3. Run the same test sequence:

```bash
python amazon_health_check.py
python amazon_seller_test.py
python amazon_reports_test.py
```

**Production safety rules:**
- `amazon_reports_test.py` creates a real report request but does not download data
- No financial data is modified by any test script
- All tests are read-only or create minimal report requests

---

## 6. Common SP-API Errors

### LWA / OAuth errors

| Error | Cause | Fix |
|---|---|---|
| `invalid_client` | Wrong `LWA_CLIENT_ID` or `LWA_CLIENT_SECRET` | Re-copy from Seller Central → Develop Apps |
| `invalid_grant` | Refresh token expired or revoked | Re-authorise the app in Seller Central |
| `unauthorized_client` | App in Draft state | Publish the app or use self-authorisation |
| `access_denied` | Seller revoked the app's access | Re-initiate the OAuth flow with the seller |

### AWS / SigV4 errors

| Error | Cause | Fix |
|---|---|---|
| `InvalidClientTokenId` | `AWS_ACCESS_KEY_ID` is wrong or key deactivated | Verify in IAM console |
| `SignatureDoesNotMatch` | `AWS_SECRET_ACCESS_KEY` is wrong | Re-copy the secret key (it cannot be retrieved after creation) |
| `ExpiredToken` | Using temporary STS credentials that expired | Refresh via `AssumeRole` or use long-term credentials |
| `AccessDenied` | IAM policy missing `execute-api:Invoke` | Add the policy above to the IAM user/role |

### SP-API errors

| HTTP | Code | Cause | Fix |
|---|---|---|---|
| 401 | `Unauthorized` | Invalid or expired access token | Check LWA token exchange |
| 403 | `Forbidden` | App not authorised for this seller | Seller must re-authorise, or app needs publishing |
| 403 | `AccessDenied` | IAM policy doesn't allow this SP-API endpoint | Check IAM policy |
| 400 | `InvalidInput` | Bad request parameters | Check request body / query params |
| 400 | `InvalidMarketplace` | Marketplace ID not valid for this seller | Use a marketplace the seller is enrolled in |
| 429 | `QuotaExceeded` | Rate limit hit | Back off and retry (exponential) |
| 500 | `InternalServerError` | Amazon-side error | Retry after a few seconds |

### App-specific errors

| Error | Cause | Fix |
|---|---|---|
| MD9100 | App set to Self-Authorization only | Change to Third-Party OAuth in the SP-API portal |
| `Application … is not an authorized marketplace application` | App not approved for this marketplace | Submit the app for Amazon's review |

---

## 7. Troubleshooting Guide

### "Cannot connect to SP_API_ENDPOINT"

1. Check internet connectivity from the test machine
2. Verify `SP_API_ENDPOINT` is a valid URL
3. Try: `curl -I https://sellingpartnerapi-eu.amazon.com`

### "SignatureDoesNotMatch" on every request

1. Check `AWS_REGION` matches the endpoint:
   - EU/India → `eu-west-1`
   - NA       → `us-east-1`
   - FE       → `us-west-2`
2. Verify system clock is correct (SigV4 is time-sensitive):
   ```bash
   date -u
   # Must be within 5 minutes of UTC
   ```
3. Ensure `AWS_SECRET_ACCESS_KEY` has no leading/trailing whitespace in `.env`

### "403 Forbidden" on Sellers / Reports API (even though OAuth works)

1. Check the app is not in **Draft** state:
   - Seller Central → Develop Apps → Status column
2. For `clear_settle_prod`: ensure the seller has completed the OAuth authorisation flow
3. For self-authorisation (`clear_settle_test`): ensure you clicked "Authorise" for your own account

### Google Sign-In works but SP-API doesn't

These are independent authentication systems. SP-API issues mean:
- The LWA refresh token may not be stored correctly in the backend
- Check the `SP_API_REFRESH_TOKEN` in the ClearSettle backend `.env` on the VM

### Reports API returns 400 "InvalidInput"

The `GET_FLAT_FILE_OPEN_LISTINGS_DATA` report type requires the seller to have
active listings in the specified marketplace. Try:
- A different marketplace ID if the seller isn't active in India
- `GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE` (settlement reports are always available)

### Sandbox returns 200 but Production returns 403

Expected when the SP-API app is still in Draft/pending review state. Sandbox
bypasses authorisation checks; production does not.

---

## Architecture Notes

```
.env
 └─ SPAPIConfig (from_env)
      ├─ LWA token exchange (POST api.amazon.com/auth/o2/token)
      │    └─ LWAToken (access_token, expires_in)
      ├─ AWS credentials
      │    ├─ Direct: AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY
      │    └─ Assumed role: STS AssumeRole → temp credentials
      └─ SigV4 signing (_sp_client.sigv4_headers)
           └─ SPAPIClient.request(method, path, params, body)
                └─ SP-API endpoint (sellers / reports / orders / ...)
```

All signing is implemented in pure Python (`hmac`, `hashlib`) — no `boto3`
dependency required. The `_sp_client.py` module is the only shared dependency
across all test scripts.

---

## Security Notes

- **Secrets are never printed**: client secret, refresh token, and AWS secret key
  are always masked in output (e.g. `amzn1.app***Vh`)
- **`.env` is gitignored** — never commit it
- **Logs** only contain masked values and non-sensitive metadata
- These scripts are read-only test utilities — they do not modify any seller data
