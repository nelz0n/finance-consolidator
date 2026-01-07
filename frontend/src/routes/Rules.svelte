<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api.js';

  let rules = [];
  let categoryTree = [];
  let loading = true;
  let error = null;
  let success = null;

  // Modal state
  let showRuleModal = false;
  let editingRule = null;
  let ruleForm = createEmptyRule();

  // Track mousedown on modal backdrop to prevent closing when selecting text
  let ruleModalBackdropMouseDown = false;

  // Filter state
  let filterText = '';

  onMount(async () => {
    await Promise.all([loadRules(), loadCategories()]);
  });

  function createEmptyRule() {
    return {
      priority: 100,
      description_contains: '',
      institution_exact: '',
      counterparty_account_exact: '',
      counterparty_name_contains: '',
      variable_symbol_exact: '',
      type_contains: '',
      amount_czk_min: null,
      amount_czk_max: null,
      tier1: '',
      tier2: '',
      tier3: ''
    };
  }

  async function loadRules() {
    try {
      loading = true;
      error = null;
      const response = await api.get('/rules');
      console.log('Rules API response:', response);
      console.log('Rules data:', response.data);
      console.log('Rules count:', response.data?.length);
      rules = response.data;
    } catch (err) {
      console.error('Error loading rules:', err);
      error = `Failed to load rules: ${err.message}`;
    } finally {
      loading = false;
    }
  }

  async function loadCategories() {
    try {
      const response = await api.get('/categories/tree');
      categoryTree = response.data;
      console.log('Category tree loaded:', categoryTree);
      console.log('Total tier1 categories:', categoryTree.length);
    } catch (err) {
      console.error('Failed to load categories:', err);
    }
  }

  function openAddModal() {
    editingRule = null;
    ruleForm = createEmptyRule();
    showRuleModal = true;
  }

  function openEditModal(rule) {
    editingRule = rule;
    ruleForm = { ...rule };
    showRuleModal = true;
  }

  function closeModal() {
    showRuleModal = false;
    editingRule = null;
    ruleForm = createEmptyRule();
    error = null;
  }

  async function saveRule() {
    try {
      error = null;
      success = null;

      // Validation
      if (!ruleForm.tier1 || !ruleForm.tier2 || !ruleForm.tier3) {
        error = 'Please select all category tiers';
        return;
      }

      if (editingRule) {
        // Update existing rule
        await api.put(`/rules/${editingRule.id}`, ruleForm);
        success = 'Rule updated successfully';
      } else {
        // Create new rule
        await api.post('/rules', ruleForm);
        success = 'Rule created successfully';
      }

      closeModal();
      await loadRules();
    } catch (err) {
      error = err.response?.data?.detail || err.message;
    }
  }

  async function deleteRule(ruleId) {
    if (!confirm('Delete this rule?')) return;

    try {
      error = null;
      success = null;
      await api.delete(`/rules/${ruleId}`);
      success = 'Rule deleted successfully';
      await loadRules();
    } catch (err) {
      error = err.response?.data?.detail || err.message;
    }
  }

  // Make tier2 and tier3 options reactive
  $: tier2Options = (() => {
    console.log('Computing tier2Options, tier1:', ruleForm.tier1);
    if (!ruleForm.tier1) return [];
    const tier1Cat = categoryTree.find(cat => cat.tier1 === ruleForm.tier1);
    console.log('Found tier1Cat:', tier1Cat);
    const options = tier1Cat ? tier1Cat.tier2_categories : [];
    console.log('Tier2 options:', options);
    return options;
  })();

  $: tier3Options = (() => {
    console.log('Computing tier3Options, tier1:', ruleForm.tier1, 'tier2:', ruleForm.tier2);
    if (!ruleForm.tier1 || !ruleForm.tier2) return [];
    const tier1Cat = categoryTree.find(cat => cat.tier1 === ruleForm.tier1);
    if (!tier1Cat) return [];
    const tier2Cat = tier1Cat.tier2_categories.find(cat => cat.tier2 === ruleForm.tier2);
    console.log('Found tier2Cat:', tier2Cat);
    const options = tier2Cat ? tier2Cat.tier3 : [];
    console.log('Tier3 options:', options);
    return options;
  })();

  function onTier1Change() {
    ruleForm.tier2 = '';
    ruleForm.tier3 = '';
  }

  function onTier2Change() {
    ruleForm.tier3 = '';
  }

  function getFilteredRules() {
    if (!filterText) return rules;

    const filter = filterText.toLowerCase();
    return rules.filter(rule => {
      return (
        rule.description_contains?.toLowerCase().includes(filter) ||
        rule.institution_exact?.toLowerCase().includes(filter) ||
        rule.counterparty_name_contains?.toLowerCase().includes(filter) ||
        rule.tier1?.toLowerCase().includes(filter) ||
        rule.tier2?.toLowerCase().includes(filter) ||
        rule.tier3?.toLowerCase().includes(filter)
      );
    });
  }

  function getRuleConditions(rule) {
    const conditions = [];

    if (rule.description_contains) {
      conditions.push(`Description contains "${rule.description_contains}"`);
    }
    if (rule.institution_exact) {
      conditions.push(`Institution = "${rule.institution_exact}"`);
    }
    if (rule.counterparty_account_exact) {
      conditions.push(`Account = "${rule.counterparty_account_exact}"`);
    }
    if (rule.counterparty_name_contains) {
      conditions.push(`Name contains "${rule.counterparty_name_contains}"`);
    }
    if (rule.variable_symbol_exact) {
      conditions.push(`VS = "${rule.variable_symbol_exact}"`);
    }
    if (rule.type_contains) {
      conditions.push(`Type contains "${rule.type_contains}"`);
    }
    if (rule.amount_czk_min !== null || rule.amount_czk_max !== null) {
      if (rule.amount_czk_min !== null && rule.amount_czk_max !== null) {
        conditions.push(`Amount: ${rule.amount_czk_min} - ${rule.amount_czk_max} CZK`);
      } else if (rule.amount_czk_min !== null) {
        conditions.push(`Amount >= ${rule.amount_czk_min} CZK`);
      } else {
        conditions.push(`Amount <= ${rule.amount_czk_max} CZK`);
      }
    }

    return conditions.length > 0 ? conditions.join(' AND ') : 'No conditions';
  }

  // Make reactive statement depend on rules and filterText explicitly
  $: filteredRules = (() => {
    if (!filterText) return rules;
    const filter = filterText.toLowerCase();
    return rules.filter(rule => {
      return (
        rule.description_contains?.toLowerCase().includes(filter) ||
        rule.institution_exact?.toLowerCase().includes(filter) ||
        rule.counterparty_name_contains?.toLowerCase().includes(filter) ||
        rule.tier1?.toLowerCase().includes(filter) ||
        rule.tier2?.toLowerCase().includes(filter) ||
        rule.tier3?.toLowerCase().includes(filter)
      );
    });
  })();
</script>

<div class="rules-container">
  <div class="header">
    <h1>Categorization Rules</h1>
    <button class="btn btn-primary" on:click={openAddModal}>
      + Add Rule
    </button>
  </div>

  {#if error}
    <div class="alert alert-error">{error}</div>
  {/if}

  {#if success}
    <div class="alert alert-success">{success}</div>
  {/if}

  <div class="filter-section">
    <input
      type="text"
      class="filter-input"
      placeholder="🔍 Filter rules..."
      bind:value={filterText}
    />
    <span class="result-count">{filteredRules.length} rules</span>
  </div>

  {#if loading}
    <div class="loading">Loading rules...</div>
  {:else}
    <div class="rules-table-container">
      <table class="rules-table">
        <thead>
          <tr>
            <th>Priority</th>
            <th>Conditions</th>
            <th>Category</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {#each filteredRules as rule}
            <tr class="rule-row">
              <td>
                <span class="priority-badge">
                  {rule.priority}
                </span>
              </td>
              <td class="conditions-cell">
                <div class="conditions-text">{getRuleConditions(rule)}</div>
              </td>
              <td>
                <div class="category-path">
                  <span class="tier1">{rule.tier1}</span>
                  <span class="separator">→</span>
                  <span class="tier2">{rule.tier2}</span>
                  <span class="separator">→</span>
                  <span class="tier3">{rule.tier3}</span>
                </div>
              </td>
              <td>
                <div class="action-buttons">
                  <button
                    class="btn-icon"
                    on:click={() => openEditModal(rule)}
                    title="Edit"
                  >
                    ✎
                  </button>
                  <button
                    class="btn-icon btn-danger"
                    on:click={() => deleteRule(rule.id)}
                    title="Delete"
                  >
                    🗑
                  </button>
                </div>
              </td>
            </tr>
          {/each}

          {#if filteredRules.length === 0}
            <tr>
              <td colspan="4" class="no-rules">
                No rules found. {filterText ? 'Try a different filter.' : 'Add your first rule!'}
              </td>
            </tr>
          {/if}
        </tbody>
      </table>
    </div>
  {/if}
</div>

<!-- Add/Edit Rule Modal -->
{#if showRuleModal}
  <div class="modal-backdrop"
    on:mousedown={() => ruleModalBackdropMouseDown = true}
    on:mouseup={() => {
      if (ruleModalBackdropMouseDown) {
        closeModal();
      }
      ruleModalBackdropMouseDown = false;
    }}>
    <div class="modal modal-large" on:click|stopPropagation on:mousedown|stopPropagation on:mouseup|stopPropagation>
      <div class="modal-header">
        <h2>{editingRule ? 'Edit Rule' : 'Add New Rule'}</h2>
        <button class="close-btn" on:click={closeModal}>×</button>
      </div>

      <div class="modal-body">
        <div class="form-row">
          <div class="form-group">
            <label for="priority">Priority (higher = checked first)</label>
            <input
              id="priority"
              type="number"
              bind:value={ruleForm.priority}
              min="0"
              max="1000"
            />
          </div>
        </div>

        <h3>Conditions (all must match)</h3>
        <div class="form-row">
          <div class="form-group">
            <label for="desc">Description contains</label>
            <input
              id="desc"
              type="text"
              bind:value={ruleForm.description_contains}
              placeholder="e.g., NETFLIX, Spotify"
            />
          </div>

          <div class="form-group">
            <label for="inst">Institution (exact)</label>
            <input
              id="inst"
              type="text"
              bind:value={ruleForm.institution_exact}
              placeholder="e.g., ČSOB, Wise"
            />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="cp-name">Counterparty name contains</label>
            <input
              id="cp-name"
              type="text"
              bind:value={ruleForm.counterparty_name_contains}
              placeholder="e.g., Google, Amazon"
            />
          </div>

          <div class="form-group">
            <label for="cp-account">Counterparty account (exact)</label>
            <input
              id="cp-account"
              type="text"
              bind:value={ruleForm.counterparty_account_exact}
              placeholder="e.g., 123456789/0300"
            />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="vs">Variable symbol (exact)</label>
            <input
              id="vs"
              type="text"
              bind:value={ruleForm.variable_symbol_exact}
              placeholder="e.g., 12345"
            />
          </div>

          <div class="form-group">
            <label for="type">Type contains</label>
            <input
              id="type"
              type="text"
              bind:value={ruleForm.type_contains}
              placeholder="e.g., Úroky, Převod"
            />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="amt-min">Amount min (CZK)</label>
            <input
              id="amt-min"
              type="number"
              bind:value={ruleForm.amount_czk_min}
              placeholder="e.g., 0"
              step="0.01"
            />
          </div>

          <div class="form-group">
            <label for="amt-max">Amount max (CZK)</label>
            <input
              id="amt-max"
              type="number"
              bind:value={ruleForm.amount_czk_max}
              placeholder="e.g., 1000"
              step="0.01"
            />
          </div>
        </div>

        <h3>Category Assignment</h3>
        <div class="form-row">
          <div class="form-group">
            <label for="tier1">Tier1 *</label>
            <select
              id="tier1"
              bind:value={ruleForm.tier1}
              on:change={onTier1Change}
              required
            >
              <option value="">Select Tier1...</option>
              {#each categoryTree as tier1Cat}
                <option value={tier1Cat.tier1}>{tier1Cat.tier1}</option>
              {/each}
            </select>
          </div>

          <div class="form-group">
            <label for="tier2">Tier2 *</label>
            <select
              id="tier2"
              bind:value={ruleForm.tier2}
              on:change={onTier2Change}
              required
              disabled={!ruleForm.tier1}
            >
              <option value="">Select Tier2...</option>
              {#each tier2Options as tier2Cat}
                <option value={tier2Cat.tier2}>{tier2Cat.tier2}</option>
              {/each}
            </select>
          </div>

          <div class="form-group">
            <label for="tier3">Tier3 *</label>
            <select
              id="tier3"
              bind:value={ruleForm.tier3}
              required
              disabled={!ruleForm.tier2}
            >
              <option value="">Select Tier3...</option>
              {#each tier3Options as tier3Name}
                <option value={tier3Name}>{tier3Name}</option>
              {/each}
            </select>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn btn-secondary" on:click={closeModal}>Cancel</button>
        <button class="btn btn-primary" on:click={saveRule}>
          {editingRule ? 'Update Rule' : 'Create Rule'}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .rules-container {
    padding: 2rem;
    max-width: 1400px;
    margin: 0 auto;
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
  }

  h1 {
    font-size: 2rem;
    margin: 0;
    color: #333;
  }

  h3 {
    margin-top: 1.5rem;
    margin-bottom: 1rem;
    color: #555;
    font-size: 1.1rem;
    border-bottom: 2px solid #e0e0e0;
    padding-bottom: 0.5rem;
  }

  .loading {
    text-align: center;
    padding: 3rem;
    color: #666;
  }

  .alert {
    padding: 1rem;
    border-radius: 4px;
    margin-bottom: 1rem;
  }

  .alert-error {
    background-color: #fee;
    color: #c33;
    border: 1px solid #fcc;
  }

  .alert-success {
    background-color: #efe;
    color: #3a3;
    border: 1px solid #cfc;
  }

  .filter-section {
    display: flex;
    gap: 1rem;
    align-items: center;
    margin-bottom: 1rem;
  }

  .filter-input {
    flex: 1;
    padding: 0.75rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
  }

  .result-count {
    color: #666;
    font-size: 0.9rem;
  }

  .rules-table-container {
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    overflow-x: auto;
  }

  .rules-table {
    width: 100%;
    border-collapse: collapse;
  }

  .rules-table th {
    background-color: #f8f9fa;
    padding: 1rem;
    text-align: left;
    font-weight: 600;
    border-bottom: 2px solid #dee2e6;
  }

  .rules-table td {
    padding: 1rem;
    border-bottom: 1px solid #dee2e6;
  }

  .rule-row:hover {
    background-color: #f8f9fa;
  }

  .priority-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 12px;
    background-color: #6c757d;
    color: white;
    font-size: 0.875rem;
    font-weight: 500;
  }

  .conditions-cell {
    max-width: 400px;
  }

  .conditions-text {
    font-size: 0.875rem;
    color: #666;
    line-height: 1.4;
  }

  .category-path {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.9rem;
  }

  .category-path .tier1 {
    color: #1976d2;
    font-weight: 600;
  }

  .category-path .tier2 {
    color: #388e3c;
    font-weight: 500;
  }

  .category-path .tier3 {
    color: #666;
  }

  .category-path .separator {
    color: #ccc;
  }

  .action-buttons {
    display: flex;
    gap: 0.5rem;
  }

  .btn-icon {
    background: none;
    border: 1px solid #ddd;
    border-radius: 4px;
    cursor: pointer;
    padding: 0.25rem 0.5rem;
    font-size: 0.9rem;
    transition: all 0.2s;
  }

  .btn-icon:hover {
    background-color: #f0f0f0;
    border-color: #999;
  }

  .btn-icon.btn-danger {
    color: #dc3545;
  }

  .btn-icon.btn-danger:hover {
    background-color: #dc3545;
    color: white;
    border-color: #dc3545;
  }

  .no-rules {
    text-align: center;
    padding: 3rem !important;
    color: #999;
  }

  .btn {
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 4px;
    font-size: 1rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-primary {
    background-color: #007bff;
    color: white;
  }

  .btn-primary:hover {
    background-color: #0056b3;
  }

  .btn-secondary {
    background-color: #6c757d;
    color: white;
  }

  .btn-secondary:hover {
    background-color: #545b62;
  }

  /* Modal styles */
  .modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0,0,0,0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal {
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    max-width: 90%;
    max-height: 90vh;
    overflow-y: auto;
  }

  .modal-large {
    min-width: 700px;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.5rem;
    border-bottom: 1px solid #dee2e6;
  }

  .modal-header h2 {
    margin: 0;
    font-size: 1.5rem;
  }

  .close-btn {
    background: none;
    border: none;
    font-size: 2rem;
    cursor: pointer;
    color: #999;
    line-height: 1;
    padding: 0;
  }

  .close-btn:hover {
    color: #333;
  }

  .modal-body {
    padding: 1.5rem;
  }

  .form-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-bottom: 1rem;
  }

  .form-group {
    display: flex;
    flex-direction: column;
  }

  .form-group label {
    font-weight: 600;
    margin-bottom: 0.5rem;
    color: #333;
    font-size: 0.9rem;
  }

  .form-group input,
  .form-group select {
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
  }

  .form-group input:focus,
  .form-group select:focus {
    outline: none;
    border-color: #007bff;
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    padding: 1.5rem;
    border-top: 1px solid #dee2e6;
  }
</style>
