import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import { apiError } from '../lib/errors';

const money = (value) => `INR ${Number(value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

/** Admin: how much each hospital is owed, and a record of every transfer made to them. */
export default function AdminSettlements() {
  const [data, setData] = useState(null);
  const [payouts, setPayouts] = useState([]);
  const [open, setOpen] = useState(null);           // hospital row whose payout form is open
  const [form, setForm] = useState({ amount: '', reference: '', note: '' });
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');

  function load() {
    api.get('/admin-panel/settlements/').then((r) => setData(r.data)).catch((e) => setError(apiError(e, 'Unable to load settlements.')));
    api.get('/admin-panel/payouts/').then((r) => setPayouts(r.data)).catch(() => {});
  }
  useEffect(() => { load(); }, []);

  function openForm(row) {
    setOpen(row);
    setForm({ amount: Number(row.balance) > 0 ? row.balance : '', reference: '', note: '' });
    setMsg('');
    setError('');
  }

  async function submit(e) {
    e.preventDefault();
    setError('');
    try {
      await api.post('/admin-panel/payouts/', { hospital: open.hospital_id, ...form });
      setMsg(`Payout of ${money(form.amount)} to ${open.hospital} recorded.`);
      setOpen(null);
      load();
    } catch (e2) {
      setError(apiError(e2, 'Unable to record the payout.'));
    }
  }

  const input = 'rounded-lg border p-3';
  return (
    <div className="mx-auto max-w-7xl px-6 py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-green-700">Application admin</p>
          <h1 className="text-4xl font-black">Settlements</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-500">
            Patients pay the platform. The platform keeps {data ? `${data.commission_percent}%` : 'its commission'} of every
            consultation fee and owes the rest to the hospital. Transfer the money to the hospital yourself (bank or UPI), then
            record it here with the transfer reference.
          </p>
        </div>
        <Link to="/admin/dashboard" className="rounded-lg border bg-white px-4 py-2 text-sm font-semibold">Back to dashboard</Link>
      </div>

      {msg && <div className="mt-5 rounded-xl bg-green-50 p-3 text-sm text-green-700">{msg}</div>}
      {error && <div className="mt-5 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      {data && (
        <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[
            ['Your commission (all time)', data.totals.commission],
            ['Owed to hospitals', data.totals.balance],
            ['Already paid out', data.totals.paid_out],
            ['Refunds to give patients', data.totals.refund_due],
          ].map(([label, value]) => (
            <div key={label} className="rounded-2xl border bg-white p-5">
              <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
              <p className="mt-1 text-2xl font-black">{money(value)}</p>
            </div>
          ))}
        </div>
      )}

      <div className="mt-6 overflow-x-auto rounded-2xl border bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="p-3">Hospital</th><th className="p-3">Paid online</th><th className="p-3">Cash at desk</th>
              <th className="p-3">Your commission</th><th className="p-3">Owed to hospital</th><th className="p-3">Paid out</th>
              <th className="p-3">Balance</th><th className="p-3">Action</th>
            </tr>
          </thead>
          <tbody>
            {data?.rows.map((r) => (
              <tr key={r.hospital_id} className="border-t">
                <td className="p-3"><p className="font-semibold">{r.hospital}</p><p className="text-xs text-slate-500">{r.city}</p></td>
                <td className="p-3">{money(r.online_paid)}</td>
                <td className="p-3">{money(r.cash_paid)}</td>
                <td className="p-3">{money(r.commission)}</td>
                <td className="p-3">{money(r.net_due)}</td>
                <td className="p-3">{money(r.paid_out)}</td>
                <td className={`p-3 font-bold ${Number(r.balance) < 0 ? 'text-red-600' : ''}`}>
                  {money(r.balance)}
                  {Number(r.balance) < 0 && <span className="block text-xs font-normal">hospital owes you</span>}
                </td>
                <td className="p-3">
                  <button
                    disabled={Number(r.balance) <= 0}
                    onClick={() => openForm(r)}
                    className="rounded-lg bg-green-600 px-3 py-2 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Record payout
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && !data.rows.length && <p className="p-8 text-center text-slate-500">No hospitals yet.</p>}
      </div>

      {open && (
        <form onSubmit={submit} className="mt-6 rounded-2xl border bg-white p-6">
          <h2 className="font-bold">Record a payout to {open.hospital}</h2>
          <p className="mt-1 text-sm text-slate-500">Owed right now: {money(open.balance)}. Do the bank / UPI transfer first, then enter it here.</p>
          <div className="mt-4 grid gap-3 md:grid-cols-4">
            <input required type="number" min="0.01" step="0.01" max={open.balance} className={input} placeholder="Amount (INR)" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} />
            <input required className={input} placeholder="Bank / UPI reference no." value={form.reference} onChange={(e) => setForm({ ...form, reference: e.target.value })} />
            <input className={input} placeholder="Note (optional)" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
            <div className="flex gap-2">
              <button className="flex-1 rounded-lg bg-green-600 p-3 font-semibold text-white">Save payout</button>
              <button type="button" onClick={() => setOpen(null)} className="rounded-lg border px-4">Cancel</button>
            </div>
          </div>
        </form>
      )}

      <section className="mt-8">
        <h2 className="text-xl font-bold">Payout history</h2>
        <div className="mt-3 overflow-x-auto rounded-2xl border bg-white">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50">
              <tr><th className="p-3">Date</th><th className="p-3">Hospital</th><th className="p-3">Amount</th><th className="p-3">Reference</th><th className="p-3">Note</th><th className="p-3">Recorded by</th></tr>
            </thead>
            <tbody>
              {payouts.map((p) => (
                <tr key={p.id} className="border-t">
                  <td className="p-3 whitespace-nowrap">{new Date(p.created_at).toLocaleString()}</td>
                  <td className="p-3">{p.hospital}</td>
                  <td className="p-3 font-semibold">{money(p.amount)}</td>
                  <td className="p-3">{p.reference}</td>
                  <td className="p-3 text-slate-500">{p.note || '—'}</td>
                  <td className="p-3">{p.paid_by || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!payouts.length && <p className="p-6 text-center text-slate-500">No payouts recorded yet.</p>}
        </div>
      </section>
    </div>
  );
}