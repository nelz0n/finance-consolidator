<script>
  import { onMount } from 'svelte';

  let loading = true;
  let error = null;
  let saveSuccess = false;
  let activeTab = 'app'; // 'app', 'currency', 'institutions', 'accounts'

  // Transaction field reference - what fields can be mapped
  const TRANSACTION_FIELDS = [
    { name: 'date', required: true, description: 'Transaction date (will be parsed using date format)' },
    { name: 'amount', required: true, description: 'Transaction amount (will be parsed using decimal/thousands separators)' },
    { name: 'currency', required: true, description: 'Currency code (e.g., CZK, EUR, USD)' },
    { name: 'description', required: true, description: 'Transaction description/note' },
    { name: 'account', required: false, description: 'Your account number' },
    { name: 'counterparty_account', required: false, description: 'Other party account number' },
    { name: 'counterparty_name', required: false, description: 'Other party name' },
    { name: 'counterparty_bank', required: false, description: 'Other party bank code' },
    { name: 'transaction_type', required: false, description: 'Type of transaction (e.g., card payment, transfer)' },
    { name: 'transaction_id', required: false, description: 'Unique transaction identifier from bank' },
    { name: 'variable_symbol', required: false, description: 'Variable symbol (Czech banking)' },
    { name: 'constant_symbol', required: false, description: 'Constant symbol (Czech banking)' },
    { name: 'specific_symbol', required: false, description: 'Specific symbol (Czech banking)' },
    { name: 'reference', required: false, description: 'Payment reference' },
    { name: 'note', required: false, description: 'Additional notes' }
  ];

  // App settings
  let appSettings = {
    google_drive: { input_folder_id: '' },
    google_sheets: { master_sheet_id: '', transactions_tab: '' },
    processing: { timezone: '' }
  };

  // Currency settings
  let currencySettings = {
    base_currency: 'CZK',
    use_cnb_api: true,
    supported: [],
    rates: {}
  };

  // Institutions
  let institutions = [];
  let selectedInstitution = null;
  let ownerMappings = []; // Array of {account, owner} objects for easy editing
  let showInstitutionForm = false;
  let isEditingInstitution = false; // Track if we're editing vs creating
  let institutionForm = {
    name: '',
    type: 'bank',
    country: 'CZ',
    filename_patterns: [''],
    encoding: 'utf-8-sig',
    delimiter: ';',
    has_header: true,
    skip_rows: 0,
    date_format: '%d.%m.%Y',
    decimal_separator: ',',
    thousands_separator: ' ',
    reverse_sign: false,
    column_mapping: {},
    owner_mappings: {},
    category_mappings: {}
  };
  let columnMappingRows = []; // For editing column mappings
  let transformations = []; // For building combined/concatenated fields
  let defaults = []; // Default values (array of {field, value})
  let skipPatterns = []; // Filtering patterns (array of strings)
  let stripWhitespace = false; // Description cleanup: strip extra whitespace
  let removePatterns = []; // Description cleanup: regex patterns to remove (array of strings)
  let showFieldReference = false; // Toggle field reference panel

  // Owners (global)
  let owners = [];
  let selectedOwner = null;
  let showAddAccountForm = false;
  let newAccount = { account: '', institution_id: '' };

  // Accounts management
  let accounts = {}; // { "account_number": { description: "..." } }
  let editingAccount = null;
  let showAddAccountModal = false;
  let accountForm = { account_number: '', description: '' };

  // Track mousedown on modal backdrop to prevent closing when selecting text
  let accountModalBackdropMouseDown = false;

  onMount(async () => {
    await loadSettings();
    if (activeTab === 'accounts') {
      await loadAccounts();
    }
  });

  // Load accounts when switching to accounts tab
  $: if (activeTab === 'accounts' && Object.keys(accounts).length === 0) {
    loadAccounts();
  }

  async function loadSettings() {
    try {
      loading = true;
      error = null;

      // Load app settings
      const appResponse = await fetch('/api/v1/settings/app');
      if (!appResponse.ok) throw new Error('Failed to load app settings');
      const appData = await appResponse.json();
      appSettings = appData;
      currencySettings = appData.currency;

      // Load institutions
      const instResponse = await fetch('/api/v1/settings/institutions');
      if (!instResponse.ok) throw new Error('Failed to load institutions');
      const instData = await instResponse.json();
      institutions = instData.institutions;

      // Load owners
      const ownersResponse = await fetch('/api/v1/settings/owners');
      if (!ownersResponse.ok) throw new Error('Failed to load owners');
      const ownersData = await ownersResponse.json();
      owners = ownersData.owners;

      loading = false;
    } catch (err) {
      error = err.message;
      loading = false;
    }
  }

  async function saveAppSettings() {
    try {
      const response = await fetch('/api/v1/settings/app', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          google_drive: appSettings.google_drive,
          google_sheets: appSettings.google_sheets,
          processing: appSettings.processing,
          currency: currencySettings
        })
      });

      if (!response.ok) throw new Error('Failed to save settings');

      saveSuccess = true;
      setTimeout(() => saveSuccess = false, 3000);
    } catch (err) {
      error = err.message;
    }
  }

  // Accounts functions
  async function loadAccounts() {
    try {
      const response = await fetch('/api/v1/accounts');
      if (!response.ok) throw new Error('Failed to load accounts');
      const data = await response.json();
      accounts = data.accounts || {};
    } catch (err) {
      error = err.message;
    }
  }

  async function saveAccounts() {
    try {
      const response = await fetch('/api/v1/accounts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ accounts })
      });

      if (!response.ok) throw new Error('Failed to save accounts');

      saveSuccess = true;
      setTimeout(() => saveSuccess = false, 3000);
      await loadAccounts();
    } catch (err) {
      error = err.message;
    }
  }

  function openAddAccountModal() {
    accountForm = { account_number: '', description: '' };
    editingAccount = null;
    showAddAccountModal = true;
  }

  function openEditAccountModal(accountNumber) {
    accountForm = {
      account_number: accountNumber,
      description: accounts[accountNumber]?.description || ''
    };
    editingAccount = accountNumber;
    showAddAccountModal = true;
  }

  function closeAccountModal() {
    showAddAccountModal = false;
    accountForm = { account_number: '', description: '' };
    editingAccount = null;
  }

  async function saveAccount() {
    if (!accountForm.account_number || !accountForm.description) {
      error = 'Account number and description are required';
      return;
    }

    try {
      accounts[accountForm.account_number] = { description: accountForm.description };
      await saveAccounts();
      closeAccountModal();
    } catch (err) {
      error = err.message;
    }
  }

  async function deleteAccount(accountNumber) {
    if (!confirm(`Delete account "${accountNumber}"?`)) return;

    try {
      delete accounts[accountNumber];
      await saveAccounts();
    } catch (err) {
      error = err.message;
    }
  }

  async function saveOwnerMappings(institutionId) {
    try {
      // Convert array back to object for API
      const mappingsObject = {};
      ownerMappings.forEach(({ account, owner }) => {
        if (account && account.trim()) { // Only save non-empty accounts
          mappingsObject[account.trim()] = owner.trim();
        }
      });

      const response = await fetch(`/api/v1/settings/institutions/${institutionId}/owners`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(mappingsObject)
      });

      if (!response.ok) throw new Error('Failed to save owner mappings');

      saveSuccess = true;
      setTimeout(() => saveSuccess = false, 3000);
      await loadSettings();
    } catch (err) {
      error = err.message;
    }
  }

  function selectInstitution(institution) {
    selectedInstitution = institution;
    showInstitutionForm = false;
    // Convert object to array for easy editing
    ownerMappings = Object.entries(institution.owner_mappings || {}).map(([account, owner]) => ({
      account,
      owner
    }));
  }

  function addOwnerMapping() {
    ownerMappings = [...ownerMappings, { account: '', owner: '' }];
  }

  function removeOwnerMapping(index) {
    ownerMappings = ownerMappings.filter((_, i) => i !== index);
  }

  function openNewInstitutionForm() {
    institutionForm = {
      name: '',
      type: 'bank',
      country: 'CZ',
      filename_patterns: [''],
      encoding: 'utf-8-sig',
      delimiter: ';',
      has_header: true,
      skip_rows: 0,
      date_format: '%d.%m.%Y',
      decimal_separator: ',',
      thousands_separator: ' ',
      reverse_sign: false,
      column_mapping: {},
      owner_mappings: {},
      category_mappings: {}
    };
    columnMappingRows = [];
    transformations = [];
    defaults = [];
    skipPatterns = [];
    stripWhitespace = false;
    removePatterns = [];
    showInstitutionForm = true;
    isEditingInstitution = false;
    selectedInstitution = null;
  }

  function addFilenamePattern() {
    institutionForm.filename_patterns = [...institutionForm.filename_patterns, ''];
  }

  function removeFilenamePattern(index) {
    institutionForm.filename_patterns = institutionForm.filename_patterns.filter((_, i) => i !== index);
  }

  function addColumnMapping() {
    columnMappingRows = [...columnMappingRows, { field: '', column: '' }];
  }

  function removeColumnMapping(index) {
    columnMappingRows = columnMappingRows.filter((_, i) => i !== index);
  }

  function addTransformation() {
    transformations = [...transformations, { name: '', parts: [{ type: 'column', value: '' }] }];
  }

  function removeTransformation(index) {
    transformations = transformations.filter((_, i) => i !== index);
  }

  function addTransformationPart(transformIndex) {
    transformations[transformIndex].parts = [...transformations[transformIndex].parts, { type: 'column', value: '' }];
  }

  function removeTransformationPart(transformIndex, partIndex) {
    transformations[transformIndex].parts = transformations[transformIndex].parts.filter((_, i) => i !== partIndex);
  }

  function buildTransformationString(transformation) {
    // Build the concatenation string like: 'Column1' + ' ' + 'Column2'
    return transformation.parts
      .map(part => `'${part.value}'`)
      .join(' + ');
  }

  function parseTransformationString(name, transformString) {
    // Parse a string like: "'Column1' + ' / ' + 'Column2'" into parts
    // This is a simple parser - splits by ' + ' and removes quotes
    const parts = [];

    if (!transformString) return { name, parts: [{ type: 'column', value: '' }] };

    // Split by ' + ' (with spaces)
    const tokens = transformString.split(/\s*\+\s*/);

    for (const token of tokens) {
      let value = token.trim();

      // Remove surrounding quotes
      if ((value.startsWith("'") && value.endsWith("'")) ||
          (value.startsWith('"') && value.endsWith('"'))) {
        value = value.slice(1, -1);
      }

      // Determine if it's a column or fixed text
      // Heuristic: if it looks like a column name (alphanumeric with spaces/underscores)
      // and doesn't contain special chars like [, :, etc., it's likely a column
      const isFixedText = /[\[\]\:\(\)]/.test(value) || value.length < 3;

      parts.push({
        type: isFixedText ? 'text' : 'column',
        value: value
      });
    }

    return { name, parts: parts.length > 0 ? parts : [{ type: 'column', value: '' }] };
  }

  function addDefault() {
    defaults = [...defaults, { field: '', value: '' }];
  }

  function removeDefault(index) {
    defaults = defaults.filter((_, i) => i !== index);
  }

  function addSkipPattern() {
    skipPatterns = [...skipPatterns, ''];
  }

  function removeSkipPattern(index) {
    skipPatterns = skipPatterns.filter((_, i) => i !== index);
  }

  function addRemovePattern() {
    removePatterns = [...removePatterns, ''];
  }

  function removeRemovePattern(index) {
    removePatterns = removePatterns.filter((_, i) => i !== index);
  }

  async function createInstitution() {
    try {
      // Build column_mapping from rows
      const column_mapping = {};
      columnMappingRows.forEach(({ field, column }) => {
        if (field && column) {
          column_mapping[field] = column;
        }
      });

      // Build transformations object
      const custom_transformations = {};
      transformations.forEach(transform => {
        if (transform.name && transform.name.trim()) {
          custom_transformations[transform.name.trim()] = buildTransformationString(transform);
        }
      });

      // Add description cleanup if configured
      if (stripWhitespace || removePatterns.length > 0) {
        const descConfig = {};
        if (stripWhitespace) {
          descConfig.strip_whitespace = true;
        }
        if (removePatterns.length > 0) {
          descConfig.remove_patterns = removePatterns.filter(p => p.trim());
        }
        custom_transformations.description = descConfig;
      }

      // Build defaults object
      const defaultsObj = {};
      defaults.forEach(({ field, value }) => {
        if (field && field.trim()) {
          defaultsObj[field.trim()] = value;
        }
      });

      const payload = {
        ...institutionForm,
        column_mapping,
        custom_transformations,
        defaults: defaultsObj,
        skip_patterns: skipPatterns
      };

      const response = await fetch('/api/v1/settings/institutions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create institution');
      }

      saveSuccess = true;
      setTimeout(() => saveSuccess = false, 3000);
      showInstitutionForm = false;
      await loadSettings();
    } catch (err) {
      error = err.message;
    }
  }

  async function openEditInstitutionForm() {
    if (!selectedInstitution) return;

    try {
      // Fetch full institution config
      const response = await fetch(`/api/v1/settings/institutions/${selectedInstitution.id}`);
      if (!response.ok) throw new Error('Failed to load institution details');

      const config = await response.json();

      // Populate form with existing data
      institutionForm = {
        name: config.institution.name,
        type: config.institution.type,
        country: config.institution.country,
        filename_patterns: config.file_detection.filename_patterns || [''],
        encoding: config.csv_format?.encoding || config.format?.encoding || 'utf-8-sig',
        delimiter: config.csv_format?.delimiter || config.format?.delimiter || ';',
        has_header: config.csv_format?.has_header ?? config.format?.has_header ?? true,
        skip_rows: config.csv_format?.skip_rows ?? config.format?.skip_rows ?? 0,
        date_format: config.transformations?.date?.format || '%d.%m.%Y',
        decimal_separator: config.transformations?.amount?.decimal_separator || ',',
        thousands_separator: config.transformations?.amount?.thousands_separator || ' ',
        reverse_sign: config.transformations?.amount?.reverse_sign || false,
        column_mapping: config.column_mapping || config.columns || {},
        owner_mappings: config.owner_detection?.account_mapping || {},
        category_mappings: config.category_mapping || {}
      };

      // Convert column_mapping to rows
      columnMappingRows = Object.entries(institutionForm.column_mapping).map(([field, column]) => ({
        field,
        column
      }));

      // Parse transformations from config
      transformations = [];
      if (config.transformations) {
        // Look for custom transformations (not date/amount which are standard)
        for (const [key, value] of Object.entries(config.transformations)) {
          if (key !== 'date' && key !== 'amount' && typeof value === 'string') {
            // This is a custom transformation like combined_description
            transformations.push(parseTransformationString(key, value));
          }
        }
      }

      // Parse defaults from column_mapping.defaults
      defaults = [];
      if (config.column_mapping?.defaults || (config.columns && typeof config.columns === 'object' && config.columns.defaults)) {
        const defaultsObj = config.column_mapping?.defaults || config.columns?.defaults;
        defaults = Object.entries(defaultsObj).map(([field, value]) => ({ field, value }));
      }

      // Parse skip patterns from filtering.skip_if_contains
      skipPatterns = [];
      if (config.filtering?.skip_if_contains) {
        skipPatterns = [...config.filtering.skip_if_contains];
      }

      // Parse description cleanup from transformations.description
      stripWhitespace = false;
      removePatterns = [];
      if (config.transformations?.description) {
        const descConfig = config.transformations.description;
        stripWhitespace = descConfig.strip_whitespace || false;
        removePatterns = [...(descConfig.remove_patterns || [])];
      }

      showInstitutionForm = true;
      isEditingInstitution = true;
    } catch (err) {
      error = err.message;
    }
  }

  async function updateInstitution() {
    if (!selectedInstitution) return;

    try {
      // Build column_mapping from rows
      const column_mapping = {};
      columnMappingRows.forEach(({ field, column }) => {
        if (field && column) {
          column_mapping[field] = column;
        }
      });

      // Build transformations object
      const custom_transformations = {};
      transformations.forEach(transform => {
        if (transform.name && transform.name.trim()) {
          custom_transformations[transform.name.trim()] = buildTransformationString(transform);
        }
      });

      // Add description cleanup if configured
      if (stripWhitespace || removePatterns.length > 0) {
        const descConfig = {};
        if (stripWhitespace) {
          descConfig.strip_whitespace = true;
        }
        if (removePatterns.length > 0) {
          descConfig.remove_patterns = removePatterns.filter(p => p.trim());
        }
        custom_transformations.description = descConfig;
      }

      // Build defaults object
      const defaultsObj = {};
      defaults.forEach(({ field, value }) => {
        if (field && field.trim()) {
          defaultsObj[field.trim()] = value;
        }
      });

      const payload = {
        name: institutionForm.name,
        type: institutionForm.type,
        country: institutionForm.country,
        filename_patterns: institutionForm.filename_patterns,
        encoding: institutionForm.encoding,
        delimiter: institutionForm.delimiter,
        has_header: institutionForm.has_header,
        skip_rows: institutionForm.skip_rows,
        date_format: institutionForm.date_format,
        decimal_separator: institutionForm.decimal_separator,
        thousands_separator: institutionForm.thousands_separator,
        reverse_sign: institutionForm.reverse_sign,
        column_mapping,
        custom_transformations,
        defaults: defaultsObj,
        skip_patterns: skipPatterns,
        owner_mappings: institutionForm.owner_mappings,
        category_mappings: institutionForm.category_mappings
      };

      const response = await fetch(`/api/v1/settings/institutions/${selectedInstitution.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update institution');
      }

      saveSuccess = true;
      setTimeout(() => saveSuccess = false, 3000);
      showInstitutionForm = false;
      isEditingInstitution = false;
      await loadSettings();

      // Re-select the institution to refresh
      const updatedInstitution = institutions.find(i => i.id === selectedInstitution.id);
      if (updatedInstitution) {
        selectInstitution(updatedInstitution);
      }
    } catch (err) {
      error = err.message;
    }
  }

  async function deleteInstitution(institutionId) {
    if (!confirm(`Are you sure you want to delete this institution? This cannot be undone.`)) {
      return;
    }

    try {
      const response = await fetch(`/api/v1/settings/institutions/${institutionId}`, {
        method: 'DELETE'
      });

      if (!response.ok) throw new Error('Failed to delete institution');

      saveSuccess = true;
      setTimeout(() => saveSuccess = false, 3000);
      selectedInstitution = null;
      await loadSettings();
    } catch (err) {
      error = err.message;
    }
  }

  // Owners tab functions
  function selectOwner(owner) {
    selectedOwner = owner;
    showAddAccountForm = false;
  }

  function openAddAccountForm() {
    newAccount = { account: '', institution_id: institutions.length > 0 ? institutions[0].id : '' };
    showAddAccountForm = true;
  }

  async function addAccount() {
    try {
      const response = await fetch(`/api/v1/settings/owners/${encodeURIComponent(selectedOwner.name)}/accounts?account=${encodeURIComponent(newAccount.account)}&institution_id=${newAccount.institution_id}`, {
        method: 'POST'
      });

      if (!response.ok) throw new Error('Failed to add account');

      saveSuccess = true;
      setTimeout(() => saveSuccess = false, 3000);
      showAddAccountForm = false;
      await loadSettings();
      // Re-select owner to refresh
      const updatedOwner = owners.find(o => o.name === selectedOwner.name);
      if (updatedOwner) selectOwner(updatedOwner);
    } catch (err) {
      error = err.message;
    }
  }

  async function removeAccount(ownerName, account, institutionId) {
    if (!confirm(`Remove account ${account} from ${ownerName}?`)) return;

    try {
      const response = await fetch(`/api/v1/settings/owners/${encodeURIComponent(ownerName)}/accounts?account=${encodeURIComponent(account)}&institution_id=${institutionId}`, {
        method: 'DELETE'
      });

      if (!response.ok) throw new Error('Failed to remove account');

      saveSuccess = true;
      setTimeout(() => saveSuccess = false, 3000);
      await loadSettings();
      // Re-select owner to refresh
      const updatedOwner = owners.find(o => o.name === ownerName);
      if (updatedOwner) selectOwner(updatedOwner);
    } catch (err) {
      error = err.message;
    }
  }

</script>

<div class="settings">
  <h1>⚙️ Settings</h1>

  {#if loading}
    <p>Loading settings...</p>
  {:else if error}
    <div class="error">Error: {error}</div>
  {:else}
    <!-- Tabs -->
    <div class="tabs">
      <button
        class="tab"
        class:active={activeTab === 'app'}
        on:click={() => activeTab = 'app'}
      >
        Application
      </button>
      <button
        class="tab"
        class:active={activeTab === 'currency'}
        on:click={() => activeTab = 'currency'}
      >
        Currency
      </button>
      <button
        class="tab"
        class:active={activeTab === 'institutions'}
        on:click={() => activeTab = 'institutions'}
      >
        Institutions
      </button>
      <button
        class="tab"
        class:active={activeTab === 'accounts'}
        on:click={() => activeTab = 'accounts'}
      >
        Accounts
      </button>
    </div>

    <!-- Tab Content -->
    <div class="tab-content">
      {#if activeTab === 'app'}
        <div class="settings-section">
          <h2>Application Settings</h2>

          <h3>General Configuration</h3>

          <div class="form-group">
            <label>Timezone</label>
            <select bind:value={appSettings.processing.timezone}>
              <option value="Europe/Prague">Europe/Prague</option>
              <option value="Europe/London">Europe/London</option>
              <option value="America/New_York">America/New_York</option>
              <option value="UTC">UTC</option>
            </select>
          </div>

          <button class="btn btn-primary" on:click={saveAppSettings}>
            Save Application Settings
          </button>
        </div>

      {:else if activeTab === 'currency'}
        <div class="settings-section">
          <h2>Currency Settings</h2>

          <div class="form-group">
            <label>Base Currency</label>
            <select bind:value={currencySettings.base_currency}>
              <option value="CZK">CZK</option>
              <option value="EUR">EUR</option>
              <option value="USD">USD</option>
              <option value="GBP">GBP</option>
            </select>
          </div>

          <div class="form-group">
            <label class="checkbox-label">
              <input
                type="checkbox"
                bind:checked={currencySettings.use_cnb_api}
              />
              Use CNB API for real-time exchange rates
            </label>
            <p class="hint">When disabled, uses static rates below</p>
          </div>

          <h3>Exchange Rates (Fallback)</h3>
          <p class="hint">These rates are used when CNB API is disabled or fails</p>

          {#each Object.entries(currencySettings.rates) as [currency, rate]}
            <div class="form-group inline">
              <label>{currency}:</label>
              <input
                type="number"
                step="0.01"
                bind:value={currencySettings.rates[currency]}
                style="width: 150px;"
              />
            </div>
          {/each}

          <button class="btn btn-primary" on:click={saveAppSettings}>
            Save Currency Settings
          </button>
        </div>

      {:else if activeTab === 'institutions'}
        <div class="settings-section-wide">
          <div class="section-header">
            <h2>Institution Configurations</h2>
            <button class="btn btn-success" on:click={openNewInstitutionForm}>
              + New Institution
            </button>
          </div>

          <div class="institutions-layout">
            <div class="institution-list">
              <h3>Institutions ({institutions.length})</h3>
              {#each institutions as institution}
                <div
                  class="institution-item"
                  class:selected={selectedInstitution?.id === institution.id}
                  on:click={() => selectInstitution(institution)}
                >
                  <div class="institution-name">{institution.name}</div>
                  <div class="institution-meta">{institution.type} • {institution.country}</div>
                </div>
              {/each}
            </div>

            <div class="institution-details">
              {#if showInstitutionForm}
                <div class="institution-form">
                  <h3>{isEditingInstitution ? 'Edit Institution' : 'Create New Institution'}</h3>

                  <div class="form-group">
                    <label>Institution Name * <span class="help-icon" title="Unique name for this financial institution">ℹ️</span></label>
                    <input type="text" bind:value={institutionForm.name} placeholder="e.g., My Bank" />
                  </div>

                  <div class="form-row">
                    <div class="form-group">
                      <label>Type <span class="help-icon" title="Type of financial institution">ℹ️</span></label>
                      <select bind:value={institutionForm.type}>
                        <option value="bank">Bank</option>
                        <option value="payment_service">Payment Service</option>
                        <option value="investment">Investment</option>
                        <option value="other">Other</option>
                      </select>
                    </div>

                    <div class="form-group">
                      <label>Country Code <span class="help-icon" title="ISO 2-letter country code (e.g., CZ, US, GB)">ℹ️</span></label>
                      <input type="text" bind:value={institutionForm.country} placeholder="e.g., CZ" maxlength="2" />
                    </div>
                  </div>

                  <div class="form-group">
                    <label>Filename Patterns * <span class="help-icon" title="Patterns to automatically detect files from this institution. Use * as wildcard. Example: bank_export_*.csv will match bank_export_2024.csv">ℹ️</span></label>
                    <p class="hint">Pattern to detect files from this institution (supports * wildcard)</p>
                    {#each institutionForm.filename_patterns as pattern, index}
                      <div class="pattern-row">
                        <input type="text" bind:value={institutionForm.filename_patterns[index]} placeholder="e.g., bank_export_*.csv" />
                        {#if institutionForm.filename_patterns.length > 1}
                          <button class="btn-icon" on:click={() => removeFilenamePattern(index)}>✕</button>
                        {/if}
                      </div>
                    {/each}
                    <button class="btn btn-small" on:click={addFilenamePattern}>+ Add Pattern</button>
                  </div>

                  <!-- STEP 1: File Format -->
                  <div class="processing-step">
                    <h4><span class="step-badge">Step 1</span> File Format <span class="help-icon" title="Basic CSV file structure settings. Applied when reading the file.">ℹ️</span></h4>
                    <p class="step-hint">📄 Define how the parser should read your CSV/XLSX file</p>
                  </div>

                  <div class="form-row">
                    <div class="form-group">
                      <label>Encoding <span class="help-icon" title="Character encoding of the CSV file. Most banks use UTF-8 with BOM.">ℹ️</span></label>
                      <select bind:value={institutionForm.encoding}>
                        <option value="utf-8">UTF-8</option>
                        <option value="utf-8-sig">UTF-8 with BOM</option>
                        <option value="iso-8859-1">ISO-8859-1</option>
                        <option value="windows-1252">Windows-1252</option>
                      </select>
                    </div>

                    <div class="form-group">
                      <label>Delimiter <span class="help-icon" title="Character that separates columns in the CSV file">ℹ️</span></label>
                      <select bind:value={institutionForm.delimiter}>
                        <option value=";">Semicolon (;)</option>
                        <option value=",">Comma (,)</option>
                        <option value="\t">Tab</option>
                      </select>
                    </div>

                    <div class="form-group">
                      <label>Skip Rows <span class="help-icon" title="Number of rows to skip at the beginning of the file (before header)">ℹ️</span></label>
                      <input type="number" bind:value={institutionForm.skip_rows} min="0" />
                    </div>
                  </div>

                  <div class="form-group checkbox-group">
                    <label class="checkbox-label">
                      <input type="checkbox" bind:checked={institutionForm.has_header} />
                      File has header row <span class="help-icon" title="Check if the CSV file has a header row with column names">ℹ️</span>
                    </label>
                  </div>

                  <!-- STEP 2: Row Filtering -->
                  <div class="processing-step">
                    <h4><span class="step-badge">Step 2</span> Row Filtering (Optional) <span class="help-icon" title="Skip rows where ANY column contains these patterns. Applied immediately after reading, before any other processing.">ℹ️</span></h4>
                    <p class="step-hint">🔍 Filter out unwanted rows (headers, summaries, etc.) before processing</p>
                  </div>

                  <div class="form-group">
                    <p class="hint">Skip rows that contain specific text patterns in any column. Useful for removing bank headers or summary rows.</p>

                    {#if skipPatterns.length === 0}
                      <p class="no-skip-patterns">No filtering patterns configured. Example: "Pohyby na účtu" to skip account summary rows.</p>
                    {/if}

                    {#each skipPatterns as pattern, index}
                      <div class="pattern-row">
                        <input
                          type="text"
                          bind:value={skipPatterns[index]}
                          placeholder="Pattern to skip (e.g., 'Account Summary', 'Pohyby na účtu')"
                          class="skip-pattern-input"
                        />
                        <button class="btn-icon" on:click={() => removeSkipPattern(index)}>✕</button>
                      </div>
                    {/each}
                    <button class="btn btn-small" on:click={addSkipPattern}>+ Add Filter Pattern</button>
                  </div>

                  <!-- STEP 3: Field Transformations -->
                  <div class="processing-step">
                    <h4><span class="step-badge">Step 3</span> Field Transformations (Optional) <span class="help-icon" title="Combine multiple CSV columns into single fields before mapping. Applied in the parser.">ℹ️</span></h4>
                    <p class="step-hint">🔗 Concatenate CSV columns (e.g., combine account number + bank code)</p>
                  </div>

                  <div class="form-group">
                    <p class="hint">Build combined fields by joining multiple CSV columns. These can then be mapped to transaction fields in Step 4.</p>

                    {#if transformations.length === 0}
                      <p class="no-transformations">No transformations defined. Example: Combine "Account" + "/" + "Bank Code" into one field.</p>
                    {/if}

                    {#each transformations as transform, tIndex}
                      <div class="transformation-builder">
                        <div class="transformation-header">
                          <input
                            type="text"
                            bind:value={transform.name}
                            placeholder="Transformation name (e.g., combined_account)"
                            class="transformation-name"
                          />
                          <button class="btn-icon" on:click={() => removeTransformation(tIndex)}>✕</button>
                        </div>

                        <div class="transformation-parts">
                          {#each transform.parts as part, pIndex}
                            <div class="transformation-part">
                              <select bind:value={part.type} class="part-type">
                                <option value="column">CSV Column</option>
                                <option value="text">Fixed Text</option>
                              </select>
                              <input
                                type="text"
                                bind:value={part.value}
                                placeholder={part.type === 'column' ? 'Column name' : 'Text value'}
                                class="part-value"
                              />
                              {#if transform.parts.length > 1}
                                <button class="btn-icon-small" on:click={() => removeTransformationPart(tIndex, pIndex)}>✕</button>
                              {/if}
                            </div>
                            {#if pIndex < transform.parts.length - 1}
                              <span class="part-connector">+</span>
                            {/if}
                          {/each}
                        </div>

                        <button class="btn btn-small" on:click={() => addTransformationPart(tIndex)}>+ Add Part</button>

                        <div class="transformation-preview">
                          <strong>Result:</strong> <code>{buildTransformationString(transform)}</code>
                        </div>
                      </div>
                    {/each}

                    <button class="btn btn-small" on:click={addTransformation}>+ Add Transformation</button>
                  </div>

                  <!-- Field Reference Panel -->
                  <div class="field-reference-toggle">
                    <button class="btn btn-info btn-small" on:click={() => showFieldReference = !showFieldReference}>
                      {showFieldReference ? '▼' : '▶'} Transaction Field Reference
                    </button>
                  </div>

                  {#if showFieldReference}
                    <div class="field-reference-panel">
                      <h5>Available Transaction Fields</h5>
                      <p class="hint">Map CSV columns to these standardized fields. Fields marked with * are required.</p>
                      <div class="field-reference-list">
                        {#each TRANSACTION_FIELDS as field}
                          <div class="field-reference-item">
                            <span class="field-name">
                              {field.name}
                              {#if field.required}<span class="required">*</span>{/if}
                            </span>
                            <span class="field-description">{field.description}</span>
                          </div>
                        {/each}
                      </div>
                    </div>
                  {/if}

                  <!-- STEP 4: Column Mapping -->
                  <div class="processing-step">
                    <h4><span class="step-badge">Step 4</span> Column Mapping * <span class="help-icon" title="Map CSV columns (or transformations from Step 3) to standardized transaction fields.">ℹ️</span></h4>
                    <p class="step-hint">📋 Map your bank's columns to our standard transaction format</p>
                  </div>

                  <div class="form-group">
                    <p class="hint">Connect CSV columns to transaction fields. You can map regular columns or transformations created in Step 3.</p>
                    {#each columnMappingRows as mapping, index}
                      <div class="mapping-row">
                        <select bind:value={mapping.field} class="field-select">
                          <option value="">Select field...</option>
                          {#each TRANSACTION_FIELDS as field}
                            <option value={field.name}>
                              {field.name} {field.required ? '*' : ''} - {field.description}
                            </option>
                          {/each}
                        </select>
                        <span>→</span>
                        <input type="text" bind:value={mapping.column} placeholder="CSV column name or transformation" class="column-input" />
                        <button class="btn-icon" on:click={() => removeColumnMapping(index)}>✕</button>
                      </div>
                    {/each}
                    <button class="btn btn-small" on:click={addColumnMapping}>+ Add Mapping</button>
                  </div>

                  <!-- STEP 5: Field Defaults -->
                  <div class="processing-step">
                    <h4><span class="step-badge">Step 5</span> Field Defaults (Optional) <span class="help-icon" title="Set default values for fields if they're empty after column mapping. Special directive 'extract_from_filename' extracts account from filename.">ℹ️</span></h4>
                    <p class="step-hint">📌 Fill in missing fields or extract values from filename</p>
                  </div>

                  <div class="form-group">
                    <p class="hint">Set fallback values when fields are empty. Use special directive 'extract_from_filename' for Partners Bank-style account extraction.</p>

                    {#if defaults.length === 0}
                      <p class="no-defaults">No defaults configured. Example: Extract account from filename "vypis_1330299329_*.csv"</p>
                    {/if}

                    {#each defaults as def, index}
                      <div class="mapping-row">
                        <select bind:value={def.field} class="default-field-select">
                          <option value="">Select field...</option>
                          <option value="account">account</option>
                          <option value="account_bank_code">account_bank_code (appended to account)</option>
                          <option value="currency">currency</option>
                          <option value="owner">owner</option>
                        </select>
                        <span>→</span>
                        <input
                          type="text"
                          bind:value={def.value}
                          placeholder={def.field === 'account' ? "Value or 'extract_from_filename'" : def.field === 'account_bank_code' ? 'Bank code (e.g., 6363)' : 'Default value'}
                          class="default-value-input"
                        />
                        <button class="btn-icon" on:click={() => removeDefault(index)}>✕</button>
                      </div>
                    {/each}
                    <button class="btn btn-small" on:click={addDefault}>+ Add Default</button>
                  </div>

                  <!-- STEP 6: Amount & Date Parsing -->
                  <div class="processing-step">
                    <h4><span class="step-badge">Step 6</span> Amount & Date Parsing <span class="help-icon" title="How to parse amounts and dates from the CSV. Applied during normalization.">ℹ️</span></h4>
                    <p class="step-hint">📊 Define number and date formats used by your bank</p>
                  </div>
                  <div class="form-row">
                    <div class="form-group">
                      <label>Date Format <span class="help-icon" title="Python strftime format. Common: %d.%m.%Y (31.12.2024), %Y-%m-%d (2024-12-31), %d. %m. %Y (31. 12. 2024)">ℹ️</span></label>
                      <input type="text" bind:value={institutionForm.date_format} placeholder="%d.%m.%Y" />
                      <p class="hint">Python strftime format (e.g., %d.%m.%Y for 31.12.2024)</p>
                    </div>
                  </div>

                  <div class="form-row">
                    <div class="form-group">
                      <label>Decimal Separator <span class="help-icon" title="Character used for decimal point in amounts">ℹ️</span></label>
                      <select bind:value={institutionForm.decimal_separator}>
                        <option value=",">Comma (,) - e.g., 1000,50</option>
                        <option value=".">Dot (.) - e.g., 1000.50</option>
                      </select>
                    </div>

                    <div class="form-group">
                      <label>Thousands Separator <span class="help-icon" title="Character used to separate thousands in amounts">ℹ️</span></label>
                      <select bind:value={institutionForm.thousands_separator}>
                        <option value=" ">Space - e.g., 1 000,50</option>
                        <option value=",">Comma (,) - e.g., 1,000.50</option>
                        <option value=".">Dot (.) - e.g., 1.000,50</option>
                        <option value="">None - e.g., 1000.50</option>
                      </select>
                    </div>

                    <div class="form-group checkbox-group">
                      <label class="checkbox-label">
                        <input type="checkbox" bind:value={institutionForm.reverse_sign} />
                        Reverse sign <span class="help-icon" title="Check if bank shows expenses as positive and income as negative">ℹ️</span>
                      </label>
                    </div>
                  </div>

                  <!-- STEP 7: Description Cleanup -->
                  <div class="processing-step">
                    <h4><span class="step-badge">Step 7</span> Description Cleanup (Optional) <span class="help-icon" title="Clean up transaction descriptions after all other processing. Applied last in the normalizer to remove bank-specific prefixes and formatting.">ℹ️</span></h4>
                    <p class="step-hint">🧹 Remove unwanted text from descriptions (e.g., amount prefixes, location markers)</p>
                  </div>

                  <div class="form-group">
                    <p class="hint">Clean transaction descriptions by removing extra whitespace and unwanted patterns. Applied after all other transformations.</p>

                    <div class="form-group checkbox-group">
                      <label class="checkbox-label">
                        <input type="checkbox" bind:checked={stripWhitespace} />
                        Strip extra whitespace <span class="help-icon" title="Collapses multiple spaces, tabs, and newlines into single spaces">ℹ️</span>
                      </label>
                      <p class="hint">Converts "Payment    at   restaurant" → "Payment at restaurant"</p>
                    </div>

                    <h5>Remove Patterns (Regex)</h5>
                    <p class="hint">Use regular expressions to remove specific text patterns from descriptions.</p>

                    {#if removePatterns.length === 0}
                      <p class="no-remove-patterns">No removal patterns configured. Example regex: "^Částka: [\\d,.]+ CZK" removes amount prefix from ČSOB.</p>
                    {/if}

                    {#each removePatterns as pattern, index}
                      <div class="pattern-row">
                        <input
                          type="text"
                          bind:value={removePatterns[index]}
                          placeholder="Regex pattern (e.g., '^Částka: [\d,.]+ CZK ')"
                          class="remove-pattern-input"
                        />
                        <button class="btn-icon" on:click={() => removeRemovePattern(index)}>✕</button>
                      </div>
                    {/each}
                    <button class="btn btn-small" on:click={addRemovePattern}>+ Add Pattern</button>

                    {#if removePatterns.length > 0}
                      <div class="hint-advanced">
                        ⚠️ Advanced: Patterns use Python regex syntax. Test carefully before deploying.
                      </div>
                    {/if}
                  </div>

                  <div class="form-actions">
                    <button class="btn btn-primary" on:click={isEditingInstitution ? updateInstitution : createInstitution}>
                      {isEditingInstitution ? 'Update Institution' : 'Create Institution'}
                    </button>
                    <button class="btn btn-secondary" on:click={() => { showInstitutionForm = false; isEditingInstitution = false; }}>Cancel</button>
                  </div>
                </div>

              {:else if selectedInstitution}
                <div class="institution-header">
                  <h3>{selectedInstitution.name}</h3>
                  <div class="institution-actions">
                    <button class="btn btn-secondary" on:click={openEditInstitutionForm}>
                      ✏️ Edit
                    </button>
                    <button class="btn btn-danger" on:click={() => deleteInstitution(selectedInstitution.id)}>
                      Delete
                    </button>
                  </div>
                </div>

                <div class="institution-details-view">
                  <div class="detail-group">
                    <h4>Basic Information</h4>
                    <div class="detail-row">
                      <span class="detail-label">Name:</span>
                      <span class="detail-value">{selectedInstitution.name}</span>
                    </div>
                    <div class="detail-row">
                      <span class="detail-label">Type:</span>
                      <span class="detail-value">{selectedInstitution.type}</span>
                    </div>
                    <div class="detail-row">
                      <span class="detail-label">Country:</span>
                      <span class="detail-value">{selectedInstitution.country}</span>
                    </div>
                    <div class="detail-row">
                      <span class="detail-label">Filename Patterns:</span>
                      <span class="detail-value">{selectedInstitution.filename_patterns?.join(', ') || 'None'}</span>
                    </div>
                  </div>

                  <div class="detail-group">
                    <h4>File Format</h4>
                    <div class="detail-row">
                      <span class="detail-label">Encoding:</span>
                      <span class="detail-value">{selectedInstitution.encoding}</span>
                    </div>
                    <div class="detail-row">
                      <span class="detail-label">Delimiter:</span>
                      <span class="detail-value">{selectedInstitution.delimiter === ';' ? 'Semicolon (;)' : selectedInstitution.delimiter === ',' ? 'Comma (,)' : 'Tab'}</span>
                    </div>
                    <div class="detail-row">
                      <span class="detail-label">Skip Rows:</span>
                      <span class="detail-value">{selectedInstitution.skip_rows || 0}</span>
                    </div>
                    <div class="detail-row">
                      <span class="detail-label">Has Header:</span>
                      <span class="detail-value">{selectedInstitution.has_header ? 'Yes' : 'No'}</span>
                    </div>
                  </div>

                  <div class="detail-group">
                    <h4>Data Transformations</h4>
                    <div class="detail-row">
                      <span class="detail-label">Date Format:</span>
                      <span class="detail-value">{selectedInstitution.date_format || 'Not set'}</span>
                    </div>
                    <div class="detail-row">
                      <span class="detail-label">Decimal Separator:</span>
                      <span class="detail-value">{selectedInstitution.decimal_separator || '.'}</span>
                    </div>
                    <div class="detail-row">
                      <span class="detail-label">Thousands Separator:</span>
                      <span class="detail-value">{selectedInstitution.thousands_separator || 'None'}</span>
                    </div>
                  </div>

                  <div class="detail-group">
                    <h4>Column Mappings</h4>
                    {#if selectedInstitution.column_mapping && Object.keys(selectedInstitution.column_mapping).length > 0}
                      <div class="mappings-grid">
                        {#each Object.entries(selectedInstitution.column_mapping) as [field, column]}
                          <div class="mapping-item">
                            <span class="mapping-field">{field}:</span>
                            <span class="mapping-column">{column}</span>
                          </div>
                        {/each}
                      </div>
                    {:else}
                      <p class="no-data">No column mappings defined</p>
                    {/if}
                  </div>
                </div>
              {:else}
                <p class="placeholder">Select an institution or create a new one</p>
              {/if}
            </div>
          </div>
        </div>

      {:else if activeTab === 'accounts'}
        <div class="settings-section">
          <div class="section-header">
            <h2>Account Descriptions</h2>
            <button class="btn btn-primary" on:click={openAddAccountModal}>
              + Add Account
            </button>
          </div>
          <p class="hint">Manage account numbers and their descriptions. Institution is determined during file upload.</p>

          {#if Object.keys(accounts).length === 0}
            <p class="no-accounts">No accounts configured. Add your first account!</p>
          {:else}
            <table class="accounts-table">
              <thead>
                <tr>
                  <th>Account Number</th>
                  <th>Description</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {#each Object.entries(accounts).sort() as [accountNumber, accountConfig]}
                  <tr>
                    <td class="account-number">{accountNumber}</td>
                    <td>{accountConfig.description}</td>
                    <td>
                      <button
                        class="btn-icon"
                        on:click={() => openEditAccountModal(accountNumber)}
                        title="Edit"
                      >
                        ✎
                      </button>
                      <button
                        class="btn-icon btn-danger"
                        on:click={() => deleteAccount(accountNumber)}
                        title="Delete"
                      >
                        🗑
                      </button>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          {/if}
        </div>

      {/if}
    </div>

    {#if saveSuccess}
      <div class="success-message">
        ✓ Settings saved successfully!
      </div>
    {/if}
  {/if}
</div>

<!-- Add/Edit Account Modal -->
{#if showAddAccountModal}
  <div class="modal-backdrop"
    on:mousedown={() => accountModalBackdropMouseDown = true}
    on:mouseup={() => {
      if (accountModalBackdropMouseDown) {
        closeAccountModal();
      }
      accountModalBackdropMouseDown = false;
    }}>
    <div class="modal" on:click|stopPropagation on:mousedown|stopPropagation on:mouseup|stopPropagation>
      <div class="modal-header">
        <h2>{editingAccount ? 'Edit Account' : 'Add New Account'}</h2>
        <button class="close-btn" on:click={closeAccountModal}>×</button>
      </div>

      <div class="modal-body">
        <div class="form-group">
          <label for="account-number">Account Number *</label>
          <input
            id="account-number"
            type="text"
            bind:value={accountForm.account_number}
            placeholder="e.g., 210621040/0300"
            disabled={!!editingAccount}
          />
          <p class="hint">Include bank code (e.g., /0300 for ČSOB, /6363 for Partners)</p>
        </div>

        <div class="form-group">
          <label for="account-description">Description *</label>
          <input
            id="account-description"
            type="text"
            bind:value={accountForm.description}
            placeholder="e.g., ČSOB Main Account"
          />
        </div>

        {#if error}
          <div class="error-message">{error}</div>
        {/if}
      </div>

      <div class="modal-footer">
        <button class="btn btn-secondary" on:click={closeAccountModal}>Cancel</button>
        <button class="btn btn-primary" on:click={saveAccount}>
          {editingAccount ? 'Update' : 'Add'}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .settings {
    max-width: 1400px;
    padding: 20px;
  }

  h1 {
    margin-bottom: 30px;
    color: #2c3e50;
  }

  h2 {
    color: #2c3e50;
    margin-bottom: 20px;
  }

  h3 {
    color: #495057;
    margin-bottom: 15px;
    font-size: 1.1rem;
  }

  h4 {
    color: #495057;
    margin-top: 20px;
    margin-bottom: 12px;
    font-size: 1rem;
    font-weight: 600;
  }

  /* Tabs */
  .tabs {
    display: flex;
    gap: 4px;
    border-bottom: 2px solid #e0e0e0;
    margin-bottom: 30px;
  }

  .tab {
    padding: 12px 24px;
    background: none;
    border: none;
    border-bottom: 3px solid transparent;
    cursor: pointer;
    font-size: 1rem;
    color: #666;
    transition: all 0.2s;
  }

  .tab:hover {
    color: #2c3e50;
    background: #f8f9fa;
  }

  .tab.active {
    color: #007bff;
    border-bottom-color: #007bff;
    font-weight: 600;
  }

  /* Tab Content */
  .tab-content {
    background: white;
    border-radius: 8px;
    padding: 30px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  }

  .settings-section {
    max-width: 700px;
  }

  .settings-section-wide {
    max-width: 100%;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }

  /* Form Elements */
  .form-group {
    margin-bottom: 20px;
  }

  .form-group.inline {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .form-group label {
    display: block;
    margin-bottom: 8px;
    font-weight: 600;
    color: #495057;
  }

  .checkbox-label {
    display: flex !important;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    font-weight: normal !important;
  }

  .checkbox-group {
    margin-top: 15px;
  }

  .form-group input[type="text"],
  .form-group input[type="number"],
  .form-group select {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
  }

  .form-group input:focus,
  .form-group select:focus {
    outline: none;
    border-color: #007bff;
  }

  .form-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
  }

  .hint {
    margin-top: 6px;
    font-size: 0.85rem;
    color: #999;
  }

  .pattern-row,
  .mapping-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
  }

  .pattern-row input,
  .mapping-row input,
  .mapping-row select {
    flex: 1;
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.95rem;
  }

  /* Buttons */
  .btn {
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1rem;
    transition: background-color 0.2s;
  }

  .btn-primary {
    background: #007bff;
    color: white;
  }

  .btn-primary:hover {
    background: #0056b3;
  }

  .btn-secondary {
    background: #6c757d;
    color: white;
  }

  .btn-secondary:hover {
    background: #5a6268;
  }

  .btn-success {
    background: #28a745;
    color: white;
  }

  .btn-success:hover {
    background: #218838;
  }

  .btn-danger {
    background: #dc3545;
    color: white;
  }

  .btn-danger:hover {
    background: #c82333;
  }

  .btn-small {
    padding: 8px 16px;
    font-size: 0.9rem;
    background: #6c757d;
    color: white;
  }

  .btn-small:hover {
    background: #5a6268;
  }

  .btn-icon {
    padding: 6px 10px;
    background: #dc3545;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
  }

  .btn-icon:hover {
    background: #c82333;
  }

  .btn-icon-small {
    padding: 4px 8px;
    background: #dc3545;
    color: white;
    border: none;
    border-radius: 3px;
    cursor: pointer;
    font-size: 0.8rem;
  }

  .btn-icon-small:hover {
    background: #c82333;
  }

  .form-actions {
    display: flex;
    gap: 10px;
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid #e0e0e0;
  }

  /* Institutions Layout */
  .institutions-layout {
    display: grid;
    grid-template-columns: 300px 1fr;
    gap: 30px;
    margin-top: 20px;
  }

  .institution-list {
    border-right: 1px solid #e0e0e0;
    padding-right: 20px;
    max-height: 600px;
    overflow-y: auto;
  }

  .institution-item {
    padding: 12px;
    border-radius: 6px;
    cursor: pointer;
    transition: background-color 0.2s;
    margin-bottom: 8px;
  }

  .institution-item:hover {
    background: #f8f9fa;
  }

  .institution-item.selected {
    background: #e7f3ff;
    border-left: 3px solid #007bff;
  }

  .institution-name {
    font-weight: 600;
    color: #2c3e50;
    margin-bottom: 4px;
  }

  .institution-meta {
    font-size: 0.85rem;
    color: #999;
  }

  .institution-details {
    padding-left: 20px;
    max-height: 600px;
    overflow-y: auto;
  }

  .institution-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 2px solid #e0e0e0;
  }

  .institution-header h3 {
    margin: 0;
  }

  .institution-form {
    max-width: 700px;
  }

  .placeholder {
    color: #999;
    font-style: italic;
    padding: 40px;
    text-align: center;
  }

  /* Owner Mappings */
  .owner-mappings {
    margin-bottom: 20px;
  }

  .account-input {
    flex: 1;
  }

  .owner-input {
    flex: 1;
  }

  /* Owners Layout */
  .owners-layout {
    display: grid;
    grid-template-columns: 300px 1fr;
    gap: 30px;
    margin-top: 20px;
  }

  .owners-list {
    border-right: 1px solid #e0e0e0;
    padding-right: 20px;
    max-height: 600px;
    overflow-y: auto;
  }

  .owner-item {
    padding: 12px;
    border-radius: 6px;
    cursor: pointer;
    transition: background-color 0.2s;
    margin-bottom: 8px;
  }

  .owner-item:hover {
    background: #f8f9fa;
  }

  .owner-item.selected {
    background: #e7f3ff;
    border-left: 3px solid #007bff;
  }

  .owner-name {
    font-weight: 600;
    color: #2c3e50;
    margin-bottom: 4px;
  }

  .owner-meta {
    font-size: 0.85rem;
    color: #999;
  }

  .owner-details {
    padding-left: 20px;
  }

  .accounts-list {
    margin-bottom: 20px;
  }

  .no-accounts {
    color: #999;
    font-style: italic;
    padding: 20px;
    text-align: center;
    background: #f8f9fa;
    border-radius: 6px;
  }

  .accounts-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 20px;
  }

  .accounts-table th {
    background: #f8f9fa;
    padding: 12px;
    text-align: left;
    font-weight: 600;
    color: #495057;
    border-bottom: 2px solid #e0e0e0;
  }

  .accounts-table td {
    padding: 12px;
    border-bottom: 1px solid #f0f0f0;
  }

  .accounts-table tr:hover {
    background: #f8f9fa;
  }

  .account-number {
    font-family: 'Courier New', monospace;
    font-weight: 600;
  }

  .add-account-form {
    background: #f8f9fa;
    padding: 20px;
    border-radius: 6px;
    margin-top: 20px;
  }

  /* Success Message */
  .success-message {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: #28a745;
    color: white;
    padding: 15px 25px;
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    animation: slideIn 0.3s ease-out;
    z-index: 1000;
  }

  @keyframes slideIn {
    from {
      transform: translateY(100px);
      opacity: 0;
    }
    to {
      transform: translateY(0);
      opacity: 1;
    }
  }

  .error {
    color: #dc3545;
    padding: 15px;
    background: #ffe6e6;
    border-radius: 6px;
    margin-bottom: 20px;
  }

  /* Help Icons */
  .help-icon {
    cursor: help;
    color: #007bff;
    font-size: 0.9rem;
    margin-left: 5px;
  }

  /* Field Reference Panel */
  .field-reference-toggle {
    margin: 20px 0 10px 0;
  }

  .btn-info {
    background: #17a2b8;
    color: white;
  }

  .btn-info:hover {
    background: #138496;
  }

  .field-reference-panel {
    background: #f0f8ff;
    border: 1px solid #b8daff;
    border-radius: 6px;
    padding: 20px;
    margin-bottom: 20px;
  }

  .field-reference-panel h5 {
    margin-top: 0;
    color: #004085;
  }

  .field-reference-list {
    display: grid;
    gap: 8px;
  }

  .field-reference-item {
    display: grid;
    grid-template-columns: 200px 1fr;
    gap: 15px;
    padding: 8px;
    background: white;
    border-radius: 4px;
  }

  .field-name {
    font-weight: 600;
    color: #2c3e50;
    font-family: 'Courier New', monospace;
  }

  .field-name .required {
    color: #dc3545;
    margin-left: 3px;
  }

  .field-description {
    color: #666;
    font-size: 0.9rem;
  }

  /* Column Mapping Improvements */
  .field-select {
    min-width: 300px;
  }

  .column-input {
    flex: 1;
    min-width: 200px;
  }

  .hint-advanced {
    margin-top: 10px;
    padding: 10px;
    background: #fff3cd;
    border-left: 3px solid #ffc107;
    font-size: 0.9rem;
    color: #856404;
  }

  /* Transformation Builder */
  .no-transformations {
    padding: 20px;
    background: #f8f9fa;
    border-radius: 6px;
    color: #666;
    font-style: italic;
    text-align: center;
    margin-bottom: 15px;
  }

  .transformation-builder {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 15px;
    margin-bottom: 15px;
  }

  .transformation-header {
    display: flex;
    gap: 10px;
    margin-bottom: 15px;
  }

  .transformation-name {
    flex: 1;
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-weight: 600;
  }

  .transformation-parts {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
  }

  .transformation-part {
    display: flex;
    gap: 8px;
    align-items: center;
    background: white;
    padding: 8px;
    border-radius: 4px;
    border: 1px solid #ddd;
  }

  .part-type {
    padding: 6px 10px;
    border: 1px solid #ddd;
    border-radius: 3px;
    font-size: 0.85rem;
  }

  .part-value {
    padding: 6px 10px;
    border: 1px solid #ddd;
    border-radius: 3px;
    min-width: 150px;
  }

  .part-connector {
    font-weight: bold;
    color: #007bff;
    font-size: 1.2rem;
  }

  .transformation-preview {
    margin-top: 10px;
    padding: 10px;
    background: #e7f3ff;
    border-left: 3px solid #007bff;
    border-radius: 4px;
  }

  .transformation-preview code {
    background: white;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Courier New', monospace;
    color: #d63384;
  }

  /* Defaults Section */
  .no-defaults {
    padding: 20px;
    background: #f8f9fa;
    border-radius: 6px;
    color: #666;
    font-style: italic;
    text-align: center;
    margin-bottom: 15px;
  }

  .default-field-select {
    min-width: 250px;
  }

  .default-value-input {
    flex: 1;
    min-width: 200px;
  }

  /* Filtering Section */
  .no-skip-patterns {
    padding: 20px;
    background: #f8f9fa;
    border-radius: 6px;
    color: #666;
    font-style: italic;
    text-align: center;
    margin-bottom: 15px;
  }

  .skip-pattern-input {
    flex: 1;
  }

  .remove-pattern-input {
    flex: 1;
    font-family: 'Courier New', monospace;
    font-size: 0.9rem;
  }

  .no-remove-patterns {
    padding: 20px;
    background: #f8f9fa;
    border-radius: 6px;
    color: #666;
    font-style: italic;
    text-align: center;
    margin-bottom: 15px;
  }

  /* Processing Steps */
  .processing-step {
    margin-top: 35px;
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 2px solid #e7f3ff;
  }

  .processing-step h4 {
    margin: 0;
    color: #2c3e50;
    font-size: 1.15rem;
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .step-badge {
    display: inline-block;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    letter-spacing: 0.5px;
  }

  .step-hint {
    color: #666;
    font-size: 0.95rem;
    margin: 8px 0 0 0;
    font-style: italic;
  }

  /* Export Tab Styles */
  .export-controls {
    background: #f8f9fa;
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 30px;
  }

  .export-controls h3 {
    margin-top: 0;
    color: #2c3e50;
  }

  .export-controls .btn-primary {
    margin-top: 20px;
  }

  .export-controls .btn-primary:disabled {
    background: #6c757d;
    cursor: not-allowed;
  }

  .export-status {
    margin-bottom: 30px;
  }

  .status-card {
    background: white;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    padding: 20px;
    margin-top: 15px;
  }

  .status-card.status-completed {
    border-color: #28a745;
    background: #f0fff4;
  }

  .status-card.status-failed {
    border-color: #dc3545;
    background: #fff5f5;
  }

  .status-card.status-processing {
    border-color: #007bff;
    background: #f0f8ff;
  }

  .status-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 15px;
    padding-bottom: 15px;
    border-bottom: 1px solid #e0e0e0;
  }

  .status-badge {
    display: inline-block;
    padding: 6px 16px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    color: white;
    background: #6c757d;
  }

  .status-card.status-completed .status-badge {
    background: #28a745;
  }

  .status-card.status-failed .status-badge {
    background: #dc3545;
  }

  .status-card.status-processing .status-badge {
    background: #007bff;
  }

  .status-id {
    font-size: 0.85rem;
    color: #999;
    font-family: 'Courier New', monospace;
  }

  .status-message {
    padding: 15px;
    border-radius: 6px;
    margin-bottom: 15px;
    font-size: 0.95rem;
  }

  .status-message.success {
    background: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
  }

  .status-message.error {
    background: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
  }

  .status-message.processing,
  .status-message.pending {
    background: #d1ecf1;
    color: #0c5460;
    border: 1px solid #bee5eb;
  }

  .status-details {
    display: flex;
    gap: 20px;
    font-size: 0.85rem;
    color: #666;
  }

  .export-history {
    margin-top: 30px;
  }

  .export-jobs-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 15px;
    background: white;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  }

  .export-jobs-table th {
    background: #f8f9fa;
    padding: 12px 15px;
    text-align: left;
    font-weight: 600;
    color: #495057;
    border-bottom: 2px solid #e0e0e0;
  }

  .export-jobs-table td {
    padding: 12px 15px;
    border-bottom: 1px solid #f0f0f0;
  }

  .export-jobs-table tr:hover {
    background: #f8f9fa;
  }

  .export-jobs-table tr:last-child td {
    border-bottom: none;
  }

  .job-id {
    font-family: 'Courier New', monospace;
    font-size: 0.9rem;
    color: #666;
  }

  .status-badge-small {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    color: white;
    background: #6c757d;
  }

  .status-badge-small.status-completed {
    background: #28a745;
  }

  .status-badge-small.status-failed {
    background: #dc3545;
  }

  .status-badge-small.status-processing {
    background: #007bff;
  }
</style>
