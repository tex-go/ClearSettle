# ClearSettle Backend Log Observation Guide

How to watch backend logs in real-time while testing mobile uploads from an Android device.

---

## Setup

1. Connect your Android phone via USB (or on the same Wi-Fi network)
2. Start the backend (Docker or local)
3. Upload a report from the mobile app
4. Watch the log stream below

---

## Option 1 — Docker (recommended for local dev)

```bash
docker logs -f backend
```

To filter only ingestion-related lines:

```bash
docker logs -f backend 2>&1 | grep -E "\[(INFO|WARNING|ERROR)\].*ingestion|pipeline|parser|ledger|recon|upload|dashboard"
```

To see only errors:

```bash
docker logs -f backend 2>&1 | grep "\[ERROR\]"
```

Full command with timestamps:

```bash
docker logs -f --timestamps backend
```

---

## Option 2 — Log file (if running without Docker)

```bash
tail -f logs/clearsettle.log
```

Or redirect output when starting the server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1 | tee logs/clearsettle.log
```

Then watch in another terminal:

```bash
tail -f logs/clearsettle.log | grep -E "\[INFO\]|\[WARNING\]|\[ERROR\]"
```

---

## Option 3 — Google Cloud Run

```bash
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=clearsettle-backend" \
  --format="value(textPayload)"
```

Or use the Cloud Console:
1. Cloud Run → clearsettle-backend → Logs tab
2. Filter: `textPayload =~ "\[(INFO|WARNING|ERROR)\]"`

---

## Option 4 — VS Code Terminal (live monitoring)

1. Open VS Code integrated terminal  
2. Run the backend directly:
   ```bash
   cd clearsettle-app/backend
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
3. In a **second** terminal tab, filter the output:
   ```bash
   # PowerShell
   docker logs -f backend | Select-String -Pattern "\[(INFO|WARNING|ERROR)\]"
   
   # Bash
   docker logs -f backend | grep --line-buffered -E "\[(INFO|WARNING|ERROR)\]"
   ```

---

## What to Expect During a Successful Upload

When you upload `tip_top_payment_report_april2026.xlsx` from the mobile app, you should see:

```
[INFO]    ... | app.routers.ingestion   | Upload received file=tip_top_payment_report_april2026.xlsx bytes=245760 company=<uuid>
[INFO]    ... | app.routers.ingestion   | File saved file_id=<uuid>
[INFO]    ... | app.routers.ingestion   | Pipeline started file_id=<uuid>
[INFO]    ... | pipeline.router         | Fingerprinting 'tip_top_payment_report_april2026.xlsx' (245760 bytes)
[INFO]    ... | pipeline.router         | Fingerprint complete: 5 sheet(s), 87 unique columns, sig=a3f9c2...
[INFO]    ... | pipeline.router         | Platform=flipkart confidence=96.50% signals=12
[INFO]    ... | app.routers.ingestion   | Platform detected platform=flipkart confidence=0.97 needs_review=False
[INFO]    ... | pipeline.router         | Report type=payment_report confidence=98.00%
[INFO]    ... | pipeline.router         | Schema version=v2_payment parser=flipkart_payment_parser match=94.00%
[INFO]    ... | app.routers.ingestion   | Parser selected parser=flipkart_payment_parser schema=v2_payment report_type=payment_report
[INFO]    ... | pipeline.router         | Running parser flipkart_payment_parser
[INFO]    ... | pipeline.router         | Parse complete: 523 ledger records, 3 recon issues
[INFO]    ... | app.routers.ingestion   | Records parsed count=523 recon_issues=3
[INFO]    ... | app.routers.ingestion   | Ledger creation started file_id=<uuid> records=523
[INFO]    ... | app.routers.ingestion   | Ledger records created count=523 file_id=<uuid>
[INFO]    ... | app.routers.ingestion   | Reconciliation completed recon_issues=3 file_id=<uuid>
[INFO]    ... | app.routers.ingestion   | Dashboard metrics generated platform=flipkart type=payment_report ledger=523 status=done file_id=<uuid>
```

---

## Common Error Patterns

### Column mapping failed
```
[ERROR]   ... | pipeline.router | Parser raised unexpected exception: KeyError 'Settlement ID'
```
**Fix:** The Excel sheet uses a non-standard column name. Check `flipkart_column_aliases.dart` / `payment_parser.py`.

### Platform not detected
```
[WARNING] ... | pipeline.router | Platform confidence 45.00% below threshold — file flagged for manual review
```
**Fix:** Upload with explicit hint: `platform=flipkart` in the form fields, or use the Manual Review endpoint.

### File too large
```
[ERROR]   ... | app.routers.ingestion | 413 File too large. Max 100 MB.
```

### Database migration pending
```
[ERROR]   ... | app.routers.ingestion | Database error: column "xxx" does not exist. Run 'alembic upgrade head'
```
**Fix:** `cd clearsettle-app/backend && alembic upgrade head`

---

## Log Levels

| Level     | Meaning                                             |
|-----------|-----------------------------------------------------|
| `[INFO]`  | Normal progress — each stage of the pipeline        |
| `[WARNING]` | Non-fatal issue — low confidence, schema drift, fallback |
| `[ERROR]` | Processing failed — check error= field for details  |
| `[DEBUG]` | Verbose detail — enable with `LOG_LEVEL=DEBUG`      |

---

## Set Log Level

```bash
# In docker-compose.yml or shell:
LOG_LEVEL=DEBUG docker-compose up

# Or in .env:
LOG_LEVEL=DEBUG
```

---

## Android Phone → Laptop Setup

1. Ensure phone and laptop are on the same network, OR use USB tethering
2. In mobile app, the `API_BASE_URL` build var should point to your laptop's IP:
   ```
   --dart-define=API_BASE_URL=http://192.168.1.x:8000
   ```
3. Start backend: `docker-compose up` (binds to `0.0.0.0:8000`)
4. Upload report from phone → watch logs on laptop terminal
5. The complete flow from upload to dashboard data takes ~5–30 seconds depending on file size
