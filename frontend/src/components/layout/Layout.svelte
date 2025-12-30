<script>
  import { Link } from 'svelte-routing';
</script>

<div class="app-container">
  <nav class="sidebar">
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
  .main-content {
    flex: 1;
    padding: 30px;
    overflow-y: auto;
  }
</style>
