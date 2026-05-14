/**
 * Cleanup Section Component
 * Search and delete embedding documents from vector store
 *
 * Features:
 * - Search documents by metadata (document_name, document_version)
 * - Preview matching documents before deletion
 * - Delete old documents before ingesting new versions
 * - Confirmation dialog with delete count
 */
import React, { useState } from 'react';
import {
  Search,
  Trash2,
  FolderOpen,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Loader,
} from 'lucide-react';
import { searchByMetadata, deleteDocuments } from '../services/api';

/**
 * CleanupSection Component
 * @param {function} onSuccess - Callback when document is deleted
 * @param {function} onError - Callback on error
 * @returns {JSX.Element} - Cleanup section component
 */
function CleanupSection({ onSuccess, onError }) {
  // Search state
  const [documentName, setDocumentName] = useState('');
  const [documentVersion, setDocumentVersion] = useState('');
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [searchError, setSearchError] = useState(null);

  // Delete state
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState(null);
  const [deleteSuccess, setDeleteSuccess] = useState(null);

  /**
   * Search for documents by metadata
   */
  const handleSearch = async (e) => {
    e.preventDefault();

    if (!documentName.trim() && !documentVersion.trim()) {
      setSearchError('Please enter at least one search criteria');
      return;
    }

    setSearchLoading(true);
    setSearchError(null);
    setSearchResults([]);
    setDeleteSuccess(null);
    setDeleteError(null);

    try {
      const payload = {
        document_name: documentName.trim() || undefined,
        document_version: documentVersion.trim() || undefined,
      };

      const response = await searchByMetadata(payload);
      setSearchResults(response.results || []);
    } catch (err) {
      setSearchError(err.message || 'Search failed');
    } finally {
      setSearchLoading(false);
    }
  };

  /**
   * Delete documents based on search criteria
   */
  const handleDelete = async () => {
    if (!documentName.trim() && !documentVersion.trim()) {
      setDeleteError('No criteria to delete');
      return;
    }

    const confirmMessage = `Are you sure you want to delete all documents${
      documentName.trim() ? ` with name "${documentName}"` : ''
    }${documentVersion.trim() ? ` and version "${documentVersion}"` : ''}?`;

    if (!window.confirm(confirmMessage)) {
      return;
    }

    setDeleteLoading(true);
    setDeleteError(null);
    setDeleteSuccess(null);

    try {
      const payload = {
        document_name: documentName.trim() || undefined,
        document_version: documentVersion.trim() || undefined,
      };

      const response = await deleteDocuments(payload);
      setDeleteSuccess(response);
      setSearchResults([]); // Clear search results after deletion
      setDocumentName('');
      setDocumentVersion('');

      if (onSuccess) {
        onSuccess(response);
      }
    } catch (err) {
      setDeleteError(err.message || 'Delete failed');
      if (onError) {
        onError(err);
      }
    } finally {
      setDeleteLoading(false);
    }
  };

  /**
   * Reset form to initial state
   */
  const handleReset = () => {
    setDocumentName('');
    setDocumentVersion('');
    setSearchResults([]);
    setSearchError(null);
    setDeleteError(null);
    setDeleteSuccess(null);
  };

  return (
    <div className="cleanup-container">
      {/* Search Section */}
      <div className="cleanup-search">
        <div className="card-header">
          <h2 className="card-title">
            <Search size={20} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
            Search Documents
          </h2>
        </div>

        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1rem' }}>
          Search for documents in the vector store using metadata filters before deletion.
        </p>

        {/* Success Alert */}
        {deleteSuccess && (
          <div className="alert alert-success" style={{ marginBottom: '1rem' }}>
            <CheckCircle size={20} />
            <span>
              Successfully deleted {deleteSuccess.deleted_count} chunks from the vector store.
            </span>
          </div>
        )}

        {/* Error Alert */}
        {(searchError || deleteError) && (
          <div className="alert alert-error" style={{ marginBottom: '1rem' }}>
            <XCircle size={20} />
            <span>{searchError || deleteError}</span>
          </div>
        )}

        <form onSubmit={handleSearch}>
          <div className="form-group">
            <label className="form-label">Document Name</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g., HR Policy, Company Handbook"
              value={documentName}
              onChange={(e) => setDocumentName(e.target.value)}
              disabled={searchLoading || deleteLoading}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Document Version</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g., 1.0, v2.0, 2024"
              value={documentVersion}
              onChange={(e) => setDocumentVersion(e.target.value)}
              disabled={searchLoading || deleteLoading}
            />
          </div>

          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={searchLoading || deleteLoading}
              style={{ flex: 1 }}
            >
              {searchLoading ? (
                <Loader size={18} style={{ animation: 'spin 1s linear infinite' }} />
              ) : (
                <>
                  <Search size={18} />
                  Search
                </>
              )}
            </button>

            {(searchResults.length > 0 || deleteSuccess) && (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleReset}
                disabled={searchLoading || deleteLoading}
              >
                Reset
              </button>
            )}
          </div>
        </form>

        {/* Search Results */}
        {searchResults.length > 0 && (
          <div style={{ marginTop: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <FolderOpen size={18} style={{ color: 'var(--accent-primary)' }} />
              <strong>
                Found {searchResults.length} matching chunk(s)
              </strong>
            </div>

            <div className="cleanup-results">
              {searchResults.slice(0, 20).map((result, index) => (
                <div key={index} className="result-item">
                  <div className="doc-info">
                    <span className="doc-name">
                      {result.document_name || 'Unknown Document'}
                    </span>
                    <span className="doc-meta">
                      {result.document_version ? `v${result.document_version} • ` : ''}
                      Chunk ID: {result.id?.substring(0, 8) || index}
                    </span>
                  </div>
                </div>
              ))}

              {searchResults.length > 20 && (
                <div style={{ textAlign: 'center', padding: '0.5rem', color: 'var(--text-muted)' }}>
                  + {searchResults.length - 20} more results
                </div>
              )}
            </div>
          </div>
        )}

        {searchResults.length === 0 && !searchLoading && !searchError && (documentName || documentVersion) && (
          <div style={{ marginTop: '1.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Search size={32} style={{ opacity: 0.5, marginBottom: '0.5rem' }} />
            <p>No documents found matching your criteria</p>
          </div>
        )}
      </div>

      {/* Delete Section */}
      <div className="cleanup-delete">
        <div className="card-header">
          <h2 className="card-title">
            <Trash2 size={20} style={{ marginRight: '0.5rem', verticalAlign: 'middle', color: '#ef4444' }} />
            Delete Documents
          </h2>
        </div>

        <p style={{ color: 'var(--text-secondary', fontSize: '0.9rem', marginBottom: '1rem' }}>
          Delete old documents from the vector store before ingesting new versions. This helps avoid duplicate or outdated embeddings.
        </p>

        {/* Warning Box */}
        <div
          style={{
            background: 'rgba(245, 158, 11, 0.1)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
            borderRadius: 8,
            padding: '1rem',
            marginBottom: '1.5rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
            <AlertTriangle size={20} style={{ color: 'var(--accent-orange)', flexShrink: 0, marginTop: 2 }} />
            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              <strong style={{ color: 'var(--accent-orange)' }}>Warning:</strong> This action cannot be undone.
              All matching chunks will be permanently removed from the vector store.
            </div>
          </div>
        </div>

        {/* Current Search Criteria */}
        <div
          style={{
            padding: '1rem',
            background: 'var(--bg-input)',
            borderRadius: 8,
            marginBottom: '1rem',
          }}
        >
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Delete Criteria
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {documentName && (
              <span style={{ padding: '0.25rem 0.5rem', background: 'var(--bg-card)', borderRadius: 4, fontSize: '0.85rem' }}>
                Name: <strong>{documentName}</strong>
              </span>
            )}
            {documentVersion && (
              <span style={{ padding: '0.25rem 0.5rem', background: 'var(--bg-card)', borderRadius: 4, fontSize: '0.85rem' }}>
                Version: <strong>{documentVersion}</strong>
              </span>
            )}
            {!documentName && !documentVersion && (
              <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                No criteria set - enter search criteria above
              </span>
            )}
          </div>
        </div>

        {/* Delete Button */}
        <button
          className="btn btn-danger"
          onClick={handleDelete}
          disabled={deleteLoading || (!documentName.trim() && !documentVersion.trim())}
          style={{ width: '100%' }}
        >
          {deleteLoading ? (
            <>
              <Loader size={18} style={{ animation: 'spin 1s linear infinite' }} />
              Deleting...
            </>
          ) : (
            <>
              <Trash2 size={18} />
              Delete Matching Documents
            </>
          )}
        </button>

        {/* Quick Tips */}
        <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'var(--bg-input)', borderRadius: 8 }}>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Quick Tips
          </div>
          <ul style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', paddingLeft: '1.25rem', lineHeight: 1.6 }}>
            <li>Search by document name to find all versions</li>
            <li>Search by version to delete specific version</li>
            <li>Clear both fields to delete all documents</li>
            <li>Recommended: Delete before ingesting new version</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default CleanupSection;