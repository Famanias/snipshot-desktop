# Implementation Plan - Transition to Private Storage Bucket and Signed URLs

This plan details the transition of the image storage bucket in Supabase from **public** to **private**, securing user-uploaded images, and updating the desktop application's backend API integration to use dynamically generated signed URLs.

## User Review Required

> [!IMPORTANT]
> The Supabase images storage bucket must be set to private in the Supabase Dashboard. 
> Path: **Supabase Dashboard** → **Storage** → **images** → **Edit** → uncheck **Public** → **Save**.
> This operation should be performed in sync with deploying this update, as setting the bucket to private will immediately break older clients relying on static public URLs.

## Error Handling

### Signed URL Generation Failures
If the Supabase API client fails to generate a signed URL (due to network timeout, credential mismatch, or storage bucket configuration issues), the client will:
- Log the exception/error to standard output or log stream.
- Set the `public_url` field of the image to `None` or `""`.
- Proceed with returning the list of images or the image record.
- **Goal**: Prevent a storage/network glitch from completely blocking folder listings or image metadata retrieval.

### Missing Files
If a database record exists for an image but the corresponding physical file is missing from the Supabase bucket:
- The `create_signed_url` / `create_signed_urls` API might return an error structure for that specific path.
- The helpers will filter out error items, setting `public_url` to `""` for that image, while allowing other valid images to fetch their signed URLs.
- The UI will gracefully fallback to the default image/icon (rendered as `📷`).

### Expired URLs & Dynamic UI Refresh Caching
Signed URLs are generated with a TTL of 1 hour (`expires_in=3600`).
- **Dashboard Thumbnails**: Since PyQt's `ThumbnailLabel` fetches the image asynchronously and caches/renders the `QPixmap` in memory, already-rendered thumbnails will persist even if the URL expires.
- **Image Preview Caching**: To avoid loading expired URLs while minimizing unnecessary API calls, the UI will cache the signed URL creation timestamp.
  - Image records returned by the API will include a `_signed_at` UNIX timestamp.
  - When clicking to preview an image, the UI will check if the signed URL is older than 50 minutes (3000 seconds) or is missing.
  - If it is fresh, the existing `public_url` is used immediately.
  - If it is stale or missing, the UI fetches a fresh image record, updates the local dictionary in-place (ensuring the updated values are cached/shared), and then opens the preview.
- **Open in Browser / Sharing**: If a user shares a signed URL or opens it in a browser after 1 hour, the link will expire and return an HTTP 403 Forbidden error from Supabase. This is the expected and desired security behavior.

---

## Proposed Changes

### Supabase API Client

We will modify `supabase_client.py` to stop inserting values into the `public_url` column during upload, and implement dynamic signed URL generation for retrieved image data.

#### [MODIFY] [supabase_client.py](file:///c:/Users/neilc/OneDrive/Documents/GitHub/snipshot-desktop/api/supabase_client.py)

- Add low-level utility helpers:
  - `_get_signed_url(self, path: str, expires_in: int = 3600) -> Optional[str]`: Fetches a single signed URL from Supabase storage, returning `None` if it fails.
  - `_get_signed_urls(self, paths: list[str], expires_in: int = 3600) -> dict[str, str]`: Fetches signed URLs in batch using `create_signed_urls`, returning a mapping of `path -> signed_url`.
- Add dictionary mapping helpers:
  - `_sign_single_image_url(self, img: dict, expires_in: int = 3600) -> dict`: Populates the `public_url` field of an image dict and sets `_signed_at = time.time()`.
  - `_sign_image_urls(self, images: list[dict], expires_in: int = 3600) -> list[dict]`: Populates the `public_url` field of a list of image dicts and sets `_signed_at = time.time()`.
- Remove the database insertion of `public_url` in `upload_image` and `upload_image_bytes`.
- Update `get_images`, `get_image`, `get_recent_images`, `upload_image`, `upload_image_bytes`, `move_image_to_folder` (alias `update_image`), and `search_images` to pass retrieved image records through these signing helpers before returning them.

#### Flow for uploads:
```
Upload file to Storage
       ↓
Insert DB record (without public_url field)
       ↓
Receive inserted DB row
       ↓
Generate signed URL and set _signed_at
       ↓
Inject signed URL into return payload (as public_url)
```

---

### UI Components

We will update the preview trigger to check the signed URL age before performing an API call.

#### [MODIFY] [dashboard.py](file:///c:/Users/neilc/OneDrive/Documents/GitHub/snipshot-desktop/ui/dashboard.py)

- Modify `_on_image_clicked(self, image_data: dict)`:
  - Import `time`.
  - Check if `time.time() - image_data.get("_signed_at", 0) > 3000` or `not image_data.get("public_url")`.
  - If stale/missing, call `api_client.get_image(image_data["id"])`. If successful, update `image_data` in-place using `image_data.update(res["data"])`.
  - Open `ImagePreviewDialog` with `image_data`.

---

## Verification Plan

### Automated Tests
- Verify using a test script that `supabase_client.py` successfully signs URLs and returns them inside the `public_url` field for single fetches, lists, searches, and uploads.
- Run the python test suite if available:
  ```powershell
  .venv\Scripts\python test.py
  ```

### Manual Verification
- Launch the PyQt5 application:
  ```powershell
  .venv\Scripts\python main.py
  ```
- Log in and verify that thumbnails load and display correctly on the dashboard.
- Double-click/preview an image to verify it renders in the `ImagePreviewDialog`.
- Verify in console output that clicking an image twice within 50 minutes does not trigger a reload API call, but clicking it after simulating a stale timestamp triggers one reload call and works.
- Use "Open in Browser" from the image preview dialog and verify that it opens a working signed URL (containing `?token=...`).
- Upload a new screenshot and confirm it uploads successfully, renders the thumbnail, and can be viewed.
- Check that local mode continues to function properly by toggling to local mode.
