<script>
  import { onMount, onDestroy } from 'svelte';
  import Chart from '../../lib/chartConfig.js';
  import { createDualAxisLineConfig } from '../../lib/chartConfig.js';

  export let data = [];
  export let title = 'Savings Rate Trend';
  export let onMonthClick = null; // Callback for month click

  let canvas;
  let chart;

  onDestroy(() => {
    if (chart) {
      chart.destroy();
    }
  });

  // Create/update chart when data or canvas changes
  $: if (canvas && data && data.length > 0) {
    const labels = data.map(d => d.period);
    const rateData = data.map(d => d.rate);
    const amountData = data.map(d => d.savings);

    // Create onClick handler
    const handleClick = onMonthClick ? (event, elements) => {
      if (elements.length > 0) {
        const index = elements[0].index;
        const monthLabel = labels[index];
        const ctrlKey = event.native?.ctrlKey || event.native?.metaKey || false;
        onMonthClick(monthLabel, ctrlKey);
      }
    } : null;

    if (!chart) {
      // Create chart if it doesn't exist
      const config = createDualAxisLineConfig(labels, rateData, amountData, '', handleClick);
      chart = new Chart(canvas, config);
    } else {
      // Update existing chart
      chart.data.labels = labels;
      chart.data.datasets[0].data = rateData;
      chart.data.datasets[1].data = amountData;
      chart.update();
    }
  }
</script>

<div class="chart-container">
  <canvas bind:this={canvas}></canvas>
  {#if onMonthClick}
    <p class="hint">💡 Ctrl+Click a month to view transactions</p>
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
