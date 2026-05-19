# Refactor Plan: Direct Supabase Connection

## Overview
Refactor the desktop app to connect directly to Supabase, eliminating the need to run the `database_api` server locally. This simplifies deployment and reduces infrastructure overhead.

---

## Current Architecture
```
Desktop App → database_api (FastAPI on port :8000) → Supabase
```

**Issue**: Users must run a separate FastAPI server before using the desktop app.

---

## Target Architecture
```
Desktop App → Supabase (direct)
```

**Benefit**: One-command startup. No need for a separate server.

---

## Implementation Plan

### Phase 1: Dependencies & Configuration

#### 1.1 Add Supabase SDK to `requirements.txt`
```
supabase>=1.0.0  # For direct auth, storage, and PostgREST queries
```

#### 1.2 Update `config.py`
Add Supabase credentials:
```python
# Supabase credentials (direct connection)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")  # Public anon key for frontend
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # Optional: for privileged ops
```

**Note**: The desktop app is effectively a "frontend" so use `ANON_KEY` for normal operations. `SERVICE_KEY` only if needed for admin tasks.

---

### Phase 2: Create SupabaseAPIClient

#### 2.1 Create `api/supabase_client.py`
A new client class that mirrors the interface of `APIClient` but uses Supabase SDK directly.

**Key responsibilities:**
1. **Authentication** (Supabase Auth):
   - `register(email, password)` → `supabase.auth.sign_up()`
   - `login(email, password)` → `supabase.auth.sign_in_with_password()`
   - `logout()` → `supabase.auth.sign_out()`
   - `get_profile()` → Fetch from `auth.user()` + optional DB profile table

2. **Folders** (PostgREST via supabase-py):
   - `get_folders()` → `supabase.table("folders").select("*").execute()`
   - `create_folder(name, description)` → `supabase.table("folders").insert({...}).execute()`
   - `get_folder(folder_id)` → `supabase.table("folders").select("*").eq("id", folder_id).execute()`
   - `update_folder(folder_id, name, description)` → `.update({...}).eq("id", folder_id).execute()`
   - `delete_folder(folder_id, delete_images)` → Handle cascade delete logic

3. **Images** (Supabase Storage + PostgREST):
   - `get_images(folder_id, page, per_page)` → Query `images` table with pagination
   - `get_image(image_id)` → Fetch metadata + public URL
   - `upload_image(file, original_filename, source_lang, target_lang, folder_id)`:
     - Generate unique path: `{user_id}/{timestamp}_{filename}`
     - Upload to Supabase Storage bucket
     - Save metadata to `images` table
     - Return public URL
   - `download_image(image_id, save_path)` → Download from Supabase Storage
   - `delete_image(image_id)` → Delete from storage + database
   - `search_images(query)` → Full-text search on filename/language fields

4. **Session & Token Management**:
   - Store `access_token`, `refresh_token`, `user` in instance variables
   - Automatically refresh tokens when expired (Supabase SDK handles this)
   - Persist tokens to local storage (see Phase 3)

#### 2.2 Implementation Notes
- Use `supabase-py` library for type safety and ease of use
- All methods should return `{"success": bool, "data": Any, "error": str}` for consistency
- Handle network errors gracefully (timeout, no connection, etc.)
- Implement retry logic for transient failures (optional but recommended)

---

### Phase 3: Token Persistence

#### 3.1 Create `api/token_storage.py`
Store tokens locally so users don't have to log in every app restart.

```python
# Encrypt and store tokens in:
# Windows: %APPDATA%/SnipShot/tokens.json
# Linux/Mac: ~/.snipshot/tokens.json

def save_tokens(access_token, refresh_token):
    """Save tokens to local encrypted file"""
    
def load_tokens():
    """Load tokens from local file"""
    
def clear_tokens():
    """Delete token file on logout"""
```

**Security Note**: Tokens should be encrypted using a simple cipher (e.g., `cryptography` library) to avoid plaintext storage.

#### 3.2 Update `SupabaseAPIClient`
- On `login()` or `register()`: call `save_tokens()`
- On app startup: call `load_tokens()` and set `access_token`
- On `logout()`: call `clear_tokens()`

---

### Phase 4: Update API Module

#### 4.1 Update `api/__init__.py`
```python
from .supabase_client import SupabaseAPIClient

# Default implementation is now SupabaseAPIClient
_default_client = SupabaseAPIClient()

class _ClientProxy:
    # ... keep existing proxy logic
    
api_client = _ClientProxy(_default_client)
```

**Backward Compatibility**: The proxy pattern ensures all existing code continues to work unchanged.

---

### Phase 5: Update UI Components

#### 5.1 Login/Register Flow
- No changes needed if using the existing `api_client` interface
- Ensure error messages map correctly to Supabase error codes

#### 5.2 Dashboard
- Verify folder/image list UI works with new response format
- Confirm pagination works with PostgREST queries

#### 5.3 Image Upload
- Ensure file is uploaded to correct Supabase Storage path
- Display progress indicator (optional)
- Return public URL and handle storage quota errors

#### 5.4 Local Mode Toggle
The existing "Use Local Mode" button should continue to work:
```python
# On login page
from local_api import LocalAPIClient
api_client.set_impl(LocalAPIClient())
```

---

### Phase 6: Environment Configuration

#### 6.1 Create `.env.example`
```
# Supabase credentials (get from Supabase dashboard)
SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
SUPABASE_ANON_KEY=YOUR_ANON_KEY
SUPABASE_SERVICE_KEY=YOUR_SERVICE_KEY  # Optional

# Translator API (separate from Supabase)
TRANSLATOR_URL=http://localhost:8001

# Local storage directory (for local mode)
LOCAL_STORAGE_DIR=%APPDATA%/SnipShot
```

#### 6.2 Update `.env` (or create new one)
Copy `.env.example` and fill in actual Supabase credentials from your dashboard.

---

### Phase 7: Testing

#### 7.1 Unit Tests (`test.py`)
- Test `SupabaseAPIClient` auth flow (register, login, logout)
- Test folder CRUD operations
- Test image upload/download
- Test token persistence

#### 7.2 Integration Tests
- Run desktop app and verify:
  - Login works
  - Folders load
  - Image upload works
  - Image download works
  - Logout clears tokens

#### 7.3 Performance Tests (`test_performance.py`)
- Measure response times (should be faster without local server hop)
- Test pagination with large image counts

---

### Phase 8: Cleanup & Deprecation

#### 8.1 Database API Server
Once direct Supabase is working:
- Keep `database_api/` for reference (document as deprecated)
- Or remove entirely if not needed for other services

#### 8.2 Update Documentation
- Update `README.md` with new setup instructions
- Remove "run database_api" step
- Add Supabase credentials setup step

#### 8.3 Handle Edge Cases
- What if Supabase is down? → Graceful error messages
- What if user is offline? → Cache data locally or show offline UI
- What if token expires? → Refresh automatically or prompt to re-login

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|-----------|
| Supabase API changes | Low | Medium | Pin SDK version, monitor updates |
| Token expiry bugs | Medium | High | Test token refresh thoroughly |
| Plaintext token storage | High | High | Implement encryption in Phase 3 |
| Offline scenarios | Medium | Medium | Add offline mode or caching |
| CORS issues | Low | Medium | Ensure Supabase dashboard has correct domains |

---

## Rollback Plan

If issues arise:
1. Keep `api/client.py` (HTTP client) as-is
2. Keep `database_api/` running for fallback
3. Use `_ClientProxy` to switch between implementations
4. Add a CLI flag: `python main.py --use-http-api`

---

## Success Criteria

- ✅ Desktop app connects directly to Supabase (no local server needed)
- ✅ All auth, folder, and image operations work
- ✅ Users can log in and are remembered across app restarts (token persistence)
- ✅ Local mode still works as alternative
- ✅ Performance is equal or better than HTTP client approach
- ✅ Error messages are clear and actionable

---

## Timeline Estimate

| Phase | Effort | Notes |
|-------|--------|-------|
| 1. Dependencies | 30 min | Add supabase-py, update config |
| 2. SupabaseAPIClient | 4-6 hours | Main implementation |
| 3. Token Persistence | 1-2 hours | Local storage + encryption |
| 4. API Module Update | 30 min | Swap default client |
| 5. UI Component Updates | 1-2 hours | Integration testing |
| 6. Environment Setup | 30 min | .env.example creation |
| 7. Testing | 2-3 hours | Unit + integration tests |
| 8. Cleanup | 1 hour | Documentation, deprecation notes |
| **Total** | **~10-15 hours** | **~2-3 days with testing** |

---

## Questions & Decisions

1. **Token Storage Encryption**: Use `cryptography.fernet` or simpler approach?
   - Recommend: Fernet (built-in, solid security)

2. **Offline Support**: Should desktop app cache data locally?
   - Recommend: Optional feature for Phase 2 (not MVP)

3. **Service Key Usage**: Should desktop ever use service key?
   - Recommend: No. Keep app-level access via anon key only.

4. **Keep database_api?**: 
   - Recommend: Keep as reference, document as deprecated. May be useful for future backend services.

5. **Local Mode vs Direct**: Should users have a toggle?
   - Recommend: Yes. Existing UI already supports this via `set_impl()`.
