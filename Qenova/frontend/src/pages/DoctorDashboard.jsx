import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckCheck, FileText, PhoneCall, Radio, Timer } from 'lucide-react';
import { api } from '../lib/api';
import { apiError } from '../lib/errors';
import useQueueSocket from '../lib/useQueueSocket';

export default function DoctorDashboard() {
  const [data, setData] = useState(null);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [working, setWorking] = useState(false);

  async function load() {
    try {
      const r = await api.get('/appointments/doctor/queue/');
      setData(r.data);
    } catch (e) {
      setErr(apiError(e, 'Unable to load your queue.'));
    }
  }
  useEffect(() => { load(); }, []);

  const live = useQueueSocket(data?.hospital_id, () => load());

  async function act(url, fallback) {
    setWorking(true);
    setErr('');
    try {
      const r = await api.post(url);
      setMsg(r.data.message || '');
      await load();
    } catch (e) {
      setErr(apiError(e, fallback));
    } finally {
      setWorking(false);
    }
  }

  const current = data?.current;
  const waiting = data?.waiting || [];

  return (
    <div className="mx-auto max-w-7xl px-6 py-10">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-green-700">Doctor dashboard</p>
          <h1 className="text-4xl font-black">{data?.doctor_name || 'My queue'}</h1>
          <p className="mt-2 flex items-center gap-2 text-slate-500">
            Today · {data?.date}
            <span className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${live ? 'bg-green-100 text-green-700' : 'bg-slate-200 text-slate-600'}`}>
              <Radio size={12} /> {live ? 'Live' : 'Refreshing every 5s'}
            </span>
          </p>
        </div>
        <button
          disabled={working || (!current && !waiting.length)}
          onClick={() => act('/appointments/doctor/call-next/', 'Unable to call the next patient.')}
          className="flex items-center gap-2 rounded-xl bg-green-600 px-6 py-4 text-lg font-bold text-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          <PhoneCall size={20} /> Call next patient
        </button>
      </div>

      {msg && <div className="mt-5 rounded-xl bg-green-50 p-3 text-sm text-green-700">{msg}</div>}
      {err && <div className="mt-5 rounded-xl bg-red-50 p-3 text-sm text-red-700">{err}</div>}

      <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          ['Waiting', waiting.length],
          ['Not arrived yet', data?.upcoming.length ?? 0],
          ['Completed today', data?.completed_count ?? 0],
          ['Avg consult', `${data?.average_minutes ?? '-'} min`],
        ].map(([label, value]) => (
          <div key={label} className="rounded-2xl border bg-white p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
            <p className="mt-1 text-3xl font-black">{value}</p>
          </div>
        ))}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <section className="rounded-2xl border bg-white p-6 lg:col-span-1">
          <h2 className="font-bold">Now consulting</h2>
          {current ? (
            <div className="mt-4 rounded-2xl bg-amber-50 p-5 text-center">
              <p className="text-sm text-amber-800">Token</p>
              <p className="text-7xl font-black text-amber-900">#{current.token_number}</p>
              <p className="mt-2 text-lg font-semibold">{current.patient_name}</p>
              {current.is_walk_in && <p className="text-sm text-purple-700">Walk-in</p>}
              <Link
                to={`/doctor/prescription/${current.id}`}
                state={{ patient: current.patient_name, token: current.token_number }}
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-purple-600 p-3 font-semibold text-white"
              >
                <FileText size={18} /> {current.has_prescription ? 'Edit prescription' : 'Write prescription'}
              </Link>
              <button
                disabled={working}
                onClick={() => act('/appointments/doctor/complete/', 'Unable to complete.')}
                className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg bg-slate-800 p-3 font-semibold text-white disabled:opacity-50"
              >
                <CheckCheck size={18} /> Complete consultation
              </button>
            </div>
          ) : (
            <p className="mt-4 rounded-xl bg-slate-50 p-5 text-center text-slate-500">
              No one is inside. Press “Call next patient”.
            </p>
          )}
        </section>

        <section className="rounded-2xl border bg-white p-6 lg:col-span-2">
          <h2 className="font-bold">Waiting queue</h2>
          <div className="mt-4 space-y-2">
            {waiting.map((a) => (
              <div key={a.id} className="flex items-center justify-between rounded-xl bg-slate-50 p-4">
                <div className="flex items-center gap-4">
                  <span className="grid h-10 w-10 place-items-center rounded-full bg-blue-600 font-bold text-white">{a.position}</span>
                  <div>
                    <p className="font-semibold">
                      #{a.token_number} · {a.patient_name}
                      {a.is_walk_in && <span className="ml-2 rounded-full bg-purple-100 px-2 py-0.5 text-xs text-purple-700">Walk-in</span>}
                    </p>
                    <p className="text-sm text-slate-500">Booked for {a.is_walk_in ? 'walk-in' : a.appointment_time}</p>
                  </div>
                </div>
                <p className="flex items-center gap-1 text-sm text-slate-600"><Timer size={14} /> ~{a.estimated_wait_minutes} min</p>
              </div>
            ))}
            {!waiting.length && <p className="rounded-xl bg-slate-50 p-5 text-center text-slate-500">Nobody is waiting right now.</p>}
          </div>

          {!!data?.recent_completed?.length && (
            <>
              <h2 className="mt-8 font-bold">Recently completed</h2>
              <div className="mt-3 space-y-2">
                {data.recent_completed.map((a) => (
                  <div key={a.id} className="flex items-center justify-between rounded-xl border p-3 text-sm">
                    <span className="font-semibold">#{a.token_number} · {a.patient_name}</span>
                    <Link
                      to={a.has_prescription ? `/prescriptions/${a.id}` : `/doctor/prescription/${a.id}`}
                      state={{ patient: a.patient_name, token: a.token_number }}
                      className="rounded-lg bg-purple-50 px-3 py-1 font-semibold text-purple-700"
                    >
                      {a.has_prescription ? 'View prescription' : 'Write prescription'}
                    </Link>
                  </div>
                ))}
              </div>
            </>
          )}

          {!!data?.upcoming.length && (
            <>
              <h2 className="mt-8 font-bold">Booked, not arrived yet</h2>
              <div className="mt-3 space-y-2">
                {data.upcoming.map((a) => (
                  <div key={a.id} className="flex items-center justify-between rounded-xl border p-3 text-sm">
                    <span className="font-semibold">#{a.token_number} · {a.patient_name}</span>
                    <span className="text-slate-500">{a.appointment_time}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}