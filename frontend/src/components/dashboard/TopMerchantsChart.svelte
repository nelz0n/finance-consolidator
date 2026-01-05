<script>
  import { onMount, onDestroy } from 'svelte';
  import Chart from '../../lib/chartConfig.js';
  import { createHorizontalBarConfig, COLORS } from '../../lib/chartConfig.js';

  export let data = [];
  export let title = 'Top Merchants';
  export let type = 'expense'; // 'expense' or 'income'
  export let onBarClick = null; // Navigate to transactions filtered by merchant

  let canvas;
  let chart;

  onDestroy(() => {
    if (chart) {
      chart.destroy();
    }
  });

  // Create/update chart when data or canvas changes
  $: if (canvas && data && data.length > 0) {
    const labels = data.map(d => d.counterparty);
    const values = data.map(d => d.total);

    if (!chart) {
      // Create chart if it doesn't exist
      const color = type === 'expense' ? COLORS.expenses : COLORS.income;

      // Create onClick handler
      const handleClick = onBarClick ? (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          const merchant = labels[index];
          const ctrlKey = event.native?.ctrlKey || event.native?.metaKey || false;
          onBarClick(merchant, ctrlKey);
        }
      } : null;

      const config = createHorizontalBarConfig(labels, values, '', color, handleClick);
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
  {#if onBarClick}
    <p class="hint">💡 Click on a bar to view transactions</p>
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
