# AGENTS.md — python-rasenmaeher-api

## Purpose
Core REST API for Deploy App (RASENMAEHER). Acts as the central identity broker and enrollment
hub: it handles user enrollment requests, issues and validates certificates via CFSSL, brokers
authentication through Keycloak and OpenLDAP, and exposes the product integration API that all
services (TAK, Matrix, BattleLog, etc.) must implement to participate in the Deploy App ecosystem.

## Stack & Key Technologies
- **Language:** Python 3.11
- **Framework:** FastAPI + Uvicorn
- **ORM / DB:** SQLModel (SQLAlchemy + Pydantic), PostgreSQL (`raesenmaeher` schema)
- **Auth:** python-keycloak, python-ldap3
- **PKI:** httpx calls to cfssl service
- **Key libs:** libpvarki (internal pvarki library), cryptography, pydantic v2
- **Testing:** pytest, pytest-cov (65% minimum coverage), tox
- **Linting:** pre-commit, pylint (shared `pylintrc`)
- **Container:** Docker multi-target (devel_shell, tox, production)

## Development Setup
```bash
# Docker (recommended)
export DOCKER_BUILDKIT=1
# Linux SSH agent forwarding:
export DOCKER_SSHAGENT="-v $SSH_AUTH_SOCK:$SSH_AUTH_SOCK -e SSH_AUTH_SOCK"

docker build --ssh default --target devel_shell -t rasenmaeher_api:devel_shell .
docker create --name rasenmaeher_api_devel -v $(pwd):/app -p 8000:8000 \
  -it $(echo $DOCKER_SSHAGENT) rasenmaeher_api:devel_shell
docker start -i rasenmaeher_api_devel

# Native (uv — installs Python 3.11 + deps into .venv automatically)
uv sync

# Required env vars (set in .env or export):
# RM_CFSSL_HOST, RM_KEYCLOAK_SERVER_URL, RM_KEYCLOAK_CLIENT_ID,
# RM_KEYCLOAK_REALM_NAME, RM_KEYCLOAK_CLIENT_SECRET,
# RM_LDAP_CONN_STRING, RM_LDAP_USERNAME, RM_LDAP_CLIENT_SECRET
```

## Running Tests
```bash
# Via tox (CI method, builds fresh environment)
docker build --ssh default --target tox -t rasenmaeher_api:tox .
docker run --rm -it -v $(pwd):/app $(echo $DOCKER_SSHAGENT) rasenmaeher_api:tox

# Directly inside devel_shell container
pytest tests/ -v --cov=rasenmaeher_api --cov-fail-under=65

# Pre-commit
pre-commit install --install-hooks
pre-commit run --all-files
```

## Code Conventions
- Router modules go in `src/rasenmaeher_api/routers/` named by domain (e.g., `enroll.py`).
- SQLModel models in `src/rasenmaeher_api/models/`.
- Follow pylint rules in `pylintrc` at root; pre-commit enforces this.

## Architecture Notes
**Key API endpoints:**
- `POST /api/v1/enroll/init` — Start enrollment; returns work_id
- `GET  /api/v1/enroll/status/{work_id}` — Poll enrollment status
- `GET  /api/v1/enroll/deliver/{id_string}` — Download credential package
- `POST /api/v1/enroll/accept` — Admin accepts enrollment request
- `POST /api/v1/product/sign_csr` — Product signs its CSR via internal CA

**Integration contract:** All product integration APIs must implement the user lifecycle
callbacks (`/api/v1/users/created`, `revoked`, `promoted`, `demoted`). These are called by
`rmapi` when user state changes.

**Certificate flow:** `rmapi` → `cfssl:8888` → signs CSR → returns cert chain. The CA public
cert is at `/ca_public/ca_chain.pem` on the shared Docker volume.

**Backend services manifest:** Product services announce themselves via a JSON manifest at
`/pvarki/kraftwerk-rasenmaeher-init.json` (written by miniwerk to the shared volume).

**Database:** PostgreSQL schema `raesenmaeher`. In dev, SQLite fallback is available
(`RM_SQLITE_FILEPATH_DEV`).

## Common Agent Pitfalls
1. **All env vars are `RM_` prefixed.** The setting name in code is lowercase without the
   prefix. `RM_CFSSL_HOST` in env → `settings.cfssl_host` in Python. Do not hardcode hostnames.
2. **`rmapi` depends on cfssl AND keycloak being healthy before it can serve requests.** In
   compose, it has explicit health-check dependencies. In unit tests, mock both clients.
3. **Do not edit the DB schema directly.** Schema migrations must go through SQLModel model
   changes + Alembic migration scripts. Running `CREATE TABLE` ad hoc will break the migration state.
4. **Coverage threshold is 65%.** New endpoints without tests will fail CI. Add at least a basic
   happy-path test for every new route.
5. **The `libpvarki` library is installed from a private Nexus registry.** If pip install fails
   with a 401, check that SSH agent forwarding is set up correctly for the Docker build.

## Related Repos
- https://github.com/pvarki/docker-rasenmaeher-integration (orchestration root)
- https://github.com/pvarki/python-pvarki-cfssl (certificate authority)
- https://github.com/pvarki/docker-rasenmaeher-keycloak (identity provider)
- https://github.com/pvarki/python-miniwerk (cert + manifest orchestration)
