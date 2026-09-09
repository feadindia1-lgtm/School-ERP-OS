# Student Master + Guardian + Family — Architecture (Prompt 3)

> **Student Master is the single authoritative student identity for the entire School OS.**
> There is no parallel student collection. The Prompt-2 `StudentStub` / `GuardianStub`
> were evolved *in place* into `Student` / `Guardian`. Existing IDs preserved.

## Collections (existing evolved + new)
- `students` — **canonical** Student Master (evolved from Prompt-2 stub)
- `guardians` — **canonical** Guardian Master (evolved)
- `student_guardians` — many-to-many relationship layer
- `student_enrollments` — historical academic placement (one row per AY)
- `families` — household grouping (siblings share via `family_id`)
- `admission_conversions` — unchanged; still points at `students._id`

## Lifecycle states
`PROSPECT · ACTIVE · INACTIVE · ON_LEAVE · TRANSFERRED · WITHDRAWN · GRADUATED · ALUMNI` — changed only via `POST /students/{id}/status` (audited).

## Admission conversion (evolved in `services/conversion.py`)
1. Reject if application ≠ APPROVED. 2. Idempotency: repeated calls return the same `student_id` (`already_converted=true`). 3. Create canonical `Student`. 4. **Reuse** existing `Guardian` if `(tenant_id, mobile_primary)` already exists — no duplicate guardian for siblings. 5. Create `StudentGuardian` (primary, emergency, pickup, fee, academic). 6. Create `StudentEnrollment` seed row. 7. Insert `AdmissionConversion`. 8. Update application → `CONVERTED`, propagate CRM lead → `ADMITTED`. Full audit `admission.convert`. Duplicate prevention backed by unique index `admission_conversions (tenant_id, application_id)`.

## RBAC — new permissions
`student.create · student.update · student.status.manage · student.enrollment.view/manage · student.guardian.view/manage · student.document.view/upload · student.family.view/manage · guardian.view/create/update · family.view/manage`

## API — `/api/v1/school`
- Students: `GET/POST /students · GET/PATCH /students/{id} · POST /students/{id}/status`
- Enrollments: `GET/POST /students/{id}/enrollments · PATCH /enrollments/{id}`
- Guardians: `GET/POST /guardians · GET/PATCH /guardians/{id}`
- Relationships: `GET/POST /students/{id}/guardians · PATCH/DELETE /student-guardians/{rid}`
- Families: `GET/POST /families · GET/PATCH /families/{id}`

## Indexes (tenant-first)
`students`: unique `(tenant_id, admission_number)`, `(tenant_id, student_number)`, plus `(tenant_id, status)`, `(tenant_id, academic_year, class_name)`, `(tenant_id, family_id)`, `(tenant_id, application_id)`.
`guardians`: `(tenant_id, mobile_primary)`, `(tenant_id, email)`, `(tenant_id, family_id)`.
`student_guardians`: `(tenant_id, student_id)`, `(tenant_id, guardian_id)`.
`student_enrollments`: `(tenant_id, student_id, academic_year)`, `(tenant_id, academic_year, class_name)`.
`families`: `(tenant_id, family_name)`.

## Migration / backwards compatibility
- `students` collection is preserved. Old StudentStub rows keep their `_id`; new fields simply arrive as `null` for legacy rows until a subsequent PATCH.
- Old `guardians` rows survive; conversion service now writes the new schema (`first_name`, `mobile_primary`). Existing rows remain readable — front-end tolerates missing fields.
- `admission_conversions.student_id` continues to point at the same `_id`.

## Sibling / shared guardian
Same `Guardian` reused when another admission comes in with the same mobile. UI can additionally set `family_id` on both students to reveal them under a Family.

## Future integration rules
Every downstream module (Attendance, Fees, Exams, Curriculum, Reports, Portal, Mobile) MUST reference `student_id`, `guardian_id`, `family_id` — never recreate identity.
