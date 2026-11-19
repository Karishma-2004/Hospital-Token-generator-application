import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import { apiError } from '../lib/errors';

const ROLES = [['', 'All roles'], ['USER', 'Patients'], ['DOCTOR', 'Doctors'], ['RECEPTIONIST', 'Hospital staff'], ['ADMIN', 'Admins']];

export default function AdminUsers() {
  const [data, setData] = useState({ results: [], count: 0, page: 1, pages: 1 });
  const [search, setSearch] = useState('');
  const [role, setRole] = useState('');
  const [active, setActive] = useState('');
  const [page, setPage] = useState(1);
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');

  function load() {
    const params = { page };
    if (search.trim()) params.search = search.trim();
    if (role) params.role = role;
    if (active) params.active = active;
    api.get('/admin-panel/users/', { params })
      .then((r) => setData(r.data))
      .catch((e) => setError(apiError(e, 'Unable to load users.')));
  }
  useEffect(() => { load(); }, [page, role, active]);

  const tell = (ok, text) => { setMsg(ok ? text : ''); setError(ok ? '' : text); };

  async function toggle(u) {
    const next = !u.is_active;
    if (!window.confirm(`${next ? 'Reactivate' : 'Deactivate'} ${u.name || u.username}?`)) return;
    try {
      await api.patch(`/admin-panel/users/${u.id}/`, { is_active: next });
      tell(true, `${u.username} ${next ? 'reactivated' : 'deactivated'}.`);
      load();
    } catch (e) {
      tell(false, apiError(e, 'Unable to update the user.'));
    }
  }

  async function remove(u) {
    if (!window.confirm(`Permanently delete ${u.name || u.username}? This cannot be undone.`)) return;
    try {
      await api.delete(`/admin-panel/users/${u.id}/`);
      tell(true, `${u.username} deleted.`);
      load();
    } catch (e) {
      tell(false, apiError(e, 'Unable to delete the user.'));
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-green-700">Application admin</p>
          <h1 className="text-4xl font-black">Users</h1>
          <p className="mt-1 text-sm text-slate-500">{data.count} accounts. Deactivating blocks sign-in immediately and can be undone; deleting is permanent and only possible for accounts with no appointment history.</p>
        </div>
        <Link to="/admin/dashboard" className="rounded-lg border bg-white px-4 py-2 text-sm font-semibold">Back to dashboard</Link>
      </div>

      {msg && <div className="mt-5 rounded-xl bg-green-50 p-3 text-sm text-green-700">{msg}</div>}
      {error && <div className="mt-5 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      <form onSubmit={(e) => { e.preventDefault(); setPage(1); load(); }} className="mt-6 flex flex-wrap gap-2">
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search name, email, username, mobile" className="min-w-[240px] flex-1 rounded-lg border bg-white p-3" />
        <select value={role} onChange={(e) => { setPage(1); setRole(e.target.value); }} className="rounded-lg border bg-white p-3">
          {ROLES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <select value={active} onChange={(e) => { setPage(1); setActive(e.target.value); }} className="rounded-lg border bg-white p-3">
          <option value="">Active and inactive</option><option value="true">Active</option><option value="false">Inactive</option>
        </select>
        <button className="rounded-lg bg-green-600 px-5 font-semibold text-white">Search</button>
      </form>

      <div className="mt-5 overflow-x-auto rounded-2xl border bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50">
            <tr><th className="p-3">User</th><th className="p-3">Role</th><th className="p-3">Hospital</th><th className="p-3">Appointments</th><th className="p-3">Joined</th><th className="p-3">Status</th><th className="p-3">Actions</th></tr>
          </thead>
          <tbody>
            {data.results.map((u) => (
              <tr key={u.id} className="border-t">
                <td className="p-3"><p className="font-semibold">{u.name || u.username}</p><p className="text-xs text-slate-500">{u.email}{u.mobile ? ` · ${u.mobile}` : ''}</p></td>
                <td className="p-3">{u.role}</td>
                <td className="p-3">{u.hospital || '—'}</td>
                <td className="p-3">{u.appointments}</td>
                <td className="p-3">{u.date_joined.slice(0, 10)}</td>
                <td className="p-3"><span className={`rounded-full px-3 py-1 text-xs font-semibold ${u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>{u.is_active ? 'Active' : 'Inactive'}</span></td>
                <td className="p-3">
                  {u.role === 'ADMIN' ? <span className="text-xs text-slate-400">Protected</span> : (
                    <div className="flex gap-2">
                      <button onClick={() => toggle(u)} className="rounded-lg border px-3 py-1">{u.is_active ? 'Deactivate' : 'Reactivate'}</button>
                      <button onClick={() => remove(u)} className="rounded-lg bg-red-50 px-3 py-1 text-red-700">Delete</button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!data.results.length && <p className="p-8 text-center text-slate-500">No users match.</p>}
      </div>

      <div className="mt-4 flex items-center justify-between text-sm">
        <span className="text-slate-500">Page {data.page} of {data.pages}</span>
        <div className="flex gap-2">
          <button disabled={data.page <= 1} onClick={() => setPage(data.page - 1)} className="rounded-lg border bg-white px-4 py-2 disabled:opacity-40">Previous</button>
          <button disabled={data.page >= data.pages} onClick={() => setPage(data.page + 1)} className="rounded-lg border bg-white px-4 py-2 disabled:opacity-40">Next</button>
        </div>
      </div>
    </div>
  );
}
