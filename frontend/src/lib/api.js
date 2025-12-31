/**
 * API client for backend communication
 */
import axios from 'axios';

const API_BASE = '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Transactions API
export const transactionsApi = {
  getAll: (params) => api.get('/transactions', { params }),
  getById: (id) => api.get(`/transactions/${id}`),
  update: (id, data) => api.put(`/transactions/${id}`, data),
  delete: (id) => api.delete(`/transactions/${id}`),
  getUncategorized: () => api.get('/transactions/uncategorized/list'),
  reapplyRules: (params) => api.post('/transactions/reapply-rules', null, { params })
};

// Dashboard API
export const dashboardApi = {
  getSummary: (params) => api.get('/dashboard/summary', { params })
};

// Categories API
export const categoriesApi = {
  getTree: () => api.get('/categories/tree'),
  getTier1: () => api.get('/categories/tier1'),
  getTier2: (tier1) => api.get(`/categories/tier2/${tier1}`),
  getTier3: (tier1, tier2) => api.get(`/categories/tier3/${tier1}/${tier2}`),
  createTier1: (name) => api.post(`/categories/tier1?name=${encodeURIComponent(name)}`),
  createTier2: (tier1, name) => api.post(`/categories/tier2/${tier1}?name=${encodeURIComponent(name)}`),
  createTier3: (tier1, tier2, name) => api.post(`/categories/tier3/${tier1}/${tier2}?name=${encodeURIComponent(name)}`),
  deleteTier1: (tier1) => api.delete(`/categories/tier1/${tier1}`),
  deleteTier2: (tier1, tier2) => api.delete(`/categories/tier2/${tier1}/${tier2}`),
  deleteTier3: (tier1, tier2, tier3) => api.delete(`/categories/tier3/${tier1}/${tier2}/${tier3}`)
};

// Rules API
export const rulesApi = {
  getAll: () => api.get('/rules'),
  create: (rule) => api.post('/rules', rule),
  update: (id, rule) => api.put(`/rules/${id}`, rule),
  delete: (id) => api.delete(`/rules/${id}`),
  test: (rule, transaction) => api.post('/rules/test', { rule, transaction })
};

// Accounts API
export const accountsApi = {
  getAll: () => api.get('/accounts'),
  save: (config) => api.post('/accounts', config),
  update: (accountNumber, account) => api.put(`/accounts/${accountNumber}`, account),
  delete: (accountNumber) => api.delete(`/accounts/${accountNumber}`)
};

// Export api for direct use
export { api };

export default api;
