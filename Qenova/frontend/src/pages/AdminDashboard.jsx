import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Download } from 'lucide-react';
import { api } from '../lib/api';
import { apiError } from '../lib/errors';

const isoDay = (offset = 0) => {
  const d = new Date();
  d.setDate(d.getDate() + offset);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};
const money = (value) => `INR ${Number(value || 0).toLocaleString('en-IN')}`;

function Card({ label, value, hint }) {
  return (
    <div className="rounded-2xl border bg-white p-5">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-3xl font-black">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

export default function AdminDashboard() {
  const [days, setDays] = useState(30);
  const [stats, setStats] = useState(null);
  const [from, setFrom] = useState(isoDay(-29));
  const [to, setTo] = useState(isoDay(0));
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/admin-panel/stats/', { params: { days } })
      .then((r) => setStats(r.data))
      .catch((e) => setError(apiError(e, 'Unable to load the dashboard.')));
  }, [days]);

  function loadReport() {
    setError('');
    api.get('/admin-panel/report/', { params: { from, to } })
      .then((r) => setReport(r.data))
      .catch((e) => setError(apiError(e, 'Unable to load the report.')));
  }
  useEffect(() => { loadReport(); }, []);

  async function downloadCsv() {
    try {
      const r = await api.get('/admin-panel/report/', { params: { from, to, export: 'csv' }, responseType: 'blob' });
      const url = URL.createObjectURL(r.data);
      const link = document.createElement('a');
      link.href = url;
      link.download = `medibook-report-${from}-to-${to}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError('Unable to download the report.');
    }
  }

  const peak = stats ? Math.max(1, ...stats.daily.map((d) => d.total)) : 1;
  const by = (obj, key) => (obj && obj[key]) || 0;

  return (
    <div className="mx-auto max-w-7xl px-6 py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-green-700">Application admin</p>
          <h1 className="text-4xl font-black">Dashboard</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/admin" className="rounded-lg border bg-white px-4 py-2 text-sm font-semibold">Hospital approvals</Link>
          <Link to="/admin/users" className="rounded-lg border bg-white px-4 py-2 text-sm font-semibold">Manage users</Link>
          <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="rounded-lg border bg-white px-3 py-2 text-sm">
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>
      </div>
      {error && <div className="mt-5 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      {stats && (
        <>
          <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Card label="Users" value={stats.users.total} hint={`${stats.users.active} active · ${by(stats.users.by_role, 'USER')} patients · ${by(stats.users.by_role, 'DOCTOR')} doctors`} />
            <Card label="Hospitals" value={stats.hospitals.total} hint={`${by(stats.hospitals.by_status, 'APPROVED')} approved · ${by(stats.hospitals.by_status, 'PENDING')} pending`} />
            <Card label="Appointments today" value={stats.appointments.today} hint={`${stats.appointments.total} in total · ${stats.appointments.walk_ins} walk-ins`} />
            <Card label="Revenue" value={money(stats.revenue.total)} hint={`Your commission: ${money(stats.revenue.commission_total)} · ${money(stats.revenue.in_period)} paid in the last ${stats.days} days`} />          </div>

          <section className="mt-6 rounded-2xl border bg-white p-6">
            <h2 className="font-bold">Appointments per day</h2>
            <div className="mt-4 flex h-40 items-end gap-1 overflow-x-auto">
              {stats.daily.map((d) => (
                <div key={d.date} className="flex min-w-[10px] flex-1 flex-col justify-end" title={`${d.date}: ${d.total} booked, ${d.completed} completed, ${d.cancelled} cancelled`}>
                  <div className="w-full rounded-t bg-green-500" style={{ height: `${(d.total / peak) * 100}%`, minHeight: d.total ? 3 : 0 }} />
                </div>
              ))}
            </div>
            <div className="mt-2 flex justify-between text-xs text-slate-500"><span>{stats.daily[0]?.date}</span><span>{stats.daily[stats.daily.length - 1]?.date}</span></div>
          </section>

          <div className="mt-6 grid gap-6 lg:grid-cols-3">
            <section className="rounded-2xl border bg-white p-6">
              <h2 className="font-bold">Appointments by status</h2>
              <div className="mt-3 space-y-2 text-sm">
                {Object.entries(stats.appointments.by_status).map(([status, n]) => (
                  <div key={status} className="flex justify-between rounded-lg bg-slate-50 p-3"><span>{status.replace('_', ' ')}</span><b>{n}</b></div>
                ))}
              </div>
            </section>
            <section className="rounded-2xl border bg-white p-6">
              <h2 className="font-bold">Busiest hospitals</h2>
              <div className="mt-3 space-y-2 text-sm">
                {stats.top_hospitals.map((h) => (
                  <div key={h.id} className="flex justify-between rounded-lg bg-slate-50 p-3"><span>{h.name}</span><b>{h.appointments}</b></div>
                ))}
                {!stats.top_hospitals.length && <p className="text-slate-500">No appointments yet.</p>}
              </div>
            </section>
            <section className="rounded-2xl border bg-white p-6">
              <h2 className="font-bold">Top doctors (completed visits)</h2>
              <div className="mt-3 space-y-2 text-sm">
                {stats.top_doctors.map((d) => (
                  <div key={d.id} className="flex justify-between rounded-lg bg-slate-50 p-3"><span>{d.name}<span className="block text-xs text-slate-500">{d.hospital}</span></span><b>{d.completed}</b></div>
                ))}
                {!stats.top_doctors.length && <p className="text-slate-500">No completed visits yet.</p>}
              </div>
            </section>
          </div>
        </>
      )}

      <section className="mt-6 rounded-2xl border bg-white p-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 className="font-bold">Hospital report</h2>
          <div className="flex flex-wrap items-end gap-2">
            <label className="text-xs text-slate-500">From<input type="date" value={from} max={to} onChange={(e) => setFrom(e.target.value)} className="mt-1 block rounded-lg border p-2 text-sm text-slate-900" /></label>
            <label className="text-xs text-slate-500">To<input type="date" value={to} min={from} onChange={(e) => setTo(e.target.value)} className="mt-1 block rounded-lg border p-2 text-sm text-slate-900" /></label>
            <button onClick={loadReport} className="rounded-lg bg-green-600 px-4 py-2 text-sm font-semibold text-white">Run report</button>
            <button onClick={downloadCsv} className="flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-semibold"><Download size={14} /> CSV</button>
          </div>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b"><th className="p-3">Hospital</th><th className="p-3">City</th><th className="p-3">Appointments</th><th className="p-3">Completed</th><th className="p-3">Cancelled</th><th className="p-3">No-show</th><th className="p-3">Walk-ins</th><th className="p-3">Revenue</th></tr>
            </thead>
            <tbody>
              {report?.rows.map((r) => (
                <tr key={r.hospital} className="border-b">
                  <td className="p-3 font-semibold">{r.hospital}</td><td className="p-3">{r.city}</td><td className="p-3">{r.appointments}</td>
                  <td className="p-3">{r.completed}</td><td className="p-3">{r.cancelled}</td><td className="p-3">{r.no_show}</td><td className="p-3">{r.walk_ins}</td><td className="p-3">{money(r.revenue)}</td>
                </tr>
              ))}
              {report && (
                <tr className="bg-slate-50 font-bold">
                  <td className="p-3" colSpan={2}>Total</td><td className="p-3">{report.totals.appointments}</td><td className="p-3">{report.totals.completed}</td>
                  <td className="p-3">{report.totals.cancelled}</td><td className="p-3">{report.totals.no_show}</td><td className="p-3">{report.totals.walk_ins}</td><td className="p-3">{money(report.totals.revenue)}</td>
                </tr>
              )}
            </tbody>
          </table>
          {report && !report.rows.length && <p className="p-6 text-center text-slate-500">No hospitals yet.</p>}
        </div>
      </section>
    </div>
  );
}
