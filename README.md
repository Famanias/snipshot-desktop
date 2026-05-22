# SnipShot Desktop

A desktop application for capturing, translating, and organizing manga/comic screenshots.

You may visit the earlier versions of this repository at https://github.com/Famanias/snipshot-archived

## Features

- 📸 **Screen Capture** - Snip any region of your screen
- 🌐 **Translation** - Automatically translate manga/comics to English
- ☁️ **Local & Cloud Storage** - Save translations to your account or locally
- 📁 **Folder Organization** - Organize translations like Google Drive

## Requirements

- Python 3.9.11
- PyQt5
- Backend services running (Database API + Translator API)

## Installation

1. Clone the repository:
```bash
cd snipshot-desktop
```

2. Create a virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy environment file:
```bash
copy .env.example .env
```

5. Configure `.env` with your API URLs:
```env
API_BASE_URL=http://localhost:8002/api
TRANSLATOR_URL=http://localhost:8000 (you have to clone the backend repository of this system: https://github.com/Famanias/snipshot-backend)
```

## Running the App

Make sure backend services are running first:

```bash
# Terminal 1: Backend API
cd ../snipshot-backend
python main.py

```

Then run the desktop app:

```bash
python main.py
```

## Usage

1. **Create Account** - Register with email/password
2. **Login** - Sign in to your account
3. **Capture** - Click "New Snip" or use keyboard shortcut
4. **Select Region** - Draw a rectangle around the manga/comic
5. **Translate** - Wait for translation (1-2 minutes)
6. **Save** - Choose a folder and save to your account

## Building Executable

### Using PyInstaller

```bash
pip install pyinstaller

pyinstaller --onefile --windowed --name SnipShot --hidden-import=keyring --hidden-import=keyring.backends --hidden-import=keyring.backends.Windows main.py
```

The executable will be in `dist/SnipShot.exe`

### Using Inno Setup

After creating the PyInstaller executable, use Inno Setup to create an installer:

1. Open Inno Setup Compiler
2. Create new script with wizard
3. Point to `dist/SnipShot.exe`
4. Configure application info
5. Compile to create installer

## Project Structure

```
snipshot-desktop/
├── main.py                 # Application entry point
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables
│
├── api/
│   ├── __init__.py
│   └── client.py           # HTTP client for backend APIs
│
├── ui/
│   ├── __init__.py
│   ├── styles.py           # Qt stylesheets
│   ├── login.py            # Login screen
│   ├── register.py         # Registration screen
│   ├── dashboard.py        # Main dashboard
│   ├── capture.py          # Screen capture overlay
│   └── translation.py      # Translation dialog
│
├── utils/
│   ├── __init__.py
│   └── helpers.py          # Utility functions
│
└── resources/
    └── icon.ico            # Application icon
```

## Tech Stack

- **Frontend**: PyQt5 (Python GUI)
- **Backend**: FastAPI (snipshot-backend)
- **Database**: Supabase PostgreSQL
- **Storage**: Supabase Storage
- **Auth**: Supabase Auth (JWT)
- **Translation**: Meta LLAMA 4 via Groq / OpenRouter API(local VM)

## License

MIT License
