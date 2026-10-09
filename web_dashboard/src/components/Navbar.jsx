import React from 'react';
import { Siren, Cpu, Wifi, Radio, Volume2, VolumeX, ShieldAlert } from 'lucide-react';

export default function Navbar({
  systemMode,
  activeRoad,
  espConnected,
  espIp,
  soundEnabled,
  toggleSound,
  onReset
}) {
  return (
    <header className="navbar">
      <div className="brand">
        <div className="brand-icon-box">
          <Siren size={26} className={systemMode === 'EMERGENCY' ? 'banner-siren' : ''} />
        </div>
        <div>
          <h1 className="brand-title">
            Smart Traffic AI <span style={{ color: 'var(--color-cyan)', fontSize: '0.85rem' }}>v2.4 IoT</span>
          </h1>
          <p className="brand-subtitle">Emergency Vehicle Preemption & Hospital Gateway</p>
        </div>
      </div>

      <div className="nav-badges">
        {/* ESP32 Status */}
        <div className={`status-pill ${espConnected ? 'online' : ''}`}>
          <Wifi size={14} />
          <span>ESP32: {espConnected ? `ONLINE (${espIp})` : 'READY (MOCK)'}</span>
          <span className="dot-indicator" style={{ color: espConnected ? '#10b981' : '#f59e0b' }} />
        </div>

        {/* Arduino Roadside Status */}
        <div className="status-pill online">
          <Cpu size={14} />
          <span>ARDUINO UNO: ACTIVE</span>
          <span className="dot-indicator" style={{ color: '#10b981' }} />
        </div>

        {/* System State Pill */}
        <div className={`status-pill ${systemMode === 'EMERGENCY' ? 'emergency' : ''}`}>
          <ShieldAlert size={14} />
          <span>
            {systemMode === 'EMERGENCY' ? `PRIORITY: ROAD ${activeRoad}` :
             systemMode === 'TRANSITION_YELLOW' ? 'TRANSITION: 2.0s YELLOW' : 'NORMAL CYCLE'}
          </span>
          <span className="dot-indicator" />
        </div>

        {/* Siren Sound Toggle */}
        <button
          className={`btn btn-sm ${soundEnabled ? 'btn-primary' : 'btn-secondary'}`}
          onClick={toggleSound}
          title={soundEnabled ? 'Disable Audio Siren' : 'Enable Audio Siren'}
        >
          {soundEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
          <span>{soundEnabled ? 'Audio ON' : 'Audio Muted'}</span>
        </button>

        {systemMode !== 'NORMAL' && (
          <button className="btn btn-secondary btn-sm" onClick={onReset}>
            Reset Normal
          </button>
        )}
      </div>
    </header>
  );
}
