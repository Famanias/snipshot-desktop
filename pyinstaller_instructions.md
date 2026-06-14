# SnipShot Desktop — Executable & Installer Packaging Guide

This guide describes how to build the Windows standalone directory (`--onedir`) and compile it into a single-file setup installer (`SnipShot_Setup_1.0.0.exe`).

---

## Prerequisites

1. **Inno Setup**: Ensure you have [Inno Setup 6](https://jrsoftware.org/isdl.php) installed on your system.
2. **Path Verification**: Ensure the `ISCC.exe` compiler is in your System PATH, or locate its path (typically `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`).

---

## Step 1: Prepare the Environment

Before building, activate your local virtual environment and install all dependencies:

```powershell
# 1. Open PowerShell in the project directory: d:\repos\snipshot-desktop

# 2. Activate the virtual environment
.\venv\Scripts\activate

# 3. Install the dependencies
pip install -r requirements.txt

# 4. (Optional) Verify PyInstaller is installed
pyinstaller --version
```

---

## Step 2: Build the Executable Directory (`--onedir`)

Run the following command to bundle the Python application into a standalone folder:

```powershell
pyinstaller `
    --name SnipShot `
    --onedir `
    --windowed `
    --icon "resources/icon.ico" `
    --add-data "ui/icons;ui/icons" `
    --add-data "resources;resources" `
    --hidden-import PyQt5.sip `
    --hidden-import keyring.backends.Windows `
    --hidden-import supabase `
    --hidden-import numpy `
    --hidden-import gotrue `
    --hidden-import postgrest `
    --hidden-import storage3 `
    --hidden-import realtime `
    --hidden-import supafunc `
    --hidden-import httpx `
    --hidden-import httpcore `
    --hidden-import h11 `
    --hidden-import anyio `
    --hidden-import sniffio `
    --hidden-import certifi `
    --hidden-import plyer `
    --hidden-import plyer.platforms.win.notification `
    --hidden-import platformdirs `
    --hidden-import cryptography `
    --hidden-import local_api `
    --hidden-import local_api.client `
    --hidden-import local_api.database `
    --hidden-import local_api.storage `
    main.py
```

*Note: The backtick (`` ` ``) is used for line continuation in PowerShell. If using standard Command Prompt (cmd), replace the backticks with carets (`^`).*

### Why these options are chosen:
* `--onedir`: Bundles the application as a single directory in `dist/SnipShot/`. This has faster launch times compared to `--onefile` and is the preferred packaging format.
* `--windowed`: Suppresses the command-prompt console window when launching.
* `--add-data "ui/icons;ui/icons"`: Packages all SVG icons dynamically loaded by the theme system.
* `--add-data "resources;resources"`: Includes the application icon and taskbar branding.
* `--hidden-import ...`: Forces inclusion of dynamic sub-dependencies (like `keyring.backends.Windows`, database/storage engines of `supabase`, and HTTP transports of `httpx`) that static analyzers cannot detect.
* **Auto-excluded database**: `local_api/snipshot.db` is not added to `--add-data`, meaning it is excluded from the build. The application will initialize a fresh database automatically on the client PC's first run.

---

## Step 3: Compile the Installer with Inno Setup

Once PyInstaller finishes successfully, you will find the bundled folder at `dist/SnipShot/`. Now, compile this directory into a setup installer:

```powershell
# Compile the installer using the command-line compiler
ISCC.exe installer.iss
```

*If `ISCC.exe` is not in your path, run it by supplying the absolute path:*
```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer1.iss
```

### What this does:
* Compiles all files inside `dist/SnipShot/*` (recursively preserving subdirectories).
* Creates desktop and start menu shortcuts for `SnipShot.exe`.
* Packages the installer as `SnipShot_Setup_1.0.0.exe` in the `installer/` directory.
