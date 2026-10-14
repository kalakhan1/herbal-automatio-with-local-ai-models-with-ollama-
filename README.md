# 🌿 Herbal Content Automation System

Local Windows application to generate SEO content for herbal products and blogs.

## What It Does

- You paste product names (comma-separated)
- System generates **product pages** + **blog articles** for each product
- Uses **Ollama** (local AI, no paid API)
- Validates SEO + duplicate content
- Exports CSV files for WooCommerce + WordPress
- Everything runs locally on your PC

## Requirements

- **Windows 10/11**
- **Python 3.10+** ([download](https://www.python.org/downloads/))
- **Ollama** ([download](https://ollama.com/download/windows))
- **8 GB RAM** minimum

## STEP 1 — Install Python

1. Download Python 3.10+ from python.org
2. **Important:** During installation, tick "**Add Python to PATH**"
3. Verify in PowerShell:
   ```powershell
   python --version
   ```

## STEP 2 — Install Ollama

1. Download from https://ollama.com/download/windows
2. Install it (it runs in background as Windows service)
3. **Open PowerShell** and pull a small model:
   ```powershell
   ollama pull llama3.2:3b
   ```
   Other options:
   - `llama3.2:1b` — smallest, fastest
   - `llama3.2:3b` — balanced (recommended)
   - `mistral:7b` — better quality, needs more RAM

4. **Verify it works:**
   ```powershell
   ollama list
   ```
   Should show your downloaded model.

5. **Keep Ollama running:** It runs in background. If needed:
   ```powershell
   ollama serve
   ```

## STEP 3 — Setup the Project

Open PowerShell, go to project folder:
```powershell
cd "C:\path\to\herbal_automation"
```

Run setup:
```powershell
.\setup.ps1
```

This will:
- Create Python virtual environment (`.venv`)
- Install dependencies
- Create `.env` from `.env.example`

**If you get "execution policy" error:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## STEP 4 — Configure

Open `.env` file and update:
```
WP_BASE_URL=https://yoursite.com
WP_USERNAME=admin
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
OLLAMA_MODEL=llama3.2:3b
```

**How to create WordPress Application Password:**
1. Login to WordPress admin
2. Users → Profile
3. Scroll to "Application Passwords"
4. Name: `Herbal Automation`
5. Click "Add New Application Password"
6. Copy the password (24 chars) — paste in `.env`

## STEP 5 — Start the App

```powershell
.\start.ps1
```

Open browser: **http://127.0.0.1:5000**

## STEP 6 — Use the App

1. **Products page** — Paste product names, click "Add Products"
2. Click "Generate Batch" — generates 3 products at a time
3. **Dashboard** — track progress
4. **Export page** — download CSVs when done
5. **Settings** — test Ollama, configure WordPress

## First-Time Workflow

```
1. Paste names → Add Products
2. Test Ollama connection (Settings page)
3. Generate Batch (test with 3 products first)
4. Check SEO scores on Dashboard
5. Run Duplicate Check
6. Build Internal Links
7. Export CSVs
8. Import products CSV to WooCommerce
9. Use blogs CSV with WP All Import plugin
```

## Test Mode

By default `TEST_MODE=true` — safe. Only generates 3 products.
Change to `TEST_MODE=false` in `.env` when ready.

## Troubleshooting

**"Ollama not running"**
```powershell
ollama serve
```

**"Model not found"**
```powershell
ollama pull llama3.2:3b
```

**"Import flask could not be resolved"** (VS Code warning only)
- Ignore if app runs. Or select venv interpreter in VS Code.

**App slow?**
- Use smaller model: `ollama pull llama3.2:1b`
- Reduce `BATCH_SIZE` in `.env`

## Folder Structure

```
herbal_automation/
├── main.py                 # App entry
├── config.py               # Configuration
├── database.py             # SQLite
├── services/               # Business logic
├── routes/                 # Flask routes
├── templates/              # HTML
├── static/                 # CSS/JS
├── data/                   # Database (auto)
├── logs/                   # Logs (auto)
├── uploads/                # Images (auto)
└── output/                 # Generated CSVs (auto)
```

## Customizing

Edit `.env`:
- `MIN_WORD_COUNT` — target words per article
- `BATCH_SIZE` — products per batch
- `SIMILARITY_THRESHOLD` — duplicate cutoff (0.82 default)

## Security

- Never commit `.env` (it's in `.gitignore`)
- Rotate WordPress App Password periodically
- App runs locally (not exposed to internet)

## Next Steps

- Phase 2 will add: Image Manager, WordPress upload, ZIP export
- Currently: Products/Blogs generation + SEO + CSV export working

---

**Questions?** Check `logs/app.log` for details.