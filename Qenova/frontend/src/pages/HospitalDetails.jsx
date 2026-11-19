import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../lib/api';

export default function HospitalDetails() {
  const { hospitalId } = useParams();
  const [hospital, setHospital] = useState(null);
  const [doctors, setDoctors] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [search, setSearch] = useState('');
  const [department, setDepartment] = useState('');

  const loadDoctors = () => api.get(`/doctors/hospitals/${hospitalId}/doctors/`, {
    params: { ...(search ? { search } : {}), ...(department ? { department } : {}) }
  }).then((r) => setDoctors(r.data));

  useEffect(() => {
    api.get(`/doctors/hospitals/${hospitalId}/`).then((r) => setHospital(r.data));
    api.get(`/doctors/hospitals/${hospitalId}/departments/`).then((r) => setDepartments(r.data));
  }, [hospitalId]);

  useEffect(() => { loadDoctors(); }, [hospitalId, search, department]);

  if (!hospital) return <div className="mx-auto max-w-7xl px-6 py-10">Loading hospital...</div>;

  return (
    <div className="mx-auto max-w-7xl px-6 py-10">
      <section className="rounded-3xl bg-slate-900 p-8 text-white">
        <p className="text-sm font-semibold text-green-300">Approved hospital</p>
        <h1 className="mt-2 text-4xl font-black">{hospital.name}</h1>
        <p className="mt-3 text-slate-300">{hospital.address}, {hospital.city}, {hospital.state} - {hospital.pincode}</p>
        <p className="mt-2 text-slate-300">{hospital.phone} · {hospital.email}</p>
        {hospital.description && <p className="mt-4 max-w-3xl text-slate-300">{hospital.description}</p>}
      </section>

      <section className="mt-8">
        <div className="flex flex-col gap-3 lg:flex-row">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 rounded-xl border bg-white px-4 py-3"
            placeholder="Search doctor or specialization..."
          />
          <select
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            className="rounded-xl border bg-white px-4 py-3 lg:w-72"
          >
            <option value="">All departments</option>
            {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </div>

        <h2 className="mt-8 text-2xl font-bold">Doctors in {hospital.name}</h2>
        <div className="mt-5 overflow-hidden rounded-2xl border bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="p-4">#</th>
                  <th className="p-4">Doctor</th>
                  <th className="p-4">Department</th>
                  <th className="p-4">Specialization</th>
                  <th className="p-4">Experience</th>
                  <th className="p-4">Fee</th>
                  <th className="p-4">Action</th>
                </tr>
              </thead>
              <tbody>
                {doctors.map((d, index) => (
                  <tr key={d.id} className="border-t transition hover:bg-green-50/40">
                    <td className="p-4 text-slate-500">{index + 1}</td>
                    <td className="whitespace-nowrap p-4 font-bold">Dr. {d.user.first_name} {d.user.last_name}</td>
                    <td className="p-4">
                      <span className="rounded-full bg-green-50 px-3 py-1 text-xs font-semibold text-green-700">{d.department_name}</span>
                    </td>
                    <td className="p-4">{d.specialization}</td>
                    <td className="whitespace-nowrap p-4">{d.experience_years} years</td>
                    <td className="whitespace-nowrap p-4 font-semibold">₹{d.consultation_fee}</td>
                    <td className="p-4">
                      <Link
                        to={`/doctors/${d.id}/slots`}
                        className="inline-flex whitespace-nowrap rounded-lg bg-green-600 px-4 py-2 font-semibold text-white"
                      >
                        View slots
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!doctors.length && (
            <p className="p-8 text-center text-slate-500">No verified doctors match your search.</p>
          )}
        </div>
      </section>
    </div>
  );
}