import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../lib/api';
import useQueueSocket from '../lib/useQueueSocket';

/** Public lobby display. Open it full screen on a TV: /queue-board/<hospital id> */
export default function QueueBoard() {
  const { hospitalId } = useParams();
  const [board, setBoard] = useState(null);
  const [error, setError] = useState('');
  const [clock, setClock] = useState(new Date());

  async function load() {
    try {
      const r = await api.get(`/appointments/queue-board/${hospitalId}/`);
      setBoard(r.data);
      setError('');
    } catch (e) {
      setError(e.response?.status === 404 ? 'Hospital not found.' : 'Unable to load the queue.');
    }
  }
  useEffect(() => { load(); }, [hospitalId]);
  useEffect(() => {
    const t = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const live = useQueueSocket(hospitalId, (pushed) => {
    if (pushed) setBoard((old) => ({ ...(old || {}), ...pushed }));
    else load();
  });

  return (
    <div className="min-h-screen bg-slate-900 p-8 text-white">
      <div className="flex items-end justify-between">
        <div>
          <p className="text-sm uppercase tracking-widest text-green-400">Live queue</p>
          <h1 className="text-4xl font-black">{board?.hospital?.name || 'Queue'}</h1>
        </div>
        <div className="text-right">
          <p className="text-4xl font-black tabular-nums">{clock.toLocaleTimeString()}</p>
          <p className="text-sm text-slate-400">{live ? '● Live' : '○ Updating every 5s'}</p>
        </div>
      </div>

      {error && <p className="mt-10 text-xl text-red-300">{error}</p>}

      <div className="mt-8 grid gap-6 md:grid-cols-2 xl:grid-cols-3">
        {board?.doctors?.map((d) => (
          <div key={d.doctor_id} className="rounded-3xl bg-slate-800 p-6">
            <p className="text-xl font-bold">{d.doctor_name}</p>
            <p className="text-sm text-slate-400">{d.department}</p>
            <div className="mt-5 rounded-2xl bg-green-600 p-5 text-center">
              <p className="text-xs uppercase tracking-widest text-green-100">Now serving</p>
              <p className="text-8xl font-black tabular-nums">{d.now_serving ? `#${d.now_serving}` : '—'}</p>
            </div>
            <p className="mt-5 text-xs uppercase tracking-widest text-slate-400">
              Next in line {d.waiting_count > 0 && `(${d.waiting_count} waiting)`}
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {d.waiting.map((t) => (
                <span key={t} className="rounded-xl bg-slate-700 px-4 py-2 text-2xl font-bold tabular-nums">#{t}</span>
              ))}
              {!d.waiting.length && <span className="text-slate-500">No one waiting</span>}
            </div>
          </div>
        ))}
      </div>
      {board && !board.doctors?.length && !error && (
        <p className="mt-16 text-center text-2xl text-slate-400">No doctors are available today.</p>
      )}
      <p className="mt-10 text-right text-xs text-slate-500">Last update {board?.updated_at}</p>
    </div>
  );
}