<script>
  import { onMount, onDestroy } from 'svelte';
  import Chart from '../../lib/chartConfig.js';
  import { createLineConfig, COLORS } from '../../lib/chartConfig.js';

  export let data = [];
  export let title = 'Monthly Trends';
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
    const labels = data.map(d => d.month);

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
      const datasets = [
        {
          label: 'Income',
          data: data.map(d => d.income),
          borderColor: COLORS.income,
          backgroundColor: 'transparent',
          tension: 0.3,
          fill: false,
          borderWidth: 3,
          pointRadius: 4,
          pointBackgroundColor: COLORS.income,
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          pointHoverRadius: 6
        },
        {
          label: 'Expenses',
          data: data.map(d => Math.abs(d.expenses)),
          borderColor: COLORS.expenses,
          backgroundColor: 'transparent',
          tension: 0.3,
          fill: false,
          borderWidth: 3,
          pointRadius: 4,
          pointBackgroundColor: COLORS.expenses,
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          pointHoverRadius: 6
        },
        {
          label: 'Net',
          data: data.map(d => d.net),
          borderColor: COLORS.net,
          backgroundColor: 'transparent',
          tension: 0.3,
          fill: false,
          borderWidth: 2,
          borderDash: [8, 4],
          pointRadius: 3,
          pointBackgroundColor: COLORS.net,
          pointBorderColor: '#fff',
          pointBorderWidth: 1,
          pointHoverRadius: 5
        }
      ];
      const config = createLineConfig(labels, datasets, '', handleClick);
      chart = new Chart(canvas, config);
    } else {
      // Update existing chart
      chart.data.labels = labels;
      chart.data.datasets[0].data = data.map(d => d.income);
      chart.data.datasets[1].data = data.map(d => Math.abs(d.expenses));
      chart.data.datasets[2].data = data.map(d => d.net);
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
    height: 400px;
  }

  .hint {
    text-align: center;
    font-size: 0.75rem;
    color: #95a5a6;
    margin: 8px 0 0 0;
    font-style: italic;
  }
</style>
