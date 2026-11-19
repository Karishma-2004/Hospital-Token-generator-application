import { useEffect, useRef, useState } from 'react';
import { BellRing, Clock } from 'lucide-react';
import { api } from '../lib/api';
import useQueueSocket from '../lib/useQueueSocket';

function beep() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    osc.frequency.value = 880;
    osc.connect(ctx.destination);
    osc.start();
    setTimeout(() => { osc.stop(); ctx.close(); }, 400);
  } catch {
    /* sound is optional */
  }
}

function QueueCard({ item, refresh }) {
  useQueueSocket(item.hospital_id, () => refresh());

  // fire the alert once when the patient becomes "near", and again when it is their turn
  const alerted = useRef({ near: false, turn: false });
  useEffect(() => {
    const trigger = (kind, title, body) => {
      if (alerted.current[kind]) return;
      alerted.current[kind] = true;
      beep();
      if (navigator.vibrate) navigator.vibrate([300, 150, 300]);
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(title, { body });
      }
    };
    if (item.your_turn) {
      trigger('turn', 'It is your turn', `Please go in to ${item.doctor_name} now (token #${item.token_number}).`);
    } else if (item.near) {
      trigger('near', 'Your turn is near', `${item.patients_ahead} patient(s) ahead of you for ${item.doctor_name}.`);
    }
  }, [item.near, item.your_turn, item.patients_ahead, item.doctor_name, item.token_number]);

  return (
    <div className="rounded-2xl border bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm text-slate-500">{item.hospital_name} · {item.doctor_name}</p>
          <p className="text-2xl font-black">Your token #{item.token_number}</p>
        </div>
        <div className="text-right">
          <p className="text-xs uppercase tracking-wide text-slate-500">Now serving</p>
          <p className="text-3xl font-black">{item.now_serving ? `#${item.now_serving}` : '—'}</p>
        </div>
      </div>

      {item.status === 'BOOKED' && (
        <p className="mt-4 rounded-xl bg-slate-50 p-3 text-sm text-slate-600">
          Appointment at {item.appointment_time}. Show your QR ticket at reception to join the queue.
        </p>
      )}

      {item.status === 'CHECKED_IN' && (
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <div className="rounded-xl bg-blue-50 p-4">
            <p className="text-sm text-blue-700">Patients ahead of you</p>
            <p className="text-4xl font-black text-blue-900">{item.patients_ahead}</p>
          </div>
          <div className="rounded-xl bg-blue-50 p-4">
            <p className="flex items-center gap-1 text-sm text-blue-700"><Clock size={14} /> Estimated wait</p>
            <p className="text-4xl font-black text-blue-900">~{item.estimated_wait_minutes} min</p>
          </div>
        </div>
      )}

      {item.near && item.status === 'CHECKED_IN' && (
        <div className="mt-4 flex items-center gap-3 rounded-xl bg-amber-100 p-4 font-semibold text-amber-900">
          <BellRing /> Your turn is near. Please be ready outside the doctor's room.
        </div>
      )}
      {item.your_turn && (
        <div className="mt-4 flex items-center gap-3 rounded-xl bg-green-600 p-4 font-bold text-white">
          <BellRing /> It is your turn. Please go in now.
        </div>
      )}
    </div>
  );
}

/** Live queue cards for the patient's appointments today. Renders nothing if there are none. */
export default function QueueStatus() {
  const [items, setItems] = useState([]);
  const [permission, setPermission] = useState(
    typeof Notification === 'undefined' ? 'unsupported' : Notification.permission
  );

  async function load() {
    try {
      const r = await api.get('/appointments/my-queue/');
      setItems(r.data.items || []);
    } catch {
      /* the main page already shows its own errors */
    }
  }
  useEffect(() => { load(); }, []);

  if (!items.length) return null;
  return (
    <div className="mt-6 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xl font-black">Today's live queue</h2>
        {permission === 'default' && (
          <button
            onClick={() => Notification.requestPermission().then(setPermission)}
            className="rounded-lg border bg-white px-3 py-2 text-sm font-semibold"
          >
            Enable alerts on this device
          </button>
        )}
      </div>
      {items.map((item) => <QueueCard key={item.id} item={item} refresh={load} />)}
    </div>
  );
}