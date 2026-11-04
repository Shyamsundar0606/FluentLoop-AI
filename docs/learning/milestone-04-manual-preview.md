# Milestone 04 Manual Draft Preview

This local-only Compose stack is separate from the main FluentLoop application. It has its own persistent PostgreSQL volume, Redis, Mailpit, backend, and frontend. Draft preview is enabled only in the isolated development API and still requires a verified account with the `admin` role. Do not reuse a main-app account or change its role.

## Start the isolated preview

From the repository root in PowerShell:

```powershell
docker compose -p fluentloop-preview -f docker-compose.preview.yml up --build -d
docker compose -p fluentloop-preview -f docker-compose.preview.yml ps
```

The preview backend runs migrations and imports the bundled A1 content as draft on startup. The import is idempotent and does not publish lessons.

| Service | Local address |
|---|---|
| Preview frontend | http://localhost:3001 |
| Preview API docs | http://localhost:8001/docs |
| Preview API readiness | http://localhost:8001/api/v1/health/ready |
| Preview PostgreSQL | 127.0.0.1:5433 |
| Preview Redis | 127.0.0.1:6380 |
| Preview Mailpit | http://localhost:8026 |

Use the preview frontend at port 3001, not the main app at port 3000. The preview backend uses distinct cookie names and accepts only the preview frontend origins, so it does not overwrite the main app session.

## Create the dedicated administrator

The prepared preview includes the dedicated, verified administrator created in this environment. If provisioning another account is needed later, create a fresh verified administrator only in the preview database. This PowerShell example prompts for credentials without echoing the password and refuses to replace an existing account:

```powershell
$email = Read-Host "Preview administrator email"
$securePassword = Read-Host "Preview administrator password" -AsSecureString
$password = [System.Net.NetworkCredential]::new("", $securePassword).Password
$env:PREVIEW_ADMIN_EMAIL = $email
$env:PREVIEW_ADMIN_PASSWORD = $password
@'
import os
from app.core.database import SessionLocal
from app.models import User, UserPreferences, UserProfile
from app.schemas import EmailRequest, validate_password_strength
from app.security import hash_password, utcnow

email = EmailRequest(email=os.environ["PREVIEW_ADMIN_EMAIL"]).email
password = os.environ["PREVIEW_ADMIN_PASSWORD"]
validate_password_strength(password)
db = SessionLocal()
try:
    if db.query(User.id).filter(User.email == email).first():
        raise SystemExit("That email already exists in the isolated preview database; no changes made.")
    user = User(email=email, password_hash=hash_password(password), role="admin",
                is_active=True, email_verified_at=utcnow())
    db.add(user)
    db.flush()
    db.add(UserProfile(user_id=user.id, display_name="Preview Developer",
                       onboarding_completed_at=utcnow()))
    db.add(UserPreferences(user_id=user.id))
    db.commit()
    print("Verified preview administrator created.")
finally:
    db.close()
'@ | docker compose -p fluentloop-preview -f docker-compose.preview.yml exec -T preview-backend python -
Remove-Item Env:PREVIEW_ADMIN_EMAIL
Remove-Item Env:PREVIEW_ADMIN_PASSWORD
$password = $null
$securePassword = $null
```

Save that account's login details in your local password manager. The API does not expose a preview account credential. The account is restricted to this preview database; it has no role or account in the main database.

## Manually test lessons and progress

1. Sign in at http://localhost:3001 with the preview administrator.
2. Open **French courses**, select A1, and confirm the 10 draft lessons show the **Draft Preview** label.
3. Open a lesson and start or continue it. Select answers and submit them; grading and feedback come from the preview backend.
4. Use **Save and exit** or refresh to verify the current session resumes. Continue through all questions and complete the lesson.
5. Review the saved score and progress page/dashboard. Sign out and sign back in to verify progress persists.
6. Repeat for any of the other A1 lessons.

All imported lesson records remain `draft`. The existing independent French-language, pedagogy, answer-key, and licensing review requirements remain unchanged.

## Ordinary learner access

Use a separate `learner` account in the preview environment (a verified ordinary test learner is already available in the prepared environment), verify new registrations through http://localhost:8026, and sign in. Ordinary learners must not see A1 drafts in the course list and direct requests for a draft lesson or a developer's session must return 404. Do not elevate the learner account.

## Stop and retain preview data

```powershell
docker compose -p fluentloop-preview -f docker-compose.preview.yml down
```

This stops and removes only the preview containers and network. It keeps the named `fluentloop-preview_preview_postgres_data` volume and its preview users/progress. Do not add `-v` if you want to retain them. The main Compose project and its volume are unaffected.
