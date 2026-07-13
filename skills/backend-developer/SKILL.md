---
name: backend-developer
description: Practical backend engineering playbook — request/response cycle, REST design, HTTP methods/status, middleware, auth vs authz, Node.js event loop, async/await, error handling, env/config, logging, SQL vs NoSQL, schema design, indexing, transactions/ACID, relationships, JWT/sessions/cookies, password hashing, rate limiting, Redis caching, scalability, API versioning and deployment. Load for ANY backend, API, or server task.
---

# Backend Developer Playbook

Practical rules + patterns. Theory kept short; **do / don't** emphasized. This is the knowledge base the `autonomous-coding-loop` /build mode follows.

## 1. Request–Response Cycle
- Client sends HTTP request (method, URL, headers, body) → server parses → routes → handler runs → response (status, headers, body) returned.
- Never block the response path with heavy sync work; offload to jobs/queues/workers.
- Always set correct `Content-Type` and an explicit status code.

## 2. REST API Design
- Resources are **nouns, plural**: `/users`, `/orders/123/items`. No verbs in paths.
- Stateless. JSON by default. Use HTTP method for the action.
- Version via `/v1/...` prefix (simplest, explicit).
- Consistent error envelope: `{ "error": { "code": "...", "message": "...", "details": {} } }`.
- Pagination: `?limit=&offset=` or cursor; filtering `?status=active`; sorting `?sort=-createdAt`.

## 3. HTTP Methods & Status Codes
- GET(read), POST(create), PUT(replace), PATCH(partial), DELETE(remove), HEAD/OPTIONS.
- 2xx: 200 / 201 created / 204 no content. 3xx redirect. 4xx: 400, 401, 403, 404, 409 conflict, 422 validation. 5xx: 500, 502, 503.
- Idempotent: GET/PUT/DELETE yes, POST no — design and retry logic accordingly.

## 4. Middleware & Request Flow
- Order matters: logging → cors → body-parse → auth → validation → route → response/error.
- Each middleware: `(req, res, next)`; call `next()` or send response. Don't double-send.
- Keep middleware thin — cross-cutting concerns only.

## 5. Authentication vs Authorization
- **AuthN** = who you are (login, token). **AuthZ** = what you may do (roles/permissions).
- Always authenticate first, then authorize per route/resource.

## 6. Event Loop & Non-Blocking I/O
- Node is single-threaded; offloads I/O to libuv. Never block with sync CPU-heavy work.
- Offload heavy compute to `worker_threads` or a queue.

## 7. Async/Await & Promises
- Prefer `async/await` over `.then`. Always `await` or return the promise.
- Use `Promise.allSettled` when one failure shouldn't kill the batch.
- Never leave floating promises (handle `unhandledRejection`).

## 8. Error Handling & Global Middleware
- Throw typed errors; wrap handlers in an async catcher.
- Global error handler LAST in chain: logs, maps to status, returns envelope. **Never leak stack traces to client.**
- `process.on('unhandledRejection' | 'uncaughtException')` → log + exit cleanly (let supervisor restart).

## 9. Environment Variables & Config
- `.env` (gitignored) + `config.js` reading `process.env` with defaults + validation (zod/dotenv).
- Never commit secrets. One config object per environment.

## 10. Logging & Debugging
- Structured JSON logs (pino/winston) with a correlation id per request.
- Levels: error/warn/info/debug. **Never log secrets or tokens.**
- `DEBUG` namespace or pino level via env.

## 11. SQL vs NoSQL
- **SQL (Postgres)**: relational, ACID, joins, consistency — money, core domain.
- **NoSQL (Mongo/Dynamo)**: flexible schema, horizontal scale — logs, sessions, loose data.
- Choose by consistency + relationship needs, not hype.

## 12. Database Schema Design
- Normalize (3NF) unless perf demands denormalization.
- Clear names; constraints (NOT NULL, FK, unique).
- Migrations in code (prisma/knex/TypeORM), never manual prod edits.

## 13. Indexing & Query Optimization
- Index columns in WHERE/JOIN/ORDER BY. Composite index **order matters**.
- `EXPLAIN/ANALYZE`. Avoid `SELECT *`; fix N+1 with joins/includes.
- Too many indexes slow writes.

## 14. Transactions & ACID
- Wrap multi-step writes in a transaction; rollback on failure.
- Mind isolation levels; avoid long transactions holding locks.

## 15. Relationships
- 1–1 (profile↔user), 1–many (user→posts), many–many (students↔courses via join table).
- Model FK + join tables; understand the SQL behind the ORM.

## 16. JWT, Sessions & Cookies
- JWT: stateless, signed, **short expiry + refresh token**. Store refresh in `httpOnly` cookie.
- Sessions: server state in Redis, cookie holds id.
- Cookies: `httpOnly`, `secure`, `sameSite=strict/lax`. Avoid localStorage JWT if XSS risk.

## 17. Password Hashing
- `argon2` (preferred) or `bcrypt`. Salt automatic. **Never** plaintext/MD5/SHA.
- Constant-time compare. Rate-limit login.

## 18. Rate Limiting & Caching (Redis)
- Rate limit per IP/user: sliding window / token bucket in Redis.
- Cache expensive reads with TTL; invalidate on write. Prevent stampede (lock/singleflight).

## 19. Scalability
- Horizontal scaling: stateless servers behind a load balancer.
- Shared state → Redis/DB. Idempotent endpoints. Health checks + graceful shutdown.

## 20. API Versioning & Deployment
- Version in URL `/v1` or header. Deprecate with notice + `Sunset` header.
- Deploy: containerize, CI/CD, env config, zero-downtime rolling. Monitor + rollback plan.

---

**Daily improvement:** after each project session, append real patterns/lessons from the day's work to the relevant section via `skill_manage(action='patch')`. This keeps the playbook sharp as we build.
