import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../lib/api';

export default function DoctorSlots({ user }) {
  const { doctorId } = useParams();
  const navigate = useNavigate();
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(null);
  const [message, setMessage] = useState('');

  const load = () => api.get(`/appointments/doctors/${doctorId}/slots/`, { params: { date } }).then(r => { setData(r.data); setSelected(null); }).catch(e => setMessage(e.response?.data?.detail || 'Unable to load slots.'));
  useEffect(() => { load(); }, [doctorId, date]);

  async function book() {
    if (!selected) return;
    if (!user) { navigate('/login', { state: { from: `/doctors/${doctorId}/slots` } }); return; }
    try {
      const r = await api.post('/appointments/', { doctor: doctorId, appointment_date: date, appointment_time: selected.start_time });
      navigate('/appointments', { state: { booked: r.data } });
    } catch (e) { setMessage(e.response?.data?.detail || 'Unable to book this slot.'); load(); }
  }

  return <div className="mx-auto max-w-5xl px-6 py-10">
    <div className="rounded-3xl bg-white p-7 shadow-sm">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div><p className="text-sm font-semibold text-green-700">BookMyShow-style slot view</p><h1 className="mt-1 text-3xl font-black">{data?.doctor || 'Doctor'}</h1><p className="text-slate-500">{data?.specialization} · {data?.hospital}</p></div>
        <input type="date" value={date} min={new Date().toISOString().slice(0,10)} onChange={e => setDate(e.target.value)} className="rounded-xl border px-4 py-3" />
      </div>
      {message && <div className="mt-5 rounded-xl bg-red-50 p-3 text-sm text-red-700">{message}</div>}
      <div className="mt-7 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
        {data?.slots?.map(slot => <button key={slot.start_time} disabled={slot.status !== 'AVAILABLE'} onClick={() => setSelected(slot)} className={`rounded-xl border p-4 text-left transition ${slot.status === 'PAST' ? 'cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400' : slot.status === 'BOOKED' ? 'cursor-not-allowed border-red-200 bg-red-50 text-red-500' : selected?.start_time === slot.start_time ? 'border-green-600 bg-green-600 text-white' : 'border-green-200 bg-green-50 text-green-800 hover:bg-green-100'}`}>
          <div className="font-bold">{slot.start_time}</div><div className="mt-1 text-xs">{slot.status === 'BOOKED' ? 'Booked' : slot.status === 'PAST' ? 'Passed' : 'Available'}</div>
        </button>)}
      </div>
      {!data?.slots?.length && <p className="mt-7 text-slate-500">The doctor has no schedule for this date.</p>}
      {selected && <div className="mt-7 flex flex-col gap-4 rounded-2xl bg-green-50 p-5 md:flex-row md:items-center md:justify-between"><div><p className="text-sm text-slate-500">Selected slot</p><p className="text-xl font-bold">{selected.start_time} - {selected.end_time}</p></div><button onClick={book} className="rounded-xl bg-green-600 px-6 py-3 font-semibold text-white">Confirm appointment</button></div>}
    </div>
  </div>;
}
