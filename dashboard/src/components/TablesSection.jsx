/**
 * Tables Section Component
 * Display real-time data from all 4 MySQL tables
 *
 * Features:
 * - View documents, chunks, queries, and eval_results tables
 * - Auto-refresh data on tab switch
 * - Expandable table rows for detailed view
 */
import React, { useState, useEffect } from 'react';
import { Table, RefreshCw, Loader, ChevronDown, ChevronRight } from 'lucide-react';
import { getTablesData } from '../services/api';

/**
 * TablesSection Component
 * @returns {JSX.Element} - Tables section component
 */
function TablesSection() {
  const [tablesData, setTablesData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTable, setActiveTable] = useState('documents');
  const [expandedRows, setExpandedRows] = useState({});

  /**
   * Fetch tables data from API
   */
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getTablesData();
      setTablesData(data);
    } catch (err) {
      setError(err.message || 'Failed to fetch table data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  /**
   * Toggle row expansion
   */
  const toggleRow = (tableId, rowId) => {
    setExpandedRows(prev => ({
      ...prev,
      [`${tableId}-${rowId}`]: !prev[`${tableId}-${rowId}`]
    }));
  };

  const tables = [
    { id: 'documents', label: 'Documents', icon: '📄' },
    { id: 'chunks', label: 'Chunks', icon: '📋' },
    { id: 'queries', label: 'Queries', icon: '❓' },
    { id: 'eval_results', label: 'Eval Results', icon: '📊' },
  ];

  const renderTableHeaders = (tableId) => {
    const headers = {
      documents: ['ID', 'Filename', 'Document Name', 'Version', 'Source Type', 'Total Chunks', 'Created At'],
      chunks: ['ID', 'Document ID', 'Index', 'Text Preview', 'Vector ID', 'Created At'],
      queries: ['ID', 'Question', 'Answer', 'Retrieved Chunks', 'Created At'],
      eval_results: ['ID', 'Query ID', 'Faithfulness', 'Answer Relevancy', 'Context Precision', 'Context Recall', 'Evaluated At'],
    };
    return headers[tableId] || [];
  };

  const renderCellValue = (tableId, row, key) => {
    const value = row[key];
    if (value === null || value === undefined) return <span style={{ color: 'var(--text-muted)' }}>NULL</span>;

    if (key === 'text') return <span style={{ maxWidth: '300px', display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{value}</span>;
    if (key === 'question') return <span style={{ maxWidth: '250px', display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{value}</span>;
    if (key === 'answer') return <span style={{ maxWidth: '200px', display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{value}</span>;
    if (key === 'id' || key === 'query_id' || key === 'document_id' || key === 'vector_id') return <code style={{ fontSize: '0.75rem' }}>{String(value).substring(0, 8)}...</code>;
    if (['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall'].includes(key)) return value !== null ? value.toFixed(4) : '-';

    return String(value);
  };

  const renderRow = (tableId, row, index) => {
    const isExpanded = expandedRows[`${tableId}-${row.id}`];

    return (
      <React.Fragment key={row.id || index}>
        <tr
          onClick={() => toggleRow(tableId, row.id)}
          style={{ cursor: 'pointer', background: isExpanded ? 'var(--bg-input)' : 'transparent' }}
        >
          <td style={{ width: '40px', textAlign: 'center' }}>
            {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </td>
          {renderTableHeaders(tableId).map((header, i) => {
            const key = header.toLowerCase().replace(/\s/g, '_');
            return (
              <td key={i} style={{ padding: '0.75rem', borderBottom: '1px solid var(--border-color)', fontSize: '0.85rem' }}>
                {renderCellValue(tableId, row, key)}
              </td>
            );
          })}
        </tr>
        {isExpanded && (
          <tr>
            <td colSpan={renderTableHeaders(tableId).length + 1} style={{ padding: '1rem', background: 'var(--bg-input)', borderBottom: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.85rem' }}>
                <strong style={{ color: 'var(--accent-primary)' }}>Full Data:</strong>
                <pre style={{ marginTop: '0.5rem', padding: '0.75rem', background: 'var(--bg-card)', borderRadius: '6px', overflow: 'auto', maxHeight: '200px', fontSize: '0.75rem' }}>
                  {JSON.stringify(row, null, 2)}
                </pre>
              </div>
            </td>
          </tr>
        )}
      </React.Fragment>
    );
  };

  if (loading) {
    return (
      <div className="tables-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '400px' }}>
        <Loader size={32} style={{ animation: 'spin 1s linear infinite', color: 'var(--accent-primary)' }} />
        <span style={{ marginLeft: '1rem', color: 'var(--text-secondary)' }}>Loading table data...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="tables-container" style={{ padding: '2rem', textAlign: 'center' }}>
        <div className="alert alert-error">
          <span>Error: {error}</span>
        </div>
        <button className="btn btn-primary" onClick={fetchData} style={{ marginTop: '1rem' }}>
          <RefreshCw size={18} />
          Retry
        </button>
      </div>
    );
  }

  const currentTableData = tablesData?.[activeTable];

  return (
    <div className="tables-container">
      {/* Header */}
      <div className="tables-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Table size={24} style={{ color: 'var(--accent-primary)' }} />
          <div>
            <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600 }}>Database Tables</h2>
            <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Real-time view of MySQL database tables
            </p>
          </div>
        </div>
        <button className="btn btn-secondary" onClick={fetchData} disabled={loading}>
          <RefreshCw size={18} style={{ marginRight: '0.5rem' }} />
          Refresh
        </button>
      </div>

      {/* Table Tabs */}
      <div className="tables-tabs">
        {tables.map(table => (
          <button
            key={table.id}
            className={`table-tab ${activeTable === table.id ? 'active' : ''}`}
            onClick={() => setActiveTable(table.id)}
          >
            <span style={{ marginRight: '0.5rem' }}>{table.icon}</span>
            {table.label}
            <span className="table-count">{tablesData?.[table.id]?.count || 0}</span>
          </button>
        ))}
      </div>

      {/* Table Content */}
      <div className="tables-content">
        <div className="table-info">
          <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Showing {currentTableData?.data?.length || 0} of {currentTableData?.count || 0} records
          </span>
        </div>

        {currentTableData?.data?.length > 0 ? (
          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: '40px' }}></th>
                  {renderTableHeaders(activeTable).map((header, i) => (
                    <th key={i} style={{ padding: '0.75rem', textAlign: 'left', background: 'var(--bg-input)', fontSize: '0.85rem', fontWeight: 600 }}>
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {currentTableData.data.map((row, index) => renderRow(activeTable, row, index))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Table size={48} style={{ opacity: 0.3, marginBottom: '1rem' }} />
            <p>No data in this table yet</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default TablesSection;