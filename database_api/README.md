# SnipShot Database API - Supabase Edition

User management and image storage service powered by Supabase.

## Overview

This service handles:
- **User Auth** - Registration, login via Supabase Auth
- **Image Storage** - Upload/delete via Supabase Storage
- **Image Metadata** - CRUD via Supabase PostgreSQL

## Architecture

```
Frontend (Desktop/Mobile)
    │
    ├── VM Translator API (Google Cloud)
    │         └── Translates images → Returns translated PNG
    │
    └── Database API (this service)
              ├── Supabase Auth (users)
              ├── Supabase Storage (images)
              └── Supabase PostgreSQL (metadata)
```

## Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/users/register` | ❌ | Create account |
| POST | `/api/users/login` | ❌ | Login → JWT |
| GET | `/api/users/me` | ✅ | Get profile |
| POST | `/api/images` | ✅ | Upload image file |
| POST | `/api/images/from-url` | ✅ | Save image from URL |
| GET | `/api/images` | ✅ | List user's images |
| GET | `/api/images/{id}` | ✅ | Get image details |
| DELETE | `/api/images/{id}` | ✅ | Delete image |

## Supabase Setup

### 1. Create Supabase Project
1. Go to [supabase.com](https://supabase.com) and create a project
2. Note down your project URL and API keys

### 2. Create Storage Bucket
1. Go to Storage in Supabase Dashboard
2. Create a new bucket called `images`
3. Set it to **Public** (for serving images)

### 3. Get Credentials
From Settings > API:
- Project URL → `SUPABASE_URL`
- anon public key → `SUPABASE_ANON_KEY`
- service_role key → `SUPABASE_SERVICE_KEY`
- JWT Secret → `SUPABASE_JWT_SECRET`

From Settings > Database:
- Connection string (URI) → `DATABASE_URL`

## Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your Supabase credentials

# Run
uvicorn main:app --reload --port 8000
```

## Environment Variables

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...
SUPABASE_JWT_SECRET=your-jwt-secret
SUPABASE_STORAGE_BUCKET=images

# Database
DATABASE_URL=postgresql+asyncpg://...
```

## Deploy to Render (or any platform)

1. Push to GitHub
2. Create Web Service on Render
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Add environment variables (from Supabase Dashboard)
4. Deploy!

## Project Structure

```
database_api/
├── main.py              # FastAPI app
├── config.py            # Supabase client
├── schemas.py           # Pydantic models
├── requirements.txt     # Dependencies
├── auth/
│   ├── security.py      # JWT verification
│   └── dependencies.py  # Auth middleware
├── database/
│   ├── connection.py    # PostgreSQL connection
│   └── models.py        # SQLAlchemy Image model
└── routes/
    ├── users.py         # Auth endpoints
    └── images.py        # Image CRUD
```

## API Usage

### Register
```bash
curl -X POST http://localhost:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass123"}'
```

### Login
```bash
curl -X POST http://localhost:8000/api/users/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass123"}'

# Response: {"access_token": "eyJ...", ...}
```

### Upload Image
```bash
curl -X POST http://localhost:8000/api/images \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@image.png" \
  -F "original_filename=my_image.png"
```

### Save Image from URL
```bash
curl -X POST http://localhost:8000/api/images/from-url \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "image_url=https://..." \
  -F "original_filename=translated.png"
```

### List Images
```bash
curl http://localhost:8000/api/images \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Frontend Integration

```javascript
// 1. Register/Login with Supabase (or via this API)
const { access_token } = await fetch('/api/users/login', {
  method: 'POST',
  body: JSON.stringify({ email, password })
}).then(r => r.json());

// 2. Translate image via VM
const translated = await fetch('http://VM_IP:8000/translate', {
  method: 'POST',
  body: formData
}).then(r => r.json());

// 3. Save to user's account
await fetch('/api/images/from-url', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${access_token}` },
  body: new URLSearchParams({
    image_url: translated.image_url,
    original_filename: 'translated.png'
  })
});

// 4. List saved images
const { images } = await fetch('/api/images', {
  headers: { 'Authorization': `Bearer ${access_token}` }
}).then(r => r.json());
```
