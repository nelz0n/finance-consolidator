<script>
  import { onMount, onDestroy } from 'svelte';
  import Chart from '../../lib/chartConfig.js';
  import { createPieConfig } from '../../lib/chartConfig.js';

  export let data = [];
  export let title = 'Category Breakdown';
  export let type = 'expenses'; // 'expenses' or 'income'
  export let onSliceClick = null; // Callback for drill-down

  let canvas;
  let chart;

  onDestroy(() => {
    if (chart) {
      chart.destroy();
    }
  });

  // Create/update chart when data or canvas changes
  $: if (canvas && data && data.length > 0) {
    const labels = data.map(d => d.category);
    const values = data.map(d => type === 'expenses' ? d.expenses : d.income);

    // Create onClick handler for drill-down
    const handleClick = onSliceClick ? (event, elements) => {
      if (elements.length > 0) {
        const index = elements[0].index;
        const category = labels[index];
        const ctrlKey = event.native?.ctrlKey || event.native?.metaKey || false;
        onSliceClick(category, ctrlKey);
      }
    } : null;

    if (!chart) {
      // Create chart if it doesn't exist
      const config = createPieConfig(labels, values, '', handleClick);
      chart = new Chart(canvas, config);
    } else {
      // Update existing chart
      chart.data.labels = labels;
      chart.data.datasets[0].data = values;
      chart.update();
    }
  }
</script>

<div class="chart-container">
  <canvas bind:this={canvas}></canvas>
  {#if onSliceClick}
    <p class="hint">💡 Click to drill down • Ctrl+Click to view transactions</p>
  {/if}
</div>

<style>
  .chart-container {
    position: relative;
    height: 350px;
  }

  .hint {
    text-align: center;
    font-size: 0.75rem;
    color: #95a5a6;
    margin: 8px 0 0 0;
    font-style: italic;
  }
</style>
