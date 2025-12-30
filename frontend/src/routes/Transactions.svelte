<script>
  import { onMount } from 'svelte';
  import { transactionsApi, categoriesApi } from '../lib/api.js';

  // Data
  let transactions = [];
  let loading = true;
  let error = null;
  let pagination = {};
  let categoryTree = [];
  let owners = [];

  // Re-apply rules
  let reapplyingRules = false;
  let reapplySuccess = null;
  let reapplyStats = null;

  // Filters
  let searchQuery = '';
  let searchDebounceTimer = null;
  let fromDate = '';
  let toDate = '';
  let selectedOwner = '';
  let selectedTier1 = '';
  let selectedTier2 = '';
  let selectedTier3 = '';
  let showInternalOnly = 'all'; // 'all', 'internal', 'exclude'
  let minAmount = '';
  let maxAmount = '';
  let selectedInstitution = '';
  let showAdvancedFilters = false;
  let institutions = [];

  // Pagination
  let currentPage = 1;
  let itemsPerPage = 50;

  // Sorting
  let sortBy = 'date';
  let sortOrder = 'desc';

  // Column customization
  let showColumnSelector = false;
  const allColumns = [
    { key: 'date', label: 'Date', default: true, sortable: true },
    { key: 'description', label: 'Description', default: true, sortable: true },
    { key: 'amount', label: 'Amount', default: true, sortable: true },
    { key: 'currency', label: 'Currency', default: false, sortable: false },
    { key: 'category_tier1', label: 'Category (Tier1)', default: true, sortable: true },
    { key: 'category_tier2', label: 'Category (Tier2)', default: false, sortable: true },
    { key: 'category_tier3', label: 'Category (Tier3)', default: false, sortable: true },
    { key: 'owner', label: 'Owner', default: true, sortable: true },
    { key: 'institution', label: 'Institution', default: false, sortable: true },
    { key: 'account', label: 'Account', default: false, sortable: false },
    { key: 'is_internal_transfer', label: 'Internal Transfer', default: false, sortable: false },
    { key: 'counterparty_name', label: 'Counterparty', default: false, sortable: false },
    { key: 'counterparty_account', label: 'Counterparty Account', default: false, sortable: false },
    { key: 'type', label: 'Type', default: false, sortable: false },
    { key: 'variable_symbol', label: 'Variable Symbol', default: false, sortable: false }
  ];

  let visibleColumns = {};

  // Load column preferences from localStorage
  function loadColumnPreferences() {
    const saved = localStorage.getItem('transactionColumns');
    if (saved) {
      try {
        visibleColumns = JSON.parse(saved);
      } catch (e) {
        // If parsing fails, use defaults
        visibleColumns = {};
        allColumns.forEach(col => {
          visibleColumns[col.key] = col.default;
        });
      }
    } else {
      // Use defaults
      allColumns.forEach(col => {
        visibleColumns[col.key] = col.default;
      });
    }
  }

  // Save column preferences to localStorage
  function saveColumnPreferences() {
    localStorage.setItem('transactionColumns', JSON.stringify(visibleColumns));
  }

  function toggleColumn(key) {
    visibleColumns[key] = !visibleColumns[key];
    saveColumnPreferences();
  }

  function resetColumns() {
    allColumns.forEach(col => {
      visibleColumns[col.key] = col.default;
    });
    saveColumnPreferences();
  }

  // Computed
  $: tier2Options = selectedTier1 ? getTier2Options(selectedTier1) : [];
  $: tier3Options = selectedTier1 && selectedTier2 ? getTier3Options(selectedTier1, selectedTier2) : [];
  $: skip = (currentPage - 1) * itemsPerPage;

  async function loadCategoryTree() {
    try {
      const response = await categoriesApi.getTree();
      categoryTree = response.data;
    } catch (err) {
      console.error('Failed to load category tree:', err);
    }
  }

  async function loadAllOwners() {
    try {
      // Load transactions to extract unique owners (use max limit of 200)
      const response = await transactionsApi.getAll({ limit: 200 });
      const ownerSet = new Set();
      const institutionSet = new Set();

      response.data.data.forEach(txn => {
        if (txn.owner && txn.owner !== '-') {
          ownerSet.add(txn.owner);
        }
        if (txn.institution && txn.institution !== '-') {
          institutionSet.add(txn.institution);
        }
      });

      owners = Array.from(ownerSet).sort();
      institutions = Array.from(institutionSet).sort();
    } catch (err) {
      console.error('Failed to load owners:', err);
    }
  }

  async function loadTransactions() {
    try {
      loading = true;
      error = null;

      const params = {
        skip,
        limit: itemsPerPage,
        sort_by: sortBy,
        sort_order: sortOrder
      };

      // Add filters if set
      if (searchQuery.trim()) params.search = searchQuery.trim();
      if (fromDate) params.from_date = fromDate;
      if (toDate) params.to_date = toDate;
      if (selectedOwner) params.owner = selectedOwner;
      if (selectedInstitution) params.institution = selectedInstitution;
      if (selectedTier1) params.category_tier1 = selectedTier1;
      if (selectedTier2) params.category_tier2 = selectedTier2;
      if (selectedTier3) params.category_tier3 = selectedTier3;
      if (showInternalOnly === 'internal') params.is_internal_transfer = true;
      if (showInternalOnly === 'exclude') params.is_internal_transfer = false;
      if (minAmount) params.min_amount = parseFloat(minAmount);
      if (maxAmount) params.max_amount = parseFloat(maxAmount);

      const response = await transactionsApi.getAll(params);
      transactions = response.data.data;
      pagination = response.data.pagination;
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  function getTier2Options(tier1) {
    const tier1Cat = categoryTree.find(c => c.tier1 === tier1);
    return tier1Cat ? tier1Cat.tier2_categories || [] : [];
  }

  function getTier3Options(tier1, tier2) {
    const tier1Cat = categoryTree.find(c => c.tier1 === tier1);
    if (!tier1Cat) return [];
    const tier2Cat = tier1Cat.tier2_categories.find(c => c.tier2 === tier2);
    return tier2Cat ? tier2Cat.tier3 || [] : [];
  }

  function handleSearchInput(e) {
    searchQuery = e.target.value;
    // Debounce search
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
      currentPage = 1; // Reset to first page
      loadTransactions();
    }, 300);
  }

  function handleSort(column) {
    if (sortBy === column) {
      // Toggle order
      sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
    } else {
      sortBy = column;
      sortOrder = 'desc';
    }
    currentPage = 1;
    loadTransactions();
  }

  function handleFilterChange() {
    currentPage = 1; // Reset to first page when filters change
    loadTransactions();
  }

  function clearFilters() {
    searchQuery = '';
    fromDate = '';
    toDate = '';
    selectedOwner = '';
    selectedInstitution = '';
    selectedTier1 = '';
    selectedTier2 = '';
    selectedTier3 = '';
    showInternalOnly = 'all';
    minAmount = '';
    maxAmount = '';
    currentPage = 1;
    loadTransactions();
  }

  function nextPage() {
    if (currentPage < pagination.total_pages) {
      currentPage++;
      loadTransactions();
    }
  }

  function prevPage() {
    if (currentPage > 1) {
      currentPage--;
      loadTransactions();
    }
  }

  function goToPage(page) {
    currentPage = Math.max(1, Math.min(page, pagination.total_pages));
    loadTransactions();
  }

  function changePageSize(newSize) {
    itemsPerPage = newSize;
    currentPage = 1;
    loadTransactions();
  }

  onMount(async () => {
    loadColumnPreferences();
    await loadCategoryTree();
    await loadAllOwners();
    await loadTransactions();
  });

  function formatDate(dateStr) {
    return new Date(dateStr).toLocaleDateString();
  }

  function formatAmount(amount, currency) {
    return `${parseFloat(amount).toFixed(2)} ${currency}`;
  }

  function getSortIcon(column) {
    if (sortBy !== column) return '⇅';
    return sortOrder === 'asc' ? '↑' : '↓';
  }

  function getCellValue(txn, columnKey) {
    const value = txn[columnKey];

    // Format based on column type
    switch (columnKey) {
      case 'date':
        return formatDate(value);
      case 'amount':
        return formatAmount(value, txn.currency);
      case 'is_internal_transfer':
        return value === 'TRUE' ? 'Yes' : 'No';
      case 'category_tier1':
      case 'category_tier2':
      case 'category_tier3':
        return value || 'Uncategorized';
      default:
        return value || '-';
    }
  }

  function getCellClass(txn, columnKey) {
    if (columnKey === 'amount') {
      if (parseFloat(txn.amount) < 0) return 'negative';
      if (parseFloat(txn.amount) > 0) return 'positive';
    }
    return '';
  }

  function exportToCSV() {
    // Get visible columns
    const visibleCols = allColumns.filter(col => visibleColumns[col.key]);

    // Create CSV header
    const header = visibleCols.map(col => col.label).join(',');

    // Create CSV rows
    const rows = transactions.map(txn => {
      return visibleCols.map(col => {
        const value = getCellValue(txn, col.key);
        // Escape commas and quotes
        const escaped = String(value).replace(/"/g, '""');
        return `"${escaped}"`;
      }).join(',');
    });

    // Combine header and rows
    const csv = [header, ...rows].join('\n');

    // Add UTF-8 BOM for proper character encoding (especially for Slovak characters)
    const BOM = '\uFEFF';
    const csvWithBOM = BOM + csv;

    // Create download link
    const blob = new Blob([csvWithBOM], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `transactions_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  function exportToExcel() {
    // Create a proper Excel file using HTML table format that Excel can read as .xlsx
    const visibleCols = allColumns.filter(col => visibleColumns[col.key]);

    // Build HTML table
    let html = '<html xmlns:x="urn:schemas-microsoft-com:office:excel">';
    html += '<head>';
    html += '<meta charset="UTF-8">';
    html += '<xml><x:ExcelWorkbook><x:ExcelWorksheets><x:ExcelWorksheet>';
    html += '<x:Name>Transactions</x:Name>';
    html += '<x:WorksheetOptions><x:DisplayGridlines/></x:WorksheetOptions>';
    html += '</x:ExcelWorksheet></x:ExcelWorksheets></x:ExcelWorkbook></xml>';
    html += '</head><body>';
    html += '<table>';

    // Header row
    html += '<thead><tr>';
    visibleCols.forEach(col => {
      html += `<th>${col.label}</th>`;
    });
    html += '</tr></thead>';

    // Data rows
    html += '<tbody>';
    transactions.forEach(txn => {
      html += '<tr>';
      visibleCols.forEach(col => {
        const value = getCellValue(txn, col.key);
        // Escape HTML special characters
        const escaped = String(value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        html += `<td>${escaped}</td>`;
      });
      html += '</tr>';
    });
    html += '</tbody></table></body></html>';

    // Add UTF-8 BOM for proper character encoding
    const BOM = '\uFEFF';
    const htmlWithBOM = BOM + html;

    // Create download link
    const blob = new Blob([htmlWithBOM], { type: 'application/vnd.ms-excel;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `transactions_${new Date().toISOString().split('T')[0]}.xls`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  async function reapplyRules() {
    // Confirmation dialog
    const totalTransactions = pagination.total_items || 0;
    const message = `Re-apply manual categorization rules to ${totalTransactions} filtered transaction(s)?

Logic:
• Manual rule matches → Update categories
• No manual rule + was AI-categorized → Keep AI categories
• Otherwise → Leave unchanged

AI categorization will NOT be called.`;

    if (!confirm(message)) {
      return;
    }

    reapplyingRules = true;
    reapplySuccess = null;
    reapplyStats = null;
    error = null;

    try {
      // Build filter params
      const params = {
        from_date: fromDate || null,
        to_date: toDate || null,
        owner: selectedOwner || null,
        institution: selectedInstitution || null,
        category_tier1: selectedTier1 || null,
        category_tier2: selectedTier2 || null,
        category_tier3: selectedTier3 || null,
        is_internal_transfer: showInternalOnly === 'all' ? null : showInternalOnly === 'internal',
        min_amount: minAmount ? parseFloat(minAmount) : null,
        max_amount: maxAmount ? parseFloat(maxAmount) : null,
        search: searchQuery || null
      };

      // Call API
      const response = await transactionsApi.reapplyRules(params);

      reapplySuccess = response.data.message;
      reapplyStats = response.data.stats;

      // Reload transactions to show updated categories
      await loadTransactions();

      // Clear success message after 10 seconds
      setTimeout(() => {
        reapplySuccess = null;
        reapplyStats = null;
      }, 10000);
    } catch (err) {
      error = `Failed to re-apply rules: ${err.response?.data?.detail || err.message}`;
      setTimeout(() => { error = null; }, 5000);
    } finally {
      reapplyingRules = false;
    }
  }
</script>

<div class="transactions">
  <div class="header">
    <h1>Transactions</h1>
    <div class="header-actions">
      <button class="btn btn-reapply" on:click={reapplyRules} disabled={reapplyingRules || loading || transactions.length === 0}>
        {reapplyingRules ? '🔄 Re-applying...' : '🔁 Re-apply Rules'}
      </button>
      <button class="btn btn-export" on:click={exportToCSV} disabled={transactions.length === 0}>
        📥 Export CSV
      </button>
      <button class="btn btn-export" on:click={exportToExcel} disabled={transactions.length === 0}>
        📊 Export Excel
      </button>
      <button class="btn btn-columns" on:click={() => showColumnSelector = !showColumnSelector}>
        ⚙️ Columns
      </button>
      <button class="btn btn-refresh" on:click={loadTransactions} disabled={loading}>
        {loading ? '🔄 Refreshing...' : '🔄 Refresh'}
      </button>
    </div>
  </div>

  <!-- Column Selector Dropdown -->
  {#if showColumnSelector}
    <div class="column-selector">
      <div class="column-selector-header">
        <h3>Show/Hide Columns</h3>
        <button class="btn-reset" on:click={resetColumns}>Reset to Default</button>
      </div>
      <div class="column-list">
        {#each allColumns as column}
          <label class="column-item">
            <input
              type="checkbox"
              bind:checked={visibleColumns[column.key]}
              on:change={() => saveColumnPreferences()}
            />
            <span>{column.label}</span>
          </label>
        {/each}
      </div>
    </div>
  {/if}

  <!-- Search Bar -->
  <div class="search-bar">
    <input
      type="text"
      placeholder="🔍 Search descriptions, counterparties..."
      bind:value={searchQuery}
      on:input={handleSearchInput}
      class="search-input"
    />
    {#if searchQuery}
      <button class="btn-clear" on:click={() => { searchQuery = ''; handleFilterChange(); }}>
        ✕
      </button>
    {/if}
  </div>

  <!-- Quick Filters -->
  <div class="filters">
    <div class="filter-row">
      <div class="filter-group">
        <label>From Date:</label>
        <input
          type="date"
          bind:value={fromDate}
          on:change={handleFilterChange}
          class="filter-input"
        />
      </div>

      <div class="filter-group">
        <label>To Date:</label>
        <input
          type="date"
          bind:value={toDate}
          on:change={handleFilterChange}
          class="filter-input"
        />
      </div>

      <div class="filter-group">
        <label>Owner:</label>
        <select bind:value={selectedOwner} on:change={handleFilterChange} class="filter-select">
          <option value="">All Owners</option>
          {#each owners as owner}
            <option value={owner}>{owner}</option>
          {/each}
        </select>
      </div>

      <div class="filter-group">
        <label>Category (Tier1):</label>
        <select bind:value={selectedTier1} on:change={handleFilterChange} class="filter-select">
          <option value="">All Categories</option>
          {#each categoryTree as cat}
            <option value={cat.tier1}>{cat.tier1}</option>
          {/each}
        </select>
      </div>

      {#if selectedTier1 && tier2Options.length > 0}
        <div class="filter-group">
          <label>Tier2:</label>
          <select bind:value={selectedTier2} on:change={handleFilterChange} class="filter-select">
            <option value="">All</option>
            {#each tier2Options as cat}
              <option value={cat.tier2}>{cat.tier2}</option>
            {/each}
          </select>
        </div>
      {/if}

      {#if selectedTier2 && tier3Options.length > 0}
        <div class="filter-group">
          <label>Tier3:</label>
          <select bind:value={selectedTier3} on:change={handleFilterChange} class="filter-select">
            <option value="">All</option>
            {#each tier3Options as tier3}
              <option value={tier3}>{tier3}</option>
            {/each}
          </select>
        </div>
      {/if}

      <div class="filter-group">
        <label>Transfer Type:</label>
        <select bind:value={showInternalOnly} on:change={handleFilterChange} class="filter-select">
          <option value="all">All</option>
          <option value="internal">Internal Only</option>
          <option value="exclude">Exclude Internal</option>
        </select>
      </div>

      <button class="btn btn-clear-filters" on:click={clearFilters}>
        Clear Filters
      </button>

      <button class="btn btn-advanced" on:click={() => showAdvancedFilters = !showAdvancedFilters}>
        {showAdvancedFilters ? '▲ Hide Advanced' : '▼ Show Advanced'}
      </button>
    </div>

    <!-- Advanced Filters -->
    {#if showAdvancedFilters}
      <div class="advanced-filters">
        <h4>Advanced Filters</h4>
        <div class="filter-row">
          <div class="filter-group">
            <label>Min Amount:</label>
            <input
              type="number"
              step="0.01"
              bind:value={minAmount}
              on:input={handleFilterChange}
              class="filter-input"
              placeholder="e.g., 100"
            />
          </div>

          <div class="filter-group">
            <label>Max Amount:</label>
            <input
              type="number"
              step="0.01"
              bind:value={maxAmount}
              on:input={handleFilterChange}
              class="filter-input"
              placeholder="e.g., 5000"
            />
          </div>

          <div class="filter-group">
            <label>Institution:</label>
            <select bind:value={selectedInstitution} on:change={handleFilterChange} class="filter-select">
              <option value="">All Institutions</option>
              {#each institutions as institution}
                <option value={institution}>{institution}</option>
              {/each}
            </select>
          </div>
        </div>
      </div>
    {/if}
  </div>

  <!-- Success message for re-apply rules -->
  {#if reapplySuccess && reapplyStats}
    <div class="success-banner">
      <div class="success-message">
        <strong>✅ {reapplySuccess}</strong>
        <div class="success-stats">
          <span class="stat">✏️ Updated by rules: {reapplyStats.updated_by_rule}</span>
          <span class="stat">🤖 Preserved AI: {reapplyStats.preserved_ai}</span>
          <span class="stat">➖ Unchanged: {reapplyStats.unchanged}</span>
        </div>
      </div>
      <button class="btn-close" on:click={() => { reapplySuccess = null; reapplyStats = null; }}>✕</button>
    </div>
  {/if}

  {#if loading}
    <p>Loading transactions...</p>
  {:else if error}
    <p class="error">Error: {error}</p>
  {:else}
    {#if transactions.length === 0}
      <div class="no-results">
        <p>No transactions found matching your filters.</p>
        <button class="btn" on:click={clearFilters}>Clear Filters</button>
      </div>
    {:else}
      <div class="table-container">
        <table>
          <thead>
            <tr>
              {#each allColumns as column}
                {#if visibleColumns[column.key]}
                  <th
                    class:sortable={column.sortable}
                    on:click={() => column.sortable && handleSort(column.key)}
                  >
                    {column.label}
                    {#if column.sortable}
                      {getSortIcon(column.key)}
                    {/if}
                  </th>
                {/if}
              {/each}
            </tr>
          </thead>
          <tbody>
            {#each transactions as txn}
              <tr>
                {#each allColumns as column}
                  {#if visibleColumns[column.key]}
                    <td class={getCellClass(txn, column.key)}>
                      {getCellValue(txn, column.key)}
                    </td>
                  {/if}
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}

    <!-- Pagination Controls -->
    {#if pagination}
      <div class="pagination-container">
        <div class="pagination-info">
          Showing {transactions.length} of {pagination.total_items} transactions
        </div>

        <div class="pagination-controls">
          <button
            class="btn btn-page"
            on:click={prevPage}
            disabled={currentPage === 1}
          >
            ← Previous
          </button>

          <div class="page-selector">
            <span>Page</span>
            <input
              type="number"
              min="1"
              max={pagination.total_pages}
              bind:value={currentPage}
              on:change={() => goToPage(currentPage)}
              class="page-input"
            />
            <span>of {pagination.total_pages}</span>
          </div>

          <button
            class="btn btn-page"
            on:click={nextPage}
            disabled={currentPage === pagination.total_pages}
          >
            Next →
          </button>

          <select
            bind:value={itemsPerPage}
            on:change={() => changePageSize(itemsPerPage)}
            class="items-per-page"
          >
            <option value={25}>25 per page</option>
            <option value={50}>50 per page</option>
            <option value={100}>100 per page</option>
            <option value={200}>200 per page</option>
          </select>
        </div>
      </div>
    {/if}
  {/if}
</div>

<style>
  .transactions {
    max-width: 1600px;
    padding: 20px;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }

  .header-actions {
    display: flex;
    gap: 10px;
  }

  h1 {
    margin: 0;
    font-size: 2rem;
    color: #2c3e50;
  }

  /* Column Selector */
  .column-selector {
    background: white;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  }

  .column-selector-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
    padding-bottom: 15px;
    border-bottom: 1px solid #eee;
  }

  .column-selector-header h3 {
    margin: 0;
    font-size: 1.1rem;
    color: #2c3e50;
  }

  .btn-reset {
    background: #6c757d;
    color: white;
    border: none;
    padding: 6px 12px;
    border-radius: 4px;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .btn-reset:hover {
    background: #5a6268;
  }

  .column-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
  }

  .column-item {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    padding: 6px;
    border-radius: 4px;
    transition: background-color 0.2s;
  }

  .column-item:hover {
    background: #f8f9fa;
  }

  .column-item input[type="checkbox"] {
    cursor: pointer;
  }

  .column-item span {
    font-size: 0.9rem;
    color: #495057;
  }

  /* Search Bar */
  .search-bar {
    position: relative;
    margin-bottom: 20px;
  }

  .search-input {
    width: 100%;
    padding: 12px 40px 12px 16px;
    font-size: 1rem;
    border: 2px solid #ddd;
    border-radius: 8px;
    transition: border-color 0.2s;
  }

  .search-input:focus {
    outline: none;
    border-color: #007bff;
  }

  .btn-clear {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    background: #e0e0e0;
    border: none;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    cursor: pointer;
    font-size: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .btn-clear:hover {
    background: #ccc;
  }

  /* Filters */
  .filters {
    background: #f8f9fa;
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  }

  .filter-row {
    display: flex;
    gap: 15px;
    flex-wrap: wrap;
    align-items: flex-end;
  }

  .filter-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .filter-group label {
    font-size: 0.85rem;
    font-weight: 600;
    color: #495057;
  }

  .filter-input,
  .filter-select {
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.9rem;
    min-width: 150px;
  }

  .filter-input:focus,
  .filter-select:focus {
    outline: none;
    border-color: #007bff;
  }

  /* Advanced Filters */
  .advanced-filters {
    background: white;
    border: 2px dashed #dee2e6;
    border-radius: 8px;
    padding: 20px;
    margin-top: 15px;
  }

  .advanced-filters h4 {
    margin: 0 0 15px 0;
    font-size: 1rem;
    color: #495057;
    font-weight: 600;
  }

  .btn-advanced {
    background: #6c757d;
    color: white;
    padding: 8px 16px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
    transition: background-color 0.2s;
  }

  .btn-advanced:hover {
    background: #5a6268;
  }

  /* Buttons */
  .btn {
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
    font-weight: 500;
    transition: all 0.2s;
  }

  .btn-refresh {
    background-color: #007bff;
    color: white;
  }

  .btn-refresh:hover:not(:disabled) {
    background-color: #0056b3;
  }

  .btn-refresh:disabled {
    background-color: #6c757d;
    cursor: not-allowed;
  }

  .btn-export {
    background-color: #28a745;
    color: white;
  }

  .btn-export:hover:not(:disabled) {
    background-color: #218838;
  }

  .btn-export:disabled {
    background-color: #ccc;
    cursor: not-allowed;
    color: #666;
  }

  .btn-columns {
    background-color: #6c757d;
    color: white;
  }

  .btn-columns:hover {
    background-color: #5a6268;
  }

  .btn-reapply {
    background-color: #17a2b8;
    color: white;
    font-weight: 600;
  }

  .btn-reapply:hover:not(:disabled) {
    background-color: #138496;
  }

  .btn-reapply:disabled {
    background-color: #ccc;
    cursor: not-allowed;
    color: #666;
  }

  .btn-clear-filters {
    background-color: #6c757d;
    color: white;
    margin-top: auto;
  }

  .btn-clear-filters:hover {
    background-color: #5a6268;
  }

  .btn-page {
    background-color: #007bff;
    color: white;
    padding: 8px 16px;
  }

  .btn-page:hover:not(:disabled) {
    background-color: #0056b3;
  }

  .btn-page:disabled {
    background-color: #ccc;
    cursor: not-allowed;
    color: #666;
  }

  /* Table */
  .table-container {
    overflow-x: auto;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th, td {
    padding: 14px 16px;
    text-align: left;
    border-bottom: 1px solid #e9ecef;
  }

  th {
    background: #f8f9fa;
    font-weight: 600;
    color: #495057;
    position: sticky;
    top: 0;
    z-index: 10;
  }

  th.sortable {
    cursor: pointer;
    user-select: none;
    transition: background-color 0.2s;
  }

  th.sortable:hover {
    background: #e9ecef;
  }

  tr:hover {
    background: #f8f9fa;
  }

  .negative {
    color: #e74c3c;
    font-weight: 600;
  }

  .positive {
    color: #27ae60;
    font-weight: 600;
  }

  /* Pagination */
  .pagination-container {
    margin-top: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 15px;
  }

  .pagination-info {
    color: #666;
    font-size: 0.95rem;
  }

  .pagination-controls {
    display: flex;
    gap: 10px;
    align-items: center;
  }

  .page-selector {
    display: flex;
    gap: 8px;
    align-items: center;
    font-size: 0.95rem;
  }

  .page-input {
    width: 60px;
    padding: 6px 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
    text-align: center;
    font-size: 0.9rem;
  }

  .page-input:focus {
    outline: none;
    border-color: #007bff;
  }

  .items-per-page {
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.9rem;
    cursor: pointer;
  }

  .items-per-page:focus {
    outline: none;
    border-color: #007bff;
  }

  .error {
    color: #e74c3c;
    padding: 20px;
    background: #fee;
    border-radius: 8px;
    border: 1px solid #fcc;
  }

  /* Success Banner */
  .success-banner {
    background: #d4edda;
    border: 1px solid #c3e6cb;
    border-radius: 6px;
    padding: 16px 20px;
    margin: 20px 0;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  }

  .success-message {
    flex: 1;
  }

  .success-message strong {
    color: #155724;
    font-size: 1.1rem;
    display: block;
    margin-bottom: 10px;
  }

  .success-stats {
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
  }

  .success-stats .stat {
    background: white;
    padding: 6px 12px;
    border-radius: 4px;
    font-size: 0.9rem;
    color: #155724;
    border: 1px solid #c3e6cb;
  }

  .btn-close {
    background: transparent;
    border: none;
    font-size: 1.5rem;
    color: #155724;
    cursor: pointer;
    padding: 0;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: background-color 0.2s;
  }

  .btn-close:hover {
    background: rgba(0, 0, 0, 0.1);
  }

  .no-results {
    text-align: center;
    padding: 60px 20px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  }

  .no-results p {
    font-size: 1.1rem;
    color: #666;
    margin-bottom: 20px;
  }

  /* Responsive */
  @media (max-width: 768px) {
    .filter-row {
      flex-direction: column;
      align-items: stretch;
    }

    .filter-input,
    .filter-select {
      min-width: auto;
      width: 100%;
    }

    .pagination-container {
      flex-direction: column;
      align-items: stretch;
    }

    .pagination-controls {
      flex-direction: column;
    }
  }
</style>
