import React, { useState, useEffect, useRef } from 'react';
import Navbar from './components/Navbar';
import IntersectionVisualizer from './components/IntersectionVisualizer';
import HospitalGateCard from './components/HospitalGateCard';
import AmbulanceBooking from './components/AmbulanceBooking';
import CameraRoadOverlay from './components/CameraRoadOverlay';
import SystemLogs from './components/SystemLogs';
import { Siren, ShieldAlert, Cpu } from 'lucide-react';

export default function App() {
  // ---------------------------------------------------------------------------
  // Traffic Lights & System State
  // ---------------------------------------------------------------------------
  const [systemMode, setSystemMode] = useState('NORMAL'); // NORMAL | TRANSITION_YELLOW | EMERGENCY
  const [activeRoad, setActiveRoad] = useState('A');      // Current Green road (or road under yellow)
  const [transitionTarget, setTransitionTarget] = useState(null); // Road to become Green after 2s Yellow
  const [transitionRemaining, setTransitionRemaining] = useState(0.0);
  const [lights, setLights] = useState({ A: 'GREEN', B: 'RED', C: 'RED' });

  // Hospital Gate & Peripherals (Arduino Uno)
  const [gateOpen, setGateOpen] = useState(false);
  const [distanceCm, setDistanceCm] = useState(85);

  // Hardware Status
  const [espConnected, setEspConnected] = useState(false);
  const [espIp, setEspIp] = useState('192.168.1.100');

  // Ambulance Booking
  const [activeBooking, setActiveBooking] = useState(null);

  // Audio Siren
  const [soundEnabled, setSoundEnabled] = useState(false);
  const audioContextRef = useRef(null);
  const sirenOscRef = useRef(null);

  // Event Logs
  const [logs, setLogs] = useState([
    { id: 1, time: '22:05:00', type: 'normal', message: 'Smart Traffic Controller initialized in Normal Cycle mode.' },
    { id: 2, time: '22:05:01', type: 'normal', message: 'ESP32 Wi-Fi REST listener & Arduino Uno Serial connected.' }
  ]);

  const addLog = (message, type = 'normal') => {
    const timeStr = new Date().toLocaleTimeString();
    setLogs(prev => [{ id: Date.now() + Math.random(), time: timeStr, type, message }, ...prev.slice(0, 49)]);
  };

  // ---------------------------------------------------------------------------
  // Audio Siren using Web Audio API
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!soundEnabled || systemMode !== 'EMERGENCY') {
      if (sirenOscRef.current) {
        try {
          sirenOscRef.current.stop();
          sirenOscRef.current.disconnect();
        } catch (e) {}
        sirenOscRef.current = null;
      }
      return;
    }

    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!audioContextRef.current) {
        audioContextRef.current = new AudioContext();
      }
      const ctx = audioContextRef.current;
      if (ctx.state === 'suspended') {
        ctx.resume();
      }

      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      gain.gain.value = 0.08; // Safe, gentle volume

      osc.type = 'sawtooth';
      const now = ctx.currentTime;
      // 2-tone hi-lo frequency siren
      for (let i = 0; i < 20; i++) {
        osc.frequency.setValueAtTime(650, now + i * 0.8);
        osc.frequency.setValueAtTime(900, now + i * 0.8 + 0.4);
      }

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      sirenOscRef.current = osc;
    } catch (e) {
      console.warn('Audio siren error:', e);
    }

    return () => {
      if (sirenOscRef.current) {
        try {
          sirenOscRef.current.stop();
          sirenOscRef.current.disconnect();
        } catch (e) {}
        sirenOscRef.current = null;
      }
    };
  }, [soundEnabled, systemMode]);

  // ---------------------------------------------------------------------------
  // Ultrasonic Sensor Threshold Check (Hospital Gate)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (distanceCm <= 15 && !gateOpen) {
      setGateOpen(true);
      addLog(`[HC-SR04] Distance ${distanceCm}cm <= 15cm: SG90 Servo opened Hospital Gate (90°).`, 'emergency');
    } else if (distanceCm > 15 && gateOpen && (!activeBooking || activeBooking.status === 'GATE_OPENED')) {
      // Auto close after vehicle clears
      const t = setTimeout(() => {
        setGateOpen(false);
        addLog('[HOSPITAL] Vehicle cleared entrance. Servo closed barrier (0°).', 'normal');
      }, 4000);
      return () => clearTimeout(t);
    }
  }, [distanceCm, gateOpen]);

  // ---------------------------------------------------------------------------
  // 2-Second Yellow Transition & Normal Cycle State Machine
  // ---------------------------------------------------------------------------
  useEffect(() => {
    let timer;

    // 1. In 2-Second Yellow Transition
    if (systemMode === 'TRANSITION_YELLOW') {
      const intervalMs = 100;
      timer = setInterval(() => {
        setTransitionRemaining(prev => {
          if (prev <= 0.15) {
            clearInterval(timer);
            // Complete Yellow transition! Turn target road GREEN!
            const newGreen = transitionTarget;
            setActiveRoad(newGreen);
            setSystemMode('EMERGENCY');
            setTransitionTarget(null);
            setLights({
              A: newGreen === 'A' ? 'GREEN' : 'RED',
              B: newGreen === 'B' ? 'GREEN' : 'RED',
              C: newGreen === 'C' ? 'GREEN' : 'RED'
            });
            addLog(`[SIGNAL PREEMPTION] 2.0s Yellow delay complete! Road ${newGreen} is now GREEN. All others RED.`, 'emergency');
            return 0.0;
          }
          return prev - 0.1;
        });
      }, intervalMs);

      return () => clearInterval(timer);
    }

    // 2. In Normal Cycle
    if (systemMode === 'NORMAL') {
      timer = setTimeout(() => {
        // Transition current road to Yellow for 2 seconds
        setLights(prev => ({
          ...prev,
          [activeRoad]: 'YELLOW'
        }));
        addLog(`[NORMAL CYCLE] Road ${activeRoad} entering 2.0s Yellow warning before next phase.`, 'transition');

        const yellowTimer = setTimeout(() => {
          // Advance to next road in round-robin: A -> B -> C -> A
          const nextRoad = activeRoad === 'A' ? 'B' : activeRoad === 'B' ? 'C' : 'A';
          setActiveRoad(nextRoad);
          setLights({
            A: nextRoad === 'A' ? 'GREEN' : 'RED',
            B: nextRoad === 'B' ? 'GREEN' : 'RED',
            C: nextRoad === 'C' ? 'GREEN' : 'RED'
          });
          addLog(`[NORMAL CYCLE] Phase advanced: Road ${nextRoad} is now GREEN.`, 'normal');
        }, 2000);

        return () => clearTimeout(yellowTimer);
      }, 8000); // 8s Green per road

      return () => clearTimeout(timer);
    }
  }, [systemMode, activeRoad, transitionTarget]);

  // ---------------------------------------------------------------------------
  // Trigger Emergency Preemption (e.g. from Camera, Button, or Booking)
  // ---------------------------------------------------------------------------
  const triggerEmergency = (targetRoad) => {
    targetRoad = targetRoad.toUpperCase();

    // If target road is already GREEN, immediately lock into Emergency mode
    if (activeRoad === targetRoad && lights[targetRoad] === 'GREEN') {
      setSystemMode('EMERGENCY');
      addLog(`[EMERGENCY] Road ${targetRoad} already Green. Locked in Priority Preemption mode.`, 'emergency');
      return;
    }

    // Otherwise, execute the required 2-second Yellow Light transition on the current road
    setTransitionTarget(targetRoad);
    setTransitionRemaining(2.0);
    setSystemMode('TRANSITION_YELLOW');
    setLights(prev => ({
      ...prev,
      [activeRoad]: 'YELLOW'
    }));

    addLog(`[SAFETY PROTOCOL] Emergency detected for Road ${targetRoad}! Setting Road ${activeRoad} to YELLOW (2.0s delay).`, 'transition');
  };

  const resetToNormal = () => {
    setSystemMode('NORMAL');
    setTransitionTarget(null);
    setTransitionRemaining(0.0);
    setLights({
      A: activeRoad === 'A' ? 'GREEN' : 'RED',
      B: activeRoad === 'B' ? 'GREEN' : 'RED',
      C: activeRoad === 'C' ? 'GREEN' : 'RED'
    });
    addLog('[SYSTEM] Emergency preemption cleared. Restored normal round-robin cycle.', 'normal');
  };

  // ---------------------------------------------------------------------------
  // Ambulance Booking Handler
  // ---------------------------------------------------------------------------
  const handleBookAmbulance = (bookingData) => {
    const booking = {
      ...bookingData,
      id: `MED-${Math.floor(1000 + Math.random() * 9000)}`,
      status: 'DISPATCHED',
      createdAt: new Date().toLocaleTimeString()
    };
    setActiveBooking(booking);
    addLog(`[DISPATCH] Emergency Mission ${booking.id} dispatched for ${booking.patientName} via Road ${booking.pickupRoad}.`, 'emergency');
  };

  const advanceBookingStep = () => {
    if (!activeBooking) return;

    if (activeBooking.status === 'DISPATCHED') {
      setActiveBooking({ ...activeBooking, status: 'APPROACHING' });
      addLog(`[MISSION] Ambulance ${activeBooking.id} reached Road ${activeBooking.pickupRoad} approach zone.`, 'emergency');
      triggerEmergency(activeBooking.pickupRoad);
    } else if (activeBooking.status === 'APPROACHING') {
      setActiveBooking({ ...activeBooking, status: 'PREEMPTION' });
      addLog(`[MISSION] Traffic preemption active for Road ${activeBooking.pickupRoad}. Ambulance passing intersection.`, 'emergency');
    } else if (activeBooking.status === 'PREEMPTION') {
      setActiveBooking({ ...activeBooking, status: 'HOSPITAL_APPROACH' });
      setDistanceCm(12); // Simulate vehicle triggering ultrasonic sensor (<15cm)
      addLog(`[MISSION] Ambulance arriving at hospital gate! Proximity sensor triggered at 12cm.`, 'emergency');
    } else if (activeBooking.status === 'HOSPITAL_APPROACH') {
      setActiveBooking({ ...activeBooking, status: 'GATE_OPENED' });
      addLog(`[MISSION COMPLETE] Patient ${activeBooking.patientName} admitted to ER. Mission accomplished!`, 'normal');
    }
  };

  const cancelBooking = () => {
    addLog(`[MISSION] Booking ${activeBooking?.id} ended/archived.`, 'normal');
    setActiveBooking(null);
    setDistanceCm(85);
    resetToNormal();
  };

  return (
    <div className="app-container">
      {/* Navigation Header */}
      <Navbar
        systemMode={systemMode}
        activeRoad={activeRoad}
        espConnected={espConnected}
        espIp={espIp}
        soundEnabled={soundEnabled}
        toggleSound={() => setSoundEnabled(!soundEnabled)}
        onReset={resetToNormal}
      />

      <main className="dashboard-content">
        {/* Emergency Preemption Banner */}
        {systemMode === 'EMERGENCY' && (
          <div className="emergency-banner">
            <div className="banner-left">
              <Siren size={30} className="banner-siren" />
              <div>
                <div className="banner-title">
                  PRIORITY EMERGENCY PREEMPTION ACTIVE - ROAD {activeRoad}
                </div>
                <div className="banner-desc">
                  Camera AI detected emergency vehicle. ESP32 signal locked to GREEN on Road {activeRoad}. Other roads locked RED.
                </div>
              </div>
            </div>
            <div className="banner-actions">
              <button className="btn btn-secondary btn-sm" onClick={resetToNormal}>
                Release Preemption
              </button>
            </div>
          </div>
        )}

        {/* Top Grid: Intersection Visualizer & Hospital Gate */}
        <div className="grid-main">
          <IntersectionVisualizer
            lights={lights}
            activeRoad={activeRoad}
            systemMode={systemMode}
            transitionTarget={transitionTarget}
            transitionRemaining={transitionRemaining}
            onTriggerEmergency={triggerEmergency}
            onReset={resetToNormal}
          />

          <HospitalGateCard
            gateOpen={gateOpen}
            distanceCm={distanceCm}
            activeRoad={activeRoad}
            isEmergency={systemMode === 'EMERGENCY'}
            onToggleGate={() => setGateOpen(!gateOpen)}
            onDistanceChange={(val) => setDistanceCm(val)}
          />
        </div>

        {/* Middle Section: Ambulance Booking & Mission Tracker */}
        <AmbulanceBooking
          activeBooking={activeBooking}
          onBookAmbulance={handleBookAmbulance}
          onAdvanceBookingStep={advanceBookingStep}
          onCancelBooking={cancelBooking}
        />

        {/* Bottom Grid: Camera Road Overlay & System Logs */}
        <div className="grid-bottom">
          <CameraRoadOverlay
            activeRoad={activeRoad}
            systemMode={systemMode}
            isEmergency={systemMode === 'EMERGENCY'}
            onTriggerEmergency={triggerEmergency}
          />

          <SystemLogs
            logs={logs}
            onClearLogs={() => setLogs([])}
          />
        </div>
      </main>
    </div>
  );
}
