<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api.js';

  let institutions = [];
  let selectedInstitution = '';
  let file = null;
  let overrideExisting = false;
  let disableAiCategorization = false;
  let uploading = false;
  let jobs = [];
  let error = null;
  let success = null;

  // Log viewer
  let showLogModal = false;
  let currentJobLog = null;
  let viewingJobId = null;

  // Auto-refresh jobs every 2 seconds
  let refreshInterval;

  onMount(async () => {
    await loadInstitutions();
    await loadJobs();

    // Start auto-refresh
    refreshInterval = setInterval(loadJobs, 2000);

    // Cleanup on destroy
    return () => {
      if (refreshInterval) {
        clearInterval(refreshInterval);
      }
    };
  });

  async function loadInstitutions() {
    try {
      const response = await api.get('/files/institutions');
      institutions = response.data;
      if (institutions.length > 0) {
        selectedInstitution = institutions[0].id;
      }
    } catch (err) {
      error = `Failed to load institutions: ${err.message}`;
    }
  }

  async function loadJobs() {
    try {
      const response = await api.get('/files/jobs');
      jobs = response.data;
    } catch (err) {
      console.error('Failed to load jobs:', err);
    }
  }

  function handleFileSelect(event) {
    const files = event.target.files;
    if (files.length > 0) {
      file = files[0];
    }
  }

  async function uploadFile() {
    if (!file || !selectedInstitution) {
      error = 'Please select a file and institution';
      return;
    }

    uploading = true;
    error = null;
    success = null;

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('institution', selectedInstitution);
      formData.append('override_existing', overrideExisting);
      formData.append('disable_ai_categorization', disableAiCategorization);

      const response = await api.post('/files/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      success = response.data.message;
      file = null;

      // Reset file input
      document.getElementById('file-input').value = '';

      // Refresh jobs list
      await loadJobs();
    } catch (err) {
      error = err.response?.data?.detail || err.message;
    } finally {
      uploading = false;
    }
  }

  async function deleteJob(jobId) {
    if (!confirm('Delete this job?')) return;

    try {
      await api.delete(`/files/jobs/${jobId}`);
      await loadJobs();
    } catch (err) {
      error = `Failed to delete job: ${err.message}`;
    }
  }

  async function viewJobLog(jobId) {
    try {
      const response = await api.get(`/files/jobs/${jobId}/log`);
      currentJobLog = response.data;
      viewingJobId = jobId;
      showLogModal = true;
    } catch (err) {
      error = `Failed to load job log: ${err.message}`;
    }
  }

  function downloadJobLog() {
    if (!currentJobLog) return;

    const blob = new Blob([currentJobLog.log_text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `job_${viewingJobId}_log.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function closeLogModal() {
    showLogModal = false;
    currentJobLog = null;
    viewingJobId = null;
  }

  function getStatusColor(status) {
    switch (status) {
      case 'completed': return 'green';
      case 'failed': return 'red';
      case 'processing': return 'blue';
      case 'pending': return 'orange';
      default: return 'gray';
    }
  }

  function getStatusIcon(status) {
    switch (status) {
      case 'completed': return '✓';
      case 'failed': return '✗';
      case 'processing': return '⟳';
      case 'pending': return '⋯';
      default: return '?';
    }
  }

  function formatDate(isoString) {
    if (!isoString) return '-';
    return new Date(isoString).toLocaleString();
  }
</script>

<div class="file-upload-container">
  <h1>File Upload & Processing</h1>

  <!-- Upload Form -->
  <div class="upload-card">
    <h2>Upload New File</h2>

    {#if error}
      <div class="alert alert-error">{error}</div>
    {/if}

    {#if success}
      <div class="alert alert-success">{success}</div>
    {/if}

    <div class="form-group">
      <label for="institution">Institution</label>
      <select id="institution" bind:value={selectedInstitution} disabled={uploading}>
        {#each institutions as inst}
          <option value={inst.id}>{inst.name}</option>
        {/each}
      </select>
      {#if selectedInstitution}
        <small class="help-text">
          Supported formats: {institutions.find(i => i.id === selectedInstitution)?.file_format}
        </small>
      {/if}
    </div>

    <div class="form-group">
      <label for="file-input">File</label>
      <input
        id="file-input"
        type="file"
        accept=".csv,.xlsx,.xls"
        on:change={handleFileSelect}
        disabled={uploading}
      />
      {#if file}
        <small class="help-text">Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)</small>
      {/if}
    </div>

    <div class="form-group checkbox-group">
      <label>
        <input type="checkbox" bind:checked={overrideExisting} disabled={uploading} />
        Override existing transactions
      </label>
      <small class="help-text">
        If checked, existing transactions with same ID will be updated
      </small>
    </div>

    <div class="form-group checkbox-group">
      <label>
        <input type="checkbox" bind:checked={disableAiCategorization} disabled={uploading} />
        Disable AI categorization fallback
      </label>
      <small class="help-text">
        If checked, transactions will only use manual rules and won't fall back to AI categorization
      </small>
    </div>

    <button
      class="btn btn-primary"
      on:click={uploadFile}
      disabled={!file || !selectedInstitution || uploading}
    >
      {uploading ? 'Uploading...' : 'Upload and Process'}
    </button>
  </div>

  <!-- Processing Jobs -->
  <div class="jobs-section">
    <h2>Processing Jobs</h2>

    {#if jobs.length === 0}
      <p class="no-jobs">No processing jobs yet. Upload a file to get started.</p>
    {:else}
      <div class="jobs-table-container">
        <table class="jobs-table">
          <thead>
            <tr>
              <th>Status</th>
              <th>File</th>
              <th>Institution</th>
              <th>Created</th>
              <th>Progress</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each jobs as job}
              <tr class="job-row status-{job.status}">
                <td>
                  <span class="status-badge" style="background-color: {getStatusColor(job.status)}">
                    {getStatusIcon(job.status)} {job.status}
                  </span>
                </td>
                <td>{job.filename}</td>
                <td>{job.institution}</td>
                <td>{formatDate(job.created_at)}</td>
                <td>
                  {#if job.status === 'completed'}
                    <div class="progress-details">
                      <div>📊 Parsed: {job.parsed_rows} | Normalized: {job.normalized_rows}</div>
                      <div>✓ Inserted: {job.inserted_rows} | Updated: {job.updated_rows}</div>
                    </div>
                  {:else if job.status === 'failed'}
                    <div class="error-text">{job.error || 'Processing failed'}</div>
                  {:else if job.status === 'processing'}
                    <div class="progress-text">
                      Parsed: {job.parsed_rows} | Normalized: {job.normalized_rows}
                    </div>
                  {:else}
                    <div class="progress-text">Waiting...</div>
                  {/if}
                </td>
                <td>
                  <button
                    class="btn btn-small btn-secondary"
                    on:click={() => viewJobLog(job.id)}
                    title="View detailed processing log"
                  >
                    📋 Log
                  </button>
                  <button
                    class="btn btn-small btn-danger"
                    on:click={() => deleteJob(job.id)}
                    disabled={job.status === 'processing'}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>

  <!-- Job Log Modal -->
  {#if showLogModal && currentJobLog}
    <div class="modal-backdrop" on:click={closeLogModal}>
      <div class="modal log-modal" on:click|stopPropagation>
        <div class="modal-header">
          <h2>Processing Log: {currentJobLog.filename}</h2>
          <button class="btn-close" on:click={closeLogModal}>✕</button>
        </div>
        <div class="modal-body">
          <div class="log-status">
            Status: <span class="status-badge" style="background-color: {getStatusColor(currentJobLog.status)}">
              {getStatusIcon(currentJobLog.status)} {currentJobLog.status}
            </span>
          </div>
          <pre class="log-content">{currentJobLog.log_text || 'No log entries yet...'}</pre>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" on:click={downloadJobLog}>
            💾 Download Log
          </button>
          <button class="btn btn-primary" on:click={closeLogModal}>Close</button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .file-upload-container {
    padding: 2rem;
    max-width: 1200px;
    margin: 0 auto;
  }

  h1 {
    font-size: 2rem;
    margin-bottom: 2rem;
    color: #333;
  }

  h2 {
    font-size: 1.5rem;
    margin-bottom: 1rem;
    color: #555;
  }

  .upload-card {
    background: white;
    border-radius: 8px;
    padding: 2rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin-bottom: 2rem;
  }

  .alert {
    padding: 1rem;
    border-radius: 4px;
    margin-bottom: 1rem;
  }

  .alert-error {
    background-color: #fee;
    color: #c33;
    border: 1px solid #fcc;
  }

  .alert-success {
    background-color: #efe;
    color: #3a3;
    border: 1px solid #cfc;
  }

  .form-group {
    margin-bottom: 1.5rem;
  }

  .form-group label {
    display: block;
    font-weight: 600;
    margin-bottom: 0.5rem;
    color: #333;
  }

  .form-group select,
  .form-group input[type="file"] {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
  }

  .checkbox-group label {
    display: flex;
    align-items: center;
    font-weight: normal;
  }

  .checkbox-group input[type="checkbox"] {
    margin-right: 0.5rem;
    width: auto;
  }

  .help-text {
    display: block;
    margin-top: 0.25rem;
    font-size: 0.875rem;
    color: #666;
  }

  .btn {
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 4px;
    font-size: 1rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn-primary {
    background-color: #007bff;
    color: white;
  }

  .btn-primary:hover:not(:disabled) {
    background-color: #0056b3;
  }

  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-small {
    padding: 0.25rem 0.75rem;
    font-size: 0.875rem;
  }

  .btn-danger {
    background-color: #dc3545;
    color: white;
  }

  .btn-danger:hover:not(:disabled) {
    background-color: #c82333;
  }

  .jobs-section {
    background: white;
    border-radius: 8px;
    padding: 2rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  }

  .no-jobs {
    text-align: center;
    color: #999;
    padding: 2rem;
  }

  .jobs-table-container {
    overflow-x: auto;
  }

  .jobs-table {
    width: 100%;
    border-collapse: collapse;
  }

  .jobs-table th {
    background-color: #f8f9fa;
    padding: 0.75rem;
    text-align: left;
    font-weight: 600;
    border-bottom: 2px solid #dee2e6;
  }

  .jobs-table td {
    padding: 0.75rem;
    border-bottom: 1px solid #dee2e6;
  }

  .job-row:hover {
    background-color: #f8f9fa;
  }

  .status-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 12px;
    color: white;
    font-size: 0.875rem;
    font-weight: 500;
  }

  .progress-text {
    font-size: 0.875rem;
    color: #666;
  }

  .error-text {
    font-size: 0.875rem;
    color: #dc3545;
  }

  .progress-details {
    font-size: 0.875rem;
    line-height: 1.6;
  }

  .progress-details div {
    margin: 2px 0;
  }

  /* Modal styles */
  .modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal {
    background: white;
    border-radius: 8px;
    width: 90%;
    max-width: 800px;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  }

  .log-modal {
    max-width: 1000px;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.5rem;
    border-bottom: 1px solid #dee2e6;
  }

  .modal-header h2 {
    margin: 0;
    font-size: 1.25rem;
  }

  .btn-close {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    padding: 0;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: background-color 0.2s;
  }

  .btn-close:hover {
    background: rgba(0, 0, 0, 0.1);
  }

  .modal-body {
    padding: 1.5rem;
    overflow-y: auto;
    flex: 1;
  }

  .log-status {
    margin-bottom: 1rem;
    font-size: 1rem;
  }

  .log-content {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 4px;
    font-family: 'Courier New', monospace;
    font-size: 0.875rem;
    line-height: 1.5;
    overflow-x: auto;
    white-space: pre-wrap;
    word-wrap: break-word;
    max-height: 500px;
    overflow-y: auto;
    border: 1px solid #dee2e6;
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
    padding: 1.5rem;
    border-top: 1px solid #dee2e6;
  }
</style>
