<script>
  import { onMount } from 'svelte';
  import { dashboardApi } from '../lib/api.js';
  import ChartCard from '../components/dashboard/ChartCard.svelte';
  import CategoryPieChart from '../components/dashboard/CategoryPieChart.svelte';
  import TrendsLineChart from '../components/dashboard/TrendsLineChart.svelte';
  import TopMerchantsChart from '../components/dashboard/TopMerchantsChart.svelte';
  import SavingsRateChart from '../components/dashboard/SavingsRateChart.svelte';
  import StackedAreaChart from '../components/dashboard/StackedAreaChart.svelte';
  import SkeletonCard from '../components/dashboard/SkeletonCard.svelte';

  // State management
  let summary = null;
  let categoryData = [];
  let trendsData = [];
  let topExpenseMerchants = [];
  let topIncomeMerchants = [];
  let savingsData = [];
  let comparisonData = null;
  let categoryTimeSeriesData = null;

  let loading = true;
  let error = null;

  // Comparison mode
  let comparisonMode = 'mom'; // 'mom' (month-over-month) or 'yoy' (year-over-year)

  // Filter state
  let fromDate = null;
  let toDate = null;
  let includeInternal = false;
  let activePreset = null; // Track which preset is active

  // Drill-down state
  let drillDownPath = { tier1: null, tier2: null };

  // Date range presets
  const datePresets = [
    { label: 'Last 30 Days', days: 30 },
    { label: 'Last 3 Months', days: 90 },
    { label: 'Last 6 Months', days: 180 },
    { label: 'Last Month', type: 'last_month' },
    { label: 'This Month', type: 'this_month' },
    { label: 'Last Year', type: 'last_year' },
    { label: 'This Year', type: 'this_year' },
    { label: 'All Time', days: null }
  ];

  onMount(() => {
    // Set default to last 6 months
    setDateRange(180, 'Last 6 Months');
    loadDashboard();
  });

  // Helper function to format date without timezone issues
  function formatDateLocal(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  function setDateRange(daysOrType, presetLabel = null) {
    activePreset = presetLabel;

    if (daysOrType === null) {
      // All Time
      fromDate = null;
      toDate = null;
    } else if (typeof daysOrType === 'number') {
      // Days-based range (Last 30 Days, Last 3 Months, etc.)
      const today = new Date();
      toDate = formatDateLocal(today);
      const from = new Date(today);
      from.setDate(from.getDate() - daysOrType);
      fromDate = formatDateLocal(from);
    } else if (typeof daysOrType === 'string') {
      // Calendar-based range
      const today = new Date();

      if (daysOrType === 'this_month') {
        // First day of current month to today
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        fromDate = formatDateLocal(firstDay);
        toDate = formatDateLocal(today);
      } else if (daysOrType === 'last_month') {
        // First day to last day of previous month
        const firstDay = new Date(today.getFullYear(), today.getMonth() - 1, 1);
        const lastDay = new Date(today.getFullYear(), today.getMonth(), 0);
        fromDate = formatDateLocal(firstDay);
        toDate = formatDateLocal(lastDay);
      } else if (daysOrType === 'this_year') {
        // January 1 of current year to today
        const firstDay = new Date(today.getFullYear(), 0, 1);
        fromDate = formatDateLocal(firstDay);
        toDate = formatDateLocal(today);
      } else if (daysOrType === 'last_year') {
        // January 1 to December 31 of previous year
        const firstDay = new Date(today.getFullYear() - 1, 0, 1);
        const lastDay = new Date(today.getFullYear() - 1, 11, 31);
        fromDate = formatDateLocal(firstDay);
        toDate = formatDateLocal(lastDay);
      }
    }
  }

  async function loadDashboard() {
    loading = true;
    error = null;

    try {
      const params = {
        from_date: fromDate,
        to_date: toDate,
        include_internal: includeInternal,
        tier1: drillDownPath.tier1,
        tier2: drillDownPath.tier2
      };

      // Parallel API calls for performance
      const [summaryRes, categoryRes, trendsRes, expenseMerchantsRes, incomeMerchantsRes, savingsRes, categoryTimeSeriesRes] = await Promise.all([
        dashboardApi.getSummary(params),
        dashboardApi.getCategories(params),
        dashboardApi.getMonthlyTrends(params),
        dashboardApi.getTopCounterparties({ ...params, type: 'expense', limit: 10 }),
        dashboardApi.getTopCounterparties({ ...params, type: 'income', limit: 10 }),
        dashboardApi.getSavingsRate(params),
        dashboardApi.getCategoryTimeSeries(params)
      ]);

      summary = summaryRes.data;
      categoryData = categoryRes.data;
      trendsData = trendsRes.data;
      topExpenseMerchants = expenseMerchantsRes.data;
      topIncomeMerchants = incomeMerchantsRes.data;
      savingsData = savingsRes.data;
      categoryTimeSeriesData = categoryTimeSeriesRes.data;


      // Load comparison if we have date range
      if (fromDate && toDate) {
        await loadComparison();
      } else {
        comparisonData = null;
      }

      loading = false;
    } catch (err) {
      error = err.message || 'Failed to load dashboard data';
      loading = false;
      console.error('Dashboard error:', err);
    }
  }

  async function loadComparison() {
    if (!fromDate || !toDate) {
      comparisonData = null;
      return;
    }

    try {
      const currentStart = new Date(fromDate);
      const currentEnd = new Date(toDate);
      const daysDiff = Math.ceil((currentEnd - currentStart) / (1000 * 60 * 60 * 24));

      let previousStart, previousEnd;

      if (comparisonMode === 'mom') {
        // Month-over-month: same number of days, shifted back
        previousEnd = new Date(currentStart);
        previousEnd.setDate(previousEnd.getDate() - 1);
        previousStart = new Date(previousEnd);
        previousStart.setDate(previousStart.getDate() - daysDiff);
      } else {
        // Year-over-year: same period, one year earlier
        previousStart = new Date(currentStart);
        previousStart.setFullYear(previousStart.getFullYear() - 1);
        previousEnd = new Date(currentEnd);
        previousEnd.setFullYear(previousEnd.getFullYear() - 1);
      }

      const params = {
        current_start: currentStart.toISOString().split('T')[0],
        current_end: currentEnd.toISOString().split('T')[0],
        previous_start: previousStart.toISOString().split('T')[0],
        previous_end: previousEnd.toISOString().split('T')[0]
      };

      const res = await dashboardApi.getComparison(params);
      comparisonData = res.data;
    } catch (err) {
      console.error('Comparison error:', err);
      comparisonData = null;
    }
  }

  function handleCategoryClick(category, ctrlKey = false) {
    // Ctrl+Click: go directly to transactions
    if (ctrlKey) {
      const params = new URLSearchParams();
      if (fromDate) params.set('from_date', fromDate);
      if (toDate) params.set('to_date', toDate);

      // Set category parameters based on current drill-down level
      if (drillDownPath.tier1 === null) {
        params.set('category_tier1', category);
      } else if (drillDownPath.tier2 === null) {
        params.set('category_tier1', drillDownPath.tier1);
        params.set('category_tier2', category);
      } else {
        params.set('category_tier1', drillDownPath.tier1);
        params.set('category_tier2', drillDownPath.tier2);
        params.set('category_tier3', category);
      }

      window.location.href = `/transactions?${params.toString()}`;
      return;
    }

    // Normal click: drill down into category hierarchy
    if (drillDownPath.tier1 === null) {
      drillDownPath.tier1 = category;
      drillDownPath.tier2 = null;
    } else if (drillDownPath.tier2 === null) {
      drillDownPath.tier2 = category;
    } else {
      // At tier3 level - navigate to transactions with filter
      navigateToTransactions(category);
      return;
    }
    loadDashboard();
  }

  function resetDrillDown() {
    drillDownPath.tier1 = null;
    drillDownPath.tier2 = null;
    loadDashboard();
  }

  function drillUpToTier1() {
    drillDownPath.tier2 = null;
    loadDashboard();
  }

  function navigateToTransactions(tier3 = null) {
    // Build URL with filters
    const params = new URLSearchParams();
    if (fromDate) params.set('from_date', fromDate);
    if (toDate) params.set('to_date', toDate);
    if (drillDownPath.tier1) params.set('category_tier1', drillDownPath.tier1);
    if (drillDownPath.tier2) params.set('category_tier2', drillDownPath.tier2);
    if (tier3) params.set('category_tier3', tier3);

    window.location.href = `/transactions?${params.toString()}`;
  }

  function handleMerchantClick(merchant, ctrlKey = false) {
    // Both normal click and Ctrl+click go to transactions (merchant chart)
    const params = new URLSearchParams();
    if (fromDate) params.set('from_date', fromDate);
    if (toDate) params.set('to_date', toDate);
    params.set('counterparty_name', merchant);
    window.location.href = `/transactions?${params.toString()}`;
  }

  function handleMonthClick(monthLabel, ctrlKey = false) {
    // Ctrl+Click on trends or savings chart: view transactions for that month
    if (!ctrlKey) return; // Only handle Ctrl+click for trends

    const params = new URLSearchParams();

    // Parse month label (format: "YYYY-MM")
    const [year, month] = monthLabel.split('-');
    const firstDay = new Date(parseInt(year), parseInt(month) - 1, 1);
    const lastDay = new Date(parseInt(year), parseInt(month), 0);

    params.set('from_date', formatDateLocal(firstDay));
    params.set('to_date', formatDateLocal(lastDay));

    // Include current drill-down filters
    if (drillDownPath.tier1) params.set('category_tier1', drillDownPath.tier1);
    if (drillDownPath.tier2) params.set('category_tier2', drillDownPath.tier2);

    window.location.href = `/transactions?${params.toString()}`;
  }

  function handleCategoryLegendClick(category, ctrlKey = false) {
    // Ctrl+Click on stacked area legend: view transactions for that category
    if (!ctrlKey) return;

    const params = new URLSearchParams();
    if (fromDate) params.set('from_date', fromDate);
    if (toDate) params.set('to_date', toDate);
    params.set('category_tier1', category);

    window.location.href = `/transactions?${params.toString()}`;
  }

  function formatAmount(amount) {
    if (typeof amount !== 'number') return '0.00';
    return amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  }

  function getDrillDownTitle() {
    if (drillDownPath.tier2) {
      return `${drillDownPath.tier1} > ${drillDownPath.tier2} Breakdown`;
    } else if (drillDownPath.tier1) {
      return `${drillDownPath.tier1} Subcategories`;
    } else {
      return 'Expense Categories';
    }
  }

  function applyFilters() {
    activePreset = null; // Clear preset when manually applying filters
    loadDashboard();
  }

  function clearFilters() {
    fromDate = null;
    toDate = null;
    includeInternal = false;
    drillDownPath.tier1 = null;
    drillDownPath.tier2 = null;
    activePreset = null;
    loadDashboard();
  }
</script>

<div class="dashboard">
  <div class="header">
    <h1>Financial Dashboard</h1>

    <!-- Filter Controls -->
    <div class="filters">
      <div class="filter-group">
        <label for="from-date">From</label>
        <input type="date" id="from-date" bind:value={fromDate} on:change={() => activePreset = null} />
      </div>

      <div class="filter-group">
        <label for="to-date">To</label>
        <input type="date" id="to-date" bind:value={toDate} on:change={() => activePreset = null} />
      </div>

      <div class="filter-group checkbox">
        <label>
          <input type="checkbox" bind:checked={includeInternal} />
          Include Internal Transfers
        </label>
      </div>

      <button class="btn-primary" on:click={applyFilters}>Apply Filters</button>
      <button class="btn-secondary" on:click={clearFilters}>Clear</button>
    </div>

    <!-- Date Range Presets -->
    <div class="date-presets">
      {#each datePresets as preset}
        <button
          class="preset-btn"
          class:active={activePreset === preset.label}
          on:click={() => { setDateRange(preset.days !== undefined ? preset.days : preset.type, preset.label); loadDashboard(); }}
        >
          {preset.label}
        </button>
      {/each}
    </div>
  </div>

  {#if loading}
    <!-- Summary Cards Skeleton -->
    <div class="summary-cards">
      {#each Array(4) as _}
        <div class="card skeleton-summary">
          <div class="skeleton-title"></div>
          <div class="skeleton-amount"></div>
          <div class="skeleton-footer"></div>
        </div>
      {/each}
    </div>

    <!-- Charts Grid Skeleton -->
    <div class="charts-grid">
      <SkeletonCard />
      <SkeletonCard />
      <SkeletonCard />
      <SkeletonCard />
      <SkeletonCard />
    </div>
  {:else if error}
    <div class="error-container">
      <p class="error">Error: {error}</p>
      <button class="btn-primary" on:click={loadDashboard}>Retry</button>
    </div>
  {:else if summary}
    <!-- Summary Cards -->
    <div class="summary-cards">
      <div class="card">
        <h3>Total Income</h3>
        <p class="amount positive">{formatAmount(summary.totals.income)} CZK</p>
        <div class="card-footer">
          {summary.totals.transaction_count} transactions
          {#if !includeInternal}(excl. transfers){/if}
        </div>
      </div>

      <div class="card">
        <h3>Total Expenses</h3>
        <p class="amount negative">{formatAmount(summary.totals.expenses)} CZK</p>
        <div class="card-footer">
          {summary.totals.transaction_count} transactions
          {#if !includeInternal}(excl. transfers){/if}
        </div>
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
        <div class="card-footer">
          {summary.internal_transfers?.count || 0} internal transfers
        </div>
      </div>
    </div>

    <!-- Period Comparison -->
    {#if comparisonData && fromDate && toDate}
      <div class="comparison-section">
        <div class="comparison-header">
          <h3>Period Comparison</h3>
          <div class="comparison-mode-toggle">
            <button
              class="mode-btn"
              class:active={comparisonMode === 'mom'}
              on:click={() => { comparisonMode = 'mom'; loadComparison(); }}
            >
              Month-over-Month
            </button>
            <button
              class="mode-btn"
              class:active={comparisonMode === 'yoy'}
              on:click={() => { comparisonMode = 'yoy'; loadComparison(); }}
            >
              Year-over-Year
            </button>
          </div>
        </div>

        <div class="comparison-cards">
          <div class="comparison-card">
            <div class="comparison-label">Income</div>
            <div class="comparison-values">
              <div class="current-value positive">{formatAmount(comparisonData.current.income)} CZK</div>
              <div class="vs-label">vs</div>
              <div class="previous-value">{formatAmount(comparisonData.previous.income)} CZK</div>
            </div>
            <div class="comparison-change" class:positive={comparisonData.change.income > 0} class:negative={comparisonData.change.income < 0}>
              <span class="change-arrow">{comparisonData.change.income > 0 ? '↑' : '↓'}</span>
              {formatAmount(Math.abs(comparisonData.change.income))} CZK
              ({Math.abs(comparisonData.change_percent.income).toFixed(1)}%)
            </div>
          </div>

          <div class="comparison-card">
            <div class="comparison-label">Expenses</div>
            <div class="comparison-values">
              <div class="current-value negative">{formatAmount(comparisonData.current.expenses)} CZK</div>
              <div class="vs-label">vs</div>
              <div class="previous-value">{formatAmount(comparisonData.previous.expenses)} CZK</div>
            </div>
            <div class="comparison-change" class:positive={comparisonData.change.expenses < 0} class:negative={comparisonData.change.expenses > 0}>
              <span class="change-arrow">{comparisonData.change.expenses > 0 ? '↑' : '↓'}</span>
              {formatAmount(Math.abs(comparisonData.change.expenses))} CZK
              ({Math.abs(comparisonData.change_percent.expenses).toFixed(1)}%)
            </div>
          </div>

          <div class="comparison-card">
            <div class="comparison-label">Net</div>
            <div class="comparison-values">
              <div class="current-value" class:positive={comparisonData.current.net > 0} class:negative={comparisonData.current.net < 0}>
                {formatAmount(comparisonData.current.net)} CZK
              </div>
              <div class="vs-label">vs</div>
              <div class="previous-value">{formatAmount(comparisonData.previous.net)} CZK</div>
            </div>
            <div class="comparison-change" class:positive={comparisonData.change.net > 0} class:negative={comparisonData.change.net < 0}>
              <span class="change-arrow">{comparisonData.change.net > 0 ? '↑' : '↓'}</span>
              {formatAmount(Math.abs(comparisonData.change.net))} CZK
              ({Math.abs(comparisonData.change_percent.net).toFixed(1)}%)
            </div>
          </div>
        </div>
      </div>
    {/if}

    <!-- Breadcrumb for Drill-down -->
    {#if drillDownPath.tier1}
      <div class="breadcrumb">
        <button class="breadcrumb-link" on:click={resetDrillDown}>All Categories</button>
        <span class="breadcrumb-separator">›</span>
        <button
          class="breadcrumb-link"
          class:active={!drillDownPath.tier2}
          on:click={drillDownPath.tier2 ? drillUpToTier1 : null}
        >
          {drillDownPath.tier1}
        </button>
        {#if drillDownPath.tier2}
          <span class="breadcrumb-separator">›</span>
          <span class="breadcrumb-current">{drillDownPath.tier2}</span>
        {/if}
      </div>
    {/if}

    <!-- Charts Grid -->
    <div class="charts-grid">
      <!-- Category Breakdown Pie Chart -->
      <ChartCard title={getDrillDownTitle()} subtitle="Click to drill down">
        {#if categoryData.length > 0}
          <CategoryPieChart
            data={categoryData}
            type="expenses"
            onSliceClick={handleCategoryClick}
          />
        {:else}
          <p class="no-data">No category data available</p>
        {/if}
      </ChartCard>

      <!-- Monthly Trends Line Chart -->
      <ChartCard title="Monthly Trends" subtitle="Monthly income (green), expenses (red), and net balance (blue dashed)">
        {#if trendsData.length > 0}
          <TrendsLineChart data={trendsData} onMonthClick={handleMonthClick} />
        {:else}
          <p class="no-data">No trend data available</p>
        {/if}
      </ChartCard>

      <!-- Top Expense Merchants -->
      <ChartCard title="Top Expense Merchants" subtitle="Click to view transactions">
        {#if topExpenseMerchants.length > 0}
          <TopMerchantsChart
            data={topExpenseMerchants}
            type="expense"
            onBarClick={handleMerchantClick}
          />
        {:else}
          <p class="no-data">No merchant data available</p>
        {/if}
      </ChartCard>

      <!-- Top Income Sources -->
      <ChartCard title="Top Income Sources" subtitle="Click to view transactions">
        {#if topIncomeMerchants.length > 0}
          <TopMerchantsChart
            data={topIncomeMerchants}
            type="income"
            onBarClick={handleMerchantClick}
          />
        {:else}
          <p class="no-data">No income source data available</p>
        {/if}
      </ChartCard>

      <!-- Savings Rate (full width) -->
      <ChartCard title="Savings Rate Trend" subtitle="Monthly savings rate (%) and amount (CZK) - rate capped at -100% to 200% for readability">
        {#if savingsData.length > 0}
          <SavingsRateChart data={savingsData} onMonthClick={handleMonthClick} />
        {:else}
          <p class="no-data">No savings data available</p>
        {/if}
      </ChartCard>

      <!-- Category Swimlane (full width) -->
      <ChartCard title="Expense Categories Over Time" subtitle="Stacked area chart showing all expense categories by month">
        {#if categoryTimeSeriesData && categoryTimeSeriesData.months && categoryTimeSeriesData.months.length > 0}
          <StackedAreaChart
            data={categoryTimeSeriesData}
            onMonthClick={handleMonthClick}
            onCategoryClick={handleCategoryLegendClick}
          />
        {:else}
          <p class="no-data">No category time series data available</p>
        {/if}
      </ChartCard>
    </div>
  {/if}
</div>

<style>
  .dashboard {
    max-width: 1600px;
    margin: 0 auto;
    padding: 20px;
  }

  .header {
    margin-bottom: 30px;
  }

  h1 {
    margin-bottom: 20px;
    color: #2c3e50;
  }

  /* Filter Controls */
  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    align-items: flex-end;
    margin-bottom: 16px;
    padding: 20px;
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
  }

  .filter-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .filter-group.checkbox {
    flex-direction: row;
    align-items: center;
  }

  .filter-group label {
    font-size: 0.85rem;
    color: #666;
    font-weight: 500;
  }

  .filter-group input[type="date"],
  .filter-group input[type="text"] {
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 6px;
    font-size: 0.9rem;
    min-width: 150px;
  }

  .filter-group input[type="date"]:focus,
  .filter-group input[type="text"]:focus {
    outline: none;
    border-color: #3498db;
  }

  .btn-primary,
  .btn-secondary {
    padding: 8px 16px;
    border-radius: 6px;
    font-size: 0.9rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    border: none;
  }

  .btn-primary {
    background: #3498db;
    color: white;
  }

  .btn-primary:hover {
    background: #2980b9;
  }

  .btn-secondary {
    background: #95a5a6;
    color: white;
  }

  .btn-secondary:hover {
    background: #7f8c8d;
  }

  /* Date Presets */
  .date-presets {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .preset-btn {
    padding: 6px 12px;
    background: white;
    border: 1px solid #ddd;
    border-radius: 6px;
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .preset-btn:hover {
    background: #f8f9fa;
    border-color: #3498db;
    color: #3498db;
  }

  .preset-btn.active {
    background: #3498db;
    color: white;
    border-color: #3498db;
    font-weight: 600;
  }

  .preset-btn.active:hover {
    background: #2980b9;
    border-color: #2980b9;
    color: white;
  }

  /* Breadcrumb */
  .breadcrumb {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 20px;
    padding: 12px 16px;
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
  }

  .breadcrumb-link {
    background: none;
    border: none;
    color: #3498db;
    cursor: pointer;
    font-size: 0.9rem;
    padding: 0;
    text-decoration: underline;
  }

  .breadcrumb-link:hover {
    color: #2980b9;
  }

  .breadcrumb-link.active {
    color: #2c3e50;
    font-weight: 600;
    text-decoration: none;
    cursor: default;
  }

  .breadcrumb-separator {
    color: #95a5a6;
  }

  .breadcrumb-current {
    color: #2c3e50;
    font-weight: 600;
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
    margin: 0 0 12px 0;
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

  /* Charts Grid */
  .charts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
    gap: 24px;
  }

  .charts-grid > :last-child {
    grid-column: 1 / -1;
  }

  /* Skeleton Loaders */
  .skeleton-summary {
    pointer-events: none;
  }

  .skeleton-title {
    height: 14px;
    width: 60%;
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 4px;
    margin-bottom: 12px;
  }

  .skeleton-amount {
    height: 32px;
    width: 80%;
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 4px;
    margin-bottom: 12px;
  }

  .skeleton-footer {
    height: 12px;
    width: 50%;
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 4px;
  }

  @keyframes shimmer {
    0% {
      background-position: -200% 0;
    }
    100% {
      background-position: 200% 0;
    }
  }

  /* Loading and Error States */
  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 400px;
    gap: 16px;
  }

  .spinner {
    width: 48px;
    height: 48px;
    border: 4px solid #f3f3f3;
    border-top: 4px solid #3498db;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  .error-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 40px;
  }

  .error {
    color: #e74c3c;
    font-size: 1rem;
  }

  .no-data {
    text-align: center;
    color: #95a5a6;
    font-style: italic;
    padding: 40px;
  }

  /* Comparison Section */
  .comparison-section {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 30px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  }

  .comparison-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }

  .comparison-header h3 {
    margin: 0;
    color: #2c3e50;
    font-size: 1.1rem;
  }

  .comparison-mode-toggle {
    display: flex;
    gap: 8px;
  }

  .mode-btn {
    padding: 6px 12px;
    background: white;
    border: 1px solid #ddd;
    border-radius: 6px;
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .mode-btn:hover {
    border-color: #3498db;
    color: #3498db;
  }

  .mode-btn.active {
    background: #3498db;
    color: white;
    border-color: #3498db;
  }

  .comparison-cards {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
  }

  .comparison-card {
    padding: 16px;
    background: #f8f9fa;
    border-radius: 8px;
    text-align: center;
  }

  .comparison-label {
    font-size: 0.85rem;
    color: #666;
    font-weight: 600;
    text-transform: uppercase;
    margin-bottom: 12px;
    letter-spacing: 0.5px;
  }

  .comparison-values {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    margin-bottom: 12px;
  }

  .current-value {
    font-size: 1.25rem;
    font-weight: bold;
    color: #2c3e50;
  }

  .vs-label {
    font-size: 0.75rem;
    color: #95a5a6;
    font-weight: 500;
  }

  .previous-value {
    font-size: 1rem;
    color: #7f8c8d;
  }

  .comparison-change {
    font-size: 0.9rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
  }

  .comparison-change.positive {
    color: #27ae60;
  }

  .comparison-change.negative {
    color: #e74c3c;
  }

  .change-arrow {
    font-size: 1.2rem;
  }

  /* Responsive Design */
  @media (max-width: 768px) {
    .filters {
      flex-direction: column;
      align-items: stretch;
    }

    .filter-group input[type="date"],
    .filter-group input[type="text"] {
      min-width: 100%;
    }

    .charts-grid {
      grid-template-columns: 1fr;
    }

    .summary-cards {
      grid-template-columns: repeat(2, 1fr);
    }

    .comparison-cards {
      grid-template-columns: 1fr;
    }

    .comparison-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 12px;
    }

    .comparison-mode-toggle {
      width: 100%;
    }

    .mode-btn {
      flex: 1;
    }
  }
</style>
