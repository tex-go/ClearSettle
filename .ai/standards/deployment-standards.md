# Production Deployment Standards
**Version:** 1.0 | **Owner:** `devops-agent`

Every production deployment follows this protocol. No exceptions. Deviations require `ceo-agent` approval and ADR documentation.

---

## Pre-Deployment Checklist

Before issuing the deploy command:
- [ ] `release-gatekeeper-agent` has issued PASS for this release
- [ ] Staging deployment is healthy and validated
- [ ] Rollback plan is documented and tested
- [ ] Database backup completed within last 2 hours
- [ ] Deploy window is within allowed hours (avoid midnight deploys)
- [ ] Team is available to monitor for 2 hours post-deploy
- [ ] `release-manager-agent` has given go-ahead

---

## Deployment Sequence

```bash
# Step 1: Pull latest release code
git checkout main
git pull origin main
git checkout tags/vX.Y.Z

# Step 2: Create host directories if not present
mkdir -p /opt/clearsettle/certbot/www
mkdir -p /opt/clearsettle/certbot/certs
mkdir -p /opt/clearsettle/uploads

# Step 3: Validate .env.prod
# Verify POSTGRES_PASSWORD contains no @ / # ? characters (URL-safety check)
# Verify SECRET_KEY, ENCRYPTION_KEY, REDIS_PASSWORD are set

# Step 4: Build and start containers
docker compose -f docker-compose.prod.yml --env-file .env.prod up --build -d

# Step 5: Wait for all containers healthy (max 120 seconds)
timeout 120 bash -c "until docker compose ps | grep -E '(unhealthy|starting)' | wc -l | grep -q '^0$'; do sleep 5; done"

# Step 6: Run migrations
docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T backend \
  alembic upgrade head

# Step 7: Health check
docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T backend \
  python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Step 8: Smoke test
curl -sf https://clearsettle.in/health
curl -sf https://clearsettle.in/api/health

# Step 9: Verify all containers
docker compose -f docker-compose.prod.yml --env-file .env.prod ps
```

---

## Health Check Endpoints

| Service | Endpoint | Expected Response | Timeout |
|---|---|---|---|
| Backend | `/health` | `200 {"status": "ok"}` | 5s |
| Frontend | `http://localhost:3000/` | `200` HTML | 5s |
| Nginx | `nginx -t` | config OK | 5s |
| Database | `pg_isready -U user -d db` | accepting connections | 5s |
| Redis | `redis-cli ping` | PONG | 5s |

All health checks must pass within 60 seconds of container start or deployment is aborted.

---

## Rollback Protocol

Automatic rollback triggers:
- Error rate > 1% of requests (monitor for 30 min post-deploy)
- `/health` endpoint returning non-200
- Migration failure at any point
- Any `release-gatekeeper-agent` smoke test failure

Manual rollback command:
```bash
# Rollback containers to previous image
docker compose -f docker-compose.prod.yml --env-file .env.prod down
# Restore previous images (from previous build digest)
docker tag clearsettle-backend:previous clearsettle-backend:latest
docker tag clearsettle-frontend:previous clearsettle-frontend:latest
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Rollback migration if applied
docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T backend \
  alembic downgrade -1

# Verify rollback
docker compose -f docker-compose.prod.yml --env-file .env.prod ps
curl -sf https://clearsettle.in/health
```

---

## Environment Variable Safety Rules

Passwords and secrets must NOT contain URL-special characters when used in DATABASE_URL construction:
- Forbidden in passwords used in DATABASE_URL: `@`, `/`, `#`, `?`, `%`
- Generate passwords using: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
- Test the resulting DATABASE_URL can be parsed before deploying

---

## SSL/TLS Requirements

- HTTPS enforced on all production traffic (no HTTP except ACME challenge)
- TLS 1.2 minimum, TLS 1.3 preferred
- Certificate auto-renewal via certbot (every 12h renewal attempt)
- SSL certificate validity check before deploy: `openssl s_client -connect clearsettle.in:443`
- HSTS header: `max-age=63072000; includeSubDomains; preload`

---

## Deployment Monitoring (Post-Deploy)

Monitor these metrics for 2 hours after every production deploy:

| Metric | Alert Threshold | Action |
|---|---|---|
| HTTP error rate (5xx) | > 0.5% | Investigate immediately |
| HTTP error rate (5xx) | > 1% | Trigger rollback |
| Response time (p99) | > 2000ms | Investigate |
| Response time (p99) | > 5000ms | Trigger rollback |
| Database connection pool | > 80% utilized | Scale or optimize |
| Migration execution time | > 60 seconds | Investigate (may indicate table lock) |
| Container restart count | > 1 | Investigate |

---

## Blue/Green Deployment (Target State)

Current: single-instance deploy with downtime risk.

Target (v2.0): Zero-downtime blue/green:
1. New "green" environment deployed alongside existing "blue"
2. Health checks pass on green
3. Load balancer switches traffic to green
4. Blue retained for 30-minute rollback window
5. Blue terminated after validation complete

`devops-agent` to implement in v2.0 milestone.
