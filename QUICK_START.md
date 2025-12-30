# 🚀 Quick Start Guide - Finance Consolidator Web UI

## Prerequisites

✅ **Python 3.8+** installed
✅ **Node.js 16+** installed
✅ **Google Sheets** with your transaction data
✅ **Google OAuth credentials** configured (see below)

---

## 📝 Step 1: Google Sheets Setup

### Create/Verify Your Google Sheets Structure

Your spreadsheet needs these tabs:

**1. Transactions** (main data storage)
- Will be populated by file uploads
- Must have header row with transaction fields

**2. Categories** (3-tier category hierarchy)
```
Tier1    | Tier2         | Tier3
---------|---------------|-------------
Príjmy   | Zamestnanie   | Plat
Výdavky  | Bývanie       | Nájom
```

**3. Categorization_Rules** (auto-categorization rules)
```
Priority | Description_contains | ... | Tier1 | Tier2 | Tier3
---------|---------------------|-----|-------|-------|-------
100      | NETFLIX             | ... | Výdavky | Zábava | Netflix
```

**4. Owner_Mapping** (optional)
```
Account         | Owner
----------------|----------
283337817/0300  | Branislav
```

### Get Your Spreadsheet ID

From your Google Sheets URL:
```
https://docs.google.com/spreadsheets/d/1abc123xyz456/edit
                                      ^^^^^^^^^^^^
                                   This is your ID
```

---

## 🔐 Step 2: Google OAuth Setup

### If You Already Have Credentials:

Skip to Step 3 if you have:
- `data/credentials/google_credentials.json`
- `data/credentials/token.pickle`

### If You Need to Set Up:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable these APIs:
   - Google Drive API
   - Google Sheets API
4. Create OAuth 2.0 credentials:
   - Type: Desktop application
   - Download JSON file
5. Save as `data/credentials/google_credentials.json`

6. Run CLI once to authenticate:
```bash
python -m src.main --dry-run
```

This creates `token.pickle` for future use.

---

## ⚙️ Step 3: Configure Settings

Edit `config/settings.yaml`:

```yaml
google_sheets:
  master_sheet_id: "YOUR_SPREADSHEET_ID_HERE"  # ⚠️ CHANGE THIS

google_drive:
  credentials_path: "data/credentials/google_credentials.json"
  token_path: "data/credentials/token.pickle"
  folder_id: "YOUR_DRIVE_FOLDER_ID"  # Optional, for CLI file scanning

categorization:
  rules_source: "google_sheets"  # Use Google Sheets for rules
  google_sheets:
    spreadsheet_id: "YOUR_SPREADSHEET_ID_HERE"  # ⚠️ CHANGE THIS
    rules_tab: "Categorization_Rules"
    categories_tab: "Categories"
    owner_mapping_tab: "Owner_Mapping"
```

---

## 📦 Step 4: Install Dependencies

### Backend:
```bash
# From project root
pip install -r requirements.txt
```

### Frontend:
```bash
cd frontend
npm install
cd ..
```

---

## 🎬 Step 5: Start the Application

### Terminal 1: Backend (API Server)
```bash
uvicorn backend.app:app --reload --port 8000
```

**You should see:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
[OK] All routers imported successfully
[OK] Registered transactions router
[OK] Registered dashboard router
[OK] Registered files router
[OK] Registered categories router
[OK] Registered rules router
```

**Test it:** http://localhost:8000/api/v1/health

Should return:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "backend": "Google Sheets"
}
```

### Terminal 2: Frontend (Web UI)
```bash
cd frontend
npm run dev
```

**You should see:**
```
  VITE v5.0.11  ready in XXX ms

  ➜  Local:   http://localhost:5173/
```

---

## 🌐 Step 6: Access the Web UI

Open your browser: **http://localhost:5173**

You should see the Finance Consolidator interface with sidebar navigation.

---

## ✅ Step 7: Verify Everything Works

### 1. Test Categories
1. Click **"🏷️ Categories"** in sidebar
2. You should see your category tree from Google Sheets
3. Try adding a new category
4. Check Google Sheets - it should appear instantly

### 2. Test Rules
1. Click **"⚙️ Rules"** in sidebar
2. You should see your categorization rules
3. Try creating a new rule
4. Check Google Sheets `Categorization_Rules` tab

### 3. Test File Upload
1. Click **"📁 Upload Files"** in sidebar
2. Select an institution (e.g., ČSOB, Wise)
3. Upload a test CSV/XLSX file
4. Watch the processing status
5. When complete, check Google Sheets `Transactions` tab
6. Your new transactions should appear!

### 4. Test Transactions Browser
1. Click **"💰 Transactions"** in sidebar
2. You should see transactions from Google Sheets
3. Try filtering/sorting

### 5. Test Dashboard
1. Click **"📊 Dashboard"** in sidebar
2. You should see summary cards with totals

---

## 🎯 Common Use Cases

### Upload and Process Bank Statements

1. **Download** CSV/XLSX from your bank
2. Go to **Upload Files** page
3. **Select** your institution
4. **Upload** the file
5. **Wait** for processing (usually <10 seconds)
6. **Check** Google Sheets - transactions appear!
7. **Review** categorization (manual rules + AI)

### Manage Categories

1. Go to **Categories** page
2. **Expand/collapse** tiers by clicking arrows
3. **Add** new category: click "+" button
4. **Delete** category: click trash icon
5. Changes sync to Google Sheets instantly

### Create Categorization Rules

1. Go to **Rules** page
2. Click **"+ Add Rule"**
3. Set **Priority** (higher = checked first)
4. Add **Conditions**:
   - Description contains "NETFLIX"
   - Institution = "ČSOB"
   - Amount range, etc.
5. Select **Category** (Tier1 → Tier2 → Tier3)
6. **Save**
7. Future transactions matching conditions will auto-categorize!

---

## 🐛 Troubleshooting

### Backend Won't Start

**Error:** `ModuleNotFoundError: No module named 'fastapi'`

**Fix:**
```bash
pip install -r requirements.txt
```

### Frontend Won't Start

**Error:** `command not found: npm`

**Fix:** Install Node.js from https://nodejs.org/

### "Failed to authenticate with Google Sheets"

**Fix:**
1. Check `data/credentials/google_credentials.json` exists
2. Run CLI once: `python -m src.main --dry-run`
3. This creates `token.pickle`
4. Restart backend

### No Transactions Showing

**Fix:**
1. Check `config/settings.yaml` has correct `master_sheet_id`
2. Check Google Sheets has `Transactions` tab
3. Check tab has header row
4. Upload a test file to populate data

### Categories Not Loading

**Fix:**
1. Check Google Sheets has `Categories` tab
2. Verify structure: Tier1 | Tier2 | Tier3
3. Check `config/settings.yaml` categorization section

---

## 📚 Next Steps

Once everything is working:

1. **Customize Categories** - Add your own expense/income categories
2. **Create Rules** - Automate categorization for recurring transactions
3. **Upload Historical Data** - Process old bank statements
4. **Review Transactions** - Verify categorization accuracy
5. **Build Dashboard** - Add charts and visualizations (coming soon)

---

## 🆘 Getting Help

- **API Docs:** http://localhost:8000/api/docs
- **Logs:** Check backend terminal for errors
- **Google Sheets:** Verify data appears correctly
- **Configuration:** Review `config/settings.yaml`

---

## 🎉 You're All Set!

Your Finance Consolidator web UI is now running and connected to Google Sheets.

**Key URLs:**
- Web UI: http://localhost:5173
- API: http://localhost:8000
- API Docs: http://localhost:8000/api/docs

Happy tracking! 📊💰
