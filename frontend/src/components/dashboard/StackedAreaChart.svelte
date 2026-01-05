<script>
  import { onDestroy } from 'svelte';
  import Chart from '../../lib/chartConfig.js';
  import { COLORS } from '../../lib/chartConfig.js';

  export let data = null; // { months: [], categories: [], data: {category: [values]} }
  export let onMonthClick = null; // Callback for Ctrl+Click
  export let onCategoryClick = null; // Callback for Ctrl+Click on legend

  let canvas;
  let chart;

  onDestroy(() => {
    if (chart) {
      chart.destroy();
    }
  });

  // Create/update chart when data or canvas changes
  $: if (canvas && data && data.months && data.months.length > 0) {
    const labels = data.months;
    const categories = data.categories;

    // Create onClick handler for months
    const handleClick = onMonthClick ? (event, elements) => {
      if (elements.length > 0) {
        const index = elements[0].index;
        const monthLabel = labels[index];
        const ctrlKey = event.native?.ctrlKey || event.native?.metaKey || false;
        onMonthClick(monthLabel, ctrlKey);
      }
    } : null;

    // Create datasets for each category
    const datasets = categories.map((category, idx) => {
      const colorIndex = idx % COLORS.categories.length;
      const color = COLORS.categories[colorIndex];

      return {
        label: category,
        data: data.data[category],
        borderColor: color,
        backgroundColor: color + '80', // 50% opacity for fill
        tension: 0.3,
        fill: true,
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: color,
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2
      };
    });

    if (!chart) {
      // Create chart if it doesn't exist
      chart = new Chart(canvas, {
        type: 'line',
        data: {
          labels,
          datasets
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          onClick: handleClick,
          interaction: {
            mode: 'index',
            intersect: false
          },
          plugins: {
            legend: {
              display: true,
              position: 'right',
              labels: {
                boxWidth: 15,
                padding: 10,
                font: {
                  size: 11
                },
                usePointStyle: true
              },
              onClick: (event, legendItem, legend) => {
                // Ctrl+Click on legend to filter transactions
                if (onCategoryClick && (event.native?.ctrlKey || event.native?.metaKey)) {
                  const categoryIndex = legendItem.datasetIndex;
                  const category = categories[categoryIndex];
                  onCategoryClick(category, true);
                } else {
                  // Default behavior: toggle visibility
                  const index = legendItem.datasetIndex;
                  const ci = legend.chart;
                  if (ci.isDatasetVisible(index)) {
                    ci.hide(index);
                    legendItem.hidden = true;
                  } else {
                    ci.show(index);
                    legendItem.hidden = false;
                  }
                }
              }
            },
            tooltip: {
              mode: 'index',
              intersect: false,
              callbacks: {
                label: (context) => {
                  const label = context.dataset.label || '';
                  const value = context.parsed.y || 0;
                  return `${label}: ${value.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ' ')} CZK`;
                },
                footer: (tooltipItems) => {
                  let sum = 0;
                  tooltipItems.forEach(item => {
                    sum += item.parsed.y;
                  });
                  return `Total: ${sum.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ' ')} CZK`;
                }
              }
            }
          },
          scales: {
            x: {
              stacked: true,
              grid: {
                display: false
              }
            },
            y: {
              stacked: true,
              beginAtZero: true,
              ticks: {
                callback: (value) => value.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
              },
              grid: {
                color: (context) => {
                  if (context.tick.value === 0) {
                    return 'rgba(0, 0, 0, 0.4)';
                  }
                  return 'rgba(0, 0, 0, 0.05)';
                },
                lineWidth: (context) => {
                  if (context.tick.value === 0) {
                    return 2;
                  }
                  return 1;
                }
              }
            }
          }
        }
      });
    } else {
      // Update existing chart
      chart.data.labels = labels;
      chart.data.datasets = datasets;
      chart.update();
    }
  }
</script>

<div class="chart-container">
  <canvas bind:this={canvas}></canvas>
  {#if onMonthClick || onCategoryClick}
    <p class="hint">
      💡 Ctrl+Click a month to view transactions
      {#if onCategoryClick}• Ctrl+Click a category in legend to filter{/if}
    </p>
  {/if}
</div>

<style>
  .chart-container {
    position: relative;
    height: 450px;
  }

  .hint {
    text-align: center;
    font-size: 0.75rem;
    color: #95a5a6;
    margin: 8px 0 0 0;
    font-style: italic;
  }
</style>
