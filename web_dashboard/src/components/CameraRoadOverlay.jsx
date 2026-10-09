import React, { useState } from 'react';
import { Camera, Crosshair, Sparkles, RefreshCw, Sliders } from 'lucide-react';

export default function CameraRoadOverlay({
  activeRoad,
  systemMode,
  isEmergency,
  onTriggerEmergency
}) {
  const [showZones, setShowZones] = useState(true);

  return (
    <div className="glass-card">
      <div className="card-header">
        <h2 className="card-title">
          <Camera size={20} color="var(--color-cyan)" />
          YOLO Camera Feed & Road Tracing Overlays
        </h2>
        <div className="card-actions">
          <button
            className={`btn btn-sm ${showZones ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setShowZones(!showZones)}
          >
            <Sliders size={14} /> {showZones ? 'Hide Road Zones' : 'Show Road Zones'}
          </button>
        </div>
      </div>

      {/* Simulated Live Camera Stream Container */}
      <div style={{
        position: 'relative',
        height: '280px',
        background: '#0d131f',
        borderRadius: 'var(--radius-md)',
        overflow: 'hidden',
        border: '1px solid var(--border-subtle)'
      }}>
        {/* Synthetic Video Canvas Background */}
        <svg width="100%" height="100%" viewBox="0 0 1000 600" preserveAspectRatio="none">
          {/* Ground */}
          <rect x="0" y="0" width="1000" height="600" fill="#1e242d" />

          {/* Road A (North approach) */}
          <polygon points="380,0 620,0 580,300 420,300" fill="#2d3748" />
          {/* Road B (East approach) */}
          <polygon points="580,300 1000,320 1000,520 540,430" fill="#2d3748" />
          {/* Road C (West approach) */}
          <polygon points="0,320 420,300 460,430 0,520" fill="#2d3748" />

          {/* Traced Road Polygons Overlay */}
          {showZones && (
            <>
              {/* Zone A */}
              <polygon
                points="390,20 610,20 570,280 430,280"
                fill={activeRoad === 'A' && isEmergency ? 'rgba(239, 68, 68, 0.45)' : 'rgba(59, 130, 246, 0.2)'}
                stroke={activeRoad === 'A' && isEmergency ? '#ef4444' : '#3b82f6'}
                strokeWidth="3"
                strokeDasharray="6,4"
              />
              <text x="500" y="150" fill="#fff" fontSize="20" fontWeight="bold" textAnchor="middle">
                ROAD A (NORTH)
              </text>

              {/* Zone B */}
              <polygon
                points="600,310 980,335 980,505 560,420"
                fill={activeRoad === 'B' && isEmergency ? 'rgba(239, 68, 68, 0.45)' : 'rgba(245, 158, 11, 0.2)'}
                stroke={activeRoad === 'B' && isEmergency ? '#ef4444' : '#f59e0b'}
                strokeWidth="3"
                strokeDasharray="6,4"
              />
              <text x="770" y="420" fill="#fff" fontSize="20" fontWeight="bold" textAnchor="middle">
                ROAD B (EAST)
              </text>

              {/* Zone C */}
              <polygon
                points="20,335 400,310 440,420 20,505"
                fill={activeRoad === 'C' && isEmergency ? 'rgba(239, 68, 68, 0.45)' : 'rgba(168, 85, 247, 0.2)'}
                stroke={activeRoad === 'C' && isEmergency ? '#ef4444' : '#a855f7'}
                strokeWidth="3"
                strokeDasharray="6,4"
              />
              <text x="230" y="420" fill="#fff" fontSize="20" fontWeight="bold" textAnchor="middle">
                ROAD C (WEST)
              </text>
            </>
          )}

          {/* YOLO Detection Box when Ambulance is in road */}
          {isEmergency && (
            <g>
              {activeRoad === 'A' && (
                <>
                  <rect x="440" y="80" width="120" height="90" fill="none" stroke="#ef4444" strokeWidth="4" />
                  <rect x="440" y="55" width="180" height="25" fill="#dc2626" />
                  <text x="445" y="72" fill="#fff" fontSize="14" fontWeight="bold">AMBULANCE [A] 96%</text>
                  <circle cx="500" cy="125" r="6" fill="#10b981" />
                </>
              )}
              {activeRoad === 'B' && (
                <>
                  <rect x="700" y="360" width="130" height="80" fill="none" stroke="#ef4444" strokeWidth="4" />
                  <rect x="700" y="335" width="180" height="25" fill="#dc2626" />
                  <text x="705" y="352" fill="#fff" fontSize="14" fontWeight="bold">AMBULANCE [B] 94%</text>
                  <circle cx="765" cy="400" r="6" fill="#10b981" />
                </>
              )}
              {activeRoad === 'C' && (
                <>
                  <rect x="180" y="360" width="130" height="80" fill="none" stroke="#ef4444" strokeWidth="4" />
                  <rect x="180" y="335" width="180" height="25" fill="#dc2626" />
                  <text x="185" y="352" fill="#fff" fontSize="14" fontWeight="bold">AMBULANCE [C] 95%</text>
                  <circle cx="245" cy="400" r="6" fill="#10b981" />
                </>
              )}
            </g>
          )}
        </svg>

        {/* Live HUD Watermark */}
        <div style={{
          position: 'absolute',
          top: 10,
          left: 12,
          background: 'rgba(0, 0, 0, 0.75)',
          padding: '4px 10px',
          borderRadius: '4px',
          fontSize: '0.72rem',
          fontFamily: 'var(--font-mono)',
          color: '#34d399',
          display: 'flex',
          gap: '0.75rem'
        }}>
          <span>CAM: FEED-01 [1080p]</span>
          <span>YOLOv8n: RUNNING</span>
          <span>LATENCY: 14ms</span>
        </div>
      </div>
    </div>
  );
}
