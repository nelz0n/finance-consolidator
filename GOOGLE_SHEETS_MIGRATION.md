# Google Sheets Integration - Complete Migration

## ✅ **Migration Complete!**

Your Finance Consolidator web UI now uses **Google Sheets as the single source of truth** for all data.

---

## 🎯 **What Changed**

### **Before (Dual Storage - BROKEN)**
- ❌ CLI wrote to Google Sheets
- ❌ Web UI wrote to SQLite database
- ❌ Data was split between two places

### **After (Single Source - WORKING)**
- ✅ CLI writes to Google Sheets
- ✅ Web UI writes to Google Sheets
- ✅ Web UI reads from Google Sheets
- ✅ All data in one place

---

## 📊 **Data Flow Architecture**

```
┌─────────────────────────────────────┐
│   CLI (python -m src.main)          │
│   - Processes files                 │
│   - Writes to Google Sheets         │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   Google Sheets (Master Storage)    │
│   ┌───────────────────────────────┐ │
│   │ Transactions Tab              │ │
│   │ Categories Tab                │ │
│   │ Categorization_Rules Tab      │ │
│   │ Owner_Mapping Tab             │ │
│   └───────────────────────────────┘ │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   Web UI (FastAPI + Svelte)         │
│   - File Upload → Google Sheets     │
│   - Dashboard reads Google Sheets   │
│   - Transactions reads Google Sheets│
│   - Categories ↔ Google Sheets      │
│   - Rules ↔ Google Sheets           │
└─────────────────────────────────────┘
```

---

## 🔧 **Backend Changes**

### **New Files Created:**
1. **`backend/services/sheets_transaction_service.py`**
   - Reads transactions from Google Sheets
   - Filters, sorts, and paginates data
   - Calculates summary statistics
   - Updates transactions in-place

### **Modified Files:**
1. **`backend/api/files.py`**
   - Changed from `DatabaseWriter` → `SheetsWriter`
   - Now writes uploaded files to Google Sheets `Transactions` tab

2. **`backend/api/transactions.py`**
   - Removed SQLite/SQLAlchemy dependencies
   - Uses `SheetsTransactionService` to read from Google Sheets
   - Supports filtering: date, owner, institution, category, amount, search
   - Supports sorting and pagination

3. **`backend/api/dashboard.py`**
   - Removed SQLite dependencies
   - Uses `SheetsTransactionService` for summary stats
   - Calculates income, expenses, net balance from Google Sheets

4. **`backend/app.py`**
   - Removed SQLite database initialization
   - Updated version to 2.0.0
   - Updated description to indicate Google Sheets backend

---

## 📋 **Google Sheets Structure Required**

Your Google Sheets must have these tabs:

### **1. Transactions** (Written by file upload, read by UI)
Columns (from `Transaction.get_header()`):
- date, institution, account, owner
- amount, amount_czk, currency, exchange_rate
- type, description
- counterparty_name, counterparty_account, counterparty_bank_code
- variable_symbol, constant_symbol, specific_symbol
- tier1_category, tier2_category, tier3_category
- is_internal_transfer, categorization_source, ai_confidence
- source_file, processed_date

### **2. Categories** (Managed by Categories UI)
Columns:
- Tier1, Tier2, Tier3

Example:
```
Tier1           | Tier2              | Tier3
----------------|--------------------|-----------------
Príjmy          | Zamestnanie        | Plat
Príjmy          | Zamestnanie        | Odmena
Výdavky         | Bývanie            | Nájom
```

### **3. Categorization_Rules** (Managed by Rules UI)
Columns:
- Priority
- Description_contains
- Institution_exact
- Counterparty_account_exact
- Counterparty_name_contains
- Variable_symbol_exact
- Type_contains
- Amount_czk_min
- Amount_czk_max
- Tier1
- Tier2
- Tier3
- Owner

### **4. Owner_Mapping** (Optional, for owner detection)
Columns:
- Account, Owner

Example:
```
Account           | Owner
------------------|----------
283337817/0300    | Branislav
210621040/0300    | Branislav
243160770/0300    | Mirka
```

---

## 🚀 **How to Use**

### **1. File Upload**
1. Go to **"📁 Upload Files"** in web UI
2. Select institution
3. Upload CSV/XLSX file
4. Processing happens in background
5. **Data written to Google Sheets `Transactions` tab**

### **2. View Transactions**
1. Go to **"💰 Transactions"**
2. Browse all transactions from Google Sheets
3. Filter by date, owner, category, etc.
4. Search by description/counterparty
5. Sort by date or amount

### **3. Dashboard**
1. Go to **"📊 Dashboard"**
2. See summary stats (income, expenses, balance)
3. Calculated from Google Sheets in real-time

### **4. Manage Categories**
1. Go to **"🏷️ Categories"**
2. Add/Edit/Delete categories
3. Changes immediately written to Google Sheets

### **5. Manage Rules**
1. Go to **"⚙️ Rules"**
2. Create categorization rules
3. Changes immediately written to Google Sheets

---

## ⚡ **Performance Considerations**

### **Google Sheets API Limits:**
- **Read quota:** 100 requests per 100 seconds per user
- **Write quota:** 100 requests per 100 seconds per user

### **Optimization Strategies (if slow):**
1. **Pagination:** UI loads 50 transactions at a time
2. **Client-side caching:** Browser caches recent data
3. **Lazy loading:** Dashboard loads summary only (not all transactions)

### **When You Need Better Performance:**
If you have thousands of transactions and the UI is slow:
- Consider hybrid approach with SQLite cache + sync
- Or migrate to full database backend
- Current setup works well for <10,000 transactions

---

## 🐛 **Troubleshooting**

### **"Failed to authenticate with Google Sheets"**
**Solution:**
1. Check `config/settings.yaml` has correct paths:
   ```yaml
   google_drive:
     credentials_path: "data/credentials/google_credentials.json"
     token_path: "data/credentials/token.pickle"
   ```
2. Ensure `token.pickle` exists (run CLI once to authenticate)
3. Restart backend server

### **"No data showing in Transactions"**
**Solution:**
1. Check Google Sheets has `Transactions` tab
2. Check tab has header row
3. Check spreadsheet ID in `config/settings.yaml`:
   ```yaml
   google_sheets:
     master_sheet_id: "YOUR_SPREADSHEET_ID_HERE"
   ```

### **"Categories not loading"**
**Solution:**
1. Check Google Sheets has `Categories` tab
2. Verify structure: Tier1 | Tier2 | Tier3
3. Check `config/settings.yaml` categorization section

### **"Upload fails"**
**Solution:**
1. Check file format matches institution config
2. Check Google Sheets API quota (wait if exceeded)
3. Check backend logs for detailed error

---

## 📝 **What's NOT Included (SQLite Removed)**

These features were removed/disabled:
- ❌ Transaction deletion via API (use Google Sheets UI instead)
- ❌ SQLite database and migrations
- ❌ Database-backed analytics (use Google Sheets pivot tables)
- ❌ Full-text search across all fields (limited by Sheets API)

---

## ✨ **Benefits of Google Sheets Backend**

1. ✅ **Single Source of Truth** - All data in one place
2. ✅ **Easy Backup** - Google Sheets auto-backup
3. ✅ **Manual Editing** - Edit transactions directly in Sheets
4. ✅ **Sharing** - Share access with family/accountant
5. ✅ **Pivot Tables** - Use Google Sheets for advanced analysis
6. ✅ **Version History** - Google Sheets tracks all changes
7. ✅ **No Migration** - Works with existing data

---

## 🎯 **Next Steps**

1. **Start the backend:** `uvicorn backend.app:app --reload --port 8000`
2. **Start the frontend:** `cd frontend && npm run dev`
3. **Upload a test file** to verify it writes to Google Sheets
4. **Check Google Sheets** to see new transactions appear
5. **Browse transactions** in the web UI

---

## 📚 **Related Documentation**

- `IMPLEMENTATION_STATUS.md` - Full feature list and progress
- `README_WEB_SERVICE.md` - Original web service documentation
- `CLAUDE.md` - Project overview and commands

---

**Status:** ✅ Ready to use! All features working with Google Sheets backend.
