<script>
  export let height = '350px';
</script>

<div class="skeleton-card" style="height: {height}">
  <div class="skeleton-header">
    <div class="skeleton-title"></div>
    <div class="skeleton-subtitle"></div>
  </div>
  <div class="skeleton-content">
    <div class="skeleton-chart"></div>
  </div>
</div>

<style>
  .skeleton-card {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  }

  .skeleton-header {
    margin-bottom: 16px;
  }

  .skeleton-title {
    height: 24px;
    width: 40%;
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 4px;
    margin-bottom: 8px;
  }

  .skeleton-subtitle {
    height: 16px;
    width: 60%;
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 4px;
  }

  .skeleton-content {
    height: calc(100% - 60px);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .skeleton-chart {
    width: 90%;
    height: 90%;
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 8px;
  }

  @keyframes shimmer {
    0% {
      background-position: -200% 0;
    }
    100% {
      background-position: 200% 0;
    }
  }
</style>
