# School OS — Architecture (Prompt 0 Foundation)

## Product
Multi-tenant SaaS for schools. Combines a CRM (**Front Porch**: inquiry→admission conversion) with an ERP (**Main House**: students, attendance, fees, payroll, academics, exams, curriculum). Serves many independent schools; each is a **tenant**.

## Stack
- **Backend:** FastAPI + Motor (async MongoDB) + PyJWT + bcrypt.
- **Frontend:** React 19, Tailwind, Shadcn UI, Framer Motion, Phosphor icons.
- **DB:** MongoDB (`school_os`).
- **Auth:** JWT access (30 min) + refresh (7 d), stored as `httpOnly; Secure; SameSite=None` cookies. Bearer header fallback for API clients.

## Layout
```
/app/backend/
├── server.py                  # entrypoint, CORS, error handlers, startup hooks
├── app/
│   ├── core/
│   │   ├── config.py          # env-driven Settings
│   │   ├── db.py              # Motor client + index creation
│   │   ├── security.py        # bcrypt + JWT helpers
│   │   ├── permissions.py     # roles, permissions, role→permission map
│   │   ├── deps.py            # auth + RBAC + tenant scoping deps
│   │   └── errors.py          # unified error envelope
│   ├── models/                # BaseDocument, Tenant, User, AuditLog
│   ├── services/
│   │   ├── audit_service.py   # centralized audit-log writer
│   │   └── seed.py            # platform superadmin seeder
│   └── api/v1/
│       ├── router.py          # /api/v1 aggregate
│       ├── auth_routes.py     # register-school, login, logout, refresh, me
│       ├── platform_routes.py # super-admin: tenants, audit, stats
│       ├── school_routes.py   # tenant-scoped: school, users, rbac, audit
│       └── meta_routes.py     # health, meta
```

## Multi-tenancy
- Every school-owned document carries `tenant_id`.
- Every school-scoped endpoint reads `tenant_id` from the authenticated user's token — never from the URL or request body — and injects it into the Mongo query.
- `enforce_tenant()` helper protects any endpoint that accepts an explicit `tenant_id`: platform admins are the only actors allowed to cross tenants; tenant users are pinned to their own.
- Users are uniquely indexed on `(email, tenant_id)`, so the same address can exist in multiple schools without collision.

## RBAC
- Roles are strings; authorization only checks **permission strings** via `require_permission("user.create")`, never role names.
- `ROLE_PERMISSIONS` maps each role to a set of permissions. Individual users may hold `extra_permissions` to add fine-grained grants.
- The platform superadmin holds every permission by default.
- Roles cannot be self-assigned; changing a role requires `role.assign`.
- Reserved role `platform_superadmin` cannot be created via school APIs.

### Roles
`platform_superadmin` · `school_owner` · `principal` · `school_admin` · `admission_officer` · `accountant` · `hr_officer` · `teacher` · `class_teacher` · `student` · `parent`

### Permissions (24, examples)
`platform.manage`, `tenant.create/view/edit/suspend`, `audit.view.platform`, `school.view/edit`, `user.view/create/edit/delete`, `role.assign`, `audit.view.school`, `student.view/edit`, `attendance.override`, `fees.collect/refund`, `payroll.process`, `exam.publish`, `lessonplan.approve`, `crm.manage/convert`.

## Auditability
Every sensitive action calls `log_event()` which writes an `audit_logs` document with `tenant_id, actor, action, resource, resource_id, ip, user_agent, old_value, new_value`. Currently wired: tenant create/update, school update, auth login/logout/register, user create/update/delete.

## Error Model
```
{ "error": { "code": "unauthorized|forbidden|not_found|conflict|validation_error|internal_error|http_error", "message": "...", "details": ... } }
```
`register_exception_handlers()` catches `HTTPException`, `RequestValidationError`, and unhandled exceptions — no raw stack traces leak.

## Health & Meta
- `GET /api/health`, `GET /api/v1/health` — pings Mongo.
- `GET /api/v1/meta` — product info + full role & permission catalog.

## API Versioning
All routes live under `/api/v1/…`. A future `/api/v2/router.py` can be added and included without breaking v1 consumers.

## API-First
Every capability the web console uses is a plain REST endpoint under `/api/v1`. Native (Expo) apps can consume the exact same endpoints with `Authorization: Bearer <token>` — the tokens returned as cookies are also valid Bearer tokens.

## Mongo Indexes (created on startup)
- `users`: `(email, tenant_id)` unique · `tenant_id`
- `tenants`: `slug` unique
- `audit_logs`: `(tenant_id, created_at desc)` · `actor_id`
- `login_attempts`: `identifier`
- `password_reset_tokens`: TTL on `expires_at`
- `refresh_tokens`: TTL on `expires_at` · unique `jti`

## Not Implemented Yet (by design in Prompt 0)
Business domains — CRM, admissions, students, attendance, fees, payroll, exams, curriculum, communication, reports, analytics, subscriptions, integrations, settings modules — are architected (roles/permissions exist) but not built.
