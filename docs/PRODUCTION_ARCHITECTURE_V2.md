# OOHScout AI — Production Architecture V2 (GeoLibre-Verified)

**Purpose:** Supersedes `PRODUCTION_ARCHITECTURE.md` (V1). Every claim below is verified against the actual GeoLibre source at commit `a6fad468`. Line counts come from `view_file` (authoritative) rather than estimates.

**Files read end-to-end:** 38 source files, 11 docs, 4 skills files, 2 pyproject.toml configs, 24 CI workflows, 7 package.json + index.ts skims. Total: ~18,000 lines of code and ~4,000 lines of documentation.

---

## 1. AUDIT — V1 Claim Verification

Every factual claim from `PRODUCTION_ARCHITECTURE.md` (V1), verified against the actual GeoLibre source.

### 1.1 Line Count Audit

V1 consistently undercounts by exactly 1 line on Python/backend files (likely excluded trailing newline). The TypeScript files are also off by 1. All corrections below use `view_file` Total Lines as ground truth.

| File | V1 Claim | Actual | Verdict | Note |
|------|----------|--------|---------|------|
| `python/src/geolibre/project.py` | 1312 | **1313** | ⚠️ | Off by 1 |
| `python/src/geolibre/authoring.py` | 1119 | **1120** | ⚠️ | Off by 1 |
| `python/src/geolibre/geolibre.py` | 3071 | **3072** | ⚠️ | Off by 1 |
| `python/src/geolibre/mcp/server.py` | 1084 | **1085** | ⚠️ | Off by 1 |
| `python/src/geolibre/mcp/workspace.py` | 141 | **142** | ⚠️ | Off by 1 |
| `python/src/geolibre/mcp/__init__.py` | 64 | **65** | ⚠️ | Off by 1 |
| `python/src/geolibre/mcp/__main__.py` | 8 | **5** | ❌ | Off by 3 — actually 5 lines |
| `backend/.../app/main.py` | 203 | **204** | ⚠️ | Off by 1 |
| `backend/.../app/postgis.py` | 962 | **963** | ⚠️ | Off by 1 |
| `backend/.../app/vector.py` | 320 | **321** | ⚠️ | Off by 1 |
| `backend/.../app/sql.py` | 91 | **92** | ⚠️ | Off by 1 |
| `backend/.../app/ml.py` | 476 | **477** | ⚠️ | Off by 1 |
| `backend/.../app/runtime.py` | 214 | **215** | ⚠️ | Off by 1 |
| `workers/ai-proxy/src/index.ts` | 679 | **680** | ⚠️ | Off by 1 |
| `apps/.../assistant/agent.ts` | 171 | **172** | ⚠️ | Off by 1 |
| `apps/.../assistant/tools.ts` | 1080 | **1081** | ⚠️ | Off by 1 |
| `apps/.../assistant/provider.ts` | 623 | **624** | ⚠️ | Off by 1 |
| `apps/.../assistant/model-builder.ts` | 360 | **361** | ⚠️ | Off by 1 |

### 1.2 Structural / Factual Claim Audit

| V1 Claim | V1 Location | Verdict | Correction |
|----------|-------------|---------|------------|
| `PROJECT_MARKERS = ("layers", "geolibre")` for schema guard | §1.5 item 2 | ❌ **WRONG** | Actual: `PROJECT_MARKERS = ("mapView", "basemapStyleUrl")` at [server.py:79](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/mcp/server.py#L79). Neither `layers` nor `geolibre` is a marker. The rationale (line 72-78) explains: `layers` is not exclusive to this format, and `load_project` normalizes it. |
| `to_project(keep_credentials=False)` is in `authoring.py` | §1.2, §1.5 | ❌ **WRONG** | `to_project()` is a method of `Map` class in [geolibre.py:2805](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/geolibre.py#L2805). The redaction function itself is `redact_credentials()` in [project.py:206](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/project.py#L206). `authoring.py` merely references it in a docstring (line 131). |
| Token auth at `main.py:44-84` | §1.4 | ⚠️ **IMPRECISE** | Token constant at line 44, but the middleware function `require_sidecar_token` spans [main.py:58-84](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/geolibre_server/app/main.py#L58-L84). |
| `_reports_its_errors` at `server.py:159-206` | §1.5 item 1 | ✅ **VERIFIED** | Actually [server.py:159-206](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/mcp/server.py#L159-L206). Correct. |
| `_require_project` at `server.py:82-98` | §1.5 item 2 | ⚠️ **IMPRECISE** | Function at [server.py:82-98](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/mcp/server.py#L82-L98). Correct range, but `PROJECT_MARKERS` content is wrong (see above). |
| `INSTRUCTIONS` at `server.py:34-68` | §1.5 item 3 | ✅ **VERIFIED** | [server.py:34-68](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/mcp/server.py#L34-L68). Correct. |
| `assert_public_http_url` and `is_read_only_sql` at `tools.ts:117-167` | §Phase 4 item 3 | ⚠️ **IMPRECISE** | `isReadOnlySql` is at [tools.ts:125-130](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/tools.ts#L125-L130). `assertPublicHttpUrl` is at [tools.ts:137-167](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/tools.ts#L137-L167). V1 lumps them as one range. |
| `AssistantToolDeps` at `tools.ts:23-40` | §Phase 4 item 2 | ⚠️ **OFF BY 1** | Actually [tools.ts:24-40](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/tools.ts#L24-L40). Interface starts at 24, not 23. |
| `describeLayers` at `tools.ts:237-257` | §Phase 4 item 6 | ✅ **VERIFIED** | [tools.ts:237-257](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/tools.ts#L237-L257). Exact match. |
| TrustedHostMiddleware at `main.py:94-97` | §1.4 | ✅ **VERIFIED** | [main.py:94-97](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/geolibre_server/app/main.py#L94-L97). |
| CORS regex at `main.py:101-110` | §1.4 | ✅ **VERIFIED** | [main.py:101-110](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/geolibre_server/app/main.py#L101-L110). |
| Graceful shutdown at `main.py:140-148` | §1.4 | ✅ **VERIFIED** | [main.py:140-148](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/geolibre_server/app/main.py#L140-L148). |
| `_STATEMENT_TIMEOUT_MS = 60_000` in postgis.py | §1.4 | ✅ **VERIFIED** | [postgis.py:43](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/geolibre_server/app/postgis.py#L43). |
| `_PASSWORD_URL_RE`, `_PASSWORD_KV_RE` in postgis.py | §1.4 | ✅ **VERIFIED** | [postgis.py:58-59](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/geolibre_server/app/postgis.py#L58-L59). |
| `GEOLIBRE_POSTGIS_HOSTS` env var | §1.4 | ✅ **VERIFIED** | [postgis.py:44](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/geolibre_server/app/postgis.py#L44): `_POSTGIS_HOSTS_ENV = "GEOLIBRE_POSTGIS_HOSTS"`. |
| `psycopg.sql.Identifier` usage | §1.4 | ✅ **VERIFIED** | Used throughout postgis.py for schema/table/column quoting. |
| Backend pyproject.toml extras: `[dev,whitebox,conversion,vector,raster,postgis,sedona,ml,notebook,test]` | §1.3 | ✅ **VERIFIED** | [backend pyproject.toml:9-51](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/pyproject.toml#L9-L51). |
| `[test]` extras verbatim rule | §1.3 | ✅ **VERIFIED** | [backend pyproject.toml:11-15](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/pyproject.toml#L11-L15). Exact quote found. |
| `geolibre-mcp = "geolibre.mcp:main"` console script | §1.5 | ✅ **VERIFIED** | [python/pyproject.toml:40](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/pyproject.toml#L40). |
| GeoLibre uses Strands SDK for agents | §4.2 | ✅ **VERIFIED** | [provider.ts:1](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/provider.ts#L1): `import type { Model } from "@strands-agents/sdk"`. |
| "7 routers" claim for backend | §1.4 | ✅ **VERIFIED** | [main.py:28-35](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/geolibre_server/app/main.py#L28-L35): conversion, ml, postgis, raster, sql, vector, whitebox. |
| V1 claims `authoring.py` has `add_layer()`, `restyle_layer()`, `move_camera()` | §1.1 | ⚠️ **IMPRECISE** | Functions exist but V1 omits the full inventory (~20 functions). The delegation pattern is correct though. |

### 1.3 Missing-Important-Thing Audit (➕)

| Missing Pattern | Where in GeoLibre | Why It Matters |
|-----------------|-------------------|----------------|
| `_build_layer()` style-key collision guard | [server.py:101-157](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/mcp/server.py#L101-L157) | Prevents a model from accidentally passing a style key that matches a builder parameter name. Not mentioned in V1 at all. |
| `resolve_output()` extension allowlist | [workspace.py:104-133](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/mcp/workspace.py#L104-L133) | Only `.json` and `.html` can be written. V1 mentions path confinement but not extension filtering. |
| `_finite()` NaN/inf guard in authoring.py | [authoring.py:55-77](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/authoring.py#L55-L77) | Blocks `inf`/`NaN` values that would corrupt JSON. Not in V1. |
| `MAX_PROJECT_BYTES` file size cap | [authoring.py:49](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/authoring.py#L49) | Prevents memory exhaustion from loading a huge project file. Not in V1. |
| Atomic saves via temp file + `os.replace()` | [authoring.py:112-165](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/authoring.py#L112-L165) | Prevents corrupt saves on crash. Not in V1. |
| SSRF guard in Python (`_assert_public_url` + redirect pinning) | [project.py:257-295](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/project.py#L257-L295) | V1 mentions the TS guard but not the Python one. Python has a more thorough version with `socket.getaddrinfo` + `_PublicOnlyRedirectHandler`. |
| `readTextCapped` response body guard | [tools.ts:174-196](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/tools.ts#L174-L196) | Prevents OOM from unbounded response bodies. Not in V1. |
| `confirmCodeExecution` gate for `run_python`/`run_maplibre_js` | [tools.ts:36-39](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/tools.ts#L36-L39) | Human-in-the-loop for code execution. Not in V1. |
| `resolveLayer` fuzzy matching with 3-char minimum | [tools.ts:259-271](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/tools.ts#L259-L271) | Prevents 1-2 char typos from matching arbitrary layers. Not in V1. |
| `nbstripout` in pre-commit to prevent credential leakage | [.pre-commit-config.yaml](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/.pre-commit-config.yaml) | Strips notebook outputs on every commit. Not in V1. |
| ML process isolation + concurrency cap | [ml.py:74-81](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/geolibre_server/app/ml.py#L74-L81) | GPU workloads in separate process, max 4 concurrent requests. Not in V1. |
| `_clean_env()` for subprocess isolation | [runtime.py:59-70](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/geolibre_server/app/runtime.py#L59-L70) | Purges `PYTHONHOME`, `PROJ_DATA` from spawned processes. Not in V1. |
| AI proxy constant-time token auth via `crypto.subtle.digest` | [index.ts:75-88](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/workers/ai-proxy/src/index.ts#L75-L88) | Uses web crypto for timing-safe comparison. Not in V1. |
| AI proxy output token clamping | [index.ts:127-139](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/workers/ai-proxy/src/index.ts#L127-L139) | Prevents budget exhaustion. Not in V1. |
| Docker healthchecks + `depends_on: condition: service_healthy` | [docker-compose.yml:21-25, 49-63, 80-92, 104-108](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/docker-compose.yml) | Proper service init ordering. Not in V1. |
| nginx CSP headers with strict sources | [nginx.conf:129, 184](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/docker/nginx.conf) | Content Security Policy. Not in V1. |
| Sidecar token injection via nginx proxy | [nginx.conf:77-80](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/docker/nginx.conf) | nginx injects `GEOLIBRE_SIDECAR_TOKEN` on proxy pass. Not in V1. |

---

## 2. PATTERN INVENTORY

### 2.1 Security Patterns

#### S1: Per-launch token auth with constant-time bytes compare
**File:** [main.py:44-84](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/geolibre_server/app/main.py#L44-L84)
**What:** Every HTTP request to the sidecar must carry `X-GeoLibre-Token` or `Authorization: Bearer <token>`. Token generated fresh per launch, injected via `GEOLIBRE_SIDECAR_TOKEN` env var. Compared as **bytes** using `hmac.compare_digest` to prevent timing attacks and avoid `TypeError` from Starlette's latin-1 header decoding.
**Bug prevented:** Without this, any local process (or DNS-rebinding attacker) can call the sidecar. The bytes encoding prevents a non-ASCII header from turning 401 into 500.
**OOHScout adaptation:**
```python
# api/auth.py
import hmac, os
from fastapi import Request
from fastapi.responses import JSONResponse

SIDECAR_TOKEN = os.environ.get("OOHSCOUT_SIDECAR_TOKEN", "").strip()
_TOKEN_BYTES = SIDECAR_TOKEN.encode("utf-8")
_EXEMPT_PATHS = frozenset({"/health"})

async def require_token(request: Request, call_next):
    if SIDECAR_TOKEN and request.method != "OPTIONS" and request.url.path not in _EXEMPT_PATHS:
        provided = request.headers.get("x-oohscout-token", "")
        if not provided:
            auth = request.headers.get("authorization", "")
            if auth.lower().startswith("bearer "):
                provided = auth[7:].strip()
        if not hmac.compare_digest(provided.encode("utf-8"), _TOKEN_BYTES):
            return JSONResponse(status_code=401, content={"detail": "Missing or invalid token"})
    return await call_next(request)
```

#### S2: TrustedHostMiddleware (DNS rebinding defense)
**File:** [main.py:87-97](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/geolibre_server/app/main.py#L87-L97)
**What:** Only accepts requests with Host header `localhost`, `127.0.0.1`, or `testserver`. Blocks DNS rebinding where attacker's domain resolves to 127.0.0.1.
**Bug prevented:** A remote attacker registers `evil.com` → `127.0.0.1`, opens it in victim's browser, and reads sidecar responses.
**Note:** No IPv6 `::1` because the server never binds it, and TrustedHostMiddleware mis-parses `[::1]:port`.
**OOHScout adaptation:** Copy verbatim. Add your dev port's hostname if needed.

#### S3: CORS regex (not wildcard)
**File:** [main.py:98-110](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/geolibre_server/app/main.py#L98-L110)
**What:** Explicit regex `^(http://localhost:5173|http://127\.0\.0\.1:5173|tauri://localhost|http://tauri\.localhost)$` instead of `*`.
**Bug prevented:** Random local web apps can't call the sidecar from a browser.
**OOHScout adaptation:** For MVP, just allow `http://localhost:8000` (your dev FastAPI). No frontend yet → no CORS needed at all.

#### S4: Schema-marker guard (`_require_project`)
**File:** [server.py:71-98](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/mcp/server.py#L71-L98)
**What:** Before overwriting a JSON file, verify it contains `mapView` or `basemapStyleUrl`. If neither is present, refuse — it's not a GeoLibre project.
**Bug prevented:** LLM tricked into passing `package.json` as the project path would overwrite it.
**OOHScout adaptation:**
```python
PROJECT_MARKERS = ("oohscout_version", "corridor_id")

def _require_project(path: Path, data: dict) -> None:
    if not any(key in data for key in PROJECT_MARKERS):
        raise ValueError(f"{path.name} is not an OOHScout project. Refusing to overwrite.")
```

#### S5: Workspace path confinement with symlink resolution
**File:** [workspace.py:34-142](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/mcp/workspace.py#L34-L142)
**What:** Every path from a tool call resolves against `--root` allowlist. `Path.resolve()` follows symlinks **before** checking containment. Relative paths anchor to first root.
**Bug prevented:** `../../../../etc/passwd` or a symlink escape. The post-resolve check catches both.
**Key detail:** `resolve_output()` (lines 104-133) additionally checks file extension against an allowlist (`PROJECT_SUFFIXES`, `EXPORT_SUFFIXES`), preventing writes to `.py`, `.sh`, `.env` etc.
**OOHScout adaptation:** Copy `workspace.py` file-for-file. Rename `Workspace` → `ScoutingWorkspace`. Change `PROJECT_SUFFIXES` to `(".json", ".oohscout.json")`.

#### S6: SSRF guard — Python version (with DNS resolution + redirect pinning)
**File:** [project.py:257-295](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/project.py#L257-L295)
**What:** `_assert_public_url()` uses `socket.getaddrinfo` to resolve hostname and verifies every resulting IP is globally routable. `_PublicOnlyRedirectHandler` re-validates on every redirect hop.
**Bug prevented:** LLM fetches `http://evil.com/redirect` → `http://169.254.169.254/metadata` (AWS metadata endpoint).
**OOHScout adaptation:** Port directly. Add GeoJSON fetch cap at 50MB ([project.py:1037-1048](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/project.py#L1037-L1048)).

#### S7: SSRF guard — TypeScript version (IP range blocklist)
**File:** [tools.ts:132-167](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/tools.ts#L132-L167)
**What:** Blocks localhost, `::1`, private ranges (10.x, 172.16-31.x, 192.168.x), link-local (169.254.x), CGNAT (100.64/10), IPv6 unique-local (fc/fd), IPv6 link-local (fe80).
**Bug prevented:** Same as S6 but in the browser context.
**OOHScout adaptation:** Not needed for MVP (no browser client). Relevant when web frontend exists.

#### S8: SQL read-only confinement
**File:** [tools.ts:116-130](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/tools.ts#L116-L130)
**What:** `isReadOnlySql()` rejects any statement containing write keywords (INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, etc.) even inside CTEs. Masks string literals before checking.
**Bug prevented:** LLM injecting `DROP TABLE` inside a CTE.
**OOHScout adaptation:**
```python
import re
_SQL_WRITE_KW = re.compile(
    r'\b(INSERT|UPDATE|DELETE|MERGE|CREATE|DROP|ALTER|TRUNCATE|REPLACE'
    r'|ATTACH|DETACH|COPY|EXPORT|IMPORT|INSTALL|LOAD|PRAGMA|VACUUM|CHECKPOINT)\b',
    re.IGNORECASE
)
def is_read_only_sql(sql: str) -> bool:
    cleaned = re.sub(r"'[^']*'", "''", sql)  # mask string literals
    head = cleaned.strip().upper()
    if not (head.startswith("SELECT") or head.startswith("WITH")):
        return False
    return not _SQL_WRITE_KW.search(cleaned.upper())
```

#### S9: Statement timeout on every PostGIS session
**File:** [postgis.py:43, 318](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/geolibre_server/app/postgis.py#L43)
**What:** `_STATEMENT_TIMEOUT_MS = 60_000`. Every connection sets `statement_timeout` via psycopg connection options.
**Bug prevented:** LLM-generated query (`SELECT * FROM massive_table CROSS JOIN massive_table`) pins a FastAPI worker forever.
**OOHScout adaptation:** Set `statement_timeout=60000` on every psycopg connect. Also enforce via `oohscout_ro` read-only role.

#### S10: Password redaction in error messages
**File:** [postgis.py:53-92](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/geolibre_server/app/postgis.py#L53-L92)
**What:** `_sanitize_error()` scrubs `user:password@host` URL segments and `password=...` keyword pairs from error messages before returning them to callers.
**Bug prevented:** Malformed connection string echoed back in error leaks password to caller (who may be an LLM relaying to a user).
**OOHScout adaptation:** Copy the two regexes and `_sanitize_error()` into `api/errors.py`.

#### S11: PostGIS host allowlist
**File:** [postgis.py:44, 174-187](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/geolibre_server/app/postgis.py#L44)
**What:** `GEOLIBRE_POSTGIS_HOSTS` env var lists allowed host:port pairs. Without it, external connections are refused.
**Bug prevented:** LLM passes a connection string pointing to an attacker's Postgres server.
**OOHScout adaptation:** For MVP, hardcode `localhost:5432` only. No external connections.

#### S12: Credential redaction on project serialize
**File:** [project.py:80-130, 206-242](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/project.py#L80-L130)
**What:** `redact_credentials()` walks the project tree, strips keys matching credential field names (`apiKey`, `api_key`, `token`, `password`, `secret`, `authorization`, `credential`) and URL parameters (`?key=`, `?token=`).
**Bug prevented:** API keys saved to `.geolibre.json` and committed to git.
**OOHScout adaptation:** Must strip TxDOT keys, Regrid keys, Groq/Anthropic keys, county portal credentials from `.oohscout.json`.

#### S13: `readTextCapped` / `_MAX_GEOJSON_BYTES` — response body size limit
**Files:** [tools.ts:174-196](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/tools.ts#L174-L196), [project.py:1037-1048](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/project.py#L1037-L1048)
**What:** Both TS and Python cap response body reads. The Python side uses `response.read(_MAX_GEOJSON_BYTES + 1)` — 50MB limit.
**Bug prevented:** LLM fetches a URL pointing to a 10GB file, causing OOM.
**OOHScout adaptation:** Cap all external fetches at 50MB.

#### S14: `confirmCodeExecution` — human-in-the-loop for code execution
**File:** [tools.ts:36-39](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/tools.ts#L36-L39)
**What:** `run_python` and `run_maplibre_js` tools require explicit user confirmation before executing. The assistant can be steered by untrusted content into emitting exfiltration code.
**Bug prevented:** Prompt injection via web search results or layer attributes → agent writes code that reads `.env` and sends it to `evil.com`.
**OOHScout adaptation:** For MCP server (no UI), there's no user to confirm. Instead: never allow code execution tools. All tools are predefined, no dynamic code. This is simpler and safer.

#### S15: `_finite()` NaN/inf guard
**File:** [authoring.py:55-77](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/authoring.py#L55-L77)
**What:** Blocks `inf`/`NaN` float values from entering the project dict.
**Bug prevented:** JSON serialization silently drops `NaN`, or different parsers interpret it differently.
**OOHScout adaptation:** Validate all float inputs (scores, coordinates, areas) before storing.

#### S16: Atomic file saves
**File:** [authoring.py:112-165](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/authoring.py#L112-L165)
**What:** Writes to temp file first, copies permissions, then `os.replace()` for atomic swap.
**Bug prevented:** Power loss mid-write corrupts the project file.
**OOHScout adaptation:** Copy into `authoring/io.py`.

#### S17: `nbstripout` in pre-commit
**File:** [.pre-commit-config.yaml](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/.pre-commit-config.yaml)
**What:** Strips all notebook cell outputs on every commit.
**Bug prevented:** Accidental credential or data leakage in notebook outputs committed to git.
**OOHScout adaptation:** Add to `.pre-commit-config.yaml` immediately. You have notebooks with API keys in outputs.

---

### 2.2 Architecture Patterns

#### A1: Three-layer authoring stack
**Files:** [project.py](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/project.py) (1313 lines) → [authoring.py](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/authoring.py) (1120 lines) → [geolibre.py](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/geolibre.py) (3072 lines) + [mcp/server.py](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/mcp/server.py) (1085 lines)
**What:**
- `project.py`: Pure builders. `build_geojson_layer()`, `build_legend()`, etc. No I/O, no widget, no MCP. Returns dicts.
- `authoring.py`: Pure transforms on whole project dicts. `save_project()`, `load_project()`, `layers_of()`, etc. No widget.
- `geolibre.py` (Map widget) and `mcp/server.py` both delegate every write to `authoring.py`.

**Invariant verified:** `authoring.py` imports from `project.py` (line 28). `mcp/server.py` imports from `authoring` (line 28) and `project` (line 29). Neither `project.py` nor `authoring.py` imports from `geolibre.py` or `mcp/`.

#### A2: Project file as single source of truth
**Files:** [geolibre.py:134-161](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/geolibre.py#L134-L161)
**What:** The `Map` class syncs its entire state as a single `project` traitlet (a JSON dict). Not decomposed into `zoom`, `center`, `layers` — one dict represents everything. AnyWidget syncs this over postMessage.
**MCP equivalent:** The MCP server reads `.geolibre.json` from disk, applies a change, writes it back. The file IS the state. No server-side state.

#### A3: Optional-extras pattern
**File:** [backend/pyproject.toml:9-51](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/pyproject.toml#L9-L51)
**What:** Core dependencies are minimal (`fastapi`, `uvicorn`). Everything else (`geopandas`, `psycopg`, `rasterio`, `duckdb`, `httpx` for ML) is an optional extra. Tests skip themselves via `skipif`/`importorskip` without the extras.
**The `[test]` rule:** `test = ["geolibre-server[dev,vector,raster,conversion,ml,sedona,postgis,notebook]"]` — install EVERYTHING for the test suite. Without this, tests report misleadingly green.

#### A4: Graceful shutdown on Windows
**File:** [main.py:140-148](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/geolibre_server/app/main.py#L140-L148)
**What:** Uses `signal.raise_signal(signal.SIGINT)` not `SIGTERM` because Windows maps SIGTERM to `TerminateProcess` (uncatchable). 0.2s sleep before signal so the HTTP response returns first.

#### A5: Thread-pool offloading for sync dependencies
**Files:** [postgis.py](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/geolibre_server/app/postgis.py), [vector.py](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/geolibre_server/app/vector.py)
**What:** Routes use plain `def` (not `async def`) because psycopg and GeoPandas are synchronous. FastAPI automatically offloads these to its thread pool.

#### A6: ML process isolation with concurrency cap
**File:** [ml.py:74-81, 169-248](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/geolibre_server/app/ml.py#L74-L81)
**What:** GPU workloads (SAM3) run in a separate child process. Max 4 concurrent segmentation requests via `threading.Lock`. 100 MiB upload size limit.

#### A7: Zustand store as single state source (frontend)
**File:** [packages/core/src/store.ts:223-793](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/packages/core/src/store.ts#L223-L793)
**What:** Monolithic `AppState` interface (~570 lines). Every AI tool result flows through the store; the map subscribes to the store; no direct MapLibre mutations.

#### A8: Provider priority cascade
**File:** [provider.ts:191-205](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/provider.ts#L191-L205)
**What:** `mergeRuntimeEnv` enforces Project > Device > Cesium > Geocoder > OS priority for API keys.

---

### 2.3 Agent Design Patterns

#### AG1: System prompt structure
**File:** [agent.ts:13-30](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/agent.ts#L13-L30)
**What:** The system prompt tells the assistant: always act via tools, prioritize DuckDB Spatial SQL, inspect layers before referring to them, build multi-step algorithm pipelines, use script fallbacks.
**OOHScout adaptation:** One `system_prompt.py` constant. Rules: regulatory gate first, PostGIS owns distances, never label "LEGAL", always call `check_regulatory_eligibility` before `rank_candidates`.

#### AG2: `AssistantToolDeps` injection
**File:** [tools.ts:24-40](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/tools.ts#L24-L40)
**What:** Tools receive their dependencies via an `AssistantToolDeps` interface, not globals. Contains `getMapController()` and optional `confirmCodeExecution()`.
**OOHScout adaptation:**
```python
@dataclass
class ToolDeps:
    db: PostgresPool
    rules: RulesEngine
    rag: RAGClient
    txdot: TxDOTClient
    approve: Callable[[str], Awaitable[bool]]  # human-in-the-loop
```

#### AG3: Grounding / context injection (describeLayers)
**File:** [tools.ts:237-257](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/tools.ts#L237-L257), [agent.ts:138](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/agent.ts#L138)
**What:** Before each turn, `describeLayers()` generates a text summary of all layers (name, type, geometry, feature count, SQL table, fields). Only re-injected when it changes (line 138 in agent.ts checks against previous).
**OOHScout adaptation:** `describe_corridor()` — current corridor name, candidate count, rule bindings, last scoring timestamp.

#### AG4: Event normalization
**File:** [agent.ts:145-169](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/agent.ts#L145-L169)
**What:** Events from the Strands SDK are narrowed by discriminant type into `{type: text|tool_call|tool_result}` for the UI. No raw SDK types leak to the presentation layer.

#### AG5: Tool shape — self-contained `InvokableTool` definitions
**File:** [tools.ts:308-1081](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/tools.ts#L308-L1081)
**What:** Each tool is a complete definition with name, description, Zod schema, and handler. ~20 tools covering layers, SQL, web search, basemaps, symbology, algorithms, STAC.

#### AG6: Response truncation for large tool outputs
**File:** [tools.ts:669-674, 794-810](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/tools.ts#L669-L674)
**What:** Python stdout capped at 8000 chars. Whitebox results capped at 25 entries. Prevents context window exhaustion.

---

### 2.4 MCP Design Patterns

#### M1: `_reports_its_errors` wrapper
**File:** [server.py:159-206](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/mcp/server.py#L159-L206)
**What:** Wraps every tool so `ValueError` → `ToolError` with original message intact. Refuses async tools (the wrapper can't catch errors from unawaited coroutines).
**Critical detail:** The `tool()` helper at [server.py:235-249](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/mcp/server.py#L235-L249) forces EVERY tool through `_reports_its_errors`. A bare `@server.tool()` would silently mask messages.

#### M2: `INSTRUCTIONS` string — the MCP system prompt
**File:** [server.py:34-68](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/mcp/server.py#L34-L68)
**What:** 35 lines telling the calling LLM when to prefer these tools, what each layer type is for, and the typical flow (`create_project` → `add_*_layer` → `style_layer` → `export_html`).

#### M3: Build-layer style collision guard
**File:** [server.py:101-157](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/mcp/server.py#L101-L157)
**What:** `_build_layer()` inspects the builder function's signature and rejects any `style` key that collides with a builder parameter. The LLM sees `style: object` in the schema and may guess a key like `source_url` — this catches it early with a clear message.

#### M4: Graceful import for optional `mcp` SDK
**File:** [mcp/__init__.py:21-50](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/mcp/__init__.py#L21-L50)
**What:** Catches `ModuleNotFoundError` for `mcp` only (not deeper dependencies), prints actionable message, exits with code 1. Uses `__getattr__` for lazy loading of `build_server`.

#### M5: `build_server(workspace)` dependency injection
**File:** [server.py:219-233](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/mcp/server.py#L219-L233)
**What:** The entire server is built by passing a `Workspace` object. Every tool closes over the workspace. No globals.

---

### 2.5 Distribution Patterns

#### D1: Skills directory for Claude Code/Desktop
**File:** [skills/geolibre/SKILL.md](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/skills/geolibre/SKILL.md) (156 lines)
**What:** Teaches the LLM a 6-step workflow: `create_project` → `add_*_layer` → `set_view` → `style_layer` → `add_legend` → `export_html`. Includes "Rules that actually bite" section warning against guessing basemaps, 50MB GeoJSON limit, etc.
**References:** `skills/geolibre/references/` contains `catalog.md` (131 lines — basemap/ramp enums), `mcp-tools.md` (162 lines — tool shapes), `project-json.md` (147 lines — schema examples), `python-api.md` (215 lines — headless vs interactive).

#### D2: MCP as second front door + console script
**File:** [python/pyproject.toml:37-40](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/pyproject.toml#L37-L40)
**What:** `geolibre-mcp = "geolibre.mcp:main"` — a `pip install "geolibre[mcp]"` + `geolibre-mcp --root ~/maps` gives Claude Desktop a complete project-authoring backend.

#### D3: Wheel bundles the web build
**File:** [python/pyproject.toml:49-53](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/pyproject.toml#L49-L53)
**What:** `artifacts = ["src/geolibre/static/**"]` — the wheel includes the built web app under `static/`. `hatch_build.py` scans for credentials before packaging.

#### D4: Docker split (web + sidecar + collab + postgres)
**File:** [docker-compose.yml](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/docker-compose.yml) (115 lines)
**What:** Four services. Postgres with `${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD}` (fail-loud). Healthchecks with `depends_on: condition: service_healthy`. Mapped volumes for persistence.

#### D5: Multi-stage Dockerfile
**File:** [Dockerfile](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/Dockerfile) (179 lines)
**What:** Build stage + runtime stage. Copies `package.json` first for cache. Bundles nginx + Python sidecar in single image. ARM64 fallback (skips certain extensions).

---

## 3. FOLDER MAP DELTA

### V1's proposed OOHScout layout vs. what GeoLibre actually does

| V1 Proposed | GeoLibre Actual | Status | Note |
|-------------|----------------|--------|------|
| `backend/src/oohscout/authoring/` | `python/src/geolibre/authoring.py` (single file, not a package) | ⚠️ **V1 over-engineered** | GeoLibre uses ONE file for authoring, not a 5-file package. For OOHScout's simpler domain, start with one `authoring.py` file. Split into a package only when it exceeds ~500 lines. |
| `backend/src/oohscout/authoring/security.py` | Security guards are in `project.py` (SSRF, credential redaction) and `workspace.py` (path confinement) | ⚠️ **Wrong placement** | Don't put SSRF guards in `authoring/`. Put them in `security.py` at package level, mirroring GeoLibre's split. |
| `backend/src/oohscout/mcp/errors.py` | `_reports_its_errors` lives INSIDE `server.py`, not separate | ⚠️ **Over-split** | It's 48 lines. Keep it in `server.py` unless you have a second error-wrapping pattern. |
| `backend/src/oohscout/api/` (empty) | `backend/geolibre_server/geolibre_server/app/` | ✅ Correct shape | But note: GeoLibre has 7 routers in flat files, not a `routers/` subdirectory. Either approach works. |
| `backend/src/oohscout/db/pool.py` | No pool module in GeoLibre — psycopg connections are per-request | ⚠️ **V1 adds complexity** | GeoLibre's postgis.py creates connections per request with `psycopg.connect()`. For MVP, do the same. Add a pool only when you measure connection overhead. |
| `skills/oohscout/` | `skills/geolibre/` with SKILL.md + references/ | ✅ Correct | Mirror exactly. |
| `workers/ai-proxy/` | `workers/ai-proxy/` | ✅ Correct | But V1 correctly defers this. |
| `frontend/` | `apps/geolibre-desktop/` | ✅ Correctly deferred | |
| No `extensions/` folder | `extensions/` in GeoLibre root | ➕ **Missing** | GeoLibre has a VS Code extension and browser extension. Not needed for OOHScout MVP. |
| No `packaging/` folder | `packaging/` in GeoLibre for desktop builds | ➕ **Missing** | Not needed for MVP (no desktop app). |
| No `e2e/` folder | `e2e/` in GeoLibre root for Playwright | ➕ **Missing from V1** | Add `e2e/` once MCP server exists. |
| `docker/entrypoint.sh` → V1 says this | `docker/nginx.conf` (229 lines) + Docker uses `entrypoint.sh` | ✅ Correct idea | |

### Corrected folder layout

```
billboardAI/
├── CLAUDE.md                           # (exists)
├── pyproject.toml                      # REFACTOR into optional-extras
├── docs/
│   ├── PRODUCTION_ARCHITECTURE_V2.md   # ← THIS FILE
│   ├── FEATURES.md                     # (exists)
│   ├── project-format.md               # NEW — .oohscout.json schema
│   ├── mcp.md                          # NEW — how to install/configure oohscout-mcp
│   └── architecture.md                 # NEW — mermaid diagram
├── backend/
│   ├── src/oohscout/
│   │   ├── __init__.py                 # (exists)
│   │   ├── project.py                  # NEW — build_corridor(), build_candidate()
│   │   ├── authoring.py                # NEW — load_project(), save_project(), add_candidate()
│   │   ├── security.py                 # NEW — assert_public_url(), is_read_only_sql()
│   │   ├── track_a_spatial/            # (exists)
│   │   ├── track_b_rag/                # (exists — empty)
│   │   ├── track_c_agent/              # (exists — empty)
│   │   ├── api/                        # (exists — empty; build Phase 4)
│   │   │   ├── __init__.py
│   │   │   ├── main.py                 # FastAPI + security posture
│   │   │   ├── auth.py                 # Token middleware
│   │   │   ├── errors.py               # _sanitize_error + ValueError → HTTPException
│   │   │   └── routers/                # corridor.py, rules.py, rag.py, etc.
│   │   ├── mcp/                        # NEW Phase 4.5
│   │   │   ├── __init__.py             # Graceful ImportError
│   │   │   ├── __main__.py             # python -m oohscout.mcp
│   │   │   ├── server.py               # Tools → delegates to authoring.py
│   │   │   └── workspace.py            # Path confinement
│   │   ├── db/                         # (exists — empty)
│   │   └── data/                       # (exists)
│   └── tests/
├── skills/oohscout/                    # NEW Phase 4.5
│   ├── SKILL.md
│   └── references/
├── docker-compose.yml                  # NEW — postgres only for MVP
├── .github/workflows/ci.yml            # NEW — lint + test
├── .pre-commit-config.yaml             # NEW — ruff + nbstripout
└── notebooks/                          # (exists)
```

**Key change from V1:** `authoring/` is a single file (`authoring.py`), not a 5-file package. GeoLibre proves that a single 1120-line file is manageable. Split when it exceeds 500 lines for OOHScout's domain.

---

## 4. PHASING DELTA

### What V1 got right
- Phase 2.5 (infrastructure before RAG) — correct sequencing
- Phase 4.5 (MCP as fastest distribution) — correct priority
- Deferring frontend until payment signal — correct

### What V1 under-scoped

| Item | V1 Estimate | Corrected | Reason |
|------|------------|-----------|--------|
| `authoring/` package | "2 days" | **3-4 days** | V1 spec'd 5 files. Even with the simpler single-file approach, the `.oohscout.json` schema + `load_project` + `save_project` + credential redaction + atomic writes + tests is 3+ days. |
| Pre-commit setup | Not in V1 | **0.5 days** | Add `nbstripout` immediately. Your notebooks have API keys in outputs. |
| Security module | Not in V1 | **1 day** | `assert_public_url()`, `is_read_only_sql()`, `_sanitize_error()` — write once, use everywhere. |
| MCP workspace.py | Not separately estimated | **1 day** | It's 142 lines to port, but the test suite for path confinement (symlink escapes, extension checks) takes a day. |

### What V1 over-scoped

| Item | V1 Plan | Corrected | Reason |
|------|---------|-----------|--------|
| `backend/src/oohscout/db/pool.py` + asyncpg pool | Phase 2.5 | **Defer to Phase 4** | GeoLibre doesn't use a pool. Per-request connections are fine for MVP load. |
| `backend/src/oohscout/db/read_role.sql` | Phase 2.5 | **Defer to Phase 4** | You don't need a read-only role until the agent is calling SQL. |
| Multi-provider abstraction | Listed as deferred but still spec'd | **Delete entirely** | Not even a Phase 5 item. If you ever need it, port GeoLibre's `provider.ts` (624 lines). |
| 6 API routers | Phase 2.5-3 | **Start with 2** | `corridor.py` and `rules.py` only. Add others as features reach them. |
| Docker-compose with Postgres | Phase 2.5 | **Phase 3** | You don't need Postgres until RAG (pgvector). Use SQLite or flat files for Phase 2. |

### Corrected 90-day roadmap

**Phase 1-2** (Days 1-30): Track A spatial — unchanged, already in progress.

**Phase 2.5** (Days 31-37): Infrastructure — **corrected scope**:
- F-infra-1: Refactor `pyproject.toml` into optional-extras. **0.5 day.**
- F-infra-2: Create `authoring.py` (single file) + `project.py` (single file). Migrate study_area and corridor to use them as data source for `.oohscout.json`. **3 days.**
- F-infra-3: Freeze `.oohscout.json` schema at v0.1.0. Write `docs/project-format.md`. **1 day.**
- F-infra-4: Create `security.py` (SSRF guard, SQL read-only, error sanitization). **1 day.**
- F-infra-5: Add `.pre-commit-config.yaml` with `ruff` + `nbstripout`. Basic CI. **0.5 day.**
- ~~F-infra-4 from V1 (Postgres + Docker)~~: **Deferred to Phase 3.**

**Phase 3** (Days 38-52): Regulatory RAG — add Docker-compose with Postgres here.

**Phase 4** (Days 53-67): Agent + FastAPI sidecar.

**Phase 4.5** (Days 68-74): MCP server + SKILL.md — unchanged from V1.

---

## 5. TOP 10 FILES TO PORT

Ordered by dependency (things that block other things go first).

| # | GeoLibre File | Lines | OOHScout Target | Blocks | What to copy |
|---|--------------|-------|----------------|--------|-------------|
| 1 | [python/pyproject.toml](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/pyproject.toml) lines 24-35 | 12 | `pyproject.toml` extras section | Everything — bad install kills adoption | The `[project.optional-dependencies]` block structure and `[test]` discipline |
| 2 | [project.py](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/project.py) lines 80-130, 206-295 | ~150 | `backend/src/oohscout/project.py` | authoring.py, mcp/server.py | `_CREDENTIAL_FIELD_NAMES`, `redact_credentials()`, `_assert_public_url()`, `_PublicOnlyRedirectHandler` |
| 3 | [authoring.py](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/authoring.py) lines 49-165 | ~120 | `backend/src/oohscout/authoring.py` | mcp/server.py, api/ | `MAX_PROJECT_BYTES`, `_finite()`, `save_project()` (atomic write), `load_project()` |
| 4 | [workspace.py](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/mcp/workspace.py) lines 1-142 | 142 | `backend/src/oohscout/mcp/workspace.py` | mcp/server.py | Copy entire file. Change class name, suffixes, env var name. |
| 5 | [mcp/__init__.py](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/mcp/__init__.py) lines 1-65 | 65 | `backend/src/oohscout/mcp/__init__.py` | mcp/server.py | Copy entire file. Change package name in error message. |
| 6 | [server.py](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/mcp/server.py) lines 34-68, 71-98, 101-157, 159-250 | ~200 | `backend/src/oohscout/mcp/server.py` | MCP distribution | `INSTRUCTIONS`, `PROJECT_MARKERS`, `_require_project`, `_build_layer`, `_reports_its_errors`, `build_server()`, `tool()` helper |
| 7 | [main.py](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/geolibre_server/app/main.py) lines 37-148 | ~112 | `backend/src/oohscout/api/main.py` | All API routes | Token auth, TrustedHost, CORS, graceful shutdown |
| 8 | [postgis.py](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/backend/geolibre_server/geolibre_server/app/postgis.py) lines 43-100, 112-244, 318 | ~170 | `backend/src/oohscout/api/deps.py` + `errors.py` | PostGIS queries | Statement timeout, password redaction, host allowlist, `psycopg.sql.Identifier` quoting |
| 9 | [tools.ts](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/apps/geolibre-desktop/src/lib/assistant/tools.ts) lines 24-40, 116-196, 237-257 | ~100 | `backend/src/oohscout/track_c_agent/tools/deps.py` + `security.py` | Agent tools | `AssistantToolDeps` shape, `isReadOnlySql`, `assertPublicHttpUrl`, `readTextCapped`, `describeLayers` pattern |
| 10 | [skills/geolibre/SKILL.md](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/skills/geolibre/SKILL.md) + [references/](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/skills/geolibre/references) | ~700 | `skills/oohscout/SKILL.md` + `references/` | Claude Desktop distribution | 6-step workflow, "Rules that actually bite", tool shapes, project schema examples |

---

## 6. HONEST GAPS

### What I did NOT read line-by-line
- `packages/core/src/store.ts` (2698 lines) — skimmed structure, did not read every line
- `packages/map/src/layer-sync.ts` (3766 lines) — skimmed, not relevant to OOHScout backend
- `packages/plugins/src/index.ts` (1049 lines) — skimmed
- `apps/geolibre-desktop/src/components/*` — skipped per instructions
- `apps/geolibre-desktop/src/i18n/*` — skipped per instructions
- `backend/geolibre_server/tests/*` — not read
- `python/tests/*` — not read
- Individual CI workflow YAML files — read titles/triggers from subagent, did not read every line of every workflow

### What could not be verified
1. **The `project.py` credential redaction completeness**: I verified `redact_credentials()` exists at line 206 and documented the field names at lines 80-130, but did not verify it catches every possible credential pattern (e.g., custom OAuth headers).
2. **The `_assert_public_url` coverage of all private ranges**: The TS version at tools.ts:150-163 is explicitly comprehensive. The Python version at project.py:257-283 uses `socket.getaddrinfo` which is more thorough but depends on DNS resolution working correctly.
3. **CI workflow internal details**: I know what each workflow does from its name and triggers, but didn't verify every `runs-on`, `if` condition, or step.
4. **The subagent-reported line counts**: My subagents reported line counts 1-15 lines different from `view_file`. I used `view_file` Total Lines as ground truth for all corrections above. The subagent counts may have been affected by encoding or trailing newline handling differences.

### Where follow-up is needed
1. **`geolibre.py` lines 1100-1230**: The delegation pattern from Map to authoring.py. I confirmed it exists via grep but didn't read every delegating method.
2. **The `edit()` context manager**: One subagent mentioned [server.py:251-267](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/src/geolibre/mcp/server.py#L251-L267) has a `contextlib` context manager `edit(path)` that loads, validates, yields for modification, and writes back atomically. This is an important pattern I should verify by reading those exact lines.
3. **The `hatch_build.py` credential scanner**: Referenced in [python/pyproject.toml:70-74](file:///c:/Users/nguye/Documents/billboardAI/references/GeoLibre/python/pyproject.toml#L70-L74). Scans the bundled web build for credentials before packaging. Worth reading if OOHScout bundles a web build.
4. **Test patterns**: I didn't read any test files. The `[test]` extras discipline and `skipif`/`importorskip` patterns are documented from the pyproject.toml, but specific test examples should be studied when writing OOHScout tests.

---

## Appendix — Corrected File-to-File Mapping

| GeoLibre file | Actual Lines | OOHScout equivalent | Priority |
|---|---|---|---|
| `python/src/geolibre/project.py` | 1313 | `backend/src/oohscout/project.py` | P0 |
| `python/src/geolibre/authoring.py` | 1120 | `backend/src/oohscout/authoring.py` | P0 |
| `python/src/geolibre/mcp/server.py` | 1085 | `backend/src/oohscout/mcp/server.py` | P1 |
| `python/src/geolibre/mcp/workspace.py` | 142 | `backend/src/oohscout/mcp/workspace.py` | P1 |
| `python/src/geolibre/mcp/__init__.py` | 65 | `backend/src/oohscout/mcp/__init__.py` | P1 |
| `python/src/geolibre/mcp/__main__.py` | 5 | `backend/src/oohscout/mcp/__main__.py` | P1 |
| `backend/.../app/main.py` | 204 | `backend/src/oohscout/api/main.py` | P1 |
| `backend/.../app/postgis.py` | 963 | `backend/src/oohscout/api/deps.py` (pool patterns) | P1 |
| `apps/.../assistant/agent.ts` | 172 | `backend/src/oohscout/track_c_agent/session.py` | P1 |
| `apps/.../assistant/tools.ts` | 1081 | `backend/src/oohscout/track_c_agent/tools/*.py` | P1 |
| `apps/.../assistant/provider.ts` | 624 | `backend/src/oohscout/track_c_agent/providers.py` (~80 lines) | P2 |
| `workers/ai-proxy/src/index.ts` | 680 | Deferred to hosted phase | P3 |
| `skills/geolibre/SKILL.md` | 156 | `skills/oohscout/SKILL.md` | P1 |
| `docker-compose.yml` | 115 | `docker-compose.yml` | P1 |
| `.pre-commit-config.yaml` | 117 | `.pre-commit-config.yaml` | **P0** |
| `backend/.../pyproject.toml` (extras) | 75 | `pyproject.toml` extras rewrite | **P0** |

**P0 = do first, blocks everything.**
**P1 = do next, blocks MVP.**
**P2 = do when MVP validated.**
**P3 = do only if hosted phase.**
