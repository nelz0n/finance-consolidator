# Setting Up Conditional Dropdowns in Google Sheets

The script has already created:
✅ Helper columns in `Categories` tab (columns I onwards)
✅ 31 named ranges for dropdown options

Now complete the setup manually in Google Sheets:

## Step 1: Set up Tier1 Dropdown (Column I)

1. Open your Google Sheet
2. Go to `Categorization_Rules` tab
3. Select column I (Tier1), starting from row 2
4. Click **Data → Data validation**
5. Set:
   - **Criteria**: List from a range
   - **Range**: `Categories!$E$2:$E$8`
   - **Show dropdown list in cell**: ✓
   - **Reject input**: ✗ (allow invalid data)
6. Click Save

## Step 2: Set up Tier2 Conditional Dropdown (Column J)

1. Select column J (Tier2), starting from row 2
2. Click **Data → Data validation**
3. Set:
   - **Criteria**: List from a range
   - **Range**: `=INDIRECT("Tier2_"&SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(I2," ","_"),"(",""),")",""))`
   - **Show dropdown list in cell**: ✓
   - **Reject input**: ✗
4. Click Save

This formula does:
- Takes the value from Tier1 (column I)
- Removes spaces and parentheses
- Looks up the corresponding named range (e.g., "Tier2_Prijmy")
- Shows only tier2 options for that tier1

## Step 3: Set up Tier3 Conditional Dropdown (Column K)

1. Select column K (Tier3), starting from row 2
2. Click **Data → Data validation**
3. Set:
   - **Criteria**: List from a range
   - **Range**: `=INDIRECT("Tier3_"&SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(J2," ","_"),"(",""),")",""))`
   - **Show dropdown list in cell**: ✓
   - **Reject input**: ✗
4. Click Save

## How It Works

### Example Flow:
1. Select **Tier1**: "Príjmy"
   - Tier2 dropdown will show ONLY: Zamestnanie, Podnikanie, Prenájom, Investície

2. Select **Tier2**: "Zamestnanie"
   - Tier3 dropdown will show ONLY: Mzda, Bonusy

3. Select **Tier2**: "Podnikanie"
   - Tier3 dropdown will show ONLY: Fakturácia(Príjem)

### Named Ranges Created:

**Tier2 ranges** (one per Tier1):
- `Tier2_Investicie_a_Sporenie`
- `Tier2_Nezaradene`
- `Tier2_Podnikanie`
- `Tier2_Prenajom`
- `Tier2_Presuny_Neutralne`
- `Tier2_Prijmy`
- `Tier2_Spotreba_Rodina`

**Tier3 ranges** (one per Tier2):
- `Tier3_Byvanie`
- `Tier3_Deti_Oliver_Alex`
- `Tier3_Doprava_Osobna`
- `Tier3_Energie_a_Sluzby`
- ... (24 total tier3 ranges)

## Troubleshooting

**If dropdowns don't work:**
1. Check that you're using the formula in "List from a range", not "Custom formula"
2. Verify the INDIRECT formula is exactly as written above
3. Make sure you selected the entire column (not just one cell)
4. Try clicking on a cell in Tier1 first, then check if Tier2 updates

**If you see #REF! error:**
- The named range might not exist for that combination
- Check the `Categories` tab to see valid combinations
- Make sure the Tier1/Tier2 value exactly matches (including spaces)

## Alternative: Using Apps Script (Advanced)

If the manual setup doesn't work, you can use Google Apps Script to automate this.
I can provide that script if needed.
