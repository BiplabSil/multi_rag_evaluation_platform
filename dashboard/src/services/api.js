/**
 * API Service Module
 * Handles all HTTP communication with the backend API
 */

const BASE_URL = import.meta.env.VITE_API_URL || 'https://x5hp4ju4lj.execute-api.us-east-1.amazonaws.com';

async function fetchAPI(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP error ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`API Error [${endpoint}]:`, error);
    throw error;
  }
}

export async function ingestDocument(payload) {
  return fetchAPI('/api/ingest', { method: 'POST', body: JSON.stringify(payload) });
}

/**
 * submitQuery - Async job pattern
 * POSTs to /api/query and immediately returns job_id
 * Client polls /api/query/status/{job_id} for results
 *
 * @param {object} payload - { question, ground_truth? }
 * @returns {Promise<object>} - { job_id, status, message }
 */
export async function submitQuery(payload) {
  try {
    const response = await fetch(`${BASE_URL}/api/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP error ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Query submission error:', error);
    throw error;
  }
}

/**
 * queryJobStatus - Check job status and results
 *
 * @param {string} jobId - Job ID returned from submitQuery
 * @returns {Promise<object>} - { job_id, status, result?, error? }
 */
export async function queryJobStatus(jobId) {
  try {
    const response = await fetch(`${BASE_URL}/api/query/status/${jobId}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP error ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`Query status error [${jobId}]:`, error);
    throw error;
  }
}

export async function getMetrics(limit = 20) {
  return fetchAPI(`/api/metrics?limit=${limit}`);
}

export async function searchByMetadata(payload) {
  return fetchAPI('/api/search-by-metadata', { method: 'POST', body: JSON.stringify(payload) });
}

export async function deleteDocuments(payload) {
  return fetchAPI('/api/documents/delete', { method: 'POST', body: JSON.stringify(payload) });
}

export async function checkHealth() {
  try {
    const response = await fetchAPI('/api/health');
    return response.status === 'ok';
  } catch {
    return false;
  }
}

export async function getTablesData() {
  return fetchAPI('/api/tables');
}

export default {
  ingestDocument,
  submitQuery,
  queryJobStatus,
  getMetrics,
  searchByMetadata,
  deleteDocuments,
  checkHealth,
  getTablesData,
};
