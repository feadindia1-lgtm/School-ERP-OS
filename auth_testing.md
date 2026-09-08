# Auth Testing Playbook

## MongoDB verification
```bash
mongosh
use school_os
db.users.findOne({role: "platform_superadmin"})  # bcrypt hash starts with $2b$
db.users.getIndexes()
db.tenants.getIndexes()
```

## API smoke tests

```bash
API=http://localhost:8001

# Health
curl -s $API/api/health

# Login as platform super admin
curl -s -c /tmp/plat.cookies -X POST $API/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"superadmin@schoolos.dev","password":"SuperAdmin@123"}'

curl -s -b /tmp/plat.cookies $API/api/v1/auth/me

# Register a new school (creates tenant + owner, logs in owner)
curl -s -c /tmp/school1.cookies -X POST $API/api/v1/auth/register-school \
  -H 'Content-Type: application/json' \
  -d '{"school_name":"Riverside Academy","slug":"riverside","contact_email":"admin@riverside.test","owner_full_name":"Ada Owner","owner_email":"owner@riverside.test","owner_password":"SchoolOwner@123"}'

# Tenant isolation
curl -s -b /tmp/school1.cookies $API/api/v1/school/users   # only riverside users
curl -s -b /tmp/school1.cookies $API/api/v1/platform/tenants  # 403 forbidden

# Platform overview
curl -s -b /tmp/plat.cookies $API/api/v1/platform/tenants
curl -s -b /tmp/plat.cookies $API/api/v1/platform/stats
```
