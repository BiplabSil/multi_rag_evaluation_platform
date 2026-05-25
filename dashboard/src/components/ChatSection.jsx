/**
 * Chat Component
 * Handles user queries and displays RAG pipeline responses
 * Uses async job polling pattern to handle long-running RAG pipelines
 */
import React, { useState } from 'react';
import { MessageSquare, Send, Loader, Target, Brain, Eye, CheckCircle, Clock } from 'lucide-react';
import { submitQuery, queryJobStatus } from '../services/api';

function MetricCard({ label, value, icon: Icon, color }) {
  const getColorValue = () => {
    if (value >= 0.8) return { bg: 'rgba(34, 197, 94, 0.2)', text: 'var(--accent-green)', label: 'Excellent' };
    if (value >= 0.6) return { bg: 'rgba(59, 130, 246, 0.2)', text: 'var(--accent-blue)', label: 'Good' };
    if (value >= 0.4) return { bg: 'rgba(245, 158, 11, 0.2)', text: 'var(--accent-orange)', label: 'Fair' };
    return { bg: 'rgba(239, 68, 68, 0.2)', text: '#ef4444', label: 'Poor' };
  };
  const colorStyle = getColorValue();
  return (
    <div style={{ padding: '1rem', background: 'var(--bg-secondary)', borderRadius: 12, border: '1px solid var(--border-color)', flex: '1 1 200px', minWidth: 180 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
        <div className={`metric-icon ${color}`} style={{ width: 36, height: 36 }}>
          <Icon size={18} />
        </div>
        <span style={{ padding: '0.25rem 0.5rem', borderRadius: 4, fontSize: '0.75rem', fontWeight: 500, background: colorStyle.bg, color: colorStyle.text }}>
          {colorStyle.label}
        </span>
      </div>
      <div style={{ fontSize: '2rem', fontWeight: 700, color: colorStyle.text }}>
        {value?.toFixed(2) || '0.00'}
      </div>
      <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
        {label}
      </div>
    </div>
  );
}

function ChatSection({ onMessage }) {
  const [question, setQuestion] = useState('');
  const [groundTruth, setGroundTruth] = useState('');
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [currentResponse, setCurrentResponse] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError(null);
    setCurrentResponse(null);
    setStatusMessage('Submitting query to backend...');

    try {
      const payload = {
        question: question.trim(),
        ground_truth: groundTruth.trim() || undefined,
      };

      // Submit query and get job_id
      const submitResponse = await submitQuery(payload);
      if (!submitResponse.job_id) {
        throw new Error('No job_id returned from server');
      }

      const jobId = submitResponse.job_id;
      console.log('Job submitted:', jobId);

      // Poll for completion
      let completed = false;
      let pollAttempts = 0;
      const maxAttempts = 600; // 10 minutes at 1s intervals

      while (!completed && pollAttempts < maxAttempts) {
        await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second

        try {
          const statusResponse = await queryJobStatus(jobId);
          console.log('Status:', statusResponse.status);

          if (statusResponse.status === 'running') {
            setStatusMessage(`Processing... (${pollAttempts}s elapsed)`);
          } else if (statusResponse.status === 'completed') {
            setCurrentResponse(statusResponse.result);
            setStatusMessage('');
            if (onMessage) onMessage(statusResponse.result);
            completed = true;
          } else if (statusResponse.status === 'failed') {
            throw new Error(statusResponse.error || 'Pipeline failed');
          }
          pollAttempts++;
        } catch (pollError) {
          if (pollError.message.includes('not found')) {
            // Job not yet created in memory, keep polling
            setStatusMessage('Initializing...');
          } else {
            throw pollError;
          }
          pollAttempts++;
        }
      }

      if (!completed) {
        throw new Error('Query timeout after 10 minutes');
      }
    } catch (err) {
      setError(err.message || 'Query failed');
      setStatusMessage('');
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setQuestion('');
    setGroundTruth('');
    setCurrentResponse(null);
    setError(null);
    setStatusMessage('');
  };

  return (
    <div className="chat-container">
      {/* Query Form */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">
            <MessageSquare size={20} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
            Ask a Question
          </h2>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="alert alert-error" style={{ marginBottom: '1rem' }}>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Your Question</label>
            <textarea
              className="form-textarea"
              placeholder="What would you like to know from your documents?"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={loading}
              rows={3}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Ground Truth (Optional)</label>
            <textarea
              className="form-textarea"
              placeholder="Expected answer for better context_recall evaluation..."
              value={groundTruth}
              onChange={(e) => setGroundTruth(e.target.value)}
              disabled={loading}
              rows={2}
              style={{ fontSize: '0.9rem' }}
            />
          </div>

          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || !question.trim()}
              style={{ flex: 1 }}
            >
              {loading ? (
                <>
                  <Loader size={18} className="spinner" style={{ animation: 'spin 1s linear infinite' }} />
                  Processing...
                </>
              ) : (
                <>
                  <Send size={18} />
                  Get Answer
                </>
              )}
            </button>

            {(currentResponse || error) && (
              <button type="button" className="btn btn-secondary" onClick={handleClear} disabled={loading}>
                Clear
              </button>
            )}
          </div>
        </form>

        {/* Progress Status */}
        {loading && statusMessage && (
          <div style={{ marginTop: '1rem', padding: '0.75rem 1rem', background: 'var(--bg-input)', borderRadius: 8, display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Clock size={16} style={{ color: 'var(--accent-orange)', flexShrink: 0 }} />
            <div>
              <div style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>{statusMessage}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                RAG pipeline takes 3–5 minutes (retrieval → LLM → RAGAS evaluation)
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Response Display */}
      {currentResponse && (
        <div className="card" style={{ animation: 'slideIn 0.3s ease' }}>
          <div className="card-header">
            <h3 className="card-title">Response</h3>
          </div>

          {/* Question */}
          <div style={{ marginBottom: '1.5rem' }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Question
            </div>
            <div style={{ fontSize: '1.1rem', fontWeight: 500, color: 'var(--text-primary)' }}>
              {currentResponse.question}
            </div>
          </div>

          {/* Answer */}
          <div style={{ marginBottom: '1.5rem' }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Answer
            </div>
            <div style={{ fontSize: '1rem', lineHeight: 1.7, color: 'var(--text-primary)', padding: '1rem', background: 'var(--bg-input)', borderRadius: 8 }}>
              {currentResponse.answer || 'No answer received'}
            </div>
          </div>

          {/* Retrieved Chunks */}
          {currentResponse.retrieved_chunks && currentResponse.retrieved_chunks.length > 0 && (
            <div style={{ marginBottom: '1.5rem' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Retrieved Context ({currentResponse.retrieved_chunks.length} chunks)
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {currentResponse.retrieved_chunks.slice(0, 3).map((chunk, index) => (
                  <div key={index} style={{ padding: '0.75rem', background: 'var(--bg-input)', borderRadius: 8, fontSize: '0.85rem', color: 'var(--text-secondary)', borderLeft: '3px solid var(--accent-primary)' }}>
                    {chunk.length > 200 ? `${chunk.substring(0, 200)}...` : chunk}
                  </div>
                ))}
                {currentResponse.retrieved_chunks.length > 3 && (
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textAlign: 'center' }}>
                    + {currentResponse.retrieved_chunks.length - 3} more chunks
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Evaluation Scores */}
          {currentResponse.scores && (
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1rem', textTransform: 'uppercase', letterSpacing: '0.5px', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <CheckCircle size={16} />
                Evaluation Metrics
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
                <MetricCard label="Faithfulness" value={currentResponse.scores.faithfulness} icon={Brain} color="blue" />
                <MetricCard label="Answer Relevancy" value={currentResponse.scores.answer_relevancy} icon={Target} color="green" />
                <MetricCard label="Context Precision" value={currentResponse.scores.context_precision} icon={Eye} color="orange" />
                <MetricCard label="Context Recall" value={currentResponse.scores.context_recall} icon={CheckCircle} color="purple" />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ChatSection;
