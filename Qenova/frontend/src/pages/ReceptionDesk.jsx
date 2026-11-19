import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Camera, CameraOff, MonitorPlay, Radio, UserPlus } from 'lucide-react';
import { api } from '../lib/api';
import { apiError } from '../lib/errors';
import useQueueSocket from '../lib/useQueueSocket';
import QrScanner from '../components/QrScanner';

const STATUS_STYLE = {
  BOOKED: 'bg-slate-100 text-slate-700',
  CHECKED_IN: 'bg-blue-100 text-blue-700',
  IN_CONSULTATION: 'bg-amber-100 text-amber-800',
  COMPLETED: 'bg-green-100 text-green-700',
};
const STATUS_LABEL = {
  BOOKED: 'Booked',
  CHECKED_IN: 'Waiting',
  IN_CONSULTATION: 'With doctor',
  COMPLETED: 'Completed',
};
const PAYMENT_LABEL = { PAID: 'Paid', NOT_REQUIRED: 'No fee', REFUND_DUE: 'Refund due', UNPAID: 'Unpaid' };
const input = 'rounded-lg border p-3';

function Detail({ label, value }) {
  return (
    <div className="rounded-xl bg-white/70 p-3">
      <p className="text-xs uppercase tracking-wide text-green-800/70">{label}</p>
      <p className="mt-0.5 font-bold text-slate-900">{value}</p>
    </div>
  );
}

export default function ReceptionDesk() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState('');
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState(null); // { ok: true, a, time } or { ok: false, text }
  const [manualCode, setManualCode] = useState('');
  const [walkIn, setWalkIn] = useState({ doctor: '', name: '', phone: '' });
  const [walkResult, setWalkResult] = useState(null);
  const [doctorFilter, setDoctorFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const busy = useRef(false);
  const handled = useRef(new Set()); // QR codes already processed, so one QR is never sent twice

  async function load() {
    try {
      const r = await api.get('/appointments/reception/today/');
      setData(r.data);
    } catch (e) {
      setErr(apiError(e, 'Unable to load today\'s appointments.'));
    }
  }
  useEffect(() => { load(); }, []);

  const live = useQueueSocket(data?.hospital?.id, () => load());

  async function submitScan(text, force = false) {
    if (busy.current || (!force && handled.current.has(text))) return;
    busy.current = true;
    try {
      const r = await api.post('/appointments/reception/scan/', { payload: text });
      handled.current.add(text);
      setScanResult({
        ok: true,
        a: r.data.appointment,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      });
      setManualCode('');
      load();
    } catch (e) {
      if (e.response?.status === 409) handled.current.add(text); // really used before: say so once, not on every frame
      setScanResult({ ok: false, text: apiError(e, 'Check-in failed.') });
    } finally {
      busy.current = false;
    }
  }

  function scanNext() {
    setScanResult(null);
    handled.current.clear();
  }

  async function manualCheckIn(id) {
    try {
      await api.post(`/appointments/${id}/status/`, { status: 'CHECKED_IN' });
      load();
    } catch (e) {
      setErr(apiError(e, 'Unable to check in.'));
    }
  }

  async function recordCash(id) {
    try {
      await api.post(`/appointments/${id}/pay/cash/`);
      load();
    } catch (e) {
      setErr(apiError(e, 'Unable to record the payment.'));
    }
  }

  async function addWalkIn(e) {
    e.preventDefault();
    setErr('');
    try {
      const r = await api.post('/appointments/reception/walk-in/', walkIn);
      setWalkResult(r.data);
      setWalkIn({ doctor: walkIn.doctor, name: '', phone: '' });
      load();
    } catch (e2) {
      setWalkResult(null);
      setErr(apiError(e2, 'Unable to register walk-in patient.'));
    }
  }

  const rows = (data?.appointments || []).filter(
    (a) => (!doctorFilter || String(a.doctor_id) === doctorFilter) && (!statusFilter || a.status === statusFilter)
  );
  const counts = data?.counts;
  const ok = scanResult?.ok ? scanResult.a : null;

  return (
    <div className="mx-auto max-w-7xl px-6 py-10">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-green-700">Reception desk</p>
          <h1 className="text-4xl font-black">{data?.hospital?.name || 'Today'}</h1>
          <p className="mt-2 flex items-center gap-2 text-slate-500">
            {data?.date}
            <span className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${live ? 'bg-green-100 text-green-700' : 'bg-slate-200 text-slate-600'}`}>
              <Radio size={12} /> {live ? 'Live' : 'Refreshing every 5s'}
            </span>
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {data?.hospital && (
            <a href={`/queue-board/${data.hospital.id}`} target="_blank" rel="noreferrer" className="flex items-center gap-2 rounded-lg border bg-white px-4 py-2 text-sm font-semibold">
              <MonitorPlay size={16} /> Open lobby display
            </a>
          )}
          <Link to="/receptionist" className="rounded-lg border bg-white px-4 py-2 text-sm font-semibold">Manage doctors &amp; departments</Link>
        </div>
      </div>

      {err && <div className="mt-5 rounded-xl bg-red-50 p-3 text-sm text-red-700">{err}</div>}

      {counts && (
        <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-5">
          {[
            ['Expected', counts.booked],
            ['Waiting', counts.waiting],
            ['With doctor', counts.in_consultation],
            ['Completed', counts.completed],
            ['Walk-ins', counts.walk_ins],
          ].map(([label, value]) => (
            <div key={label} className="rounded-2xl border bg-white p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
              <p className="mt-1 text-3xl font-black">{value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        {/* ---------------- QR scan ---------------- */}
        <section className="rounded-2xl border bg-white p-6">
          <div className="flex items-center justify-between">
            <h2 className="font-bold">Scan patient QR</h2>
            <button
              onClick={() => { setScanning(!scanning); setScanResult(null); handled.current.clear(); }}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold text-white ${scanning ? 'bg-slate-700' : 'bg-green-600'}`}
            >
              {scanning ? <><CameraOff size={16} /> Stop camera</> : <><Camera size={16} /> Start camera</>}
            </button>
          </div>
          <p className="mt-1 text-sm text-slate-500">Each QR code works once. Hold the patient's ticket in front of the camera.</p>
          <div className="mt-4">{scanning && <QrScanner onScan={submitScan} />}</div>

          {ok && (
            <div className="mt-4 rounded-2xl border-2 border-green-500 bg-green-50 p-5">
              <div className="flex items-center gap-4">
                <svg viewBox="0 0 52 52" className="h-16 w-16 shrink-0" aria-hidden="true">
                  <circle cx="26" cy="26" r="24" fill="#16a34a" />
                  <path d="M14 27 l8 8 l16 -17" fill="none" stroke="#fff" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <div>
                  <p className="text-2xl font-black text-green-800">Check-in successful</p>
                  <p className="text-sm text-green-800/80">The patient has been added to the queue.</p>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3">
                <Detail label="Patient" value={ok.patient_name} />
                <Detail label="Doctor" value={ok.doctor_name} />
                <Detail label="Token" value={`#${ok.token_number}`} />
                <Detail label="Appointment time" value={ok.appointment_time} />
                <Detail label="Checked in at" value={scanResult.time} />
                <Detail label="Fee" value={`INR ${ok.fee} · ${PAYMENT_LABEL[ok.payment_status] || ok.payment_status}`} />
              </div>
              <button onClick={scanNext} className="mt-4 w-full rounded-lg bg-green-600 p-3 font-semibold text-white">Scan next patient</button>
            </div>
          )}

          {scanResult && !scanResult.ok && (
            <div className="mt-4 rounded-2xl border-2 border-red-400 bg-red-50 p-5">
              <div className="flex items-center gap-4">
                <svg viewBox="0 0 52 52" className="h-12 w-12 shrink-0" aria-hidden="true">
                  <circle cx="26" cy="26" r="24" fill="#dc2626" />
                  <path d="M17 17 l18 18 M35 17 l-18 18" fill="none" stroke="#fff" strokeWidth="5" strokeLinecap="round" />
                </svg>
                <div>
                  <p className="text-lg font-black text-red-800">Could not check in</p>
                  <p className="text-sm text-red-700">{scanResult.text}</p>
                </div>
              </div>
              <button onClick={scanNext} className="mt-4 w-full rounded-lg border border-red-300 bg-white p-3 font-semibold text-red-700">Try another QR</button>
            </div>
          )}

          <form
            onSubmit={(e) => { e.preventDefault(); if (manualCode.trim()) submitScan(manualCode.trim(), true); }}
            className="mt-4 flex gap-2"
          >
            <input value={manualCode} onChange={(e) => setManualCode(e.target.value)} className={`min-w-0 flex-1 ${input}`} placeholder="No camera? Paste the QR text (MB1:…)" />
            <button className="rounded-lg border px-4 font-semibold">Check in</button>
          </form>
        </section>

        {/* ---------------- Walk-in ---------------- */}
        <section className="rounded-2xl border bg-white p-6">
          <h2 className="flex items-center gap-2 font-bold"><UserPlus size={18} /> Walk-in patient</h2>
          <p className="mt-1 text-sm text-slate-500">For patients without a booking. They join the queue immediately.</p>
          <form onSubmit={addWalkIn} className="mt-4 grid gap-3">
            <select required className={input} value={walkIn.doctor} onChange={(e) => setWalkIn({ ...walkIn, doctor: e.target.value })}>
              <option value="">Select doctor</option>
              {data?.doctors.map((d) => <option key={d.id} value={d.id}>{d.name} · {d.department}</option>)}
            </select>
            <input required className={input} placeholder="Patient name" value={walkIn.name} onChange={(e) => setWalkIn({ ...walkIn, name: e.target.value })} />
            <input className={input} placeholder="Phone (optional)" value={walkIn.phone} onChange={(e) => setWalkIn({ ...walkIn, phone: e.target.value })} />
            <button className="rounded-lg bg-green-600 p-3 font-semibold text-white">Generate token</button>
          </form>
          {walkResult && (
            <div className="mt-4 rounded-2xl bg-green-50 p-5 text-center">
              <p className="text-sm text-green-700">Token generated</p>
              <p className="text-6xl font-black text-green-800">#{walkResult.appointment.token_number}</p>
              <p className="mt-2 font-semibold">{walkResult.appointment.patient_name}</p>
              <p className="text-sm text-slate-600">{walkResult.appointment.doctor_name}</p>
              <p className="mt-1 text-sm text-slate-600">Patients ahead: {walkResult.patients_ahead}</p>
            </div>
          )}
        </section>
      </div>

      {/* ---------------- Today's list ---------------- */}
      <section className="mt-6 rounded-2xl border bg-white p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-bold">Today's appointments</h2>
          <div className="flex flex-wrap gap-2">
            <select className="rounded-lg border p-2 text-sm" value={doctorFilter} onChange={(e) => setDoctorFilter(e.target.value)}>
              <option value="">All doctors</option>
              {data?.doctors.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
            <select className="rounded-lg border p-2 text-sm" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">All statuses</option>
              {Object.keys(STATUS_LABEL).map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
            </select>
          </div>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b">
                <th className="p-3">Token</th><th className="p-3">Patient</th><th className="p-3">Doctor</th>
                <th className="p-3">Time</th><th className="p-3">Status</th><th className="p-3">Payment</th><th className="p-3">Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((a) => (
                <tr key={a.id} className="border-b">
                  <td className="p-3 font-bold">#{a.token_number}</td>
                  <td className="p-3">
                    {a.patient_name}
                    {a.is_walk_in && <span className="ml-2 rounded-full bg-purple-100 px-2 py-0.5 text-xs text-purple-700">Walk-in</span>}
                  </td>
                  <td className="p-3">{a.doctor_name}</td>
                  <td className="p-3">{a.is_walk_in ? 'Walk-in' : a.appointment_time}</td>
                  <td className="p-3"><span className={`rounded-full px-3 py-1 text-xs font-semibold ${STATUS_STYLE[a.status] || ''}`}>{STATUS_LABEL[a.status] || a.status}</span></td>
                  <td className="p-3">
                    {a.payment_status === 'UNPAID' ? (
                      <button onClick={() => recordCash(a.id)} className="rounded-lg bg-amber-100 px-3 py-1 font-semibold text-amber-800">
                        Cash received · INR {a.fee}
                      </button>
                    ) : (
                      <span className="text-xs text-slate-600">{PAYMENT_LABEL[a.payment_status] || a.payment_status}</span>
                    )}
                  </td>
                  <td className="p-3">
                    {a.status === 'BOOKED' && (
                      <button onClick={() => manualCheckIn(a.id)} className="rounded-lg bg-blue-600 px-3 py-1 text-white">Check in</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!rows.length && <p className="p-6 text-center text-slate-500">No appointments for today.</p>}
        </div>
      </section>
    </div>
  );
}