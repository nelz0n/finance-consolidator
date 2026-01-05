<script>
  export let title = '';
  export let subtitle = '';
  export let loading = false;
  export let error = null;
</script>

<div class="chart-card">
  {#if title}
    <div class="chart-header">
      <h3>{title}</h3>
      {#if subtitle}
        <p class="subtitle">{subtitle}</p>
      {/if}
    </div>
  {/if}

  <div class="chart-content">
    {#if loading}
      <div class="loading-state">
        <div class="spinner"></div>
        <p>Loading chart data...</p>
      </div>
    {:else if error}
      <div class="error-state">
        <p class="error-message">⚠️ {error}</p>
        <slot name="error-actions" />
      </div>
    {:else}
      <slot />
    {/if}
  </div>
</div>

<style>
  .chart-card {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    transition: box-shadow 0.2s ease;
  }

  .chart-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.12);
  }

  .chart-header {
    margin-bottom: 20px;
    border-bottom: 1px solid #f0f0f0;
    padding-bottom: 12px;
  }

  .chart-header h3 {
    margin: 0 0 8px 0;
    color: #2c3e50;
    font-size: 1.1rem;
    font-weight: 600;
  }

  .subtitle {
    margin: 0;
    font-size: 0.85rem;
    color: #7f8c8d;
  }

  .chart-content {
    position: relative;
    min-height: 300px;
  }

  .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 300px;
    color: #95a5a6;
  }

  .spinner {
    border: 3px solid #f3f3f3;
    border-top: 3px solid #3498db;
    border-radius: 50%;
    width: 40px;
    height: 40px;
    animation: spin 1s linear infinite;
    margin-bottom: 16px;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  .loading-state p {
    margin: 0;
    font-size: 0.9rem;
    font-style: italic;
  }

  .error-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 300px;
    padding: 20px;
    text-align: center;
  }

  .error-message {
    color: #e74c3c;
    margin: 0 0 16px 0;
    font-size: 0.95rem;
  }
</style>
