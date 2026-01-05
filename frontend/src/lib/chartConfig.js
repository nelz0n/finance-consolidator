/**
 * Chart.js configuration and utilities
 */
import {
  Chart,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  DoughnutController,
  LineController,
  BarController
} from 'chart.js';

// Register Chart.js components
Chart.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  DoughnutController,
  LineController,
  BarController
);

// Color palette
export const COLORS = {
  income: 'rgb(39, 174, 96)',      // Green
  expenses: 'rgb(231, 76, 60)',    // Red
  net: 'rgb(52, 152, 219)',        // Blue
  savings: 'rgb(155, 89, 182)',    // Purple

  // Category colors (cycle through for multi-category charts)
  categories: [
    'rgb(52, 152, 219)',   // Blue
    'rgb(46, 204, 113)',   // Green
    'rgb(155, 89, 182)',   // Purple
    'rgb(241, 196, 15)',   // Yellow
    'rgb(230, 126, 34)',   // Orange
    'rgb(26, 188, 156)',   // Turquoise
    'rgb(231, 76, 60)',    // Red
    'rgb(149, 165, 166)',  // Gray
    'rgb(192, 57, 43)',    // Dark Red
    'rgb(142, 68, 173)',   // Dark Purple
    'rgb(44, 62, 80)',     // Dark Blue
    'rgb(127, 140, 141)'   // Dark Gray
  ]
};

// Default chart options
export const defaultOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      position: 'top',
    },
    tooltip: {
      mode: 'index',
      intersect: false,
    }
  }
};

/**
 * Format currency for tooltips and labels
 */
export function formatCurrency(value, currency = 'CZK') {
  return new Intl.NumberFormat('cs-CZ', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value);
}

/**
 * Format number with thousand separators
 */
export function formatNumber(value) {
  return new Intl.NumberFormat('cs-CZ', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value);
}

/**
 * Create pie/donut chart configuration for category breakdown
 */
export function createPieConfig(labels, data, title, onClick = null) {
  return {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: COLORS.categories,
        borderWidth: 2,
        borderColor: '#fff',
        hoverBorderWidth: 3
      }]
    },
    options: {
      ...defaultOptions,
      plugins: {
        ...defaultOptions.plugins,
        title: {
          display: !!title,
          text: title,
          font: {
            size: 16,
            weight: 'bold'
          }
        },
        tooltip: {
          callbacks: {
            label: (context) => {
              const label = context.label || '';
              const value = context.parsed || 0;
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const percent = ((value / total) * 100).toFixed(1);
              return `${label}: ${formatCurrency(value)} (${percent}%)`;
            }
          }
        },
        legend: {
          display: true,
          position: 'right',
          labels: {
            boxWidth: 15,
            padding: 10,
            font: {
              size: 11
            }
          }
        }
      },
      onClick: onClick
    }
  };
}

/**
 * Create line chart configuration for time series
 */
export function createLineConfig(labels, datasets, title, onClick = null) {
  return {
    type: 'line',
    data: { labels, datasets },
    options: {
      ...defaultOptions,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        ...defaultOptions.plugins,
        title: {
          display: !!title,
          text: title,
          font: {
            size: 16,
            weight: 'bold'
          }
        },
        legend: {
          display: true,
          position: 'top'
        }
      },
      onClick: onClick,
      scales: {
        x: {
          grid: {
            display: false
          }
        },
        y: {
          beginAtZero: true,
          ticks: {
            callback: (value) => formatNumber(value)
          },
          grid: {
            color: (context) => {
              if (context.tick.value === 0) {
                return 'rgba(0, 0, 0, 0.4)'; // Bold dark line at zero
              }
              return 'rgba(0, 0, 0, 0.05)'; // Light lines elsewhere
            },
            lineWidth: (context) => {
              if (context.tick.value === 0) {
                return 2; // Thicker line at zero
              }
              return 1; // Normal thickness elsewhere
            }
          }
        }
      }
    }
  };
}

/**
 * Create horizontal bar chart for top counterparties
 */
export function createHorizontalBarConfig(labels, data, title, color = COLORS.expenses, onClick = null) {
  return {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: color,
        borderWidth: 0,
        borderRadius: 4
      }]
    },
    options: {
      indexAxis: 'y',
      ...defaultOptions,
      plugins: {
        ...defaultOptions.plugins,
        title: {
          display: !!title,
          text: title,
          font: {
            size: 16,
            weight: 'bold'
          }
        },
        legend: {
          display: false
        },
        tooltip: {
          callbacks: {
            label: (context) => {
              return formatCurrency(context.parsed.x);
            }
          }
        }
      },
      scales: {
        x: {
          ticks: {
            callback: (value) => formatNumber(value)
          },
          grid: {
            color: 'rgba(0, 0, 0, 0.05)'
          }
        },
        y: {
          grid: {
            display: false
          }
        }
      },
      onClick: onClick
    }
  };
}

/**
 * Create dual-axis line chart for savings rate
 */
export function createDualAxisLineConfig(labels, rateData, amountData, title, onClick = null) {
  // Cap savings rate at reasonable values (-100% to 200%) to avoid extreme chart distortion
  const cappedRateData = rateData.map(rate => {
    if (rate > 200) return 200;
    if (rate < -100) return -100;
    return rate;
  });

  return {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Savings Rate (%)',
          data: cappedRateData,
          borderColor: COLORS.savings,
          backgroundColor: 'transparent',
          tension: 0.3,
          fill: false,
          borderWidth: 3,
          pointRadius: 4,
          pointBackgroundColor: COLORS.savings,
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          pointHoverRadius: 6,
          yAxisID: 'y'
        },
        {
          label: 'Savings Amount',
          data: amountData,
          borderColor: COLORS.net,
          backgroundColor: 'transparent',
          tension: 0.3,
          fill: false,
          borderWidth: 3,
          pointRadius: 4,
          pointBackgroundColor: COLORS.net,
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          pointHoverRadius: 6,
          yAxisID: 'y1'
        }
      ]
    },
    options: {
      ...defaultOptions,
      onClick: onClick,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        ...defaultOptions.plugins,
        title: {
          display: !!title,
          text: title,
          font: {
            size: 16,
            weight: 'bold'
          }
        },
        tooltip: {
          callbacks: {
            label: (context) => {
              const datasetLabel = context.dataset.label || '';
              const value = context.parsed.y;

              // Show original uncapped value in tooltip
              if (datasetLabel.includes('Rate')) {
                const originalValue = rateData[context.dataIndex];
                if (originalValue > 200 || originalValue < -100) {
                  return `${datasetLabel}: ${originalValue.toFixed(1)}% (capped at ${value.toFixed(0)}% for display)`;
                }
                return `${datasetLabel}: ${value.toFixed(1)}%`;
              } else {
                return `${datasetLabel}: ${formatCurrency(value)}`;
              }
            }
          }
        }
      },
      scales: {
        x: {
          grid: {
            display: false
          }
        },
        y: {
          type: 'linear',
          display: true,
          position: 'left',
          title: {
            display: true,
            text: 'Savings Rate (%)',
            font: {
              weight: 'bold',
              size: 12
            }
          },
          min: -100,
          max: 200,
          ticks: {
            callback: (value) => value.toFixed(0) + '%',
            stepSize: 50
          },
          grid: {
            color: (context) => {
              if (context.tick.value === 0) {
                return 'rgba(0, 0, 0, 0.4)'; // Bold dark line at zero
              }
              return 'rgba(0, 0, 0, 0.05)'; // Light lines elsewhere
            },
            lineWidth: (context) => {
              if (context.tick.value === 0) {
                return 2; // Thicker line at zero
              }
              return 1; // Normal thickness elsewhere
            }
          }
        },
        y1: {
          type: 'linear',
          display: true,
          position: 'right',
          title: {
            display: true,
            text: 'Savings Amount (CZK)',
            font: {
              weight: 'bold',
              size: 12
            }
          },
          grid: {
            drawOnChartArea: false,
            color: (context) => {
              if (context.tick.value === 0) {
                return 'rgba(0, 0, 0, 0.4)'; // Bold dark line at zero
              }
              return 'rgba(0, 0, 0, 0.05)'; // Light lines elsewhere
            },
            lineWidth: (context) => {
              if (context.tick.value === 0) {
                return 2; // Thicker line at zero
              }
              return 1; // Normal thickness elsewhere
            }
          },
          ticks: {
            callback: (value) => formatNumber(value)
          }
        }
      }
    }
  };
}

// Export Chart for use in components
export { Chart };
export default Chart;
