# School OS — PRD & Build Log

## Original problem statement (Prompt 0)
Build the foundation of a production-ready multi-tenant SaaS platform called **School OS**. It combines Front Porch (CRM) with Main House (ERP). This prompt establishes the platform-level foundation only: project structure, database strategy, authentication foundation, tenant middleware/dependencies, RBAC foundation, API structure, error-handling pattern, logging, health endpoint, environment config, and tenant-isolation tests. No business modules are implemented yet.

## Architectural choices
- **Backend:** FastAPI + Motor + PyJWT + bcrypt (MongoDB).
- **Frontend:** React 19 + Tailwind + Shadcn UI + Framer Motion + Phosphor icons.
- **Auth:** JWT access (30 min) + refresh (7 d) in httpOnly Secure SameSite=None cookies. Bearer header fallback for API clients.
- **Multi-tenancy:** `tenant_id` on every school-owned document; tenant enforcement in service-layer deps, not the UI.
- **RBAC:** 11 roles → 24 granular permissions. Endpoints check permission strings, never role names.
- **Audit:** Central `audit_service.log_event()` writes actor, resource, IP, old/new value.
- **API:** Everything under `/api/v1/…` so `/api/v2` can coexist later.
- **Errors:** Central handler emits `{error: {code, message, details}}`.

## User personas
- **Platform Super Admin** — Emergent-side operator. Manages tenants across the entire SaaS.
- **School Owner / Management** — Runs their own school; full school-admin permissions.
- **Principal / School Admin / Admission Officer / Accountant / HR Officer / Teacher / Class Teacher** — Staff roles with tailored permission sets.
- **Student / Parent** — Read-only school view (future modules will unlock more).

## Core requirements (static)
- Tenant isolation enforced server-side.
- API-first — native apps consume the same endpoints.
- Auditable sensitive actions.
- Consistent error envelope, no raw stack traces.
- Configurable via environment variables only.

## Implemented (2026-02-09) — foundation
- Backend project restructured into `app/{core,models,services,api/v1}`.
- Config + Motor client + startup index creation.
- Bcrypt password hashing, PyJWT token helpers with JTI, refresh-token revocation on logout.
- Full RBAC catalogue (11 roles, 24 permissions) with role→permission map.
- Tenant-aware deps: `get_current_user`, `require_permission`, `require_platform_admin`, `require_tenant_user`, `enforce_tenant`.
- Central audit service and unified error envelope with FastAPI exception handlers.
- Auth endpoints: `register-school`, `login`, `refresh`, `logout`, `me` — brute-force lockout (5 fails / 15 min) using correctly parsed leftmost X-Forwarded-For.
- Platform routes: `/platform/tenants`, `/platform/tenants/{id}` (view/update), `/platform/audit-logs`, `/platform/stats`.
- School routes: `/school/`, `/school/users`, `/school/rbac`, `/school/audit-logs`.
- Meta routes: `/health`, `/meta`.
- Frontend: Landing (bento marketing), Login, Register-School, Platform Console (tenants + platform audit), School Console (8 module coming-soon cards, users CRUD, RBAC catalog, school audit).
- Docs: `/app/docs/ARCHITECTURE.md`, `/app/auth_testing.md`, `/app/memory/test_credentials.md`.
- Verified: 24/24 backend tests pass — tenant isolation, RBAC, audit, error envelope, brute-force lockout. Frontend flows 100%.

## Implemented (2026-02-09) — Prompt 1: SaaS onboarding
### Backend
- Extended `Tenant` model with `short_name, school_code, board, school_type, contact, academic, branding, modules, trial_ends_at, subscription_started_at`. Enum sets exposed (`BOARDS`, `SCHOOL_TYPES`, `SCHOOL_STATUSES`, `PLANS`) and `DEFAULT_MODULES / DEFAULT_BRANDING / DEFAULT_CONTACT / DEFAULT_ACADEMIC`.
- New `Alert` model + `alert_service.create_alert()`; pricing map in `services/pricing.py` (trial/starter/standard/premium/enterprise).
- Expanded `TenantOut` and `AuthResponse` (with `impersonation` block); added wizard DTOs (`WizardInstitution/Contact/Academic/Administrator/Branding/Modules`, `CreateSchoolRequest`, `CreateSchoolResponse`), `TenantStatusChange`, `TenantPlanChange`, `TenantEntitlementsUpdate`, `ImpersonateRequest`, `AlertOut`, `PlatformStats`.
- New / updated platform endpoints under `/api/v1/platform`:
  - `POST /schools` — wizard onboarding (creates tenant + `school_admin`, generates temp password if omitted, alerts + audits).
  - `GET  /tenants` — filtered by status/query.
  - `GET  /tenants/{id}` · `PATCH /tenants/{id}` — extended fields.
  - `POST /tenants/{id}/status` — activate / suspend / archive (audits, raises alert on suspend/archive).
  - `POST /tenants/{id}/plan` — change plan, records MRR delta and sets `subscription_started_at`.
  - `POST /tenants/{id}/entitlements` — merge module toggles (unknown keys ignored).
  - `GET  /tenants/{id}/usage` — users total + by-role, audit_events_30d, logins_30d.
  - `GET  /stats` — dashboard KPIs (`total/active/trial/suspended/archived`, students, teachers, users, MRR, audit_events_30d, subscription_status mix, recently_onboarded, open_alerts).
  - `GET  /alerts` · `POST /alerts/{id}/acknowledge`.
  - `POST /tenants/{id}/impersonate` · `POST /impersonate/exit` — full support mode with reason (>=4 chars), separate `impersonator_id` cookie, and `impersonation.start` / `impersonation.end` audit events.
- New `GET /api/v1/auth/session` — returns full session `{user, tenant, impersonation}`.
- Security: `create_access_token` accepts arbitrary claims; `get_current_user` surfaces `impersonated_by` + `impersonation_reason` on the user dict for downstream audit.
- New indexes: `tenants.school_code` (sparse), `tenants.status`, `alerts (tenant_id, acknowledged, created_at desc)`, TTL 24 h on `login_attempts.last_attempt`.

### Frontend
- Introduced sidebar shell `PlatformShell` (Dashboard / Schools / Alerts / Audit log) — foundation for future ERP module navigation.
- `PlatformDashboardPage` — 8 KPI tiles, recently-onboarded list, subscription-mix panel, open-alerts CTA.
- `PlatformSchoolsPage` — searchable + status-filtered tenants table.
- `PlatformSchoolNewPage` — 6-step wizard (Institution → Contact → Academic → Administrator → Branding → Modules); success screen displays generated temp password.
- `PlatformSchoolDetailPage` — Overview edit, plan change, entitlement toggles, usage KPIs, and support-mode dialog with mandatory reason.
- `PlatformAlertsPage` — open/all tabs, per-row acknowledge.
- `PlatformAuditPage` — action-prefix filter, dense table.
- `ImpersonationBanner` — global yellow support-mode banner with one-click exit.
- `AuthContext` upgraded to hydrate from `/auth/session` and expose `impersonation` + `exitImpersonation()`.
- `SchoolConsolePage` — module cards now reflect the tenant's `modules` toggles (enabled/disabled); impersonation banner rendered when applicable.
- `App.js` — nested routes under `/platform` via `PlatformShell`; catch-all `*` route.
- Verified: **41/41 backend tests pass** (24 foundation + 17 Prompt 1). Frontend flows 100% including wizard end-to-end, impersonation round-trip, alert acknowledgment.

## Prioritized backlog

### P0 (next prompts)
- **Front Porch (CRM):** Inquiry → Follow-up → Campus Visit → Application → Documents → Approval → Admission Fee → Student conversion.
- **Students module:** Registry, guardians, transfer, certificates.
- **Academic Years, Classes, Sections, Subjects.**

### P1
- Attendance (class-teacher + biometric hooks) with `attendance.override` audits.
- Timetable + proxy scheduling.
- Fee structures + collection + refunds.
- Communication (announcements, notifications).

### P2
- Payroll (salary components + statutory).
- Exams + marks + report cards.
- Curriculum syllabus + lesson plans + curriculum execution tracking.
- Analytics + reports.
- Subscriptions & billing for tenants.
- Integrations (SMS, email, payments).
- Expo/React Native mobile app on the same `/api/v1`.

## Not implemented (by design)
All business domains beyond auth/tenants/users/roles/audit are scaffolded via permissions only. Their endpoints will land in `/api/v1/{domain}` in subsequent prompts.
