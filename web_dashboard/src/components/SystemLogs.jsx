import React from 'react';
import { Terminal, Trash2 } from 'lucide-react';

export default function SystemLogs({ logs, onClearLogs }) {
  return (
    <div className="glass-card">
      <div className="card-header">
        <h2 className="card-title">
          <Terminal size={18} color="var(--color-cyan)" />
          System Activity & Preemption Audit Log
        </h2>
        <button className="btn btn-secondary btn-sm" onClick={onClearLogs} title="Clear Logs">
          <Trash2 size={14} /> Clear
        </button>
      </div>

      <div className="logs-list">
        {logs.length === 0 ? (
          <div style={{ color: 'var(--text-dim)', fontSize: '0.8rem', padding: '1rem', textAlign: 'center' }}>
            No activity logged yet.
          </div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className={`log-item ${log.type}`}>
              <span className="log-time">{log.time}</span>
              <span style={{ color: '#e2e8f0' }}>{log.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
