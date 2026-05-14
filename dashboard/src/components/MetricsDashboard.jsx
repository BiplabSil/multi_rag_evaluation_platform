/**
 * Metrics Dashboard Component
 * Displays RAG evaluation metrics with beautiful charts
 *
 * Features:
 * - Aggregate metrics overview (averages)
 * - Bar chart showing 4 metrics for last 10 queries
 * - Threshold line overlay on the chart
 * - Configurable threshold value
 */
import React, { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { Activity, TrendingUp, Database, RefreshCw, Settings } from 'lucide-react';
import { getMetrics } from '../services/api';

/**
 * MetricOverviewCard Component
 * Shows aggregate metric in a card format
 * @param {string} title - Metric title
 * @param {number} value - Metric value
 * @param {string} icon - Icon component
 * @param {string} color - Color theme
 * @returns {JSX.Element} - Metric card element
 */
function MetricOverviewCard({ title, value, icon: Icon, color }) {
  const colorMap = {
    blue: { bg: 'rgba(59, 130, 246, 0.2)', text: 'var(--accent-blue)' },
    green: { bg: 'rgba(34, 197, 94, 0.2)', text: 'var(--accent-green)' },
    orange: { bg: 'rgba(245, 158, 11, 0.2)', text: 'var(--accent-orange)' },
    purple: { bg: 'rgba(168, 85, 247, 0.2)', text: 'var(--accent-purple)' },
  };

  const style = colorMap[color] || colorMap.blue;

  return (
    <div className="metric-card">
      <div className="metric-header">
        <div className={`metric-icon ${color}`}>
          <Icon size={20} />
        </div>
      </div>
      <div className="metric-value" style={{ color: style.text }}>
        {value?.toFixed(2) || '0.00'}
      </div>
      <div className="metric-label">{title}</div>
    </div>
  );
}

/**
 * MetricsDashboard Component
 * @returns {JSX.Element} - Metrics dashboard with charts
 */
function MetricsDashboard() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [threshold, setThreshold] = useState(0.6);
  const [showSettings, setShowSettings] = useState(false);

  /**
   * Fetch metrics data from API
   */
  const fetchMetrics = async () => {
    setLoading(true);
    setError(null);

    try {
      // Get last 20 runs, we'll display the last 10
      const data = await getMetrics(20);
      setMetrics(data);
    } catch (err) {
      setError(err.message || 'Failed to fetch metrics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  /**
   * Prepare chart data from metrics
   * Shows last 10 queries with 4 metrics each
   */
  const getChartData = () => {
    if (!metrics?.recent || metrics.recent.length === 0) {
      return [];
    }

    // Take last 10 runs (reversed to show oldest to newest)
    const recentRuns = [...metrics.recent].reverse().slice(-10);

    return recentRuns.map((run, index) => ({
      query: `Q${index + 1}`,
      fullQuestion: run.question,
      faithfulness: run.faithfulness || 0,
      answer_relevancy: run.answer_relevancy || 0,
      context_precision: run.context_precision || 0,
      context_recall: run.context_recall || 0,
    }));
  };

  /**
   * Custom tooltip for chart
   */
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div
          style={{
            background: 'var(--bg-secondary)',
            padding: '1rem',
            borderRadius: 8,
            border: '1px solid var(--border-color)',
            boxShadow: 'var(--shadow-lg)',
          }}
        >
          <p style={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
            Query: {data.fullQuestion?.substring(0, 50) || label}
            {data.fullQuestion?.length > 50 ? '...' : ''}
          </p>
          {payload.map((entry, index) => (
            <p key={index} style={{ color: entry.color, fontSize: '0.9rem' }}>
              {entry.name}: {entry.value?.toFixed(2)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="alert alert-error">
          <span>{error}</span>
        </div>
        <button className="btn btn-primary" onClick={fetchMetrics}>
          <RefreshCw size={18} />
          Retry
        </button>
      </div>
    );
  }

  const chartData = getChartData();

  return (
    <div>
      {/* Aggregate Metrics Cards */}
      <div className="metrics-grid">
        <MetricOverviewCard
          title="Faithfulness"
          value={metrics?.avg_faithfulness}
          icon={Activity}
          color="blue"
        />
        <MetricOverviewCard
          title="Answer Relevancy"
          value={metrics?.avg_answer_relevancy}
          icon={TrendingUp}
          color="green"
        />
        <MetricOverviewCard
          title="Context Precision"
          value={metrics?.avg_context_precision}
          icon={Database}
          color="orange"
        />
        <MetricOverviewCard
          title="Context Recall"
          value={metrics?.avg_context_recall}
          icon={Activity}
          color="purple"
        />
      </div>

      {/* Total Queries Info */}
      <div
        style={{
          textAlign: 'center',
          marginBottom: '1.5rem',
          padding: '1rem',
          background: 'var(--bg-secondary)',
          borderRadius: 12,
          color: 'var(--text-secondary)',
        }}
      >
        <strong style={{ color: 'var(--text-primary)', fontSize: '1.1rem' }}>
          {metrics?.total_queries || 0}
        </strong>
        {' '} total evaluated queries
      </div>

      {/* Threshold Settings */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1rem',
        }}
      >
        <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>
          Last 10 Runs - Metric Comparison
        </h3>
        <button
          className="btn btn-secondary"
          onClick={() => setShowSettings(!showSettings)}
          style={{ padding: '0.5rem 1rem', fontSize: '0.9rem' }}
        >
          <Settings size={16} />
          Threshold: {threshold}
        </button>
      </div>

      {/* Threshold Input */}
      {showSettings && (
        <div
          style={{
            marginBottom: '1rem',
            padding: '1rem',
            background: 'var(--bg-secondary)',
            borderRadius: 8,
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
          }}
        >
          <label style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Set Threshold Line:
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={threshold}
            onChange={(e) => setThreshold(parseFloat(e.target.value))}
            style={{ flex: 1, accentColor: 'var(--accent-blue)' }}
          />
          <span
            style={{
              padding: '0.25rem 0.75rem',
              background: threshold >= 0.6 ? 'rgba(34, 197, 94, 0.2)' : 'rgba(245, 158, 11, 0.2)',
              color: threshold >= 0.6 ? 'var(--accent-green)' : 'var(--accent-orange)',
              borderRadius: 4,
              fontWeight: 500,
              minWidth: 60,
              textAlign: 'center',
            }}
          >
            {threshold.toFixed(2)}
          </span>
        </div>
      )}

      {/* Bar Chart */}
      <div className="chart-container">
        {chartData.length > 0 ? (
          <div className="chart-wrapper">
            <ResponsiveContainer width="100%" height={400}>
              <BarChart
                data={chartData}
                margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
                <XAxis
                  dataKey="query"
                  stroke="var(--text-secondary)"
                  tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
                />
                <YAxis
                  stroke="var(--text-secondary)"
                  tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
                  domain={[0, 1]}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  wrapperStyle={{ paddingTop: '1rem' }}
                  formatter={(value) => <span style={{ color: 'var(--text-primary)' }}>{value}</span>}
                />
                {/* Threshold Reference Line */}
                <ReferenceLine
                  y={threshold}
                  stroke="var(--accent-orange)"
                  strokeDasharray="5 5"
                  strokeWidth={2}
                  label={{
                    value: `Threshold (${threshold.toFixed(2)})`,
                    position: 'right',
                    fill: 'var(--accent-orange)',
                    fontSize: 12,
                  }}
                />
                <Bar
                  dataKey="faithfulness"
                  fill="var(--accent-blue)"
                  name="Faithfulness"
                  radius={[4, 4, 0, 0]}
                />
                <Bar
                  dataKey="answer_relevancy"
                  fill="var(--accent-green)"
                  name="Answer Relevancy"
                  radius={[4, 4, 0, 0]}
                />
                <Bar
                  dataKey="context_precision"
                  fill="var(--accent-orange)"
                  name="Context Precision"
                  radius={[4, 4, 0, 0]}
                />
                <Bar
                  dataKey="context_recall"
                  fill="var(--accent-purple)"
                  name="Context Recall"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="empty-state">
            <Activity size={64} />
            <p>No evaluation data available yet. Run some queries to see metrics.</p>
          </div>
        )}
      </div>

      {/* Recent Queries Table */}
      {chartData.length > 0 && (
        <div className="card" style={{ marginTop: '1.5rem' }}>
          <div className="card-header">
            <h3 className="card-title">Recent Queries</h3>
            <button className="btn btn-secondary" onClick={fetchMetrics} style={{ padding: '0.5rem 0.75rem' }}>
              <RefreshCw size={16} />
              Refresh
            </button>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <th style={{ textAlign: 'left', padding: '0.75rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Query</th>
                  <th style={{ textAlign: 'center', padding: '0.75rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Faithfulness</th>
                  <th style={{ textAlign: 'center', padding: '0.75rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Answer Relevancy</th>
                  <th style={{ textAlign: 'center', padding: '0.75rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Context Precision</th>
                  <th style={{ textAlign: 'center', padding: '0.75rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Context Recall</th>
                </tr>
              </thead>
              <tbody>
                {chartData.map((row, index) => (
                  <tr key={index} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '0.75rem', maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {row.fullQuestion?.substring(0, 80)}...
                    </td>
                    <td style={{ textAlign: 'center', padding: '0.75rem' }}>
                      <span style={{
                        padding: '0.25rem 0.5rem',
                        borderRadius: 4,
                        background: row.faithfulness >= threshold ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                        color: row.faithfulness >= threshold ? 'var(--accent-green)' : '#ef4444',
                      }}>
                        {row.faithfulness.toFixed(2)}
                      </span>
                    </td>
                    <td style={{ textAlign: 'center', padding: '0.75rem' }}>
                      <span style={{
                        padding: '0.25rem 0.5rem',
                        borderRadius: 4,
                        background: row.answer_relevancy >= threshold ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                        color: row.answer_relevancy >= threshold ? 'var(--accent-green)' : '#ef4444',
                      }}>
                        {row.answer_relevancy.toFixed(2)}
                      </span>
                    </td>
                    <td style={{ textAlign: 'center', padding: '0.75rem' }}>
                      <span style={{
                        padding: '0.25rem 0.5rem',
                        borderRadius: 4,
                        background: row.context_precision >= threshold ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                        color: row.context_precision >= threshold ? 'var(--accent-green)' : '#ef4444',
                      }}>
                        {row.context_precision.toFixed(2)}
                      </span>
                    </td>
                    <td style={{ textAlign: 'center', padding: '0.75rem' }}>
                      <span style={{
                        padding: '0.25rem 0.5rem',
                        borderRadius: 4,
                        background: row.context_recall >= threshold ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                        color: row.context_recall >= threshold ? 'var(--accent-green)' : '#ef4444',
                      }}>
                        {row.context_recall.toFixed(2)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default MetricsDashboard;