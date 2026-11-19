import { useEffect, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { Plus, Trash2 } from 'lucide-react';
import { api } from '../lib/api';
import { apiError } from '../lib/errors';

const emptyItem = { medicine: '', dosage: '', frequency: '', duration: '', instructions: '' };
const input = 'rounded-lg border p-3';

/** Doctor writes or edits the prescription of the patient they are seeing. */
export default function PrescriptionForm() {
  const { appointmentId } = useParams();
  const { state } = useLocation();
  const nav = useNavigate();
  const [form, setForm] = useState({ diagnosis: '', notes: '', advice: '', follow_up_date: '' });
  const [items, setItems] = useState([{ ...emptyItem }]);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get(`/appointments/${appointmentId}/prescription/`)
      .then((r) => {
        const rx = r.data.prescription;
        setForm({ diagnosis: rx.diagnosis, notes: rx.notes, advice: rx.advice, follow_up_date: rx.follow_up_date || '' });
        setItems(rx.items.length ? rx.items : [{ ...emptyItem }]);
      })
      .catch(() => { /* 404 = nothing written yet */ })
      .finally(() => setLoading(false));
  }, [appointmentId]);

  const setField = (key, value) => setForm({ ...form, [key]: value });
  const setItem = (index, key, value) => setItems(items.map((it, i) => (i === index ? { ...it, [key]: value } : it)));

  async function save(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await api.put(`/appointments/${appointmentId}/prescription/`, {
        ...form,
        follow_up_date: form.follow_up_date || null,
        items: items.filter((it) => it.medicine.trim()),
      });
      nav(`/prescriptions/${appointmentId}`, { replace: true });
    } catch (e2) {
      setError(apiError(e2, 'Unable to save the prescription.'));
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p className="p-10 text-center text-slate-500">Loading…</p>;
  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <p className="text-sm font-semibold text-green-700">Prescription</p>
      <h1 className="text-3xl font-black">{state?.patient ? `${state.patient}${state.token ? ` · Token #${state.token}` : ''}` : `Appointment #${appointmentId}`}</h1>
      {error && <div className="mt-5 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      <form onSubmit={save} className="mt-6 space-y-5 rounded-2xl border bg-white p-6">
        <label className="block">
          <span className="text-sm font-semibold">Diagnosis *</span>
          <textarea required rows={2} className={`mt-1 w-full ${input}`} value={form.diagnosis} onChange={(e) => setField('diagnosis', e.target.value)} />
        </label>
        <label className="block">
          <span className="text-sm font-semibold">Clinical notes</span>
          <textarea rows={2} className={`mt-1 w-full ${input}`} value={form.notes} onChange={(e) => setField('notes', e.target.value)} />
        </label>

        <div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold">Medicines</span>
            <button type="button" disabled={items.length >= 20} onClick={() => setItems([...items, { ...emptyItem }])} className="flex items-center gap-1 rounded-lg border px-3 py-1 text-sm"><Plus size={14} /> Add medicine</button>
          </div>
          <div className="mt-3 space-y-3">
            {items.map((it, index) => (
              <div key={index} className="grid gap-2 rounded-xl bg-slate-50 p-3 md:grid-cols-6">
                <input className={`${input} md:col-span-2`} placeholder="Medicine" value={it.medicine} onChange={(e) => setItem(index, 'medicine', e.target.value)} />
                <input className={input} placeholder="Dosage" value={it.dosage} onChange={(e) => setItem(index, 'dosage', e.target.value)} />
                <input className={input} placeholder="1-0-1" value={it.frequency} onChange={(e) => setItem(index, 'frequency', e.target.value)} />
                <input className={input} placeholder="Duration" value={it.duration} onChange={(e) => setItem(index, 'duration', e.target.value)} />
                <button type="button" onClick={() => setItems(items.length > 1 ? items.filter((_, i) => i !== index) : [{ ...emptyItem }])} className="grid place-items-center rounded-lg border text-red-600" aria-label="Remove medicine"><Trash2 size={16} /></button>
                <input className={`${input} md:col-span-6`} placeholder="Instructions (for example: after food)" value={it.instructions} onChange={(e) => setItem(index, 'instructions', e.target.value)} />
              </div>
            ))}
          </div>
        </div>

        <label className="block">
          <span className="text-sm font-semibold">Advice for the patient</span>
          <textarea rows={2} className={`mt-1 w-full ${input}`} value={form.advice} onChange={(e) => setField('advice', e.target.value)} />
        </label>
        <label className="block">
          <span className="text-sm font-semibold">Follow-up date</span>
          <input type="date" min={today} className={`mt-1 ${input}`} value={form.follow_up_date} onChange={(e) => setField('follow_up_date', e.target.value)} />
        </label>

        <div className="flex gap-3">
          <button disabled={saving} className="rounded-lg bg-green-600 px-6 py-3 font-semibold text-white disabled:opacity-50">{saving ? 'Saving…' : 'Save prescription'}</button>
          <button type="button" onClick={() => nav(-1)} className="rounded-lg border px-6 py-3">Cancel</button>
        </div>
      </form>
    </div>
  );
}
