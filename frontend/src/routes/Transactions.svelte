<script>
  import { onMount } from 'svelte';
  import { transactionsApi, categoriesApi, accountsApi, api } from '../lib/api.js';

  // Data
  let transactions = [];
  let loading = true;
  let error = null;
  let pagination = {};
  let categoryTree = [];
  let owners = [];
  let accounts = {}; // Map of account_number -> description
  let accountNumbers = []; // List of unique account numbers

  // Mass selection and batch operations
  let selectedTransactions = [];
  let selectMode = false;

  // Re-apply rules
  let reapplyingRules = false;
  let reapplySuccess = null;
  let reapplyStats = null;

  // Edit/Delete modal
  let showEditModal = false;
  let editingTransaction = null;
  let editForm = {
    description: '',
    amount: '',
    currency: '',
    category_tier1: '',
    category_tier2: '',
    category_tier3: '',
    counterparty_name: '',
    counterparty_account: '',
    counterparty_bank: '',
    variable_symbol: '',
    constant_symbol: '',
    specific_symbol: '',
    transaction_type: '',
    note: '',
    owner: ''
  };

  // Inline category editing
  let inlineEditingCell = null;  // { txnId, field }
  let inlineTempValue = { tier1: '', tier2: '', tier3: '' };

  // Bulk category editing
  let showBulkEditModal = false;
  let bulkEditForm = {
    category_tier1: '',
    category_tier2: '',
    category_tier3: ''
  };

  // Rule creation from transaction
  let showRuleModal = false;

  // Track mousedown on modal backdrops to prevent closing when selecting text
  let editModalBackdropMouseDown = false;
  let bulkEditModalBackdropMouseDown = false;
  let ruleModalBackdropMouseDown = false;

  let ruleFormPrefill = {
    priority: 50,
    description_contains: '',
    institution_exact: '',
    counterparty_account_exact: '',
    counterparty_name_contains: '',
    variable_symbol_exact: '',
    type_contains: '',
    amount_czk_min: null,
    amount_czk_max: null,
    category_tier1: '',
    category_tier2: '',
    category_tier3: ''
  };
  let ruleMatchingCount = null;
  let tier2Options = [];
  let tier3Options = [];
  let testingRule = false;
  let savingRule = false;

  // Filters
  let searchQuery = '';
  let searchDebounceTimer = null;
  let fromDate = '';
  let toDate = '';
  let selectedInstitution = '';
  let selectedTier1 = '';
  let selectedTier2 = '';
  let selectedTier3 = '';
  let showInternalOnly = 'all'; // 'all', 'internal', 'exclude'
  let minAmount = '';
  let maxAmount = '';
  let selectedType = '';
  let selectedAccount = '';
  let showAdvancedFilters = false;
  let institutions = [];
  let transactionTypes = [];

  // Pagination
  let currentPage = 1;
  let itemsPerPage = 50;

  // Sorting
  let sortBy = 'date';
  let sortOrder = 'desc';

  // Column customization
  let showColumnSelector = false;
  const allColumns = [
    { key: 'actions', label: 'Actions', default: true, sortable: false },
    { key: 'date', label: 'Date', default: true, sortable: true },
    { key: 'description', label: 'Description', default: true, sortable: true },
    { key: 'amount', label: 'Amount (Original)', default: true, sortable: true },
    { key: 'currency', label: 'Currency', default: true, sortable: false },
    { key: 'amount_czk', label: 'Amount (CZK)', default: false, sortable: true },
    { key: 'category_tier1', label: 'Category (Tier1)', default: true, sortable: true },
    { key: 'category_tier2', label: 'Category (Tier2)', default: false, sortable: true },
    { key: 'category_tier3', label: 'Category (Tier3)', default: false, sortable: true },
    { key: 'categorization_source', label: 'Category Source', default: false, sortable: true },
    { key: 'ai_confidence', label: 'AI Confidence', default: false, sortable: true },
    { key: 'institution', label: 'Institution', default: false, sortable: false },
    { key: 'account', label: 'Account', default: false, sortable: false },
    { key: 'account_description', label: 'Account Description', default: false, sortable: false },
    { key: 'is_internal_transfer', label: 'Internal Transfer', default: false, sortable: false },
    { key: 'counterparty_name', label: 'Counterparty', default: false, sortable: false },
    { key: 'counterparty_account', label: 'Counterparty Account', default: false, sortable: false },
    { key: 'type', label: 'Type', default: false, sortable: false },
    { key: 'variable_symbol', label: 'Variable Symbol', default: false, sortable: false }
  ];

  let visibleColumns = {};
  let columnOrder = [];  // Array of column keys in display order
  let draggedIndex = null;

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

  function selectAllColumns() {
    allColumns.forEach(col => {
      visibleColumns[col.key] = true;
    });
    saveColumnPreferences();
  }

  function deselectAllColumns() {
    allColumns.forEach(col => {
      visibleColumns[col.key] = false;
    });
    saveColumnPreferences();
  }

  // Column order management
  function initializeColumnOrder() {
    const savedOrder = localStorage.getItem('transactionColumnOrder');
    if (savedOrder) {
      try {
        columnOrder = JSON.parse(savedOrder);
        // Validate against allColumns
        const validKeys = new Set(allColumns.map(c => c.key));
        columnOrder = columnOrder.filter(k => validKeys.has(k));

        // Add any new columns not in saved order
        allColumns.forEach(col => {
          if (!columnOrder.includes(col.key)) {
            columnOrder.push(col.key);
          }
        });
      } catch (e) {
        columnOrder = allColumns.map(c => c.key);
      }
    } else {
      columnOrder = allColumns.map(c => c.key);
    }
  }

  function saveColumnOrder() {
    localStorage.setItem('transactionColumnOrder', JSON.stringify(columnOrder));
  }

  function handleDragStart(e, index) {
    draggedIndex = index;
    e.dataTransfer.effectAllowed = 'move';
  }

  function handleDrop(e, dropIndex) {
    e.preventDefault();

    if (draggedIndex === null || draggedIndex === dropIndex) {
      return;
    }

    const newOrder = [...columnOrder];
    const [draggedItem] = newOrder.splice(draggedIndex, 1);
    newOrder.splice(dropIndex, 0, draggedItem);

    columnOrder = newOrder;
    saveColumnOrder();
    draggedIndex = null;
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

  async function loadAccounts() {
    try {
      const response = await accountsApi.getAll();
      accounts = response.data.accounts || {};
    } catch (err) {
      console.error('Failed to load accounts:', err);
      accounts = {};
    }
  }

  async function loadAllOwners() {
    try {
      // Load transactions to extract unique owners, institutions, accounts, types (use max limit of 200)
      const response = await transactionsApi.getAll({ limit: 200 });
      const ownerSet = new Set();
      const institutionSet = new Set();
      const accountSet = new Set();
      const typeSet = new Set();

      response.data.data.forEach(txn => {
        if (txn.owner && txn.owner !== '-') {
          ownerSet.add(txn.owner);
        }
        if (txn.institution && txn.institution !== '-') {
          institutionSet.add(txn.institution);
        }
        if (txn.account_number && txn.account_number !== '-') {
          accountSet.add(txn.account_number);
        }
        if (txn.transaction_type && txn.transaction_type !== '-') {
          typeSet.add(txn.transaction_type);
        }
      });

      owners = Array.from(ownerSet).sort();
      institutions = Array.from(institutionSet).sort();
      accountNumbers = Array.from(accountSet).sort();
      transactionTypes = Array.from(typeSet).sort();
    } catch (err) {
      console.error('Failed to load metadata:', err);
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
      if (selectedInstitution) params.institution = selectedInstitution;
      if (selectedTier1) params.category_tier1 = selectedTier1;
      if (selectedTier2) params.category_tier2 = selectedTier2;
      if (selectedTier3) params.category_tier3 = selectedTier3;
      if (showInternalOnly === 'internal') params.is_internal_transfer = true;
      if (showInternalOnly === 'exclude') params.is_internal_transfer = false;
      if (minAmount) params.min_amount = parseFloat(minAmount);
      if (maxAmount) params.max_amount = parseFloat(maxAmount);
      // Note: account and type filters handled client-side for now

      const response = await transactionsApi.getAll(params);
      let txns = response.data.data;

      // Client-side filtering for account and type (until backend supports them)
      if (selectedAccount) {
        txns = txns.filter(t => t.account_number === selectedAccount);
      }
      if (selectedType) {
        txns = txns.filter(t => t.transaction_type === selectedType);
      }

      transactions = txns;
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
    selectedInstitution = '';
    selectedTier1 = '';
    selectedTier2 = '';
    selectedTier3 = '';
    showInternalOnly = 'all';
    minAmount = '';
    maxAmount = '';
    selectedType = '';
    selectedAccount = '';
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
    // Read URL parameters and apply filters
    const urlParams = new URLSearchParams(window.location.search);

    if (urlParams.has('from_date')) fromDate = urlParams.get('from_date');
    if (urlParams.has('to_date')) toDate = urlParams.get('to_date');
    if (urlParams.has('category_tier1')) selectedTier1 = urlParams.get('category_tier1');
    if (urlParams.has('category_tier2')) selectedTier2 = urlParams.get('category_tier2');
    if (urlParams.has('category_tier3')) selectedTier3 = urlParams.get('category_tier3');
    if (urlParams.has('counterparty_name')) searchQuery = urlParams.get('counterparty_name');

    loadColumnPreferences();
    initializeColumnOrder();
    await loadCategoryTree();
    await loadAccounts();
    await loadAllOwners();
    await loadTransactions();
  });

  function formatDate(dateStr) {
    return new Date(dateStr).toLocaleDateString();
  }

  function formatAmount(amount, currency) {
    return `${parseFloat(amount).toFixed(2)} ${currency}`;
  }

  function formatAmountWithSpaces(amount) {
    if (!amount && amount !== 0) return '-';
    const num = parseFloat(amount);
    // Split into integer and decimal parts
    const [intPart, decPart] = num.toFixed(2).split('.');
    // Add space as thousand separator
    const formattedInt = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    return `${formattedInt}.${decPart}`;
  }

  function getSortIcon(column) {
    if (sortBy !== column) return '⇅';
    return sortOrder === 'asc' ? '↑' : '↓';
  }

  function getCellValue(txn, columnKey) {
    // Map column keys to actual API field names
    let value;
    if (columnKey === 'account') {
      value = txn.account_number;
    } else if (columnKey === 'type') {
      value = txn.transaction_type;
    } else if (columnKey === 'account_description') {
      // Get description from accounts config
      const accountNum = txn.account_number;
      value = accountNum && accounts[accountNum] ? accounts[accountNum].description : '-';
    } else {
      value = txn[columnKey];
    }

    // Format based on column type
    switch (columnKey) {
      case 'date':
        return formatDate(value);
      case 'amount':
        return formatAmountWithSpaces(value);
      case 'amount_czk':
        return formatAmountWithSpaces(value);
      case 'is_internal_transfer':
        return value === true ? 'Yes' : 'No';
      case 'ai_confidence':
        return value ? `${value}%` : '-';
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
    if (columnKey === 'amount_czk') {
      if (parseFloat(txn.amount_czk) < 0) return 'negative';
      if (parseFloat(txn.amount_czk) > 0) return 'positive';
    }
    return '';
  }

  async function exportToCSV() {
    let transactionsToExport = [];

    // If there's a selection, export only selected transactions
    if (selectMode && selectedTransactions.length > 0) {
      transactionsToExport = transactions.filter(txn => selectedTransactions.includes(txn.id));
    } else {
      // Otherwise, fetch ALL filtered transactions from the API
      try {
        const params = {
          skip: 0,
          limit: 100000, // High limit to get all
          sort_by: sortBy,
          sort_order: sortOrder
        };

        // Add current filters
        if (searchQuery.trim()) params.search = searchQuery.trim();
        if (fromDate) params.from_date = fromDate;
        if (toDate) params.to_date = toDate;
        if (selectedInstitution) params.institution = selectedInstitution;
        if (selectedTier1) params.category_tier1 = selectedTier1;
        if (selectedTier2) params.category_tier2 = selectedTier2;
        if (selectedTier3) params.category_tier3 = selectedTier3;
        if (showInternalOnly === 'internal') params.is_internal_transfer = true;
        if (showInternalOnly === 'exclude') params.is_internal_transfer = false;
        if (minAmount) params.min_amount = parseFloat(minAmount);
        if (maxAmount) params.max_amount = parseFloat(maxAmount);

        const response = await transactionsApi.getAll(params);
        let txns = response.data.data;

        // Client-side filtering for account and type
        if (selectedAccount) {
          txns = txns.filter(t => t.account_number === selectedAccount);
        }
        if (selectedType) {
          txns = txns.filter(t => t.transaction_type === selectedType);
        }

        transactionsToExport = txns;
      } catch (err) {
        error = `Failed to fetch transactions for export: ${err.message}`;
        setTimeout(() => { error = null; }, 5000);
        return;
      }
    }

    // Get visible columns
    const visibleCols = allColumns.filter(col => visibleColumns[col.key]);

    // Create CSV header
    const header = visibleCols.map(col => col.label).join(',');

    // Create CSV rows
    const rows = transactionsToExport.map(txn => {
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
    const filename = selectMode && selectedTransactions.length > 0
      ? `transactions_selected_${selectedTransactions.length}_${new Date().toISOString().split('T')[0]}.csv`
      : `transactions_all_${transactionsToExport.length}_${new Date().toISOString().split('T')[0]}.csv`;
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  async function exportToExcel() {
    let transactionsToExport = [];

    // If there's a selection, export only selected transactions
    if (selectMode && selectedTransactions.length > 0) {
      transactionsToExport = transactions.filter(txn => selectedTransactions.includes(txn.id));
    } else {
      // Otherwise, fetch ALL filtered transactions from the API
      try {
        const params = {
          skip: 0,
          limit: 100000, // High limit to get all
          sort_by: sortBy,
          sort_order: sortOrder
        };

        // Add current filters
        if (searchQuery.trim()) params.search = searchQuery.trim();
        if (fromDate) params.from_date = fromDate;
        if (toDate) params.to_date = toDate;
        if (selectedInstitution) params.institution = selectedInstitution;
        if (selectedTier1) params.category_tier1 = selectedTier1;
        if (selectedTier2) params.category_tier2 = selectedTier2;
        if (selectedTier3) params.category_tier3 = selectedTier3;
        if (showInternalOnly === 'internal') params.is_internal_transfer = true;
        if (showInternalOnly === 'exclude') params.is_internal_transfer = false;
        if (minAmount) params.min_amount = parseFloat(minAmount);
        if (maxAmount) params.max_amount = parseFloat(maxAmount);

        const response = await transactionsApi.getAll(params);
        let txns = response.data.data;

        // Client-side filtering for account and type
        if (selectedAccount) {
          txns = txns.filter(t => t.account_number === selectedAccount);
        }
        if (selectedType) {
          txns = txns.filter(t => t.transaction_type === selectedType);
        }

        transactionsToExport = txns;
      } catch (err) {
        error = `Failed to fetch transactions for export: ${err.message}`;
        setTimeout(() => { error = null; }, 5000);
        return;
      }
    }

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
    transactionsToExport.forEach(txn => {
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
    const filename = selectMode && selectedTransactions.length > 0
      ? `transactions_selected_${selectedTransactions.length}_${new Date().toISOString().split('T')[0]}.xls`
      : `transactions_all_${transactionsToExport.length}_${new Date().toISOString().split('T')[0]}.xls`;
    link.setAttribute('download', filename);
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

  function openEditModal(txn) {
    editingTransaction = txn;
    editForm = {
      description: txn.description || '',
      amount: txn.amount || '',
      currency: txn.currency || 'CZK',
      category_tier1: txn.category_tier1 || '',
      category_tier2: txn.category_tier2 || '',
      category_tier3: txn.category_tier3 || '',
      counterparty_name: txn.counterparty_name || '',
      counterparty_account: txn.counterparty_account || '',
      counterparty_bank: txn.counterparty_bank || '',
      variable_symbol: txn.variable_symbol || '',
      constant_symbol: txn.constant_symbol || '',
      specific_symbol: txn.specific_symbol || '',
      transaction_type: txn.transaction_type || '',
      note: txn.note || ''
    };
    showEditModal = true;
  }

  function closeEditModal() {
    showEditModal = false;
    editingTransaction = null;
  }

  async function saveTransaction() {
    try {
      loading = true;
      await transactionsApi.update(editingTransaction.id, editForm);
      closeEditModal();
      await loadTransactions();
    } catch (err) {
      error = `Failed to update transaction: ${err.message}`;
      setTimeout(() => { error = null; }, 5000);
    } finally {
      loading = false;
    }
  }

  async function deleteTransaction(txn) {
    if (!confirm(`Delete transaction: ${txn.description}?`)) {
      return;
    }

    try {
      loading = true;
      await transactionsApi.delete(txn.id);
      await loadTransactions();
    } catch (err) {
      error = `Failed to delete transaction: ${err.message}`;
      setTimeout(() => { error = null; }, 5000);
    } finally {
      loading = false;
    }
  }

  // Rule creation functions
  async function openRuleModal(txn) {
    // Pre-fill ALL fields from transaction
    ruleFormPrefill = {
      priority: 50,  // Default priority
      description_contains: txn.description || '',
      institution_exact: txn.institution || '',
      counterparty_account_exact: txn.counterparty_account || '',
      counterparty_name_contains: txn.counterparty_name || '',
      variable_symbol_exact: txn.variable_symbol || '',
      type_contains: txn.transaction_type || '',
      amount_czk_min: null,
      amount_czk_max: null,
      category_tier1: txn.category_tier1 || '',
      category_tier2: txn.category_tier2 || '',
      category_tier3: txn.category_tier3 || ''
    };

    // Load category options if categories are set
    if (ruleFormPrefill.category_tier1) {
      await loadRuleTier2Categories();
    }
    if (ruleFormPrefill.category_tier2) {
      await loadRuleTier3Categories();
    }

    showRuleModal = true;
    ruleMatchingCount = null;
  }

  async function loadRuleTier2Categories() {
    if (!ruleFormPrefill.category_tier1) {
      tier2Options = [];
      return;
    }
    try {
      const response = await categoriesApi.getTier2(ruleFormPrefill.category_tier1);
      tier2Options = response.data || [];
    } catch (err) {
      console.error('Failed to load tier2 categories:', err);
      tier2Options = [];
    }
  }

  async function loadRuleTier3Categories() {
    if (!ruleFormPrefill.category_tier1 || !ruleFormPrefill.category_tier2) {
      tier3Options = [];
      return;
    }
    try {
      const response = await categoriesApi.getTier3(ruleFormPrefill.category_tier1, ruleFormPrefill.category_tier2);
      tier3Options = response.data || [];
    } catch (err) {
      console.error('Failed to load tier3 categories:', err);
      tier3Options = [];
    }
  }

  async function testRule() {
    if (!ruleFormPrefill.category_tier1 || !ruleFormPrefill.category_tier2 || !ruleFormPrefill.category_tier3) {
      alert('Please select all three category tiers before testing');
      return;
    }

    try {
      testingRule = true;

      // Transform payload to match RuleCreate schema - only include non-empty fields
      const rulePayload = {
        priority: ruleFormPrefill.priority,
        tier1: ruleFormPrefill.category_tier1,
        tier2: ruleFormPrefill.category_tier2,
        tier3: ruleFormPrefill.category_tier3
      };

      // Only add optional fields if they have values
      if (ruleFormPrefill.description_contains) {
        rulePayload.description_contains = ruleFormPrefill.description_contains;
      }
      if (ruleFormPrefill.institution_exact) {
        rulePayload.institution_exact = ruleFormPrefill.institution_exact;
      }
      if (ruleFormPrefill.counterparty_account_exact) {
        rulePayload.counterparty_account_exact = ruleFormPrefill.counterparty_account_exact;
      }
      if (ruleFormPrefill.counterparty_name_contains) {
        rulePayload.counterparty_name_contains = ruleFormPrefill.counterparty_name_contains;
      }
      if (ruleFormPrefill.variable_symbol_exact) {
        rulePayload.variable_symbol_exact = ruleFormPrefill.variable_symbol_exact;
      }
      if (ruleFormPrefill.type_contains) {
        rulePayload.type_contains = ruleFormPrefill.type_contains;
      }
      if (ruleFormPrefill.amount_czk_min !== null && ruleFormPrefill.amount_czk_min !== undefined && ruleFormPrefill.amount_czk_min !== '') {
        rulePayload.amount_czk_min = parseFloat(ruleFormPrefill.amount_czk_min);
      }
      if (ruleFormPrefill.amount_czk_max !== null && ruleFormPrefill.amount_czk_max !== undefined && ruleFormPrefill.amount_czk_max !== '') {
        rulePayload.amount_czk_max = parseFloat(ruleFormPrefill.amount_czk_max);
      }

      console.log('Testing rule with payload:', JSON.stringify(rulePayload, null, 2));

      // Wrap in 'rule' field because backend expects multiple body parameters
      const requestBody = { rule: rulePayload };
      console.log('Wrapped request body:', JSON.stringify(requestBody, null, 2));

      const response = await api.post('/rules/test?count_matches=true', requestBody);
      ruleMatchingCount = response.data.matching_count;
    } catch (err) {
      console.error('Failed to test rule:', err);
      console.error('Error response:', err.response);
      console.error('Error response data:', err.response?.data);

      let errorMsg = err.message;

      // Handle validation errors (422) which return an array
      if (err.response?.data?.detail) {
        console.log('Error detail:', err.response.data.detail);
        if (Array.isArray(err.response.data.detail)) {
          const messages = err.response.data.detail.map(e => {
            if (typeof e === 'object' && e.loc && e.msg) {
              return `${e.loc.join('.')}: ${e.msg}`;
            }
            return e.msg || JSON.stringify(e);
          });
          errorMsg = messages.join('\n');
        } else {
          errorMsg = err.response.data.detail;
        }
      }

      console.log('Final error message:', errorMsg);
      alert('Failed to test rule:\n\n' + errorMsg);
    } finally {
      testingRule = false;
    }
  }

  async function saveRule() {
    // Validate required fields
    if (!ruleFormPrefill.category_tier1 || !ruleFormPrefill.category_tier2 || !ruleFormPrefill.category_tier3) {
      alert('All three category tiers are required');
      return;
    }

    // Build conditions object (only non-empty fields)
    let hasCondition = false;
    if (ruleFormPrefill.description_contains) hasCondition = true;
    if (ruleFormPrefill.institution_exact) hasCondition = true;
    if (ruleFormPrefill.counterparty_account_exact) hasCondition = true;
    if (ruleFormPrefill.counterparty_name_contains) hasCondition = true;
    if (ruleFormPrefill.variable_symbol_exact) hasCondition = true;
    if (ruleFormPrefill.type_contains) hasCondition = true;
    if (ruleFormPrefill.amount_czk_min !== null) hasCondition = true;
    if (ruleFormPrefill.amount_czk_max !== null) hasCondition = true;

    if (!hasCondition) {
      alert('At least one condition is required');
      return;
    }

    try {
      savingRule = true;

      // Create rule object matching RuleCreate schema
      const newRule = {
        priority: ruleFormPrefill.priority,
        description_contains: ruleFormPrefill.description_contains || null,
        institution_exact: ruleFormPrefill.institution_exact || null,
        counterparty_account_exact: ruleFormPrefill.counterparty_account_exact || null,
        counterparty_name_contains: ruleFormPrefill.counterparty_name_contains || null,
        variable_symbol_exact: ruleFormPrefill.variable_symbol_exact || null,
        type_contains: ruleFormPrefill.type_contains || null,
        amount_czk_min: ruleFormPrefill.amount_czk_min,
        amount_czk_max: ruleFormPrefill.amount_czk_max,
        tier1: ruleFormPrefill.category_tier1,
        tier2: ruleFormPrefill.category_tier2,
        tier3: ruleFormPrefill.category_tier3,
        owner: ''
      };

      await api.post('/rules', newRule);

      showRuleModal = false;

      // Show success message with matching count
      if (ruleMatchingCount !== null) {
        alert(`Rule created successfully!\n\n${ruleMatchingCount} existing transactions match this rule.\n\nUse "Re-apply Rules" to update them.`);
      } else {
        alert('Rule created successfully!\n\nUse "Re-apply Rules" to categorize transactions.');
      }
    } catch (err) {
      console.error('Failed to create rule:', err);
      alert('Failed to create rule: ' + (err.response?.data?.detail || err.message));
    } finally {
      savingRule = false;
    }
  }

  // Mass selection functions
  function toggleSelectAll() {
    if (selectedTransactions.length === transactions.length) {
      selectedTransactions = [];
    } else {
      selectedTransactions = transactions.map(t => t.id);
    }
  }

  async function selectAllFiltered() {
    try {
      loading = true;

      // Build same filter params as loadTransactions, but fetch ALL (no pagination)
      const params = {
        skip: 0,
        limit: 100000, // Very high limit to get all
        sort_by: sortBy,
        sort_order: sortOrder
      };

      // Add filters if set
      if (searchQuery.trim()) params.search = searchQuery.trim();
      if (fromDate) params.from_date = fromDate;
      if (toDate) params.to_date = toDate;
      if (selectedInstitution) params.institution = selectedInstitution;
      if (selectedTier1) params.category_tier1 = selectedTier1;
      if (selectedTier2) params.category_tier2 = selectedTier2;
      if (selectedTier3) params.category_tier3 = selectedTier3;
      if (showInternalOnly === 'internal') params.is_internal_transfer = true;
      if (showInternalOnly === 'exclude') params.is_internal_transfer = false;
      if (minAmount) params.min_amount = parseFloat(minAmount);
      if (maxAmount) params.max_amount = parseFloat(maxAmount);

      const response = await transactionsApi.getAll(params);
      let allTxns = response.data.data;

      // Client-side filtering for account and type (if set)
      if (selectedAccount) {
        allTxns = allTxns.filter(t => t.account_number === selectedAccount);
      }
      if (selectedType) {
        allTxns = allTxns.filter(t => t.transaction_type === selectedType);
      }

      // Select all IDs
      selectedTransactions = allTxns.map(t => t.id);

    } catch (err) {
      error = `Failed to select all filtered: ${err.message}`;
      setTimeout(() => { error = null; }, 5000);
    } finally {
      loading = false;
    }
  }

  function toggleTransactionSelection(id) {
    if (selectedTransactions.includes(id)) {
      selectedTransactions = selectedTransactions.filter(tid => tid !== id);
    } else {
      selectedTransactions = [...selectedTransactions, id];
    }
  }

  async function deleteBatchTransactions() {
    const count = selectedTransactions.length;
    if (!confirm(`Delete ${count} transaction(s)? This cannot be undone.`)) {
      return;
    }

    try {
      loading = true;
      let successCount = 0;
      let failCount = 0;

      for (const id of selectedTransactions) {
        try {
          await transactionsApi.delete(id);
          successCount++;
        } catch (err) {
          failCount++;
          console.error(`Failed to delete transaction ${id}:`, err);
        }
      }

      if (failCount === 0) {
        error = `✅ Successfully deleted ${successCount} transaction(s)`;
      } else {
        error = `⚠️ Deleted ${successCount}, failed ${failCount} transaction(s)`;
      }

      setTimeout(() => { error = null; }, 5000);

      selectedTransactions = [];
      selectMode = false;
      await loadTransactions();
    } catch (err) {
      error = `Failed to delete transactions: ${err.message}`;
      setTimeout(() => { error = null; }, 5000);
    } finally {
      loading = false;
    }
  }

  function openBulkEditModal() {
    bulkEditForm = {
      category_tier1: '',
      category_tier2: '',
      category_tier3: ''
    };
    showBulkEditModal = true;
  }

  async function saveBulkEdit() {
    const count = selectedTransactions.length;

    // Validate that at least one category is selected
    if (!bulkEditForm.category_tier1 && !bulkEditForm.category_tier2 && !bulkEditForm.category_tier3) {
      error = '⚠️ Please select at least one category tier';
      setTimeout(() => { error = null; }, 3000);
      return;
    }

    if (!confirm(`Update categories for ${count} transaction(s)?`)) {
      return;
    }

    try {
      loading = true;
      showBulkEditModal = false;

      // Build updates object with only filled fields
      const updates = {};
      if (bulkEditForm.category_tier1) updates.category_tier1 = bulkEditForm.category_tier1;
      if (bulkEditForm.category_tier2) updates.category_tier2 = bulkEditForm.category_tier2;
      if (bulkEditForm.category_tier3) updates.category_tier3 = bulkEditForm.category_tier3;

      const response = await transactionsApi.bulkUpdate(selectedTransactions, updates);

      error = `✅ Successfully updated ${response.data.updated_count} transaction(s)`;
      setTimeout(() => { error = null; }, 5000);

      selectedTransactions = [];
      selectMode = false;
      await loadTransactions();
    } catch (err) {
      error = `Failed to update transactions: ${err.message}`;
      setTimeout(() => { error = null; }, 5000);
    } finally {
      loading = false;
    }
  }

  // Computed for bulk edit tier2/tier3 options
  $: bulkEditTier2Options = bulkEditForm.category_tier1 ? getTier2Options(bulkEditForm.category_tier1) : [];
  $: bulkEditTier3Options = bulkEditForm.category_tier1 && bulkEditForm.category_tier2 ? getTier3Options(bulkEditForm.category_tier1, bulkEditForm.category_tier2) : [];

  // Inline category editing functions
  function startInlineEdit(txnId, field, txn) {
    inlineEditingCell = { txnId, field };
    inlineTempValue = {
      tier1: txn.category_tier1 || '',
      tier2: txn.category_tier2 || '',
      tier3: txn.category_tier3 || ''
    };
  }

  async function saveInlineEdit(txnId) {
    if (!inlineEditingCell) return;

    try {
      const updates = {
        category_tier1: inlineTempValue.tier1,
        category_tier2: inlineTempValue.tier2,
        category_tier3: inlineTempValue.tier3
      };

      await transactionsApi.update(txnId, updates);
      await loadTransactions();
    } catch (err) {
      error = `Failed to update category: ${err.message}`;
      setTimeout(() => { error = null; }, 5000);
    } finally {
      inlineEditingCell = null;
    }
  }

  function handleInlineKeydown(e, txnId) {
    if (e.key === 'Escape') {
      inlineEditingCell = null;
      e.preventDefault();
    } else if (e.key === 'Enter') {
      saveInlineEdit(txnId);
      e.preventDefault();
    }
  }
</script>

<div class="transactions">
  <div class="header">
    <h1>Transactions</h1>
    <div class="header-actions">
      <button class="btn btn-select" on:click={() => { selectMode = !selectMode; selectedTransactions = []; }}>
        {selectMode ? '❌ Cancel Selection' : '☑️ Select'}
      </button>
      {#if selectMode}
        <button class="btn btn-select-all" on:click={selectAllFiltered} disabled={loading}>
          ☑️☑️ Select All Filtered ({pagination.total_items || 0})
        </button>
      {/if}
      {#if selectMode && selectedTransactions.length > 0}
        <button class="btn btn-primary" on:click={openBulkEditModal}>
          ✏️ Edit Categories ({selectedTransactions.length})
        </button>
        <button class="btn btn-danger" on:click={deleteBatchTransactions}>
          🗑️ Delete Selected ({selectedTransactions.length})
        </button>
      {/if}
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
        <h3>Show/Hide & Reorder Columns</h3>
        <div class="column-actions">
          <button class="btn-reset" on:click={selectAllColumns}>Select All</button>
          <button class="btn-reset" on:click={deselectAllColumns}>Deselect All</button>
          <button class="btn-reset" on:click={resetColumns}>Reset</button>
        </div>
      </div>
      <div class="column-list">
        {#each columnOrder as colKey, index (colKey)}
          {@const column = allColumns.find(c => c.key === colKey)}
          <div
            class="column-item"
            draggable="true"
            on:dragstart={(e) => handleDragStart(e, index)}
            on:drop={(e) => handleDrop(e, index)}
            on:dragover={(e) => e.preventDefault()}
            on:dragenter={(e) => e.preventDefault()}
          >
            <span class="drag-handle" title="Drag to reorder">☰</span>
            <label>
              <input
                type="checkbox"
                bind:checked={visibleColumns[column.key]}
                on:change={() => saveColumnPreferences()}
              />
              <span>{column.label}</span>
            </label>
          </div>
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
        <label>Institution:</label>
        <select bind:value={selectedInstitution} on:change={handleFilterChange} class="filter-select">
          <option value="">All Institutions</option>
          {#each institutions as institution}
            <option value={institution}>{institution}</option>
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
            <label>Type:</label>
            <select bind:value={selectedType} on:change={handleFilterChange} class="filter-select">
              <option value="">All Types</option>
              {#each transactionTypes as type}
                <option value={type}>{type}</option>
              {/each}
            </select>
          </div>

          <div class="filter-group">
            <label>Account:</label>
            <select bind:value={selectedAccount} on:change={handleFilterChange} class="filter-select">
              <option value="">All Accounts</option>
              {#each accountNumbers as accountNum}
                <option value={accountNum}>
                  {accountNum} {accounts[accountNum] ? `(${accounts[accountNum].description})` : ''}
                </option>
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
              {#if selectMode}
                <th class="checkbox-cell">
                  <input
                    type="checkbox"
                    checked={selectedTransactions.length === transactions.length && transactions.length > 0}
                    on:change={toggleSelectAll}
                    title="Select all filtered transactions"
                  />
                </th>
              {/if}
              {#each columnOrder as colKey}
                {@const column = allColumns.find(c => c.key === colKey)}
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
                {#if selectMode}
                  <td class="checkbox-cell">
                    <input
                      type="checkbox"
                      checked={selectedTransactions.includes(txn.id)}
                      on:change={() => toggleTransactionSelection(txn.id)}
                    />
                  </td>
                {/if}
                {#each columnOrder as colKey}
                  {@const column = allColumns.find(c => c.key === colKey)}
                  {#if visibleColumns[column.key]}
                    {#if column.key === 'actions'}
                      <td class="actions-cell">
                        <button class="btn-icon" on:click={() => openEditModal(txn)} title="Edit">
                          ✏️
                        </button>
                        <button class="btn-icon" on:click={() => openRuleModal(txn)} title="Create rule from this transaction">
                          ➕
                        </button>
                        <button class="btn-icon btn-danger" on:click={() => deleteTransaction(txn)} title="Delete">
                          🗑️
                        </button>
                      </td>
                    {:else if column.key === 'category_tier1' || column.key === 'category_tier2' || column.key === 'category_tier3'}
                      <td
                        class={getCellClass(txn, column.key)}
                        on:dblclick={() => startInlineEdit(txn.id, column.key, txn)}
                      >
                        {#if inlineEditingCell?.txnId === txn.id && inlineEditingCell?.field === column.key}
                          <!-- Inline select dropdown -->
                          {#if column.key === 'category_tier1'}
                            <select
                              bind:value={inlineTempValue.tier1}
                              on:change={() => { inlineTempValue.tier2 = ''; inlineTempValue.tier3 = ''; }}
                              on:blur={() => saveInlineEdit(txn.id)}
                              on:keydown={(e) => handleInlineKeydown(e, txn.id)}
                              autofocus
                              class="inline-select"
                            >
                              <option value="">Select...</option>
                              {#each categoryTree as cat}
                                <option value={cat.tier1}>{cat.tier1}</option>
                              {/each}
                            </select>
                          {:else if column.key === 'category_tier2'}
                            <select
                              bind:value={inlineTempValue.tier2}
                              on:change={() => { inlineTempValue.tier3 = ''; }}
                              on:blur={() => saveInlineEdit(txn.id)}
                              on:keydown={(e) => handleInlineKeydown(e, txn.id)}
                              autofocus
                              class="inline-select"
                            >
                              <option value="">Select...</option>
                              {#each getTier2Options(inlineTempValue.tier1) as cat}
                                <option value={cat.tier2}>{cat.tier2}</option>
                              {/each}
                            </select>
                          {:else if column.key === 'category_tier3'}
                            <select
                              bind:value={inlineTempValue.tier3}
                              on:blur={() => saveInlineEdit(txn.id)}
                              on:keydown={(e) => handleInlineKeydown(e, txn.id)}
                              autofocus
                              class="inline-select"
                            >
                              <option value="">Select...</option>
                              {#each getTier3Options(inlineTempValue.tier1, inlineTempValue.tier2) as tier3}
                                <option value={tier3}>{tier3}</option>
                              {/each}
                            </select>
                          {/if}
                        {:else}
                          <span class="editable-cell" title="Double-click to edit">
                            {getCellValue(txn, column.key)}
                          </span>
                        {/if}
                      </td>
                    {:else}
                      <td class={getCellClass(txn, column.key)}>
                        {getCellValue(txn, column.key)}
                      </td>
                    {/if}
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

  <!-- Edit Transaction Modal -->
  {#if showEditModal}
    <div class="modal-backdrop"
      on:mousedown={() => editModalBackdropMouseDown = true}
      on:mouseup={() => {
        if (editModalBackdropMouseDown) {
          closeEditModal();
        }
        editModalBackdropMouseDown = false;
      }}>
      <div class="modal" on:click|stopPropagation on:mousedown|stopPropagation on:mouseup|stopPropagation>
        <div class="modal-header">
          <h2>Edit Transaction</h2>
          <button class="btn-close" on:click={closeEditModal}>✕</button>
        </div>
        <div class="modal-body modal-scrollable">
          <!-- Core Fields Section -->
          <fieldset>
            <legend>Core Information</legend>
            <div class="form-group">
              <label>Description</label>
              <input type="text" bind:value={editForm.description} placeholder="Transaction description" class="input-full-width" />
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Amount</label>
                <input type="number" step="0.01" bind:value={editForm.amount} />
              </div>
              <div class="form-group">
                <label>Currency</label>
                <select bind:value={editForm.currency}>
                  <option value="CZK">CZK</option>
                  <option value="EUR">EUR</option>
                  <option value="USD">USD</option>
                </select>
              </div>
            </div>
          </fieldset>

          <!-- Categories Section -->
          <fieldset>
            <legend>Categories</legend>
            <div class="form-group">
              <label>Category (Tier1)</label>
              <select bind:value={editForm.category_tier1}>
                <option value="">Select Tier1</option>
                {#each categoryTree as cat}
                  <option value={cat.tier1}>{cat.tier1}</option>
                {/each}
              </select>
            </div>

            {#if editForm.category_tier1}
              <div class="form-group">
                <label>Category (Tier2)</label>
                <select bind:value={editForm.category_tier2}>
                  <option value="">Select Tier2</option>
                  {#each categoryTree.find(c => c.tier1 === editForm.category_tier1)?.tier2_categories || [] as tier2}
                    <option value={tier2.tier2}>{tier2.tier2}</option>
                  {/each}
                </select>
              </div>
            {/if}

            {#if editForm.category_tier2}
              <div class="form-group">
                <label>Category (Tier3)</label>
                <select bind:value={editForm.category_tier3}>
                  <option value="">Select Tier3</option>
                  {#each categoryTree.find(c => c.tier1 === editForm.category_tier1)?.tier2_categories?.find(t2 => t2.tier2 === editForm.category_tier2)?.tier3 || [] as tier3}
                    <option value={tier3}>{tier3}</option>
                  {/each}
                </select>
              </div>
            {/if}
          </fieldset>

          <!-- Counterparty Section -->
          <fieldset>
            <legend>Counterparty Information</legend>
            <div class="form-row">
              <div class="form-group">
                <label>Counterparty Name</label>
                <input type="text" bind:value={editForm.counterparty_name} placeholder="Name" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Counterparty Account</label>
                <input type="text" bind:value={editForm.counterparty_account} placeholder="Account number" />
              </div>
              <div class="form-group">
                <label>Counterparty Bank</label>
                <input type="text" bind:value={editForm.counterparty_bank} placeholder="Bank" />
              </div>
            </div>
          </fieldset>

          <!-- Czech Banking Symbols -->
          <fieldset>
            <legend>Czech Banking Symbols</legend>
            <div class="form-row">
              <div class="form-group">
                <label>Variable Symbol</label>
                <input type="text" bind:value={editForm.variable_symbol} placeholder="VS" />
              </div>
              <div class="form-group">
                <label>Constant Symbol</label>
                <input type="text" bind:value={editForm.constant_symbol} placeholder="CS" />
              </div>
              <div class="form-group">
                <label>Specific Symbol</label>
                <input type="text" bind:value={editForm.specific_symbol} placeholder="SS" />
              </div>
            </div>
          </fieldset>

          <!-- Additional Fields -->
          <fieldset>
            <legend>Additional Information</legend>
            <div class="form-group">
              <label>Transaction Type</label>
              <input type="text" bind:value={editForm.transaction_type} placeholder="Type" />
            </div>
            <div class="form-group">
              <label>Note</label>
              <textarea bind:value={editForm.note} placeholder="Add a note..." rows="3"></textarea>
            </div>
          </fieldset>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" on:click={closeEditModal}>Cancel</button>
          <button class="btn btn-primary" on:click={saveTransaction}>Save Changes</button>
        </div>
      </div>
    </div>
  {/if}

  <!-- Bulk Edit Categories Modal -->
  {#if showBulkEditModal}
    <div class="modal-backdrop"
      on:mousedown={() => bulkEditModalBackdropMouseDown = true}
      on:mouseup={() => {
        if (bulkEditModalBackdropMouseDown) {
          showBulkEditModal = false;
        }
        bulkEditModalBackdropMouseDown = false;
      }}>
      <div class="modal" on:click|stopPropagation on:mousedown|stopPropagation on:mouseup|stopPropagation>
        <div class="modal-header">
          <h2>✏️ Bulk Edit Categories ({selectedTransactions.length} transactions)</h2>
          <button class="btn-close" on:click={() => showBulkEditModal = false}>✕</button>
        </div>
        <div class="modal-body">
          <p style="margin-bottom: 20px; color: #666;">
            Update categories for <strong>{selectedTransactions.length}</strong> selected transaction(s).
            Only fill in the categories you want to update.
          </p>

          <fieldset>
            <legend>Categories</legend>
            <div class="form-group">
              <label>Category (Tier1)</label>
              <select bind:value={bulkEditForm.category_tier1}>
                <option value="">-- Keep unchanged --</option>
                {#each categoryTree as cat}
                  <option value={cat.tier1}>{cat.tier1}</option>
                {/each}
              </select>
            </div>

            {#if bulkEditForm.category_tier1}
              <div class="form-group">
                <label>Category (Tier2)</label>
                <select bind:value={bulkEditForm.category_tier2}>
                  <option value="">-- Keep unchanged --</option>
                  {#each bulkEditTier2Options as tier2}
                    <option value={tier2.tier2}>{tier2.tier2}</option>
                  {/each}
                </select>
              </div>
            {/if}

            {#if bulkEditForm.category_tier2}
              <div class="form-group">
                <label>Category (Tier3)</label>
                <select bind:value={bulkEditForm.category_tier3}>
                  <option value="">-- Keep unchanged --</option>
                  {#each bulkEditTier3Options as tier3}
                    <option value={tier3}>{tier3}</option>
                  {/each}
                </select>
              </div>
            {/if}
          </fieldset>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" on:click={() => showBulkEditModal = false}>Cancel</button>
          <button class="btn btn-primary" on:click={saveBulkEdit}>Update Categories</button>
        </div>
      </div>
    </div>
  {/if}

  <!-- Rule Creation Modal -->
  {#if showRuleModal}
    <div class="modal-backdrop"
      on:mousedown={() => ruleModalBackdropMouseDown = true}
      on:mouseup={() => {
        if (ruleModalBackdropMouseDown) {
          showRuleModal = false;
        }
        ruleModalBackdropMouseDown = false;
      }}>
      <div class="modal rule-modal" on:click|stopPropagation on:mousedown|stopPropagation on:mouseup|stopPropagation>
        <div class="modal-header">
          <h2>➕ Create Categorization Rule</h2>
          <button class="btn-close" on:click={() => showRuleModal = false}>✕</button>
        </div>
        <div class="modal-body">
          <!-- Priority -->
          <div class="form-group">
            <label for="rule-priority">Priority (0-1000)</label>
            <input
              type="number"
              id="rule-priority"
              bind:value={ruleFormPrefill.priority}
              min="0"
              max="1000"
            />
            <small>Higher priority rules are checked first</small>
          </div>

          <!-- Conditions Section -->
          <h3>Conditions (all must match)</h3>
          <p class="hint">Pre-filled from transaction. Remove/edit fields as needed.</p>

          <div class="form-group">
            <label for="rule-description">Description Contains</label>
            <input
              type="text"
              id="rule-description"
              bind:value={ruleFormPrefill.description_contains}
              placeholder="e.g., NETFLIX"
            />
          </div>

          <div class="form-group">
            <label for="rule-institution">Institution (exact)</label>
            <input
              type="text"
              id="rule-institution"
              bind:value={ruleFormPrefill.institution_exact}
              placeholder="e.g., ČSOB"
            />
          </div>

          <div class="form-group">
            <label for="rule-counterparty-name">Counterparty Name Contains</label>
            <input
              type="text"
              id="rule-counterparty-name"
              bind:value={ruleFormPrefill.counterparty_name_contains}
              placeholder="e.g., Google"
            />
          </div>

          <div class="form-group">
            <label for="rule-counterparty-account">Counterparty Account (exact)</label>
            <input
              type="text"
              id="rule-counterparty-account"
              bind:value={ruleFormPrefill.counterparty_account_exact}
              placeholder="e.g., 123456789/0300"
            />
          </div>

          <div class="form-group">
            <label for="rule-variable-symbol">Variable Symbol (exact)</label>
            <input
              type="text"
              id="rule-variable-symbol"
              bind:value={ruleFormPrefill.variable_symbol_exact}
              placeholder="e.g., 12345"
            />
          </div>

          <div class="form-group">
            <label for="rule-type">Type Contains</label>
            <input
              type="text"
              id="rule-type"
              bind:value={ruleFormPrefill.type_contains}
              placeholder="e.g., Úroky"
            />
          </div>

          <div class="form-row">
            <div class="form-group">
              <label for="rule-amount-min">Amount Min (CZK)</label>
              <input
                type="number"
                id="rule-amount-min"
                bind:value={ruleFormPrefill.amount_czk_min}
                step="0.01"
              />
            </div>
            <div class="form-group">
              <label for="rule-amount-max">Amount Max (CZK)</label>
              <input
                type="number"
                id="rule-amount-max"
                bind:value={ruleFormPrefill.amount_czk_max}
                step="0.01"
              />
            </div>
          </div>

          <!-- Category Assignment -->
          <h3>Category Assignment (required)</h3>

          <div class="form-group">
            <label for="rule-tier1">Tier 1 *</label>
            <select
              id="rule-tier1"
              bind:value={ruleFormPrefill.category_tier1}
              on:change={() => {
                ruleFormPrefill.category_tier2 = '';
                ruleFormPrefill.category_tier3 = '';
                loadRuleTier2Categories();
              }}
            >
              <option value="">Select Tier 1...</option>
              {#each categoryTree as cat}
                <option value={cat.tier1}>{cat.tier1}</option>
              {/each}
            </select>
          </div>

          <div class="form-group">
            <label for="rule-tier2">Tier 2 *</label>
            <select
              id="rule-tier2"
              bind:value={ruleFormPrefill.category_tier2}
              on:change={() => {
                ruleFormPrefill.category_tier3 = '';
                loadRuleTier3Categories();
              }}
              disabled={!ruleFormPrefill.category_tier1}
            >
              <option value="">Select Tier 2...</option>
              {#each tier2Options as tier2}
                <option value={tier2}>{tier2}</option>
              {/each}
            </select>
          </div>

          <div class="form-group">
            <label for="rule-tier3">Tier 3 *</label>
            <select
              id="rule-tier3"
              bind:value={ruleFormPrefill.category_tier3}
              disabled={!ruleFormPrefill.category_tier2}
            >
              <option value="">Select Tier 3...</option>
              {#each tier3Options as tier3}
                <option value={tier3}>{tier3}</option>
              {/each}
            </select>
          </div>

          <!-- Test Results -->
          {#if ruleMatchingCount !== null}
            <div class="test-results">
              <strong>Matching Transactions:</strong> {ruleMatchingCount}
              {#if ruleMatchingCount > 100}
                <span class="warning">⚠️ This rule is very broad</span>
              {/if}
            </div>
          {/if}
        </div>
        <div class="modal-footer">
          <button
            class="btn btn-secondary"
            on:click={testRule}
            disabled={testingRule}
          >
            {testingRule ? 'Testing...' : '🔍 Test Rule'}
          </button>
          <button class="btn btn-secondary" on:click={() => showRuleModal = false}>
            Cancel
          </button>
          <button
            class="btn btn-primary"
            on:click={saveRule}
            disabled={savingRule}
          >
            {savingRule ? 'Creating...' : 'Create Rule'}
          </button>
        </div>
      </div>
    </div>
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
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .column-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    background: white;
    cursor: move;
    transition: background-color 0.2s;
  }

  .column-item:hover {
    background-color: #f5f5f5;
  }

  .drag-handle {
    color: #999;
    font-weight: bold;
    cursor: grab;
    user-select: none;
  }

  .drag-handle:active {
    cursor: grabbing;
  }

  .column-item label {
    flex: 1;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
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

  .actions-cell {
    white-space: nowrap;
  }

  .checkbox-cell {
    width: 40px;
    text-align: center;
    padding: 8px;
  }

  .checkbox-cell input[type="checkbox"] {
    cursor: pointer;
    width: 18px;
    height: 18px;
  }

  .btn-select {
    background: #17a2b8;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .btn-select:hover {
    background: #138496;
  }

  .btn-select-all {
    background: #20c997;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background-color 0.2s;
    font-weight: 600;
  }

  .btn-select-all:hover:not(:disabled) {
    background: #1ab386;
  }

  .btn-select-all:disabled {
    background: #ccc;
    cursor: not-allowed;
    color: #666;
  }

  .btn-danger {
    background: #dc3545;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 0.875rem;
    cursor: pointer;
    transition: background-color 0.2s;
    font-weight: 500;
  }

  .btn-danger:hover {
    background: #c82333;
  }

  .btn-icon {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 1.2rem;
    padding: 4px 8px;
    margin: 0 2px;
    border-radius: 4px;
    transition: background-color 0.2s;
  }

  .btn-icon:hover {
    background-color: #f0f0f0;
  }

  .btn-icon.btn-danger:hover {
    background-color: #ffebee;
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

  /* Enhanced Edit Modal Styles */
  .modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal {
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    width: 90%;
    max-width: 800px;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.5rem;
    border-bottom: 1px solid #e0e0e0;
    background: linear-gradient(to bottom, #f8f9fa, #ffffff);
  }

  .modal-header h2 {
    margin: 0;
    font-size: 1.5rem;
    color: #333;
    font-weight: 600;
  }

  .btn-close {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: #999;
    line-height: 1;
    padding: 0;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: all 0.2s;
  }

  .btn-close:hover {
    background-color: #f0f0f0;
    color: #333;
  }

  .modal-body {
    padding: 1.5rem;
    overflow-y: auto;
  }

  .modal-scrollable {
    max-height: calc(90vh - 180px);
    overflow-y: auto;
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    padding: 1.5rem;
    border-top: 1px solid #e0e0e0;
    background-color: #f8f9fa;
  }

  /* Rule Modal Specific Styles */
  .rule-modal {
    max-width: 700px;
    max-height: 90vh;
  }

  .rule-modal .modal-body {
    overflow-y: auto;
  }

  .rule-modal h3 {
    margin-top: 24px;
    margin-bottom: 12px;
    color: #2c3e50;
    font-size: 1.1rem;
    font-weight: 600;
  }

  .hint {
    font-size: 0.85rem;
    color: #666;
    margin-bottom: 12px;
    font-style: italic;
  }

  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .test-results {
    padding: 12px;
    background: #e8f5e9;
    border: 1px solid #4caf50;
    border-radius: 6px;
    margin-top: 16px;
  }

  .test-results .warning {
    color: #f57c00;
    margin-left: 8px;
  }

  fieldset {
    border: 1px solid #e0e0e0;
    padding: 20px;
    margin-bottom: 20px;
    border-radius: 6px;
    background-color: #fafafa;
  }

  fieldset legend {
    font-weight: 600;
    padding: 0 12px;
    color: #444;
    font-size: 1rem;
    background-color: white;
    border-radius: 4px;
    border: 1px solid #e0e0e0;
  }

  .form-group {
    margin-bottom: 1rem;
  }

  .form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: #555;
    font-size: 0.9rem;
  }

  .form-group input,
  .form-group select,
  .form-group textarea {
    width: 100%;
    padding: 0.6rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.95rem;
    transition: border-color 0.2s;
    background-color: white;
  }

  .form-group input:focus,
  .form-group select:focus,
  .form-group textarea:focus {
    outline: none;
    border-color: #4CAF50;
    box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.1);
  }

  .input-full-width {
    width: 100%;
  }

  .form-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
  }

  /* Inline Category Editing Styles */
  .editable-cell {
    cursor: pointer;
    border-bottom: 1px dashed #ccc;
    display: block;
    width: 100%;
    padding: 2px 4px;
  }

  .editable-cell:hover {
    background-color: #f0f0f0;
    border-bottom-color: #4CAF50;
  }

  .inline-select {
    width: 100%;
    padding: 4px;
    border: 2px solid #4CAF50;
    border-radius: 4px;
    font-size: 14px;
    background: white;
  }

  .inline-select:focus {
    outline: none;
    border-color: #45a049;
    box-shadow: 0 0 5px rgba(76, 175, 80, 0.3);
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

    .form-row {
      grid-template-columns: 1fr;
    }
  }
</style>
