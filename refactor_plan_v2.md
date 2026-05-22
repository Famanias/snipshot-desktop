# Refactor Plan v2: Direct Supabase Connection

## Overview

Refactor the desktop app to connect directly to Supabase, eliminating the need to run the `database_api` server locally. This simplifies deployment, reduces infrastructure overhead, and improves security posture.

---

## Architecture

### Current
```
Desktop App → database_api (FastAPI on port :8000) → Supabase
```

### Target
```
Desktop App → Supabase (direct)
```

**Benefit**: One-command startup. No separate server. Faster round-trips.

---

## Pre-Implementation: Supabase RLS Audit ⚠️

> **Do this before writing any client code.** Without correct Row Level Security policies, users may be able to read or modify each other's data.

### Required RLS Policies

Ensure the following policies exist on every user-facing table (`folders`, `images`):

```sql
-- Users can only see their own folders
CREATE POLICY "users_own_folders" ON folders
  FOR ALL USING (auth.uid() = user_id);

-- Users can only see their own images
CREATE POLICY "users_own_images" ON images
  FOR ALL USING (auth.uid() = user_id);
```

Also apply storage bucket policies:

```sql
-- Users can only access their own storage objects
CREATE POLICY "users_own_objects" ON storage.objects
  FOR ALL USING (auth.uid()::text = (storage.foldername(name))[1]);
```

**Verification**: Test with two separate user accounts and confirm cross-user data access is blocked before proceeding.

---

## Phase 1: Dependencies & Configuration

### 1.1 Add to `requirements.txt`

```
supabase>=2.0.0   # Direct auth, storage, and PostgREST queries
keyring>=24.0.0   # OS-level secure token storage (replaces custom encryption)
```

> **Why keyring over cryptography/Fernet?** Fernet is only as secure as where you store the encryption key. If the key lives next to the token file (or is hardcoded), it's security theater. `keyring` delegates to Windows Credential Manager, macOS Keychain, or libsecret on Linux — genuinely secure with one line of code.

### 1.2 Update `config.py`

```python
import os

# Supabase credentials (direct connection)
# Get these from your Supabase dashboard → Project Settings → API
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# NEVER include SUPABASE_SERVICE_KEY in a desktop app.
# Service keys bypass RLS entirely and should only be used server-side.

# Translator API (separate service)
TRANSLATOR_URL = os.getenv("TRANSLATOR_URL", "http://localhost:8001")

# Local storage
LOCAL_STORAGE_DIR = os.getenv("LOCAL_STORAGE_DIR")
```

### 1.3 Create `.env.example`

```
# Supabase credentials — get from Supabase dashboard → Project Settings → API
SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
SUPABASE_ANON_KEY=YOUR_ANON_KEY
# NOTE: Do NOT add SUPABASE_SERVICE_KEY here. It bypasses RLS and must never ship in a desktop app.

# Translator API
TRANSLATOR_URL=http://localhost:8001

# Local mode storage
LOCAL_STORAGE_DIR=%APPDATA%/SnipShot
```

---

## Phase 2: Token Persistence (Before the Client)

> Build this before `SupabaseAPIClient` so the client can use it from day one.

### 2.1 Create `api/token_storage.py`

```python
import keyring
import json
from typing import Optional

SERVICE_NAME = "SnipShot"
TOKEN_KEY = "supabase_session"


def save_tokens(access_token: str, refresh_token: str) -> None:
    """Persist tokens to OS keychain (Credential Manager / Keychain / libsecret)."""
    payload = json.dumps({
        "access_token": access_token,
        "refresh_token": refresh_token,
    })
    keyring.set_password(SERVICE_NAME, TOKEN_KEY, payload)


def load_tokens() -> Optional[dict]:
    """Load tokens from OS keychain. Returns None if not found."""
    raw = keyring.get_password(SERVICE_NAME, TOKEN_KEY)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def clear_tokens() -> None:
    """Delete tokens from OS keychain on logout."""
    try:
        keyring.delete_password(SERVICE_NAME, TOKEN_KEY)
    except keyring.errors.PasswordDeleteError:
        pass  # Already gone, not an error
```

**Fallback**: On headless Linux environments where no keychain backend is available, `keyring` raises `NoKeyringError`. Catch it and fall back to a Fernet-encrypted file in that case only.

---

## Phase 3: Create `SupabaseAPIClient`

### 3.1 Create `api/supabase_client.py`

All methods return a consistent shape:
```python
{"success": bool, "data": Any, "error": Optional[str]}
```

#### Initialization & Session Restore

```python
from supabase import create_client, Client
from api.token_storage import load_tokens, save_tokens, clear_tokens
from config import SUPABASE_URL, SUPABASE_ANON_KEY

class SupabaseAPIClient:
    def __init__(self):
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        self._restore_session()

    def _restore_session(self):
        """On app startup, reload persisted tokens."""
        tokens = load_tokens()
        if tokens:
            try:
                self.client.auth.set_session(
                    tokens["access_token"],
                    tokens["refresh_token"]
                )
            except Exception:
                clear_tokens()  # Tokens invalid or expired past refresh window
```

#### Authentication

```python
    def register(self, email: str, password: str) -> dict:
        try:
            res = self.client.auth.sign_up({"email": email, "password": password})
            save_tokens(res.session.access_token, res.session.refresh_token)
            return {"success": True, "data": res.user}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def login(self, email: str, password: str) -> dict:
        try:
            res = self.client.auth.sign_in_with_password({"email": email, "password": password})
            save_tokens(res.session.access_token, res.session.refresh_token)
            return {"success": True, "data": res.user}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def logout(self) -> dict:
        try:
            self.client.auth.sign_out()
            clear_tokens()
            return {"success": True, "data": None, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def get_profile(self) -> dict:
        try:
            user = self.client.auth.get_user()
            return {"success": True, "data": user, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
```

#### Folders

```python
    def get_folders(self) -> dict:
        try:
            res = self.client.table("folders").select("*").execute()
            return {"success": True, "data": res.data, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def create_folder(self, name: str, description: str = "") -> dict:
        try:
            user = self.client.auth.get_user()
            res = self.client.table("folders").insert({
                "name": name,
                "description": description,
                "user_id": user.user.id,
            }).execute()
            return {"success": True, "data": res.data, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def update_folder(self, folder_id: str, name: str, description: str) -> dict:
        try:
            res = (self.client.table("folders")
                   .update({"name": name, "description": description})
                   .eq("id", folder_id)
                   .execute())
            return {"success": True, "data": res.data, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def delete_folder(self, folder_id: str, delete_images: bool = False) -> dict:
        """
        Delete a folder. If delete_images=True, remove all associated images
        from storage and the database first to avoid orphaned objects.
        """
        try:
            if delete_images:
                # 1. Fetch all images in this folder
                img_res = (self.client.table("images")
                           .select("id, storage_path")
                           .eq("folder_id", folder_id)
                           .execute())

                for img in img_res.data:
                    # 2. Delete each from storage
                    self.client.storage.from_("images").remove([img["storage_path"]])
                    # 3. Delete DB record
                    self.client.table("images").delete().eq("id", img["id"]).execute()

            # 4. Delete the folder itself
            self.client.table("folders").delete().eq("id", folder_id).execute()
            return {"success": True, "data": None, "error": None}
        except Exception as e:
            # Partial failure: log what succeeded for debugging
            return {"success": False, "data": None, "error": str(e)}
```

> **Note on cascade delete**: The order matters — storage objects first, then DB rows. If the DB row is deleted first and the storage delete fails, you have orphaned objects with no reference to clean up. Consider wrapping this in a Supabase database function/RPC for atomicity if this becomes a reliability concern.

#### Images

```python
    def get_images(self, folder_id: str, page: int = 1, per_page: int = 20) -> dict:
        try:
            offset = (page - 1) * per_page
            res = (self.client.table("images")
                   .select("*")
                   .eq("folder_id", folder_id)
                   .range(offset, offset + per_page - 1)
                   .execute())
            return {"success": True, "data": res.data, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def upload_image(
        self,
        file_path: str,
        original_filename: str,
        source_lang: str,
        target_lang: str,
        folder_id: str,
    ) -> dict:
        try:
            import time
            user = self.client.auth.get_user()
            user_id = user.user.id
            timestamp = int(time.time())
            storage_path = f"{user_id}/{timestamp}_{original_filename}"

            with open(file_path, "rb") as f:
                self.client.storage.from_("images").upload(storage_path, f)

            public_url = self.client.storage.from_("images").get_public_url(storage_path)

            res = self.client.table("images").insert({
                "folder_id": folder_id,
                "user_id": user_id,
                "storage_path": storage_path,
                "public_url": public_url,
                "original_filename": original_filename,
                "source_lang": source_lang,
                "target_lang": target_lang,
            }).execute()

            return {"success": True, "data": res.data[0], "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def delete_image(self, image_id: str) -> dict:
        """Delete image from storage first, then remove DB record."""
        try:
            # Fetch storage path before deleting DB record
            res = (self.client.table("images")
                   .select("storage_path")
                   .eq("id", image_id)
                   .single()
                   .execute())
            storage_path = res.data["storage_path"]

            # Delete from storage first
            self.client.storage.from_("images").remove([storage_path])

            # Then remove DB row
            self.client.table("images").delete().eq("id", image_id).execute()
            return {"success": True, "data": None, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def search_images(self, query: str) -> dict:
        try:
            res = (self.client.table("images")
                   .select("*")
                   .ilike("original_filename", f"%{query}%")
                   .execute())
            return {"success": True, "data": res.data, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
```

---

## Phase 4: Update API Module

### 4.1 Update `api/__init__.py`

```python
from .supabase_client import SupabaseAPIClient

_default_client = SupabaseAPIClient()

class _ClientProxy:
    def __init__(self, impl):
        self._impl = impl

    def set_impl(self, impl):
        self._impl = impl

    def __getattr__(self, name):
        return getattr(self._impl, name)

api_client = _ClientProxy(_default_client)
```

**Backward Compatibility**: The proxy pattern ensures all existing UI code continues to work without modification.

---

## Phase 5: UI Components

No structural changes are needed if `api_client` methods return consistent shapes. Verify the following:

- **Login/Register**: Map Supabase error codes to user-friendly messages (e.g., `"Email already registered"` instead of raw API errors).
- **Dashboard**: Confirm folder/image lists render correctly with PostgREST response format (`res.data` is a list).
- **Image Upload**: Show a progress indicator. Handle `StorageException` for quota errors with a clear message.
- **Local Mode Toggle**: Continues to work via `api_client.set_impl(LocalAPIClient())` — no changes needed.

---

## Phase 6: Testing

> Write unit tests alongside Phase 3, not after. Catching interface bugs early saves hours.

### 6.1 Unit Tests (`test_supabase_client.py`)

- Auth flow: register, login, session restore on restart, logout
- Token persistence: save → load → clear roundtrip
- Folder CRUD: create, read, update, delete (with and without images)
- Image: upload, fetch, paginate, delete
- Cascade delete: verify storage objects removed before DB rows

### 6.2 Integration Tests

Run the full desktop app and verify:

- [ ] Login persists across restarts
- [ ] Two accounts cannot see each other's data (RLS check)
- [ ] Image upload stores file in correct `{user_id}/` path
- [ ] Image delete removes both storage object and DB row
- [ ] Logout clears tokens from OS keychain

### 6.3 Edge Cases

- [ ] What if storage delete succeeds but DB delete fails?
- [ ] What if token is expired and refresh also fails? (Prompt re-login gracefully)
- [ ] What if Supabase is unreachable? (Show clear offline error, don't crash)
- [ ] Headless Linux: `keyring` no backend available → fall back to Fernet file storage

---

## Phase 7: Cleanup & Deprecation

- Mark `database_api/` as deprecated in its README. Keep for 1-2 sprints, then remove.
- Update root `README.md`: remove "run database_api" step, add Supabase credentials setup.
- Remove `database_api` from any startup scripts or `Procfile`/`docker-compose.yml`.
- Add a note in `config.py` warning against ever using `SERVICE_KEY` in this app.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| RLS misconfiguration exposes user data | Medium | Critical | Audit + test with two accounts before shipping |
| Cascade delete partial failure (orphaned storage) | Medium | Medium | Delete storage first; consider DB function for atomicity |
| Token expiry with no refresh | Medium | High | `set_session()` on startup; prompt re-login on `AuthError` |
| `keyring` unavailable on headless Linux | Low | Medium | Catch `NoKeyringError`, fall back to Fernet file |
| Supabase SDK breaking changes | Low | Medium | Pin SDK version (`supabase==2.x.x`), review changelog on updates |
| Offline / no connection | Medium | Medium | Catch network errors, show actionable message |
| Service key accidentally shipped | Low | Critical | Never add to `.env.example`; add lint/CI check |

---

## Rollback Plan

1. `api/client.py` (original HTTP client) remains untouched.
2. `database_api/` stays running for fallback.
3. Switch via proxy: `api_client.set_impl(HTTPAPIClient())`.
4. Optional CLI flag: `python main.py --use-http-api`.

---

## Success Criteria

- ✅ Desktop app connects directly to Supabase — no local server needed
- ✅ RLS verified: users cannot access each other's data
- ✅ All auth, folder, and image operations work end-to-end
- ✅ Tokens stored in OS keychain (not plaintext or weakly encrypted)
- ✅ Session restored automatically on app restart
- ✅ Cascade delete leaves no orphaned storage objects
- ✅ Local mode still works as an alternative
- ✅ Graceful error handling for offline and expired-token scenarios
- ✅ Service key never present in desktop app code or config

---

## Timeline Estimate

| Phase | Effort | Notes |
|-------|--------|-------|
| Pre-impl: RLS audit | 1–2 hours | Non-negotiable; do before writing any client code |
| 1. Dependencies & config | 30 min | Add packages, update config, create `.env.example` |
| 2. Token persistence | 1 hour | `keyring` implementation + headless fallback |
| 3. SupabaseAPIClient | 4–6 hours | Main implementation; write unit tests alongside |
| 4. API module update | 30 min | Swap default client in `__init__.py` |
| 5. UI verification | 1–2 hours | Smoke-test each screen, fix error message mapping |
| 6. Testing | 3–4 hours | Unit + integration + edge cases |
| 7. Cleanup | 1 hour | Docs, deprecation notes, remove startup scripts |
| **Total** | **~12–17 hours** | **~2–3 days realistic with edge case testing** |

---

## Open Decisions

| # | Question | Recommendation |
|---|----------|---------------|
| 1 | Token storage on headless Linux | Fernet fallback only when `keyring.NoKeyringError` is raised |
| 2 | Cascade delete atomicity | Start with ordered deletes (storage → DB); upgrade to Supabase RPC if reliability issues arise |
| 3 | Offline support | Out of scope for this phase; add UI error state that shows a "You appear to be offline" message |
| 4 | Service key usage | Never. Anon key + RLS only. Document this explicitly. |
| 5 | Keep `database_api`? | Deprecate; remove after 1–2 sprints once direct connection is stable |
| 6 | Local mode toggle | Keep existing UI and `set_impl()` mechanism — no changes needed |
