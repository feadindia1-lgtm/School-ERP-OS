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

## Implemented (2026-02-09) — Prompt 2: CRM + Admissions
### Backend
- Extended RBAC with granular `crm.*` and `admission.*` permissions; ADMISSION_OFFICER role wired to the CRM-heavy subset.
- New models: `CrmLead`, `CrmActivity`, `Followup`, `CampusVisit`, `AdmissionApplication`, `AdmissionDocument`, `AdmissionDocumentType`, `AdmissionConversion`, `AdmissionSettings`, `StudentStub`, `GuardianStub`.
- New services: `numbering.py` (concurrency-safe `INQ/ADM/STU-YYYY-NNNNNN` via atomic counters), `storage.py` (`LocalFilesystemStorage` under `/app/storage/tenants/{tenant_id}/`), `conversion.py` (idempotent).
- New routers: `/school/crm/*` (leads, duplicate detection, activities, follow-ups today/overdue/upcoming, visits + double-booking guard, settings, dashboard), `/school/admissions/*` (applications with state machine, doc upload/verify/reject + secure download, idempotent convert with `admission.override` guardrail).
- New indexes on all Prompt-2 collections including uniqueness on `(tenant_id, inquiry_number)`, `(tenant_id, application_number)`, `(tenant_id, application_id)` for conversions.
- All sensitive actions audited via existing `audit_service`.

### Frontend
- Introduced `SchoolShell` sidebar (Overview + Front Porch group + Administration group). Inherits tenant `branding.primary_color` / `accent_color`.
- New pages: `AdmissionsDashboardPage` (10 KPIs + stage/source breakdown), `InquiriesPage` (kanban + list + filters + pagination), `CreateInquiryDialog` (live duplicate detection, force override), `KanbanBoard` (drag-drop stage moves), `InquiryDetailPage` (prospect profile — timeline + follow-ups + stage select + create-application), `ApplicationsPage`, `ApplicationDetailPage` (document checklist with progress bar, upload/verify/reject flow, state-machine status transitions, one-click Convert to Student), `CampusVisitsPage`, `CrmConfigPage` (stages, sources, doc types with required/optional/conditional selector, block-approval toggle).
- `App.js` — nested routes under `/school` via `SchoolShell`; preserves original overview at `/school`.

### Test results
- **72/72 backend tests pass** (24 foundation + 17 platform Prompt 1 + 31 new CRM+admissions). Frontend Prompt 2 flows verified 100% (iter 6).
- Prompt 0 and Prompt 1 remain fully green — no regressions.

## Implemented (2026-02-09) — Prompt 3: Student Master + Guardian/Family
### Backend
- Canonical `Student` model replaces the Prompt-2 `StudentStub` in place (same `students` collection, IDs preserved). Full identity, snapshot placement, provenance, and lifecycle state (8 states) columns.
- New collections/models: `guardians`, `student_guardians` (M:N with relationship flags), `student_enrollments` (per-year history), `families` (sibling/fee scope container).
- New service `services/conversion.py` runs idempotent Application→Student conversion (dedupe on `(tenant_id, application_id)` via `admission_conversions`).
- New router `/api/v1/school/students*`, `/guardians*`, `/families*` — 24 endpoints total, all RBAC-gated by 12 new granular permissions (`student.*`, `guardian.*`, `family.*`, `student.guardian.*`, `student.enrollment.*`).
- New aggregate endpoints: `GET /students/stats` (Total, Active, New-this-year, Missing-info); `GET /students/{id}/timeline` (audit stream); `GET /guardians/{id}/students` (reverse lookup).
- Indexes on all new collections; tenant isolation enforced at query level; all mutating actions audited.

### Frontend
- `StudentsPage`: 4 KPI cards, status/class/year filters, sort dropdown, search, paginated table with clickable rows.
- `StudentDetailPage`: header with initials/status pill, 6 tabs (Overview, Academic, Guardians, Documents inherited from admission, Enrollments, Timeline), status change with reason, link/unlink guardian dialog, new-enrollment dialog, cross-links to family/guardian pages.
- `GuardiansPage` + `GuardianDetailPage`: search/paginated list, create dialog, inline edit, linked-students panel.
- `FamiliesPage` + `FamilyDetailPage`: create dialog, siblings + guardians panels, inline edit.
- Routes registered under existing `SchoolShell`.

### Test results
- **91/91 backend tests pass** (24 foundation + 17 Prompt 1 + 31 Prompt 2 + 17 Prompt 3 + 2 new endpoint E2E). 0 regressions.
- Frontend Prompt 3 flows verified end-to-end (KPIs, tabs, dialogs, cross-navigation, tenant isolation).

### Architectural guarantees
- **Single Student Master** — `StudentStub` code path removed; conversion writes directly to `students`.
- **Idempotent admission conversion** — repeat calls return the same `student_id`.
- **No parallel collection** created for Prompt 3.

## Implemented (2026-02-11) — Prompt 4: Academic Structure & School Calendar
### Backend
- New models (`app/models/academic.py`): `AcademicYear`, `BoardConfig`, `AcademicClass`, `AcademicSection`, `Subject`, `SubjectGroup`, `Room`, `BellSchedule` (inline periods), `WorkingDayPolicy`, `Holiday`, `TeacherAssignment`. Preset dictionary `BOARD_PRESETS` for CBSE/ICSE/IB/IGCSE/STATE/CUSTOM (labels + term structure).
- New RBAC block `ACADEMIC_PERMISSIONS` (10 granular): academic.view, academic.year.manage, academic.class.manage, academic.section.manage, academic.subject.manage, academic.room.manage, academic.schedule.manage, academic.calendar.manage, academic.assignment.manage, academic.board.config. School admin/owner/principal receive full set; teachers/class_teachers receive read-only view; admission officers receive view.
- 24 endpoints under `/api/v1/school/academic/*` with full RBAC + tenant scoping + audit logging.
- Validation rules: unique class code per year, unique section name per class, unique subject/room code per tenant, bell-schedule period non-overlap + no duplicate period_no, working-day/weekly-off conflict, teacher-user role validation, class-teacher uniqueness per section, teacher-assignment duplicate detection, historical year read-only (409 year_archived).
- Student model extended with denormalized FKs (`academic_year_id`, `class_id`, `section_id`) alongside existing string snapshots — kept both maintained for backward compatibility (per user choice 1a).
- Indexes: 15 new indexes covering all uniqueness + query paths.

### Frontend
- 9 new pages under `pages/school/academic/*`: AcademicOverviewPage (8-tile dashboard), AcademicYearsPage (create/set-current/archive), ClassesSectionsPage (nested), SubjectsPage (tabbed subjects+groups), RoomsPage, BellScheduleEditorPage (period grid + save), WorkingDaysHolidaysPage (weekday toggles + holidays), TeacherAssignmentsPage (matrix), BoardConfigPage (preset+labels+terms).
- Shared helpers `useAcademicYears` / `useCurrentYear` (localStorage-backed year selector) in `academic/_shared.js`.
- `SchoolShell` sidebar extended with "Academics" group (9 links); 10 nested routes registered in `App.js`.

### Test results
- **127/127 backend pytest** (89 foundation/CRM/admissions/student + 2 endpoint E2E + 36 academic). Zero regressions.
- **Frontend E2E fully green** — every data-testid resolved, every mutation flow verified.

### Board terminology handling
Presets + admin override implemented per user choice 2c. GET /board-config seeds from tenant.board (falls back to CBSE) and always returns the presets dictionary for the UI to offer as radio buttons; PATCH applies user overrides that survive preset changes.

### Grading scale / marks
Deferred to Prompt 6 (Exams) per user choice 3b; `marking_style` field on BoardConfig captures the placeholder without affecting current behaviour.

### Teacher assignment source
Points to existing `users` collection filtered by role in {teacher, class_teacher} per user choice 4a; no separate Teacher/Staff model introduced.

## Implemented (2026-02-12) — Prompt 5 (Phase 2): Staff Master + Leave Foundation
### Backend
- New models (`app/models/staff.py`): `Department`, `Designation`, `Employee` (canonical), `EmployeeDocument`, `EmployeeQualification`, `LeaveType`, `LeaveBalance`, `LeaveApplication`, `LeaveAdjustment`.
- Employee gains attendance hooks (`biometric_id`, `attendance_number`, `default_working_days`) — Prompt-6 Attendance will consume directly.
- Auto EMP-YYYY-NNNN via existing `numbering` service; admin override supported with uniqueness enforcement (user choice 2c).
- Employment types (full_time/part_time/contract/visiting/intern/consultant) and 8 lifecycle statuses (active/probation/on_leave/suspended/resigned/terminated/retired/notice_period).
- Leave workflow with **per-type approval_steps (1 or 2)** — user choice 4c. Two-step routes pending → approved_l1 → approved; single-step goes straight to approved.
- Leave presets shipped (CL/SL/EL/CO/ML/PL/LWP) returned inline with GET /leave-types; admin can start from a preset, override every field, or create fully custom — user choice 3c.
- Balance auto-materialization on first leave application; approve debits, cancel restores, manual adjust writes to `leave_adjustments` audit trail.
- 15 new RBAC permissions (`staff.*`, `leave.*`) wired to owner/admin/HR/teacher roles.
- `TeacherAssignment` extended with optional `employee_id`; auto-resolved at write time from linked `users.employee_id` — no regression to Prompt-4 API (user choice 1a).
- 15 new DB indexes covering uniqueness + query paths.
- New endpoints: 30 under `/api/v1/school/staff/*` — departments, designations, employees (CRUD + status + overview), documents, qualifications, leave-types (CRUD), leave-balances (list + adjust), leave-applications (list/apply/approve/reject/cancel).

### Frontend
- 5 new pages under `pages/school/staff/*`: `StaffPage` (KPIs + filters + pagination + create), `StaffDetailPage` (4-tab profile — Overview / Qualifications / Documents / Leave), `DepartmentsDesignationsPage` (tabbed CRUD), `LeaveTypesPage` (with preset selector + toggles), `LeaveApplicationsPage` (approve/reject/cancel + status filter).
- Shared `useStaffMeta` hook centralises departments/designations/leaveTypes.
- `SchoolShell` sidebar extended with "Staff" group (4 links).

### Test results
- **150/150 backend pytest** (89 foundation + 2 endpoint + 36 academic + 23 staff). Zero regressions.
- Frontend E2E fully green — every data-testid resolved, flows verified (dept/desig/leave-type creation, employee auto-code, status change, tab navigation, leave-type preset auto-fill).

### Deliberately NOT built (per prompt scope)
- Payroll — deferred to a later prompt.
- Salary structure / components / bank details beyond the free-form `kyc` blob on Employee.

### Prioritized backlog after Prompt 5
- **P0 · Prompt 6 — Attendance**: student (class-teacher / period-wise / biometric) + staff daily register, override audits, monthly summary — consumes Prompt-4 bell schedule + working-days + Prompt-5 employee.attendance_number/biometric_id.
- **P0 · Prompt 7 — Fees**: fee heads/structures, invoicing, collection, refunds, family-scoped billing.
- **P1**: Timetable & proxy engine, Payroll (leverages LeaveBalance), Exams & report cards.
