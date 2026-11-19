import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { apiError } from '../lib/errors';

const emptyDoctor = { first_name: '', last_name: '', email: '', mobile: '', password: '', department: '', specialization: '', consultation_fee: '', experience_years: 0, bio: '', registration_number: '' };
const emptyStaff = { first_name: '', last_name: '', email: '', mobile: '', password: '' };
const emptySchedule = { weekday: 0, start_time: '09:00', end_time: '13:00', slot_minutes: 15 };
const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const input = 'rounded-lg border p-3';
const COMMON_DEPARTMENTS = [
  'General Medicine', 'Cardiology', 'Neurology', 'Orthopedics', 'Pediatrics',
  'Gynecology & Obstetrics', 'Dermatology', 'ENT (Ear, Nose & Throat)', 'Ophthalmology',
  'Psychiatry', 'Urology', 'Nephrology', 'Gastroenterology', 'Pulmonology',
  'Oncology', 'Endocrinology', 'Dentistry', 'Radiology', 'Emergency Medicine', 'Physiotherapy',
];

export default function Receptionist() {
  const [me, setMe] = useState(null);
  const [doctors, setDoctors] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [staff, setStaff] = useState([]);
  const [form, setForm] = useState(emptyDoctor);
  const [staffForm, setStaffForm] = useState(emptyStaff);
  const [depChoice, setDepChoice] = useState('');
  const [depCustom, setDepCustom] = useState('');
  const [showDoctor, setShowDoctor] = useState(false);
  const [showStaff, setShowStaff] = useState(false);
  const [scheduleFor, setScheduleFor] = useState(null);
  const [schedule, setSchedule] = useState(emptySchedule);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');

  const isHospitalAdmin = me?.hospital_role === 'HOSPITAL_ADMIN';

  async function load() {
    try {
      const [m, d, ds, a] = await Promise.all([
        api.get('/auth/me/'),
        api.get('/doctors/receptionist/doctors/'),
        api.get('/doctors/receptionist/departments/'),
        api.get('/appointments/'),
      ]);
      setMe(m.data); setDoctors(d.data); setDepartments(ds.data); setAppointments(a.data.results || a.data);
      if (m.data.hospital_role === 'HOSPITAL_ADMIN') {
        const s = await api.get('/doctors/hospital-admin/staff/');
        setStaff(s.data);
      }
    } catch (e) { setErr(apiError(e, 'Unable to load dashboard.')); }
  }
  useEffect(() => { load(); }, []);

  const notify = (m) => { setMsg(m); setErr(''); };

  async function addDoctor(e) {
    e.preventDefault();
    try {
      let departmentId = form.department;
      // Department picked from the common list but not created yet: create it first.
      if (String(departmentId).startsWith('new:')) {
        const created = await api.post('/doctors/receptionist/departments/', { name: departmentId.slice(4) });
        departmentId = created.data.id;
      }
      await api.post('/doctors/receptionist/doctors/create/', {
        ...form,
        consultation_fee: Number(form.consultation_fee || 0),
        experience_years: Number(form.experience_years || 0),
        department: Number(departmentId),
      });
      setForm(emptyDoctor); setShowDoctor(false);
      notify('Doctor added. Now add a weekly schedule so patients can book slots.');
      load();
    } catch (e2) { setErr(apiError(e2, 'Unable to add doctor.')); }
  }

  async function addStaff(e) {
    e.preventDefault();
    try {
      await api.post('/doctors/hospital-admin/staff/', staffForm);
      setStaffForm(emptyStaff); setShowStaff(false);
      notify('Receptionist added.');
      load();
    } catch (e2) { setErr(apiError(e2, 'Unable to add receptionist.')); }
  }

  async function addDepartment(e) {
    e.preventDefault();
    const name = depChoice === '__other' ? depCustom.trim() : depChoice;
    if (!name) return;
    try {
      await api.post('/doctors/receptionist/departments/', { name });
      setDepChoice(''); setDepCustom(''); notify(`${name} department added.`); load();
    } catch (e2) { setErr(apiError(e2, 'Unable to add department.')); }
  }

  async function addSchedule(e) {
    e.preventDefault();
    try {
      await api.post('/doctors/receptionist/schedules/', { ...schedule, doctor: scheduleFor, weekday: Number(schedule.weekday), slot_minutes: Number(schedule.slot_minutes) });
      setSchedule(emptySchedule); notify('Schedule added.'); load();
    } catch (e2) { setErr(apiError(e2, 'Unable to add schedule.')); }
  }

  async function removeSchedule(id) {
    try { await api.delete(`/doctors/receptionist/schedules/${id}/`); load(); }
    catch (e2) { setErr(apiError(e2, 'Unable to remove schedule.')); }
  }

  async function toggleDoctor(d) {
    try { await api.patch(`/doctors/receptionist/doctors/${d.id}/`, { is_active: !d.is_active }); load(); }
    catch (e2) { setErr(apiError(e2, 'Unable to update doctor.')); }
  }

  async function verify(id) {
    try { await api.post(`/doctors/receptionist/doctors/${id}/verify/`); load(); }
    catch (e2) { setErr(apiError(e2, 'Unable to verify doctor.')); }
  }

  async function setStatus(id, status) {
    try { await api.post(`/appointments/${id}/status/`, { status }); load(); }
    catch (e2) { setErr(apiError(e2, 'Unable to update appointment.')); }
  }

  const availableDepartments = COMMON_DEPARTMENTS.filter(
    n => !departments.some(d => d.name.toLowerCase() === n.toLowerCase())
  );
  const set = (k, v) => setForm({ ...form, [k]: v });
  const setS = (k, v) => setStaffForm({ ...staffForm, [k]: v });

  return <div className="mx-auto max-w-7xl px-6 py-10">
    <p className="text-sm font-semibold text-green-700">{isHospitalAdmin ? 'Hospital Admin' : 'Hospital Receptionist'}{me?.hospital_name ? ` · ${me.hospital_name}` : ''}</p>
    <h1 className="text-4xl font-black">Hospital operations</h1>
    <p className="mt-2 text-slate-500">Doctors, departments, schedules and appointments are scoped to your hospital.</p>
    {msg && <div className="mt-5 rounded-xl bg-green-50 p-3 text-sm text-green-700">{msg}</div>}
    {err && <div className="mt-5 rounded-xl bg-red-50 p-3 text-sm text-red-700">{err}</div>}

    <div className="mt-8 grid gap-6 lg:grid-cols-3">
      <div className="space-y-6">
        <section className="rounded-2xl border bg-white p-6">
          <h2 className="font-bold">Departments</h2>
          <form onSubmit={addDepartment} className="mt-4 grid gap-2">
            <select required value={depChoice} onChange={e => setDepChoice(e.target.value)} className={input}>
              <option value="">Select a department</option>
              {availableDepartments.map(n => <option key={n} value={n}>{n}</option>)}
              <option value="__other">Other (type your own)…</option>
            </select>
            {depChoice === '__other' && <input required value={depCustom} onChange={e => setDepCustom(e.target.value)} className={input} placeholder="Department name" />}
            <button className="rounded-lg bg-green-600 p-3 font-semibold text-white">Add department</button>
          </form>
          <div className="mt-4 space-y-2">{departments.map(d => <div key={d.id} className="rounded-lg bg-slate-50 p-3">{d.name}</div>)}</div>
        </section>

        {isHospitalAdmin && <section className="rounded-2xl border bg-white p-6">
          <div className="flex items-center justify-between">
            <h2 className="font-bold">Receptionists</h2>
            <button onClick={() => setShowStaff(!showStaff)} className="rounded-lg bg-green-600 px-3 py-2 text-sm font-semibold text-white">{showStaff ? 'Close' : 'Add'}</button>
          </div>
          {showStaff && <form onSubmit={addStaff} className="mt-4 grid gap-3">
            <input required className={input} placeholder="First name" value={staffForm.first_name} onChange={e => setS('first_name', e.target.value)} />
            <input className={input} placeholder="Last name" value={staffForm.last_name} onChange={e => setS('last_name', e.target.value)} />
            <input required type="email" className={input} placeholder="Email (used as username)" value={staffForm.email} onChange={e => setS('email', e.target.value)} />
            <input className={input} placeholder="Mobile" value={staffForm.mobile} onChange={e => setS('mobile', e.target.value)} />
            <input required minLength="8" type="password" className={input} placeholder="Initial password" value={staffForm.password} onChange={e => setS('password', e.target.value)} />
            <button className="rounded-lg bg-green-600 p-3 font-semibold text-white">Create receptionist</button>
          </form>}
          <div className="mt-4 space-y-2">{staff.map(s => <div key={s.id} className="rounded-lg bg-slate-50 p-3 text-sm"><b>{s.first_name} {s.last_name}</b><div className="text-slate-500">{s.email} · {s.staff_role === 'HOSPITAL_ADMIN' ? 'Admin' : 'Receptionist'}</div></div>)}</div>
        </section>}
      </div>

      <section className="rounded-2xl border bg-white p-6 lg:col-span-2">
        <div className="flex items-center justify-between">
          <h2 className="font-bold">Doctors</h2>
          <button onClick={() => setShowDoctor(!showDoctor)} className="rounded-lg bg-green-600 px-4 py-2 text-sm font-semibold text-white">{showDoctor ? 'Close' : 'Add doctor'}</button>
        </div>
        {showDoctor && <form onSubmit={addDoctor} className="mt-5 grid gap-3 rounded-xl bg-slate-50 p-4 md:grid-cols-2">
          <input required className={input} placeholder="First name" value={form.first_name} onChange={e => set('first_name', e.target.value)} />
          <input className={input} placeholder="Last name" value={form.last_name} onChange={e => set('last_name', e.target.value)} />
          <input required type="email" className={input} placeholder="Doctor email / username" value={form.email} onChange={e => set('email', e.target.value)} />
          <input className={input} placeholder="Mobile" value={form.mobile} onChange={e => set('mobile', e.target.value)} />
          <input required minLength="8" type="password" className={input} placeholder="Initial password" value={form.password} onChange={e => set('password', e.target.value)} />
          <select required className={input} value={form.department} onChange={e => set('department', e.target.value)}>
            <option value="">Select department</option>
            {departments.length > 0 && <optgroup label="Your departments">
              {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
            </optgroup>}
            <optgroup label="Other departments (added automatically)">
              {availableDepartments.map(n => <option key={n} value={`new:${n}`}>{n}</option>)}
            </optgroup>
          </select>
          <input required className={input} placeholder="Specialization" value={form.specialization} onChange={e => set('specialization', e.target.value)} />
          <input required className={input} placeholder="Registration number" value={form.registration_number} onChange={e => set('registration_number', e.target.value)} />
          <input type="number" min="0" step="0.01" className={input} placeholder="Consultation fee" value={form.consultation_fee} onChange={e => set('consultation_fee', e.target.value)} />
          <input type="number" min="0" className={input} placeholder="Experience years" value={form.experience_years} onChange={e => set('experience_years', e.target.value)} />
          <textarea className={`${input} md:col-span-2`} placeholder="Bio" value={form.bio} onChange={e => set('bio', e.target.value)} />
          <button className="rounded-lg bg-green-600 p-3 font-semibold text-white md:col-span-2">Add doctor</button>
        </form>}

        <div className="mt-5 space-y-3">
          {doctors.map(d => <div key={d.id} className="rounded-xl bg-slate-50 p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <b>Dr. {d.user.first_name} {d.user.last_name}</b>
                <div className="text-sm text-slate-500">{d.specialization} · {d.department_name} · {d.user.email}</div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {!d.is_verified && <button onClick={() => verify(d.id)} className="rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white">Verify</button>}
                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${d.is_active && d.is_verified ? 'bg-green-100 text-green-700' : 'bg-slate-200 text-slate-600'}`}>{d.is_active && d.is_verified ? 'Visible to patients' : 'Hidden'}</span>
                <button onClick={() => toggleDoctor(d)} className="rounded-lg border px-3 py-2 text-sm">{d.is_active ? 'Deactivate' : 'Activate'}</button>
                <button onClick={() => setScheduleFor(scheduleFor === d.id ? null : d.id)} className="rounded-lg border px-3 py-2 text-sm">Schedule</button>
              </div>
            </div>
            {scheduleFor === d.id && <div className="mt-4 rounded-lg bg-white p-4">
              <div className="flex flex-wrap gap-2">
                {d.schedules?.map(s => <span key={s.id} className="flex items-center gap-2 rounded-full bg-green-50 px-3 py-1 text-xs text-green-800">{DAYS[s.weekday]} {s.start_time.slice(0, 5)}–{s.end_time.slice(0, 5)} · {s.slot_minutes}m<button onClick={() => removeSchedule(s.id)} className="font-bold text-red-600">×</button></span>)}
                {!d.schedules?.length && <span className="text-sm text-slate-500">No sessions yet — patients cannot book until you add one.</span>}
              </div>
              <form onSubmit={addSchedule} className="mt-3 grid gap-2 sm:grid-cols-5">
                <select className={input} value={schedule.weekday} onChange={e => setSchedule({ ...schedule, weekday: e.target.value })}>{DAYS.map((n, i) => <option key={n} value={i}>{n}</option>)}</select>
                <input type="time" required className={input} value={schedule.start_time} onChange={e => setSchedule({ ...schedule, start_time: e.target.value })} />
                <input type="time" required className={input} value={schedule.end_time} onChange={e => setSchedule({ ...schedule, end_time: e.target.value })} />
                <input type="number" min="5" max="120" required className={input} value={schedule.slot_minutes} onChange={e => setSchedule({ ...schedule, slot_minutes: e.target.value })} />
                <button className="rounded-lg bg-green-600 p-3 font-semibold text-white">Add</button>
              </form>
            </div>}
          </div>)}
        </div>
      </section>
    </div>

    <section className="mt-6 rounded-2xl border bg-white p-6">
      <h2 className="font-bold">Hospital appointments</h2>
      <div className="mt-4 overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead><tr className="border-b"><th className="p-3">Token</th><th className="p-3">Patient</th><th className="p-3">Doctor</th><th className="p-3">Date</th><th className="p-3">Time</th><th className="p-3">Status</th><th className="p-3">Action</th></tr></thead>
          <tbody>{appointments.map(a => <tr key={a.id} className="border-b">
            <td className="p-3 font-bold">#{a.token_number}</td>
            <td className="p-3">{a.patient_name}</td>
            <td className="p-3">Dr. {a.doctor_detail?.user?.first_name} {a.doctor_detail?.user?.last_name}</td>
            <td className="p-3">{a.appointment_date}</td>
            <td className="p-3">{a.appointment_time?.slice(0, 5)}</td>
            <td className="p-3">{a.status}</td>
            <td className="p-3">{a.status === 'BOOKED' && <button onClick={() => setStatus(a.id, 'CHECKED_IN')} className="rounded-lg bg-blue-600 px-3 py-1 text-white">Check in</button>}</td>
          </tr>)}</tbody>
        </table>
        {!appointments.length && <p className="p-6 text-center text-slate-500">No appointments yet.</p>}
      </div>
    </section>
  </div>;
}