/**
 * Ingestion Component
 * Handles document upload to the RAG platform
 *
 * Features:
 * - Upload documents via file path or URL
 * - Specify document name and version
 * - Show upload status and results
 */
import React, { useState } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle } from 'lucide-react';
import { ingestDocument } from '../services/api';

/**
 * IngestionForm Component
 * @param {function} onSuccess - Callback when ingestion succeeds
 * @param {function} onError - Callback when ingestion fails
 * @returns {JSX.Element} - Ingestion form component
 */
function IngestionForm({ onSuccess, onError }) {
  const [source, setSource] = useState('');
  const [sourceType, setSourceType] = useState('pdf');
  const [documentName, setDocumentName] = useState('');
  const [documentVersion, setDocumentVersion] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  /**
   * Handle form submission
   * Sends document metadata to backend for ingestion
   */
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!source.trim()) {
      setError('Please provide a file path or URL');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const payload = {
        source: source.trim(),
        source_type: sourceType,
        document_name: documentName.trim() || undefined,
        document_version: documentVersion.trim() || undefined,
      };

      const response = await ingestDocument(payload);
      setResult(response);

      if (onSuccess) {
        onSuccess(response);
      }
    } catch (err) {
      const errorMessage = err.message || 'Ingestion failed';
      setError(errorMessage);

      if (onError) {
        onError(err);
      }
    } finally {
      setLoading(false);
    }
  };

  /**
   * Reset form to initial state
   */
  const handleReset = () => {
    setSource('');
    setSourceType('pdf');
    setDocumentName('');
    setDocumentVersion('');
    setResult(null);
    setError(null);
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">
          <Upload size={20} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
          Document Ingestion
        </h2>
      </div>

      {/* Success Alert */}
      {result && (
        <div className="alert alert-success">
          <CheckCircle size={20} />
          <div>
            <strong>Document Ingested Successfully!</strong>
            <p style={{ fontSize: '0.9rem', marginTop: '0.25rem' }}>
              {result.filename} - {result.total_chunks} chunks created
            </p>
          </div>
        </div>
      )}

      {/* Error Alert */}
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {/* Source Type Selection */}
        <div className="form-group">
          <label className="form-label">Source Type</label>
          <select
            className="form-select"
            value={sourceType}
            onChange={(e) => setSourceType(e.target.value)}
            disabled={loading}
          >
            <option value="pdf">PDF Document</option>
            <option value="txt">Text File</option>
            <option value="url">Web URL</option>
          </select>
        </div>

        {/* Source Input */}
        <div className="form-group">
          <label className="form-label">
            {sourceType === 'url' ? 'Document URL' : 'File Path'}
          </label>
          <input
            type="text"
            className="form-input"
            placeholder={
              sourceType === 'url'
                ? 'https://example.com/document.pdf'
                : 'C:\\Documents\\report.pdf'
            }
            value={source}
            onChange={(e) => setSource(e.target.value)}
            disabled={loading}
          />
        </div>

        {/* Document Name */}
        <div className="form-group">
          <label className="form-label">Document Name (Optional)</label>
          <input
            type="text"
            className="form-input"
            placeholder="e.g., HR Policy 2024"
            value={documentName}
            onChange={(e) => setDocumentName(e.target.value)}
            disabled={loading}
          />
        </div>

        {/* Document Version */}
        <div className="form-group">
          <label className="form-label">Version (Optional)</label>
          <input
            type="text"
            className="form-input"
            placeholder="e.g., 1.0, v2.0"
            value={documentVersion}
            onChange={(e) => setDocumentVersion(e.target.value)}
            disabled={loading}
          />
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading || !source.trim()}
            style={{ flex: 1 }}
          >
            {loading ? (
              <>
                <span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                Ingesting...
              </>
            ) : (
              <>
                <Upload size={18} />
                Ingest Document
              </>
            )}
          </button>

          {(result || error) && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleReset}
              disabled={loading}
            >
              Reset
            </button>
          )}
        </div>
      </form>

      {/* Result Details */}
      {result && (
        <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'var(--bg-input)', borderRadius: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
            <FileText size={18} style={{ color: 'var(--accent-primary)' }} />
            <strong>Ingestion Details</strong>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.9rem' }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Document ID:</span>
              <span style={{ marginLeft: '0.5rem', fontFamily: 'monospace' }}>{result.document_id}</span>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Filename:</span>
              <span style={{ marginLeft: '0.5rem' }}>{result.filename}</span>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Total Chunks:</span>
              <span style={{ marginLeft: '0.5rem', fontWeight: 'bold', color: 'var(--accent-green)' }}>
                {result.total_chunks}
              </span>
            </div>
            {result.document_name && (
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Name:</span>
                <span style={{ marginLeft: '0.5rem' }}>{result.document_name}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default IngestionForm;