<script>
  import { Link } from 'svelte-routing';
  import { onMount } from 'svelte';
  import api from '../../services/api';

  let version = { commit: 'loading...', branch: '', build_time: '', environment: '' };

  onMount(async () => {
    try {
      const response = await api.get('/version');
      version = response.data;
    } catch (err) {
      console.error('Failed to fetch version:', err);
      version = { commit: 'unknown', branch: '', build_time: '', environment: '' };
    }
  });
</script>

<div class="app-container">
  <nav class="sidebar">
    <div class="sidebar-content">
      <h2>Finance Consolidator</h2>
      <ul>
        <li><Link to="/">📊 Dashboard</Link></li>
        <li><Link to="/transactions">💰 Transactions</Link></li>
        <li><Link to="/upload">📁 Upload Files</Link></li>
        <li class="nav-divider"></li>
        <li><Link to="/categories">🏷️ Categories</Link></li>
        <li><Link to="/rules">⚙️ Rules</Link></li>
        <li class="nav-divider"></li>
        <li><Link to="/settings">🔧 Settings</Link></li>
      </ul>
    </div>
    <div class="version-info">
      <div class="version-line">
        <span class="version-label">Version:</span>
        <span class="version-value" title="Git commit: {version.commit}">{version.commit}</span>
      </div>
      {#if version.branch && version.branch !== 'unknown'}
        <div class="version-line">
          <span class="version-label">Branch:</span>
          <span class="version-value">{version.branch}</span>
        </div>
      {/if}
      {#if version.build_time}
        <div class="version-line">
          <span class="version-label">Built:</span>
          <span class="version-value" title="{version.build_time}">{version.build_time.split(' ')[0]}</span>
        </div>
      {/if}
    </div>
  </nav>
  <main class="main-content">
    <slot></slot>
  </main>
</div>

<style>
  .app-container {
    display: flex;
    height: 100vh;
  }
  .sidebar {
    width: 250px;
    background: #2c3e50;
    color: white;
    padding: 20px;
    display: flex;
    flex-direction: column;
  }
  .sidebar-content {
    flex: 1;
  }
  .sidebar h2 {
    margin-top: 0;
    font-size: 1.2rem;
  }
  .sidebar ul {
    list-style: none;
    padding: 0;
  }
  .sidebar li {
    margin: 10px 0;
  }
  .sidebar li.nav-divider {
    height: 1px;
    background: #34495e;
    margin: 20px 0;
  }
  .sidebar :global(a) {
    color: white;
    text-decoration: none;
    display: block;
    padding: 10px 15px;
    border-radius: 4px;
    transition: background-color 0.2s;
  }
  .sidebar :global(a:hover) {
    background-color: #34495e;
    text-decoration: none;
  }
  .sidebar :global(a[aria-current="page"]) {
    background-color: #3498db;
  }
  .version-info {
    margin-top: 20px;
    padding-top: 15px;
    border-top: 1px solid #34495e;
    font-size: 0.75rem;
    color: #95a5a6;
  }
  .version-line {
    display: flex;
    justify-content: space-between;
    margin: 5px 0;
  }
  .version-label {
    font-weight: 600;
  }
  .version-value {
    font-family: 'Courier New', monospace;
    color: #bdc3c7;
  }
  .main-content {
    flex: 1;
    padding: 30px;
    overflow-y: auto;
  }
</style>
