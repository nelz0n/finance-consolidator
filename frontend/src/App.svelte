<script>
  import { Router, Route } from 'svelte-routing';
  import Layout from './components/layout/Layout.svelte';
  import Dashboard from './routes/Dashboard.svelte';
  import Transactions from './routes/Transactions.svelte';
  import FileUpload from './routes/FileUpload.svelte';
  import Categories from './routes/Categories.svelte';
  import Rules from './routes/Rules.svelte';
  import Settings from './routes/Settings.svelte';

  export let url = "";
</script>

<Router {url}>
  <Layout>
    <Route path="/" component={Dashboard} />
    <Route path="/transactions" component={Transactions} />
    <Route path="/upload" component={FileUpload} />
    <Route path="/categories" component={Categories} />
    <Route path="/rules" component={Rules} />
    <Route path="/settings" component={Settings} />
  </Layout>
</Router>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
      'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
      sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }
</style>
