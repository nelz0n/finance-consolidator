<script>
  import { onMount } from 'svelte';
  import { dashboardApi, transactionsApi } from '../lib/api.js';

  let summary = null;
  let transactions = [];
  let loading = true;
  let error = null;

  // Computed data
  let categoryBreakdown = [];
  let monthlyTrends = [];
  let topExpenseCategories = [];
  let topIncomeCategories = [];

  onMount(async () => {
    try {
      // Fetch summary
      const summaryResponse = await dashboardApi.getSummary();
      summary = summaryResponse.data;

      // Fetch all transactions to compute visualizations
      const txnResponse = await transactionsApi.getAll({ limit: 200 });
      transactions = txnResponse.data.data;

      // Compute visualizations
      computeCategoryBreakdown();
      computeMonthlyTrends();
      computeTopCategories();

      loading = false;
    } catch (err) {
      error = err.message;
      loading = false;
    }
  });

  function computeCategoryBreakdown() {
    const categories = {};

    transactions.forEach(txn => {
      // Skip internal transfers
      if (txn.is_internal_transfer === 'TRUE') return;

      const amount = typeof txn.amount === 'number' ? txn.amount : parseFloat(String(txn.amount).replace(',', '.'));
      const category = txn.category_tier1 || 'Uncategorized';

      if (!categories[category]) {
        categories[category] = { income: 0, expenses: 0 };
      }

      if (amount > 0) {
        categories[category].income += amount;
      } else {
        categories[category].expenses += Math.abs(amount);
      }
    });

    categoryBreakdown = Object.entries(categories).map(([name, data]) => ({
      name,
      income: data.income,
      expenses: data.expenses,
      net: data.income - data.expenses
    })).sort((a, b) => b.expenses - a.expenses);
  }

  function computeMonthlyTrends() {
    const months = {};

    transactions.forEach(txn => {
      // Skip internal transfers
      if (txn.is_internal_transfer === 'TRUE') return;

      const date = new Date(txn.date);
      const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      const amount = typeof txn.amount === 'number' ? txn.amount : parseFloat(String(txn.amount).replace(',', '.'));

      if (!months[monthKey]) {
        months[monthKey] = { income: 0, expenses: 0 };
      }

      if (amount > 0) {
        months[monthKey].income += amount;
      } else {
        months[monthKey].expenses += Math.abs(amount);
      }
    });

    monthlyTrends = Object.entries(months).map(([month, data]) => ({
      month,
      income: data.income,
      expenses: data.expenses,
      net: data.income - data.expenses
    })).sort((a, b) => a.month.localeCompare(b.month));
  }

  function computeTopCategories() {
    // Top 5 expense categories
    topExpenseCategories = categoryBreakdown
      .filter(c => c.expenses > 0)
      .sort((a, b) => b.expenses - a.expenses)
      .slice(0, 5);

    // Top 5 income categories
    topIncomeCategories = categoryBreakdown
      .filter(c => c.income > 0)
      .sort((a, b) => b.income - a.income)
      .slice(0, 5);
  }

  function formatAmount(amount) {
    return amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  }

  function getPercentage(value, total) {
    return total > 0 ? (value / total * 100).toFixed(1) : 0;
  }
</script>

<div class="dashboard">
  <h1>Financial Dashboard</h1>

  {#if loading}
    <p>Loading...</p>
  {:else if error}
    <p class="error">Error: {error}</p>
  {:else if summary}
    <!-- Summary Cards -->
    <div class="summary-cards">
      <div class="card">
        <h3>Total Income</h3>
        <p class="amount positive">{formatAmount(summary.totals.income)} CZK</p>
        <div class="card-footer">Excluding internal transfers</div>
      </div>
      <div class="card">
        <h3>Total Expenses</h3>
        <p class="amount negative">{formatAmount(summary.totals.expenses)} CZK</p>
        <div class="card-footer">Excluding internal transfers</div>
      </div>
      <div class="card">
        <h3>Net Balance</h3>
        <p class="amount" class:positive={summary.totals.net > 0} class:negative={summary.totals.net < 0}>
          {formatAmount(summary.totals.net)} CZK
        </p>
        <div class="card-footer">Income - Expenses</div>
      </div>
      <div class="card">
        <h3>Transactions</h3>
        <p class="amount">{summary.totals.transaction_count}</p>
        <div class="card-footer">{summary.internal_transfers.count} internal transfers</div>
      </div>
    </div>

    <!-- Charts Row -->
    <div class="charts-row">
      <!-- Top Expense Categories -->
      <div class="chart-card">
        <h3>Top Expense Categories</h3>
        {#if topExpenseCategories.length > 0}
          <div class="category-chart">
            {#each topExpenseCategories as category}
              <div class="category-item">
                <div class="category-label">{category.name}</div>
                <div class="category-bar-container">
                  <div
                    class="category-bar expenses"
                    style="width: {getPercentage(category.expenses, summary.totals.expenses)}%"
                  ></div>
                </div>
                <div class="category-amount">{formatAmount(category.expenses)} CZK</div>
              </div>
            {/each}
          </div>
        {:else}
          <p class="no-data">No expense data available</p>
        {/if}
      </div>

      <!-- Top Income Categories -->
      <div class="chart-card">
        <h3>Top Income Categories</h3>
        {#if topIncomeCategories.length > 0}
          <div class="category-chart">
            {#each topIncomeCategories as category}
              <div class="category-item">
                <div class="category-label">{category.name}</div>
                <div class="category-bar-container">
                  <div
                    class="category-bar income"
                    style="width: {getPercentage(category.income, summary.totals.income)}%"
                  ></div>
                </div>
                <div class="category-amount">{formatAmount(category.income)} CZK</div>
              </div>
            {/each}
          </div>
        {:else}
          <p class="no-data">No income data available</p>
        {/if}
      </div>
    </div>

    <!-- Monthly Trends -->
    {#if monthlyTrends.length > 0}
      <div class="chart-card full-width">
        <h3>Monthly Trends</h3>
        <div class="monthly-trends">
          {#each monthlyTrends as trend}
            <div class="month-item">
              <div class="month-label">{trend.month}</div>
              <div class="month-bars">
                <div class="trend-row">
                  <span class="trend-label">Income:</span>
                  <div class="trend-bar-container">
                    <div class="trend-bar income" style="width: {Math.min(100, getPercentage(trend.income, Math.max(...monthlyTrends.map(t => t.income))))}%"></div>
                  </div>
                  <span class="trend-amount">{formatAmount(trend.income)}</span>
                </div>
                <div class="trend-row">
                  <span class="trend-label">Expenses:</span>
                  <div class="trend-bar-container">
                    <div class="trend-bar expenses" style="width: {Math.min(100, getPercentage(trend.expenses, Math.max(...monthlyTrends.map(t => t.expenses))))}%"></div>
                  </div>
                  <span class="trend-amount">{formatAmount(trend.expenses)}</span>
                </div>
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/if}
  {/if}
</div>

<style>
  .dashboard {
    max-width: 1400px;
    padding: 20px;
  }

  h1 {
    margin-bottom: 30px;
    color: #2c3e50;
  }

  /* Summary Cards */
  .summary-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
  }

  .card {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    transition: transform 0.2s, box-shadow 0.2s;
  }

  .card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.12);
  }

  .card h3 {
    margin-top: 0;
    margin-bottom: 12px;
    color: #666;
    font-size: 0.85rem;
    text-transform: uppercase;
    font-weight: 600;
    letter-spacing: 0.5px;
  }

  .amount {
    font-size: 2rem;
    font-weight: bold;
    margin: 0;
    color: #2c3e50;
  }

  .amount.positive {
    color: #27ae60;
  }

  .amount.negative {
    color: #e74c3c;
  }

  .card-footer {
    margin-top: 12px;
    font-size: 0.8rem;
    color: #999;
  }

  /* Charts Row */
  .charts-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
  }

  .chart-card {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  }

  .chart-card.full-width {
    grid-column: 1 / -1;
  }

  .chart-card h3 {
    margin-top: 0;
    margin-bottom: 20px;
    color: #2c3e50;
    font-size: 1.1rem;
  }

  /* Category Charts */
  .category-chart {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .category-item {
    display: grid;
    grid-template-columns: 120px 1fr 100px;
    gap: 12px;
    align-items: center;
  }

  .category-label {
    font-size: 0.9rem;
    color: #495057;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .category-bar-container {
    background: #f0f0f0;
    border-radius: 4px;
    height: 24px;
    position: relative;
    overflow: hidden;
  }

  .category-bar {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease;
  }

  .category-bar.expenses {
    background: linear-gradient(90deg, #e74c3c, #c0392b);
  }

  .category-bar.income {
    background: linear-gradient(90deg, #27ae60, #229954);
  }

  .category-amount {
    text-align: right;
    font-size: 0.9rem;
    font-weight: 600;
    color: #495057;
  }

  /* Monthly Trends */
  .monthly-trends {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .month-item {
    border-bottom: 1px solid #f0f0f0;
    padding-bottom: 16px;
  }

  .month-item:last-child {
    border-bottom: none;
    padding-bottom: 0;
  }

  .month-label {
    font-weight: 600;
    color: #2c3e50;
    margin-bottom: 12px;
    font-size: 0.95rem;
  }

  .month-bars {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .trend-row {
    display: grid;
    grid-template-columns: 80px 1fr 100px;
    gap: 12px;
    align-items: center;
  }

  .trend-label {
    font-size: 0.85rem;
    color: #666;
  }

  .trend-bar-container {
    background: #f0f0f0;
    border-radius: 4px;
    height: 20px;
    position: relative;
    overflow: hidden;
  }

  .trend-bar {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease;
  }

  .trend-bar.income {
    background: linear-gradient(90deg, #27ae60, #229954);
  }

  .trend-bar.expenses {
    background: linear-gradient(90deg, #e74c3c, #c0392b);
  }

  .trend-amount {
    text-align: right;
    font-size: 0.85rem;
    font-weight: 500;
    color: #495057;
  }

  .no-data {
    color: #999;
    font-style: italic;
    padding: 20px;
    text-align: center;
  }

  .error {
    color: #e74c3c;
    padding: 20px;
    background: #ffe6e6;
    border-radius: 8px;
  }
</style>
