# CareerAutomated Multi-ATS Job Crawler — Operational Playbook

This document serves as the operational guide for deploying, monitoring, scaling, and managing the multi-ATS job discovery crawler in a production Virtual Machine (VM) environment.

---

## 1. Deployment Architecture Overview

The crawler is designed to run inside a Linux VM managed via **Dokploy** or **Docker Compose** with **PostgreSQL** as the operational database.

```
                    ┌──────────────────────────────────────────┐
                    │               Linux VM                   │
                    │                                          │
                    │   ┌──────────────────────────────────┐   │
                    │   │       career_worker              │   │
                    │   │   (mass_scheduler.py)            │   │
                    │   └────────────────┬─────────────────┘   │
                    │                    │                     │
                    │                    ▼                     │
                    │   ┌──────────────────────────────────┐   │
                    │   │   dokploy-postgres:5432          │   │
                    │   │   (careerautomated_operational)  │   │
                    │   └──────────────────────────────────┘   │
                    └──────────────────────────────────────────┘
```

* **Production Environment:** Runs inside Docker/Dokploy on the remote VM using PostgreSQL (`OPERATIONAL_DATABASE_URL`).
* **Local Machine Policy:** Crawlers MUST NOT run on local developer machines during normal operation. Local runs are strictly restricted to testing/dry-runs using SQLite (`data/crm.db`).

---

## 2. Environment Configuration (.env)

Ensure the `.env` file on the production VM contains the following:

```ini
APP_ENV=production
ENABLE_LOCAL_FALLBACKS=false

# Database Configuration
OPERATIONAL_DATABASE_URL="postgresql://dokploy:OMMlZ2BA9JiCKKVS5daTcXxYEbNcJCtu@dokploy-postgres:5432/careerautomated_operational"
AUTH_DATABASE_URL="postgresql://postgres.sxhlclcfznqqvayvljoe:2D99e76r%29f_.GPD@aws-1-ap-south-1.pooler.supabase.com:6543/postgres"

# Worker Parameters
MASS_CONCURRENCY=20
CRAWLER_POLL_INTERVAL=5
```

---

## 3. Running & Deploying on VM (Dokploy / Docker)

### Deploying via Docker Compose

```bash
# Build and launch background services
docker-compose up -d --build worker
```

### Checking Worker Logs

```bash
# Stream live crawler logs
docker logs -f career_worker --tail 100
```

### Scaling Worker Concurrency

To adjust concurrency without redeploying code:

```bash
docker exec -it career_worker bash -c "MASS_CONCURRENCY=30 python3 src/workers/mass_scheduler.py"
```

---

## 4. Monitoring & Health Verification

### Inspecting Crawler Progress via SQL

Connect to the PostgreSQL operational database to check progress:

```sql
-- Check total normalized jobs by provider
SELECT provider, COUNT(*) 
FROM normalized_jobs 
GROUP BY provider 
ORDER BY COUNT(*) DESC;

-- Check remaining queue backlog
SELECT provider_id, COUNT(*) 
FROM ats_registry 
WHERE status = 'ACTIVE' AND (next_check_at_tz IS NULL OR next_check_at_tz <= NOW()) 
GROUP BY provider_id 
ORDER BY COUNT(*) DESC;

-- Check failed company backoffs
SELECT provider_id, COUNT(*), SUM(failure_count) 
FROM ats_registry 
WHERE failure_count > 0 
GROUP BY provider_id;
```

---

## 5. Graceful Shutdown & Restart Procedures

The `mass_scheduler.py` engine handles `SIGTERM` and `SIGINT` signals gracefully by allowing active board sync sessions to complete and releasing active `reservation_token` leases.

### Graceful Restart

```bash
# Send graceful shutdown signal to Docker container
docker stop --time=30 career_worker

# Restart container
docker start career_worker
```

---

## 6. Failure Recovery Procedures

### Resetting Stuck Leases

If a worker crashes abruptly, reservations naturally expire after 300 seconds (`reserved_until_tz`). To manually reset stuck reservations immediately:

```sql
UPDATE ats_registry
SET reservation_token = NULL,
    reserved_by = NULL,
    reserved_until_tz = NULL
WHERE reserved_until_tz <= NOW();
```

### Re-queuing Failed Endpoints

To reset backoff retry schedules for failed endpoints:

```sql
UPDATE ats_registry
SET failure_count = 0,
    next_check_at_tz = NOW()
WHERE failure_count > 0;
```
