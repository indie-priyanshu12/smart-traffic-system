import React from 'react';
import { DoorOpen, Bell, Radio, Eye, CheckCircle2 } from 'lucide-react';

export default function HospitalGateCard({
  gateOpen,
  distanceCm,
  activeRoad,
  isEmergency,
  onToggleGate,
  onDistanceChange
}) {
  // Format 16x2 LCD lines
  const lcdLine1 = isEmergency
    ? `EMERGENCY! RD:${activeRoad} `
    : 'TRAFFIC: NORMAL ';
  const lcdLine2 = gateOpen
    ? `GATE: OPEN  ${distanceCm}cm `
    : distanceCm < 100
    ? `GATE: CLS   ${distanceCm}cm `
    : 'GATE: CLS   >1m ';

  return (
    <div className="glass-card">
      <div className="card-header">
        <h2 className="card-title">
          <DoorOpen size={20} color="var(--color-cyan)" />
          Arduino Uno: Hospital Entrance & Roadside Unit
        </h2>
        <span className="status-pill online">
          I2C LCD & PWM SERVO
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem', marginBottom: '1.25rem' }}>
        {/* 16x2 LCD Display Simulator */}
        <div>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '0.4rem' }}>
            16x2 Roadside LCD (I2C 0x27):
          </span>
          <div className="lcd-container">
            <div className="lcd-line">{lcdLine1.padEnd(16, ' ')}</div>
            <div className="lcd-line">{lcdLine2.padEnd(16, ' ')}</div>
          </div>
          <span style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '0.35rem', display: 'block' }}>
            LiquidCrystal_I2C on Arduino Uno Pins A4 (SDA), A5 (SCL)
          </span>
        </div>

        {/* Ultrasonic Sensor & Gate Control */}
        <div>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '0.4rem' }}>
            HC-SR04 Ultrasonic Distance:
          </span>
          <div style={{
            background: 'rgba(15, 21, 33, 0.85)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
            padding: '0.75rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.5rem'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>Proximity:</span>
              <span style={{
                fontSize: '1.1rem',
                fontFamily: 'var(--font-mono)',
                fontWeight: 700,
                color: distanceCm <= 15 ? 'var(--color-emergency)' : 'var(--color-cyan)'
              }}>
                {distanceCm} cm
              </span>
            </div>

            {/* Interactive distance slider for quick simulation */}
            <input
              type="range"
              min="5"
              max="150"
              value={distanceCm}
              onChange={(e) => onDistanceChange(Number(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--color-cyan)', cursor: 'pointer' }}
            />

            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#64748b' }}>
              <span>5 cm (Close)</span>
              <span style={{ color: distanceCm <= 15 ? 'var(--color-emergency)' : '#94a3b8' }}>
                Threshold: &le; 15 cm
              </span>
              <span>150 cm (Far)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Hospital Gate Barrier Servo Visualizer */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>
            Hospital Entrance Barrier (SG90 Servo on D9):
          </span>
          <span style={{
            fontSize: '0.75rem',
            fontWeight: 700,
            color: gateOpen ? '#10b981' : '#f59e0b'
          }}>
            {gateOpen ? 'BARRIER OPEN (90°)' : 'BARRIER CLOSED (0°)'}
          </span>
        </div>

        <div className="gate-visualizer">
          {/* Post */}
          <div className="gate-post" />
          {/* Rotating Barrier Arm */}
          <div className={`gate-barrier-arm ${gateOpen ? 'open' : ''}`} />

          {/* Road Surface Lines */}
          <div style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            height: '18px',
            background: '#0f172a',
            borderTop: '2px solid #334155',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-around',
            padding: '0 20px'
          }}>
            <span style={{ fontSize: '0.65rem', color: '#64748b' }}>HOSPITAL EMERGENCY BAY ENTRANCE</span>
          </div>

          {/* Status Overlay */}
          <div style={{ position: 'absolute', top: 12, right: 15, textAlign: 'right' }}>
            {gateOpen ? (
              <span style={{
                background: 'rgba(16, 185, 129, 0.2)',
                color: '#10b981',
                border: '1px solid #10b981',
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '0.75rem',
                fontWeight: 700
              }}>
                CLEAR TO ENTER
              </span>
            ) : (
              <span style={{
                background: 'rgba(239, 68, 68, 0.15)',
                color: '#ef4444',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '0.75rem',
                fontWeight: 700
              }}>
                GATE SECURED
              </span>
            )}
          </div>
        </div>

        {/* Manual Gate Control & Buzzer Info */}
        <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem' }}>
          <button
            className={`btn ${gateOpen ? 'btn-secondary' : 'btn-primary'} btn-sm`}
            style={{ flex: 1 }}
            onClick={onToggleGate}
          >
            <DoorOpen size={16} />
            {gateOpen ? 'Close Hospital Gate' : 'Open Hospital Gate (Override)'}
          </button>
        </div>
      </div>
    </div>
  );
}
