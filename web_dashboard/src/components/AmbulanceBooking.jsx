import React, { useState } from 'react';
import { Ambulance, MapPin, Hospital, AlertCircle, CheckCircle2, ChevronRight, Clock, User } from 'lucide-react';

export default function AmbulanceBooking({
  activeBooking,
  onBookAmbulance,
  onAdvanceBookingStep,
  onCancelBooking
}) {
  const [formData, setFormData] = useState({
    patientName: 'Jane Cooper',
    contact: '+1 (555) 019-2834',
    pickupRoad: 'B',
    hospital: 'Apex Central Trauma Center',
    severity: 'Critical (Code Red)',
    notes: 'Severe chest pain, urgent cardiac bypass requested'
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onBookAmbulance(formData);
  };

  const steps = [
    { id: 1, key: 'DISPATCHED', title: 'Unit Dispatched', desc: 'Ambulance left dispatch center' },
    { id: 2, key: 'APPROACHING', title: 'Approaching Intersection', desc: 'Vehicle enters Road approach zone' },
    { id: 3, key: 'PREEMPTION', title: '2s Yellow -> Green', desc: 'Traffic signal turns GREEN for ambulance' },
    { id: 4, key: 'HOSPITAL_APPROACH', title: 'Hospital Proximity', desc: 'HC-SR04 ultrasonic detects arrival' },
    { id: 5, key: 'GATE_OPENED', title: 'Admitted & Safe', desc: 'Servo gate opens 90°, arrived at ER' }
  ];

  const getCurrentStepIndex = () => {
    if (!activeBooking) return 0;
    const idx = steps.findIndex(s => s.key === activeBooking.status);
    return idx >= 0 ? idx + 1 : 1;
  };

  return (
    <div className="glass-card">
      <div className="card-header">
        <h2 className="card-title">
          <Ambulance size={20} color="var(--color-emergency)" />
          Emergency Ambulance Dispatch & Booking
        </h2>
        {activeBooking && (
          <span className="status-pill emergency">
            MISSION: {activeBooking.id}
          </span>
        )}
      </div>

      {!activeBooking ? (
        // Booking Form
        <form onSubmit={handleSubmit}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Patient Name</label>
              <input
                type="text"
                className="form-input"
                value={formData.patientName}
                onChange={(e) => setFormData({ ...formData, patientName: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Emergency Severity</label>
              <select
                className="form-select"
                value={formData.severity}
                onChange={(e) => setFormData({ ...formData, severity: e.target.value })}
              >
                <option value="Critical (Code Red)">Critical (Code Red) - Immediate Preemption</option>
                <option value="Severe Trauma">Severe Trauma - High Priority</option>
                <option value="Cardiac Emergency">Cardiac Emergency</option>
                <option value="Standard Transfer">Standard Transfer - Normal</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Incoming Approach Road</label>
              <select
                className="form-select"
                value={formData.pickupRoad}
                onChange={(e) => setFormData({ ...formData, pickupRoad: e.target.value })}
              >
                <option value="A">Road A (North Approach)</option>
                <option value="B">Road B (East Expressway)</option>
                <option value="C">Road C (West Highway)</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Destination Hospital</label>
              <select
                className="form-select"
                value={formData.hospital}
                onChange={(e) => setFormData({ ...formData, hospital: e.target.value })}
              >
                <option value="Apex Central Trauma Center">Apex Central Trauma Center</option>
                <option value="City Memorial Hospital">City Memorial Hospital</option>
                <option value="St. Jude General ER">St. Jude General ER</option>
              </select>
            </div>
          </div>

          <div style={{ marginTop: '0.5rem' }}>
            <button type="submit" className="btn btn-emergency" style={{ width: '100%' }}>
              <Ambulance size={18} />
              Dispatch Emergency Ambulance Now (Engage Preemption)
            </button>
          </div>
        </form>
      ) : (
        // Active Mission Tracker
        <div>
          {/* Booking Summary Header */}
          <div style={{
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: 'var(--radius-md)',
            padding: '1rem',
            marginBottom: '1.25rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div>
              <div style={{ fontSize: '1rem', fontWeight: 700, color: '#fff' }}>
                Patient: {activeBooking.patientName}
              </div>
              <div style={{ fontSize: '0.8rem', color: '#cbd5e1', display: 'flex', gap: '1rem', marginTop: '0.25rem' }}>
                <span>Incoming via: <strong>Road {activeBooking.pickupRoad}</strong></span>
                <span>Hospital: <strong>{activeBooking.hospital}</strong></span>
                <span>Level: <strong style={{ color: '#f87171' }}>{activeBooking.severity}</strong></span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {getCurrentStepIndex() < steps.length && (
                <button className="btn btn-primary btn-sm" onClick={onAdvanceBookingStep}>
                  Next Mission Step <ChevronRight size={14} />
                </button>
              )}
              <button className="btn btn-secondary btn-sm" onClick={onCancelBooking}>
                Cancel / Clear
              </button>
            </div>
          </div>

          {/* Stepper Timeline */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '0.5rem' }}>
            {steps.map((s, idx) => {
              const currentIdx = getCurrentStepIndex();
              const isDone = idx + 1 < currentIdx;
              const isActive = idx + 1 === currentIdx;

              return (
                <div
                  key={s.id}
                  style={{
                    background: isActive ? 'rgba(6, 182, 212, 0.15)' : isDone ? 'rgba(16, 185, 129, 0.1)' : 'rgba(255, 255, 255, 0.03)',
                    border: `1px solid ${isActive ? 'var(--color-cyan)' : isDone ? '#10b981' : 'var(--border-subtle)'}`,
                    borderRadius: 'var(--radius-sm)',
                    padding: '0.75rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.35rem'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      color: isActive ? 'var(--color-cyan)' : isDone ? '#10b981' : '#64748b'
                    }}>
                      STEP {s.id}
                    </span>
                    {isDone ? (
                      <CheckCircle2 size={14} color="#10b981" />
                    ) : (
                      <span className="dot-indicator" style={{ background: isActive ? 'var(--color-cyan)' : '#475569' }} />
                    )}
                  </div>
                  <div style={{ fontSize: '0.82rem', fontWeight: 600, color: '#fff' }}>
                    {s.title}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#94a3b8' }}>
                    {s.desc}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
