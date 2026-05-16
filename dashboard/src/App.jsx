/**
 * Main Application Component
 * Dashboard container for the Multi-RAG Evaluation Platform
 *
 * Layout: Sidebar navigation (collapsible) + Main content area
 *
 * Sections:
 * - Ingestion: Upload documents to the RAG system
 * - Chat: Ask questions and view responses with metrics
 * - Metrics: View evaluation scores with charts
 * - Cleanup: Search and delete documents from vector store
 */
import React, { useState } from 'react';
import {
  Upload,
  MessageSquare,
  BarChart3,
  Trash2,
  Database,
  ChevronLeft,
  ChevronRight,
  X,
  CheckCircle,
  LayoutDashboard,
} from 'lucide-react';

import IngestionForm from './components/IngestionForm';
import ChatSection from './components/ChatSection';
import MetricsDashboard from './components/MetricsDashboard';
import CleanupSection from './components/CleanupSection';
import TablesSection from './components/TablesSection';

/**
 * Tab configuration with icons and labels
 */
const TABS = [
  { id: 'ingest', label: 'Ingestion', icon: Upload },
  { id: 'chat', label: 'Chat', icon: MessageSquare },
  { id: 'metrics', label: 'Metrics', icon: BarChart3 },
  { id: 'cleanup', label: 'Cleanup', icon: Trash2 },
  { id: 'tables', label: 'Tables', icon: Database },
];

/**
 * Toast notification component
 * @param {string} message - Toast message
 * @param {string} type - Toast type ('success' or 'error')
 * @param {function} onClose - Close callback
 * @returns {JSX.Element} - Toast element
 */
function Toast({ message, type, onClose }) {
  return (
    <div className={`toast ${type}`}>
      {type === 'success' ? (
        <CheckCircle size={20} style={{ color: 'var(--accent-orange)' }} />
      ) : (
        <X size={20} style={{ color: '#ef4444' }} />
      )}
      <span>{message}</span>
      <button
        onClick={onClose}
        style={{
          background: 'transparent',
          border: 'none',
          color: 'var(--text-muted)',
          cursor: 'pointer',
          padding: '0.25rem',
          marginLeft: '0.5rem',
        }}
      >
        <X size={16} />
      </button>
    </div>
  );
}

/**
 * Sidebar navigation item component
 * @param {object} tab - Tab configuration
 * @param {boolean} isActive - Whether tab is currently active
 * @param {boolean} collapsed - Whether sidebar is collapsed
 * @param {function} onClick - Click handler
 * @returns {JSX.Element} - Navigation item
 */
function NavItem({ tab, isActive, collapsed, onClick }) {
  return (
    <button
      className={`nav-item ${isActive ? 'active' : ''}`}
      onClick={onClick}
      title={collapsed ? tab.label : undefined}
    >
      <tab.icon size={20} />
      {!collapsed && <span className="nav-label">{tab.label}</span>}
    </button>
  );
}

/**
 * Main App component
 * @returns {JSX.Element} - Dashboard application
 */
function App() {
  const [activeTab, setActiveTab] = useState('ingest');
  const [collapsed, setCollapsed] = useState(false);
  const [toast, setToast] = useState(null);

  /**
   * Show toast notification
   * @param {string} message - Toast message
   * @param {string} type - Toast type
   */
  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  /**
   * Handle ingestion success
   */
  const handleIngestSuccess = (response) => {
    showToast(`Document "${response.filename}" ingested successfully!`, 'success');
  };

  /**
   * Handle chat message
   */
  const handleChatMessage = (response) => {
    showToast('Query processed successfully!', 'success');
  };

  /**
   * Handle cleanup success
   */
  const handleCleanupSuccess = (response) => {
    showToast(`${response.deleted_count} documents deleted successfully!`, 'success');
  };

  /**
   * Render active tab content
   */
  const renderContent = () => {
    switch (activeTab) {
      case 'ingest':
        return <IngestionForm onSuccess={handleIngestSuccess} />;
      case 'chat':
        return <ChatSection onMessage={handleChatMessage} />;
      case 'metrics':
        return <MetricsDashboard />;
      case 'cleanup':
        return (
          <CleanupSection
            onSuccess={handleCleanupSuccess}
            onError={(err) => showToast(err.message, 'error')}
          />
        );
      case 'tables':
        return <TablesSection />;
      default:
        return <IngestionForm />;
    }
  };

  return (
    <div className="dashboard-container">
      {/* Sidebar */}
      <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
        {/* Logo/Brand */}
        <div className="sidebar-header">
          {!collapsed && (
            <div className="brand">
              <div className="brand-icon">
                <Database size={20} color="white" />
              </div>
              <div className="brand-text">
                <span className="brand-title">RAG Platform</span>
                <span className="brand-subtitle">Evaluation Dashboard</span>
              </div>
            </div>
          )}
          <button
            className="collapse-btn"
            onClick={() => setCollapsed(!collapsed)}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav">
          {TABS.map((tab) => (
            <NavItem
              key={tab.id}
              tab={tab}
              isActive={activeTab === tab.id}
              collapsed={collapsed}
              onClick={() => setActiveTab(tab.id)}
            />
          ))}
        </nav>

        {/* Collapse hint */}
        {!collapsed && (
          <div className="sidebar-footer">
            <LayoutDashboard size={14} />
            <span>Navigate sections</span>
          </div>
        )}
      </aside>

      {/* Main Content */}
      <main className="main-wrapper">
        {/* Top Bar */}
        <header className="topbar">
          <div className="topbar-left">
            <h1>{TABS.find((t) => t.id === activeTab)?.label || 'Dashboard'}</h1>
          </div>
          <div className="topbar-right">
            <span className="api-badge">
              API: http://localhost:8000
            </span>
          </div>
        </header>

        {/* Content Area */}
        <div className="content-area">
          {renderContent()}
        </div>

        {/* Footer */}
        <footer className="footer">
          Developed by Biplab Sil
        </footer>
      </main>

      {/* Toast Notification */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}

export default App;