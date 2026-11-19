import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';

export default function Hospitals() {
  const [hospitals, setHospitals] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setLoading(true);
      api.get('/doctors/hospitals/', { params: search ? { search } : {} })
        .then((r) => setHospitals(r.data))
        .catch(() => setHospitals([]))
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(timer);
  }, [search]);

  return (
    <div className="mx-auto max-w-7xl px-6 py-10">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold text-green-700">Qenova hospitals</p>
          <h1 className="mt-1 text-4xl font-black">Choose a hospital</h1>
          <p className="mt-2 text-slate-500">Open a hospital to see only its departments, doctors and appointment slots.</p>
        </div>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-xl border bg-white px-4 py-3 md:w-80"
          placeholder="Search hospitals..."
        />
      </div>

      {loading ? (
        <p className="mt-10 text-slate-500">Loading hospitals...</p>
      ) : (
        <div className="mt-8 overflow-hidden rounded-2xl border bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="p-4">#</th>
                  <th className="p-4">Hospital</th>
                  <th className="p-4">City</th>
                  <th className="p-4">State</th>
                  <th className="p-4">Address</th>
                  <th className="p-4">Phone</th>
                  <th className="p-4">Action</th>
                </tr>
              </thead>
              <tbody>
                {hospitals.map((h, index) => (
                  <tr key={h.id} className="border-t transition hover:bg-green-50/40">
                    <td className="p-4 text-slate-500">{index + 1}</td>
                    <td className="p-4">
                      <p className="font-bold">{h.name}</p>
                      {h.description && <p className="mt-0.5 max-w-xs truncate text-xs text-slate-500">{h.description}</p>}
                    </td>
                    <td className="p-4">{h.city}</td>
                    <td className="p-4">{h.state}</td>
                    <td className="max-w-xs p-4 text-slate-600">
                      {h.address}{h.pincode ? ` - ${h.pincode}` : ''}
                    </td>
                    <td className="whitespace-nowrap p-4">{h.phone}</td>
                    <td className="p-4">
                      <Link
                        to={`/hospitals/${h.id}`}
                        className="inline-flex whitespace-nowrap rounded-lg bg-green-600 px-4 py-2 font-semibold text-white"
                      >
                        Open hospital
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!hospitals.length && (
            <p className="p-8 text-center text-slate-500">No approved hospitals found.</p>
          )}
        </div>
      )}
    </div>
  );
}