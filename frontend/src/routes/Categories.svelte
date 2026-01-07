<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api.js';

  let categoryTree = [];
  let loading = true;
  let error = null;
  let success = null;

  // Modal state
  let showAddModal = false;
  let addModalType = ''; // 'tier1', 'tier2', 'tier3'
  let addModalParentTier1 = '';
  let addModalParentTier2 = '';
  let newCategoryName = '';

  // Edit mode
  let editingCategory = null;
  let editingNewName = '';

  // Expanded state for tree
  let expandedTier1 = new Set();
  let expandedTier2 = new Set();

  onMount(async () => {
    await loadCategories();
  });

  async function loadCategories() {
    try {
      loading = true;
      error = null;
      const response = await api.get('/categories/tree');
      categoryTree = response.data;

      // Expand all by default
      categoryTree.forEach(tier1 => {
        expandedTier1.add(tier1.tier1);
        tier1.tier2_categories.forEach(tier2 => {
          expandedTier2.add(`${tier1.tier1}|${tier2.tier2}`);
        });
      });
    } catch (err) {
      error = `Failed to load categories: ${err.message}`;
    } finally {
      loading = false;
    }
  }

  function toggleTier1(tier1Name) {
    if (expandedTier1.has(tier1Name)) {
      expandedTier1.delete(tier1Name);
    } else {
      expandedTier1.add(tier1Name);
    }
    expandedTier1 = expandedTier1; // Trigger reactivity
  }

  function toggleTier2(tier1Name, tier2Name) {
    const key = `${tier1Name}|${tier2Name}`;
    if (expandedTier2.has(key)) {
      expandedTier2.delete(key);
    } else {
      expandedTier2.add(key);
    }
    expandedTier2 = expandedTier2; // Trigger reactivity
  }

  function openAddModal(type, parentTier1 = '', parentTier2 = '') {
    addModalType = type;
    addModalParentTier1 = parentTier1;
    addModalParentTier2 = parentTier2;
    newCategoryName = '';
    showAddModal = true;
  }

  function closeAddModal() {
    showAddModal = false;
    newCategoryName = '';
    error = null;
  }

  async function addCategory() {
    if (!newCategoryName.trim()) {
      error = 'Category name cannot be empty';
      return;
    }

    try {
      error = null;
      success = null;

      if (addModalType === 'tier1') {
        await api.post('/categories/tier1', null, {
          params: { name: newCategoryName }
        });
        success = 'Tier1 category added successfully';
      } else if (addModalType === 'tier2') {
        await api.post(`/categories/tier2/${addModalParentTier1}`, null, {
          params: { name: newCategoryName }
        });
        success = 'Tier2 category added successfully';
      } else if (addModalType === 'tier3') {
        await api.post(
          `/categories/tier3/${addModalParentTier1}/${addModalParentTier2}`,
          null,
          { params: { name: newCategoryName } }
        );
        success = 'Tier3 category added successfully';
      }

      closeAddModal();
      await loadCategories();
    } catch (err) {
      error = err.response?.data?.detail || err.message;
    }
  }

  async function deleteCategory(tier1, tier2 = null, tier3 = null) {
    let confirmMsg = '';
    if (tier3) {
      confirmMsg = `Delete category "${tier3}"?`;
    } else if (tier2) {
      confirmMsg = `Delete category "${tier2}" and all its subcategories?`;
    } else {
      confirmMsg = `Delete category "${tier1}" and all its subcategories?`;
    }

    if (!confirm(confirmMsg)) return;

    try {
      error = null;
      success = null;

      if (tier3) {
        await api.delete(`/categories/tier3/${tier1}/${tier2}/${tier3}`);
        success = 'Tier3 category deleted';
      } else if (tier2) {
        await api.delete(`/categories/tier2/${tier1}/${tier2}`);
        success = 'Tier2 category deleted';
      } else {
        await api.delete(`/categories/tier1/${tier1}`);
        success = 'Tier1 category deleted';
      }

      await loadCategories();
    } catch (err) {
      error = err.response?.data?.detail || err.message;
    }
  }

  function startEdit(tier1, tier2 = null, tier3 = null) {
    console.log('startEdit called', { tier1, tier2, tier3 });
    if (tier3) {
      editingCategory = { tier1, tier2, tier3, level: 'tier3' };
      editingNewName = tier3;
    } else if (tier2) {
      editingCategory = { tier1, tier2, level: 'tier2' };
      editingNewName = tier2;
    } else {
      editingCategory = { tier1, level: 'tier1' };
      editingNewName = tier1;
    }
    console.log('Editing category set to:', editingCategory);
  }

  function cancelEdit() {
    editingCategory = null;
    editingNewName = '';
  }

  async function saveEdit() {
    if (!editingNewName.trim()) {
      error = 'Category name cannot be empty';
      return;
    }

    try {
      error = null;
      success = null;

      if (editingCategory.level === 'tier1') {
        await api.put(`/categories/tier1/${editingCategory.tier1}`, null, {
          params: { new_name: editingNewName }
        });
        success = 'Category renamed successfully';
      } else if (editingCategory.level === 'tier2') {
        await api.put(
          `/categories/tier2/${editingCategory.tier1}/${editingCategory.tier2}`,
          null,
          {
            params: { new_name: editingNewName }
          }
        );
        success = 'Category renamed successfully';
      } else if (editingCategory.level === 'tier3') {
        await api.put(
          `/categories/tier3/${editingCategory.tier1}/${editingCategory.tier2}/${editingCategory.tier3}`,
          null,
          {
            params: { new_name: editingNewName }
          }
        );
        success = 'Category renamed successfully';
      }

      editingCategory = null;
      editingNewName = '';
      await loadCategories();
    } catch (err) {
      error = err.response?.data?.detail || err.message;
    }
  }

  function isEditing(tier1, tier2 = null, tier3 = null) {
    if (!editingCategory) return false;

    if (tier3) {
      return editingCategory.level === 'tier3' &&
             editingCategory.tier1 === tier1 &&
             editingCategory.tier2 === tier2 &&
             editingCategory.tier3 === tier3;
    } else if (tier2) {
      return editingCategory.level === 'tier2' &&
             editingCategory.tier1 === tier1 &&
             editingCategory.tier2 === tier2;
    } else {
      return editingCategory.level === 'tier1' &&
             editingCategory.tier1 === tier1;
    }
  }
</script>

<div class="categories-container">
  <div class="header">
    <h1>Category Management</h1>
    <button class="btn btn-primary" on:click={() => openAddModal('tier1')}>
      + Add Tier1 Category
    </button>
  </div>

  {#if error}
    <div class="alert alert-error">{error}</div>
  {/if}

  {#if success}
    <div class="alert alert-success">{success}</div>
  {/if}

  {#if loading}
    <div class="loading">Loading categories...</div>
  {:else}
    <div class="category-tree">
      {#each categoryTree as tier1Cat}
        <div class="tier1-node">
          <div class="category-item tier1-item">
            <button
              class="expand-btn"
              on:click={() => toggleTier1(tier1Cat.tier1)}
            >
              {expandedTier1.has(tier1Cat.tier1) ? '▼' : '▶'}
            </button>

            {#if isEditing(tier1Cat.tier1)}
              <input
                type="text"
                class="edit-input"
                bind:value={editingNewName}
                on:keydown={(e) => e.key === 'Enter' && saveEdit()}
              />
              <button class="btn-icon btn-success" on:click={saveEdit}>✓</button>
              <button class="btn-icon btn-danger" on:click={cancelEdit}>✗</button>
            {:else}
              <span class="category-name">{tier1Cat.tier1}</span>
              <div class="category-actions">
                <button
                  class="btn-icon"
                  on:click={() => openAddModal('tier2', tier1Cat.tier1)}
                  title="Add Tier2"
                >
                  +
                </button>
                <button
                  class="btn-icon"
                  on:click|stopPropagation={() => startEdit(tier1Cat.tier1)}
                  title="Rename"
                >
                  ✎
                </button>
                <button
                  class="btn-icon btn-danger"
                  on:click={() => deleteCategory(tier1Cat.tier1)}
                  title="Delete"
                >
                  🗑
                </button>
              </div>
            {/if}
          </div>

          {#if expandedTier1.has(tier1Cat.tier1)}
            <div class="tier2-container">
              {#each tier1Cat.tier2_categories as tier2Cat}
                <div class="tier2-node">
                  <div class="category-item tier2-item">
                    <button
                      class="expand-btn"
                      on:click={() => toggleTier2(tier1Cat.tier1, tier2Cat.tier2)}
                    >
                      {expandedTier2.has(`${tier1Cat.tier1}|${tier2Cat.tier2}`) ? '▼' : '▶'}
                    </button>

                    {#if isEditing(tier1Cat.tier1, tier2Cat.tier2)}
                      <input
                        type="text"
                        class="edit-input"
                        bind:value={editingNewName}
                        on:keydown={(e) => e.key === 'Enter' && saveEdit()}
                      />
                      <button class="btn-icon btn-success" on:click={saveEdit}>✓</button>
                      <button class="btn-icon btn-danger" on:click={cancelEdit}>✗</button>
                    {:else}
                      <span class="category-name">{tier2Cat.tier2}</span>
                      <div class="category-actions">
                        <button
                          class="btn-icon"
                          on:click={() => openAddModal('tier3', tier1Cat.tier1, tier2Cat.tier2)}
                          title="Add Tier3"
                        >
                          +
                        </button>
                        <button
                          class="btn-icon"
                          on:click|stopPropagation={() => startEdit(tier1Cat.tier1, tier2Cat.tier2)}
                          title="Rename"
                        >
                          ✎
                        </button>
                        <button
                          class="btn-icon btn-danger"
                          on:click={() => deleteCategory(tier1Cat.tier1, tier2Cat.tier2)}
                          title="Delete"
                        >
                          🗑
                        </button>
                      </div>
                    {/if}
                  </div>

                  {#if expandedTier2.has(`${tier1Cat.tier1}|${tier2Cat.tier2}`)}
                    <div class="tier3-container">
                      {#each tier2Cat.tier3 as tier3Name}
                        <div class="category-item tier3-item">
                          <span class="tier3-bullet">•</span>
                          {#if isEditing(tier1Cat.tier1, tier2Cat.tier2, tier3Name)}
                            <input
                              type="text"
                              class="edit-input"
                              bind:value={editingNewName}
                              on:keydown={(e) => e.key === 'Enter' && saveEdit()}
                            />
                            <button class="btn-icon btn-success" on:click={saveEdit}>✓</button>
                            <button class="btn-icon btn-danger" on:click={cancelEdit}>✗</button>
                          {:else}
                            <span class="category-name">{tier3Name}</span>
                            <div class="category-actions">
                              <button
                                class="btn-icon"
                                on:click|stopPropagation={() => startEdit(tier1Cat.tier1, tier2Cat.tier2, tier3Name)}
                                title="Rename"
                              >
                                ✎
                              </button>
                              <button
                                class="btn-icon btn-danger"
                                on:click={() => deleteCategory(tier1Cat.tier1, tier2Cat.tier2, tier3Name)}
                                title="Delete"
                              >
                                🗑
                              </button>
                            </div>
                          {/if}
                        </div>
                      {/each}
                    </div>
                  {/if}
                </div>
              {/each}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Add Category Modal -->
{#if showAddModal}
  <div class="modal-backdrop" on:click={closeAddModal}>
    <div class="modal" on:click|stopPropagation>
      <div class="modal-header">
        <h2>Add {addModalType === 'tier1' ? 'Tier1' : addModalType === 'tier2' ? 'Tier2' : 'Tier3'} Category</h2>
        <button class="close-btn" on:click={closeAddModal}>×</button>
      </div>

      <div class="modal-body">
        {#if addModalType === 'tier2'}
          <p class="modal-info">Parent: <strong>{addModalParentTier1}</strong></p>
        {:else if addModalType === 'tier3'}
          <p class="modal-info">Parent: <strong>{addModalParentTier1} → {addModalParentTier2}</strong></p>
        {/if}

        <div class="form-group">
          <label for="category-name">Category Name</label>
          <input
            id="category-name"
            type="text"
            bind:value={newCategoryName}
            placeholder="Enter category name"
            on:keydown={(e) => e.key === 'Enter' && addCategory()}
            autofocus
          />
        </div>
      </div>

      <div class="modal-footer">
        <button class="btn btn-secondary" on:click={closeAddModal}>Cancel</button>
        <button class="btn btn-primary" on:click={addCategory}>Add Category</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .categories-container {
    padding: 2rem;
    max-width: 1200px;
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

  .loading {
    text-align: center;
    padding: 3rem;
    color: #666;
    font-size: 1.1rem;
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

  .category-tree {
    background: white;
    border-radius: 8px;
    padding: 1.5rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  }

  .tier1-node {
    margin-bottom: 1rem;
  }

  .tier2-container {
    margin-left: 2rem;
    margin-top: 0.5rem;
  }

  .tier2-node {
    margin-bottom: 0.5rem;
  }

  .tier3-container {
    margin-left: 2rem;
    margin-top: 0.5rem;
  }

  .category-item {
    display: flex;
    align-items: center;
    padding: 0.75rem;
    border-radius: 4px;
    transition: background-color 0.2s;
  }

  .category-item:hover {
    background-color: #f8f9fa;
  }

  .tier1-item {
    background-color: #e3f2fd;
    font-weight: 600;
    font-size: 1.1rem;
  }

  .tier1-item:hover {
    background-color: #bbdefb;
  }

  .tier2-item {
    background-color: #f1f8e9;
    font-weight: 500;
  }

  .tier2-item:hover {
    background-color: #dcedc8;
  }

  .tier3-item {
    font-size: 0.95rem;
  }

  .expand-btn {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 0.9rem;
    margin-right: 0.5rem;
    padding: 0.25rem 0.5rem;
    color: #666;
  }

  .expand-btn:hover {
    color: #333;
  }

  .tier3-bullet {
    margin-right: 0.75rem;
    color: #999;
    font-size: 1.5rem;
    line-height: 1;
  }

  .category-name {
    flex: 1;
  }

  .category-actions {
    display: flex;
    gap: 0.5rem;
    opacity: 0;
    transition: opacity 0.2s;
  }

  .category-item:hover .category-actions {
    opacity: 1;
  }

  .edit-input {
    flex: 1;
    padding: 0.25rem 0.5rem;
    border: 1px solid #007bff;
    border-radius: 4px;
    font-size: 1rem;
    margin-right: 0.5rem;
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

  .btn-icon.btn-success {
    color: #28a745;
    border-color: #28a745;
  }

  .btn-icon.btn-success:hover {
    background-color: #28a745;
    color: white;
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
    min-width: 400px;
    max-width: 90%;
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

  .modal-info {
    margin-bottom: 1rem;
    color: #666;
  }

  .form-group {
    margin-bottom: 1rem;
  }

  .form-group label {
    display: block;
    font-weight: 600;
    margin-bottom: 0.5rem;
    color: #333;
  }

  .form-group input {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    padding: 1.5rem;
    border-top: 1px solid #dee2e6;
  }
</style>
