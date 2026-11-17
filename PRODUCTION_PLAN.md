# PRODUCTION_PLAN — hardening mini-hr for a complete GitHub release

> Companion to `PLAN.md`. `PLAN.md` says **what to build** (RAG, HR tables, recruiting, eval).
> This file says **what must wrap around it** so the repo looks and behaves like a real,
> production-grade project — without deploying to a server.

**Scope decision:** no VPS, no domain, no HTTPS, no public demo. "Production-grade" here means:
anyone can clone, run in one command, run the tests, read the code, and trust it.

---

## 0. How this plan fits into PLAN.md

The hardening track is called **H0–H9**. Each H-stage is attached to a main stage so you
never do a big hardening pass at the end.

| H-stage | What | Do it alongside |
|---|---|---|
| H0 | Dev tooling + repo hygiene | Stage 0 |
| H1 | CI (GitHub Actions) | Stage 0 / Stage 1 |
| H2 | Test suite | Every stage (grows with it) |
| H3 | Real auth + admin bootstrap | Stage 1 |
| H4 | API hardening | Stage 2 + Stage 4 |
| H5 | Logging + request tracing | Stage 4 |
| H6 | LLM resilience + cost control | Stage 4 |
| H7 | Celery hardening | Stage 6 |
| H8 | Docker + data operations | Stage 6 |
| H9 | Security + open-source docs | Stage 9 |
| — | Replace Stage 8 with a local demo | Stage 8 |

**Rule:** do H0 + H1 first. CI and linting are cheap on day 1 and painful on day 60.

If time is short, the minimum set is **H0, H1, H2, H3 + the Makefile**.

---

## H0 — Dev tooling and repo hygiene

**Goal:** the repo enforces its own quality from the first commit.

- Move to `pyproject.toml` (keep `requirements.txt` generated from it, or use `uv`/`pip-tools`
  to produce a lock file). Pin versions.
- Add `ruff` (lint + format) and `mypy` (start lenient, tighten later).
- Add `.pre-commit-config.yaml`: ruff, ruff-format, end-of-file-fixer, `gitleaks`.
- Add `.editorconfig` and `.dockerignore`.
- Add a **Makefile** with at least:
  `make up`, `make down`, `make migrate`, `make seed`, `make test`, `make lint`,
  `make eval`, `make reset-db`.
- Add the folders the plan forgot: `tests/`, `eval/`, `docs/`, `.github/`.
- Keep the mini-rag commit style (`setup ...`, `update ...`, `fix ...`).

**Done when:** a fresh clone + `make up && make migrate && make seed` works, and
`pre-commit run --all-files` passes.

---

## H1 — Continuous integration (GitHub Actions)

**Goal:** every push proves the project still works.

Create `.github/workflows/ci.yml` with these jobs:

1. **lint** — `ruff check`, `ruff format --check`, `mypy src`.
2. **test** — start Postgres (with pgvector) as a service container, run
   `alembic upgrade head`, then `pytest` with coverage.
3. **migrations** — `alembic upgrade head` → `alembic downgrade -1` → `upgrade head`
   (proves rollback works; PLAN.md Stage 1 requires it).
4. **docker-build** — build the API image (no push).
5. **security** — `pip-audit` and `gitleaks`.

Also add `.github/dependabot.yml` (pip, docker, github-actions; weekly).

**Done when:** a green CI badge is in the README, and a deliberately broken commit turns it red.

---

## H2 — Test suite

**Goal:** tests run with **no API keys and no internet**.

Layout:

```
tests/
├── conftest.py            # test DB, fake LLM, fake embedder, async client
├── unit/
│   ├── test_chunking.py
│   ├── test_scoring.py          # screening formula, deterministic
│   ├── test_redaction.py
│   ├── test_access_controller.py
│   └── test_template_parser.py
├── integration/
│   ├── test_upload_process_index.py
│   ├── test_answer_with_citations.py
│   ├── test_refusal_paths.py    # empty retrieval → no LLM call
│   ├── test_screening_flow.py
│   └── test_role_access.py      # employee cannot read other departments
└── security/
    └── test_prompt_injection.py # chunk containing "ignore previous instructions"
```

Tasks:

- Implement `FakeLLMProvider` and `FakeEmbeddingProvider` through the **same factory** and
  `LLMInterface` (this is exactly why the factory pattern exists).
- Use a tiny fixed corpus in `tests/fixtures/`.
- Add `pytest-asyncio`, `pytest-cov`; fail CI under a coverage floor (start at 60%, raise later).
- Every bug fix gets a regression test.

**Done when:** `make test` passes offline; coverage report is generated in CI; the
prompt-injection test fails if you remove the sanitizer.

---

## H3 — Real authentication and admin bootstrap

**Goal:** roles are enforced by the backend, not assumed.

- Add `routes/auth.py`, `controllers/AuthController.py`, `routes/schemes/auth.py`.
- Passwords: `argon2` or `bcrypt` hashing. Never store plain text.
- JWT access token (short expiry, e.g. 30 min) with `sub`, `role`, `exp`; secret from env.
  Optional refresh token.
- FastAPI dependency `get_current_user` and `require_role(...)`; use it on **every** HR route.
- Add `signal` values: `AUTH_INVALID_CREDENTIALS`, `AUTH_TOKEN_EXPIRED`, `HR_ACCESS_DENIED`
  (keep the same response envelope).
- Bootstrap: `python -m src.scripts.create_admin` (or `make create-admin`) creates the first
  `hr_admin`. No default admin password in git.
- Startup check: refuse to start if `JWT_SECRET` is empty or equals the example value.
- Audit log: write login, upload, delete-candidate, and shortlist-view events.

**Done when:** a request without a token returns 401; an `employee` token calling an
`hr_admin` route returns 403 with the `HR_ACCESS_DENIED` signal; the audit log shows both.

---

## H4 — API hardening

**Goal:** the API behaves safely under bad input and heavy use.

- **Global exception handler:** unexpected errors return a signal response, never a stack trace.
- **Rate limiting:** `slowapi` (or Redis-based limiter). Strict on `/hr/ask` and `/screen`
  because they cost money; looser elsewhere.
- **Upload safety:** max file size from settings; check real file type (magic bytes), not
  only the extension; sanitize filenames; store under generated names (you already do this).
- **Pagination:** `limit` + `offset` (or cursor) on every list endpoint, with a max limit.
- **CORS + trusted hosts:** explicit allow-lists from settings, no `*` in the production config.
- **Request size limits** at both FastAPI and Nginx.
- **Security headers** in `nginx/default.conf` (`X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`).
- **Readiness:** `/api/v1/health` checks Postgres, vector DB, and broker; returns a clear
  per-component status. Add a separate cheap liveness endpoint.

**Done when:** tests prove oversized files, wrong file types, and excess requests are rejected
with proper signals; readiness turns red when you stop Postgres.

---

## H5 — Structured logging and request tracing

**Goal:** one request can be followed from the API to the Celery task.

- JSON logs (`python-json-logger` or `structlog`) with fields: `timestamp`, `level`,
  `request_id`, `user_id`, `route`, `duration_ms`.
- Middleware creates `X-Request-ID` (or reads it) and returns it in the response.
- Pass `request_id` into Celery task headers/kwargs and include it in task logs.
- Apply `utils/redaction.py` in the log formatter itself, so no one can forget it.
- Add log-level control from settings.

**Done when:** one `/ask` request can be traced by `request_id` across API and worker logs,
and a test confirms an email address in a CV never appears in logs.

---

## H6 — LLM resilience and cost control

**Goal:** the LLM can be slow or fail without breaking the service or the budget.

- Timeouts on every provider call (embedding, generation).
- Retry with exponential backoff on 429/5xx; do **not** retry on 4xx validation errors.
- Provider errors map to signals (`RAG_ANSWER_ERROR`), never raw exceptions.
- Token limits: max input context and max output tokens, from settings.
- Cache embeddings for repeated queries (Redis, key = hash of text + model).
- Record `tokens` and `latency_ms` per message (the `messages` table already has the columns)
  and expose Prometheus counters for tokens and estimated cost.
- Optional: per-user daily token budget.
- Optional: fallback provider (e.g. OpenAI → Ollama) controlled by config.

**Done when:** a test with a fake provider that times out returns a clean error signal; the
Grafana panel shows tokens per hour.

---

## H7 — Celery hardening (extends Stage 6)

**Goal:** background work fails safely and visibly.

- Set `task_soft_time_limit` and `task_time_limit` per queue.
- `acks_late=True` and `worker_prefetch_multiplier=1` for long tasks.
- Explicit concurrency per worker (separate `file_processing` and `screening` if needed).
- Failure handling: failed tasks after max retries are written to `celery_task_executions`
  with status and error (and optionally a `failed_tasks` view endpoint for `hr_admin`).
- Beat task: clean old execution rows and orphaned files.
- Test: idempotency (same request twice → one result), retry (task fails once → succeeds).

**Done when:** killing a worker mid-task triggers a retry; a task that always fails ends in
a visible `FAILED` row, not a silent loss.

---

## H8 — Docker and data operations

**Goal:** the stack is reproducible and recoverable.

- Dockerfile: multi-stage build, non-root user, `HEALTHCHECK`, no dev dependencies in the
  final image.
- Compose: pin image tags (no `latest`), healthchecks with `depends_on: condition: service_healthy`,
  resource limits, named volumes.
- Two compose files: `docker-compose.yml` (full stack) and `docker-compose.dev.yml`
  (Postgres + Redis only, run API/Celery locally).
- Env files: only `.env.example.*` in git; document every variable in one table in the README.
- Scripts in `scripts/`:
  - `backup_db.sh` and `restore_db.sh` (pg_dump / pg_restore)
  - `seed.py` (creates workspace, uploads sample data, processes, indexes, prints counts)
  - `reset_demo.py` (wipes and reseeds; guarded by a confirmation flag)
  - `delete_candidate.py` (retention requirement from PLAN.md section 12)
- Test the restore script at least once and note it in the docs.

**Done when:** `make reset-db && make seed` rebuilds a working demo from nothing; a backup
can be restored into a fresh database.

---

## H9 — Security and open-source documentation

**Goal:** a stranger can trust and contribute to the repo.

- `SECURITY.md`: how to report issues, what is in scope.
- `CONTRIBUTING.md`: setup, commands, commit style, how to run tests.
- `CHANGELOG.md` (Keep a Changelog format); update it at each `stage-*` tag.
- `.github/` templates: bug report, feature request, pull request.
- `docs/`:
  - `architecture.md` (diagram + request flows from PLAN.md)
  - `decisions.md` — short ADRs, e.g. why PGVector is default, why no LangChain,
    why `Project` is kept as "workspace"
  - `api.md` or rely on OpenAPI + Postman collection (keep both in sync)
  - `evaluation.md` — how to reproduce the metrics
- README additions: CI badge, license badge, limitations, bias note, "decision support, human
  review required" disclaimer, environment-variable table, troubleshooting.
- Verify the git history has no secrets (`gitleaks detect` on full history) **before** making the
  repo public.
- Choose a license deliberately and keep it consistent with mini-rag.

**Done when:** `gitleaks` finds nothing in history; all docs links work; a new contributor can
run tests by following `CONTRIBUTING.md` only.

---

## Replacement for Stage 8 (no server)

Skip: VPS, HTTPS, domain, public demo URL, demo reset endpoint.

Do instead:

1. A one-command local demo: `make demo` = up + migrate + seed + prints the URL and demo
   credentials (synthetic users only).
2. A 3-minute screen recording: policy question with citation → upload → shortlist.
3. Screenshots in the README (chat with citations, shortlist table, Grafana, Flower).
4. Keep the minimal `ui/` only if time allows; the API + Postman + screenshots is enough
   for v1.

**Done when:** someone with Docker installed can see the full demo working in 15 minutes
without any cloud account except an LLM key (or Ollama locally).

---

## Order of work (checklist)

**Phase 1 — foundation (with Stage 0–1)**
- [ ] H0 tooling, Makefile, pre-commit
- [ ] H1 CI with lint + test + migrations
- [ ] H2 test skeleton with fake LLM/embedder
- [ ] H3 auth + admin bootstrap

**Phase 2 — behaviour (with Stage 2–4)**
- [ ] H4 API hardening
- [ ] H5 JSON logs + request ID
- [ ] H6 LLM timeouts, retries, token limits, embedding cache

**Phase 3 — operations (with Stage 6–7)**
- [ ] H7 Celery limits, failure handling
- [ ] H8 Docker hardening, backup/restore, seed/reset scripts

**Phase 4 — release (with Stage 9)**
- [ ] H9 SECURITY/CONTRIBUTING/CHANGELOG/docs/ADRs
- [ ] Local demo + video + screenshots
- [ ] Full-history secret scan
- [ ] Tag `v1.0.0`

---

## Extra definition of done (adds to PLAN.md section 16)

- [ ] CI is green on `main` (lint, tests, migrations, docker build, security).
- [ ] `make test` passes offline with fake providers; coverage floor enforced.
- [ ] Every HR route requires a valid token and the right role; verified by tests.
- [ ] No stack traces, secrets, or raw CV text in API responses or logs.
- [ ] Rate limits, upload limits, and pagination are in place and tested.
- [ ] One-command setup (`make up migrate seed`) and one-command demo (`make demo`).
- [ ] Backup/restore and candidate-deletion scripts exist and were tested once.
- [ ] `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `docs/decisions.md` exist.
- [ ] Full git history scanned for secrets before the repo goes public.
