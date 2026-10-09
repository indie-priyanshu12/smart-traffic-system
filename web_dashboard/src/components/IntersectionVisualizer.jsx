import React from 'react';
import { Play, RotateCcw, AlertTriangle, ShieldCheck, Activity } from 'lucide-react';

export default function IntersectionVisualizer({
  lights,
  activeRoad,
  systemMode,
  transitionTarget,
  transitionRemaining,
  onTriggerEmergency,
  onReset
}) {
  return (
    <div className="glass-card">
      <div className="card-header">
        <h2 className="card-title">
          <Activity size={20} color="var(--color-cyan)" />
          3-Way Intersection Live Telemetry
        </h2>
        <div className="card-actions">
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Phase: <strong style={{ color: '#fff' }}>{systemMode}</strong>
          </span>
          {systemMode !== 'NORMAL' && (
            <button className="btn btn-secondary btn-sm" onClick={onReset}>
              <RotateCcw size={14} /> Reset
            </button>
          )}
        </div>
      </div>

      {/* 2-Second Yellow Transition Banner if active */}
      {systemMode === 'TRANSITION_YELLOW' && (
        <div style={{
          background: 'rgba(245, 158, 11, 0.15)',
          border: '1px solid rgba(245, 158, 11, 0.4)',
          borderRadius: 'var(--radius-sm)',
          padding: '0.65rem 1rem',
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <AlertTriangle size={18} color="var(--color-yellow)" />
            <span style={{ fontSize: '0.88rem', fontWeight: 600 }}>
              Safety Interlock: 2.0s Yellow Light Delay active before Road {transitionTarget} turns GREEN
            </span>
          </div>
          <div style={{
            fontSize: '0.9rem',
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
            color: 'var(--color-yellow)'
          }}>
            {transitionRemaining.toFixed(1)}s
          </div>
        </div>
      )}

      {/* Interactive Intersection Canvas Container */}
      <div className="intersection-wrapper">
        {/* Road A (North Approach - Vertical Top) */}
        <div style={{
          position: 'absolute',
          top: 0,
          left: '38%',
          width: '24%',
          height: '46%',
          background: '#1a202c',
          borderLeft: '2px dashed #4a5568',
          borderRight: '2px dashed #4a5568',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'flex-start',
          paddingTop: '10px'
        }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', letterSpacing: '0.05em' }}>
            ROAD A (NORTH)
          </span>

          {/* Traffic Signal A */}
          <div style={{ marginTop: '12px' }} className="traffic-signal-box">
            <div className={`signal-lamp red ${lights.A === 'RED' ? 'active' : ''}`} />
            <div className={`signal-lamp yellow ${lights.A === 'YELLOW' ? 'active' : ''}`} />
            <div className={`signal-lamp green ${lights.A === 'GREEN' ? 'active' : ''}`} />
          </div>

          {/* Vehicle / Ambulance in Road A */}
          {activeRoad === 'A' && (
            <div style={{
              marginTop: 'auto',
              marginBottom: '10px',
              padding: '4px 10px',
              background: systemMode === 'EMERGENCY' ? '#ef4444' : '#3b82f6',
              borderRadius: '6px',
              fontSize: '0.7rem',
              fontWeight: 800,
              color: '#fff',
              boxShadow: systemMode === 'EMERGENCY' ? '0 0 15px rgba(239, 68, 68, 0.8)' : 'none',
              animation: 'slideDown 0.4s ease'
            }}>
              {systemMode === 'EMERGENCY' ? '🚑 AMBULANCE A' : '🚗 VEHICLE A'}
            </div>
          )}
        </div>

        {/* Road C (West Approach - Horizontal Left) */}
        <div style={{
          position: 'absolute',
          top: '46%',
          left: 0,
          width: '38%',
          height: '34%',
          background: '#1a202c',
          borderTop: '2px dashed #4a5568',
          borderBottom: '2px dashed #4a5568',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 20px'
        }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8' }}>
            ROAD C (WEST)
          </span>

          {activeRoad === 'C' && (
            <div style={{
              padding: '4px 10px',
              background: systemMode === 'EMERGENCY' ? '#ef4444' : '#3b82f6',
              borderRadius: '6px',
              fontSize: '0.7rem',
              fontWeight: 800,
              color: '#fff',
              boxShadow: systemMode === 'EMERGENCY' ? '0 0 15px rgba(239, 68, 68, 0.8)' : 'none'
            }}>
              {systemMode === 'EMERGENCY' ? '🚑 AMBULANCE C' : '🚗 VEHICLE C'}
            </div>
          )}

          {/* Traffic Signal C */}
          <div className="traffic-signal-box">
            <div className={`signal-lamp red ${lights.C === 'RED' ? 'active' : ''}`} />
            <div className={`signal-lamp yellow ${lights.C === 'YELLOW' ? 'active' : ''}`} />
            <div className={`signal-lamp green ${lights.C === 'GREEN' ? 'active' : ''}`} />
          </div>
        </div>

        {/* Central Junction Box */}
        <div style={{
          position: 'absolute',
          top: '46%',
          left: '38%',
          width: '24%',
          height: '34%',
          background: '#151922',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: '1px solid rgba(255,255,255,0.06)'
        }}>
          <div style={{
            width: '80%',
            height: '80%',
            border: '2px dashed rgba(255, 255, 255, 0.15)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: '8px'
          }}>
            <span style={{ fontSize: '0.65rem', color: '#64748b', fontWeight: 600 }}>INTERSECTION</span>
            <span style={{
              fontSize: '0.85rem',
              fontWeight: 800,
              color: systemMode === 'EMERGENCY' ? 'var(--color-emergency)' : 'var(--color-cyan)'
            }}>
              {systemMode === 'EMERGENCY' ? `PRIORITY ${activeRoad}` : `GREEN: ${activeRoad}`}
            </span>
          </div>
        </div>

        {/* Road B (East Approach - Horizontal Right) */}
        <div style={{
          position: 'absolute',
          top: '46%',
          right: 0,
          width: '38%',
          height: '34%',
          background: '#1a202c',
          borderTop: '2px dashed #4a5568',
          borderBottom: '2px dashed #4a5568',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 20px'
        }}>
          {/* Traffic Signal B */}
          <div className="traffic-signal-box">
            <div className={`signal-lamp red ${lights.B === 'RED' ? 'active' : ''}`} />
            <div className={`signal-lamp yellow ${lights.B === 'YELLOW' ? 'active' : ''}`} />
            <div className={`signal-lamp green ${lights.B === 'GREEN' ? 'active' : ''}`} />
          </div>

          {activeRoad === 'B' && (
            <div style={{
              padding: '4px 10px',
              background: systemMode === 'EMERGENCY' ? '#ef4444' : '#3b82f6',
              borderRadius: '6px',
              fontSize: '0.7rem',
              fontWeight: 800,
              color: '#fff',
              boxShadow: systemMode === 'EMERGENCY' ? '0 0 15px rgba(239, 68, 68, 0.8)' : 'none'
            }}>
              {systemMode === 'EMERGENCY' ? '🚑 AMBULANCE B' : '🚗 VEHICLE B'}
            </div>
          )}

          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8' }}>
            ROAD B (EAST)
          </span>
        </div>
      </div>

      {/* Road Trigger / Simulation Bar */}
      <div style={{ marginTop: '1.25rem' }}>
        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>
          Simulation & Manual Preemption Overrides:
        </span>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr) auto', gap: '0.75rem', marginTop: '0.5rem' }}>
          <button
            className={`btn ${activeRoad === 'A' && systemMode === 'EMERGENCY' ? 'btn-emergency' : 'btn-secondary'}`}
            onClick={() => onTriggerEmergency('A')}
          >
            <Play size={14} /> Dispatch to Road A
          </button>
          <button
            className={`btn ${activeRoad === 'B' && systemMode === 'EMERGENCY' ? 'btn-emergency' : 'btn-secondary'}`}
            onClick={() => onTriggerEmergency('B')}
          >
            <Play size={14} /> Dispatch to Road B
          </button>
          <button
            className={`btn ${activeRoad === 'C' && systemMode === 'EMERGENCY' ? 'btn-emergency' : 'btn-secondary'}`}
            onClick={() => onTriggerEmergency('C')}
          >
            <Play size={14} /> Dispatch to Road C
          </button>
          <button className="btn btn-secondary" onClick={onReset} title="Restore Normal Round-Robin Cycle">
            <RotateCcw size={16} /> Reset Normal
          </button>
        </div>
      </div>
    </div>
  );
}
