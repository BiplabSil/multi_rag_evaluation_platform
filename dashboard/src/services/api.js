/**
 * API Service Module
 * Handles all HTTP communication with the backend API
 * This is a plug-and-play module - configure BASE_URL to connect to your backend
 */

// Base URL for the API - modify this to match your backend URL
const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Common fetch wrapper with error handling
 * @param {string} endpoint - API endpoint path
 * @param {object} options - Fetch options
 * @returns {Promise<object>} - JSON response
 */
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

/**
 * Ingestion Service - Document Upload
 * Ingest a document into the RAG platform
 * @param {object} payload - Document ingestion parameters
 * @param {string} payload.source - File path or URL
 * @param {string} payload.source_type - Type: 'pdf', 'txt', or 'url'
 * @param {string} [payload.document_name] - Optional human-readable name
 * @param {string} [payload.document_version] - Optional version string
 * @returns {Promise<object>} - IngestResponse with document_id, filename, total_chunks
 */
export async function ingestDocument(payload) {
  return fetchAPI('/api/ingest', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Query Service - Ask Questions
 * Run the multi-agent RAG pipeline for a user question
 * @param {object} payload - Query parameters
 * @param {string} payload.question - User's natural-language question
 * @param {string} [payload.ground_truth] - Optional reference answer
 * @returns {Promise<object>} - QueryResponse with answer, chunks, and scores
 */
export async function submitQuery(payload) {
  return fetchAPI('/api/query', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Metrics Service - Get Evaluation Statistics
 * Retrieve aggregate RAGAS evaluation statistics
 * @param {number} [limit=20] - Number of recent queries to include
 * @returns {Promise<object>} - MetricsSummary with averages and recent rows
 */
export async function getMetrics(limit = 20) {
  return fetchAPI(`/api/metrics?limit=${limit}`);
}

/**
 * Search Service - Find Documents by Metadata
 * Search for stored document chunks by metadata filters
 * @param {object} payload - Search parameters
 * @param {string} [payload.document_name] - Filter by document name
 * @param {string} [payload.document_version] - Filter by document version
 * @returns {Promise<object>} - MetadataSearchResponse with results and total count
 */
export async function searchByMetadata(payload) {
  return fetchAPI('/api/search-by-metadata', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Delete Service - Remove Documents from Vector Store
 * Delete document chunks from the vector store by metadata filters
 * @param {object} payload - Delete parameters
 * @param {string} [payload.document_name] - Delete all chunks with this document_name
 * @param {string} [payload.document_version] - Delete all chunks with this version
 * @param {string} [payload.document_id] - Delete by document ID
 * @returns {Promise<object>} - DocumentDeleteResponse with deleted_count
 */
export async function deleteDocuments(payload) {
  return fetchAPI('/api/documents/delete', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Health Check - Test API Connectivity
 * Verify the backend is running and responsive
 * @returns {Promise<boolean>} - True if API is healthy
 */
export async function checkHealth() {
  try {
    const response = await fetchAPI('/api/health');
    return response.status === 'ok';
  } catch {
    return false;
  }
}

/**
 * Tables Service - Get Real-time Table Data
 * Fetch all data from the 4 MySQL tables (documents, chunks, queries, eval_results)
 * @returns {Promise<object>} - Object with count and data for each table
 */
export async function getTablesData() {
  return fetchAPI('/api/tables');
}

export default {
  ingestDocument,
  submitQuery,
  getMetrics,
  searchByMetadata,
  deleteDocuments,
  checkHealth,
  getTablesData,
};