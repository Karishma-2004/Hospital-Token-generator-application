import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Activity,
  CalendarCheck,
  Hospital,
  QrCode,
  ShieldCheck,
} from 'lucide-react';
import { api } from '../lib/api';
import { apiError } from '../lib/errors';

const initial = {
  name: '',
  registration_number: '',
  address: '',
  city: '',
  state: '',
  pincode: '',
  phone: '',
  email: '',
  description: '',
  admin_name: '',
  admin_email: '',
  admin_password: '',
};

export default function HospitalRegister() {
  const [form, setForm] = useState(initial);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);

  const set = (k, v) => setForm({ ...form, [k]: v });

  async function submit(e) {
    e.preventDefault();
    setErr('');
    setMsg('');
    setLoading(true);

    try {
      const r = await api.post('/doctors/hospitals/register/', form);
      setMsg(r.data.message);
      setForm(initial);
    } catch (e) {
      setErr(apiError(e, 'Hospital registration failed.'));
    } finally {
      setLoading(false);
    }
  }

  const fields = [
    ['name', 'Hospital name'],
    ['registration_number', 'Hospital registration number'],
    ['address', 'Full address'],
    ['city', 'City'],
    ['state', 'State'],
    ['pincode', 'Pincode'],
    ['phone', 'Hospital phone'],
    ['email', 'Hospital email'],
    ['admin_name', 'Hospital administrator name'],
    ['admin_email', 'Administrator email'],
  ];

  return (
    <div className="grid min-h-screen lg:h-screen lg:min-h-0 lg:grid-cols-2 lg:overflow-hidden">

      {/* LEFT BACKGROUND PANEL */}
      <div className="relative hidden min-h-0 overflow-hidden bg-gradient-to-br from-slate-950 via-emerald-950 to-green-900 px-8 py-6 text-white lg:flex lg:flex-col lg:justify-between xl:px-12">

        {/* Decorative background */}
        <div className="pointer-events-none absolute -right-32 -top-32 h-80 w-80 rounded-full border-[35px] border-emerald-400/10" />

        <div className="pointer-events-none absolute -bottom-32 -left-20 h-80 w-80 rounded-full bg-emerald-400/10 blur-3xl" />

        <div className="pointer-events-none absolute right-20 top-1/3 h-60 w-60 rounded-full bg-green-500/10 blur-3xl" />

        {/* Logo */}
        <Link
          to="/"
          className="relative z-10 inline-flex w-fit items-center gap-3 text-xl font-black"
        >
          <div className="rounded-xl border border-white/10 bg-white/10 p-2.5">
            <Hospital size={25} />
          </div>
          Qenova
        </Link>

        {/* Main content */}
        <div className="relative z-10 my-auto max-w-xl py-3">

          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-emerald-300/20 bg-white/10 px-3 py-1.5 text-xs text-emerald-100">
            <Activity size={14} />
            Smart Healthcare Platform
          </div>

          <h2 className="max-w-lg text-4xl font-black leading-tight tracking-tight xl:text-5xl">
            Bring better care
            <br />
            <span className="text-emerald-300">
              to your community.
            </span>
          </h2>

          <p className="mt-3 max-w-md text-sm leading-6 text-emerald-100/70">
            Join our healthcare platform and simplify hospital management.
            Connect with patients, manage appointments, and provide a
            better healthcare experience.
          </p>

          {/* Feature cards */}
          <div className="mt-5 space-y-2">

            <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 backdrop-blur-md">
              <div className="rounded-lg bg-emerald-400/20 p-2 text-emerald-300">
                <CalendarCheck size={20} />
              </div>

              <div>
                <h3 className="text-sm font-semibold text-white">
                  Appointment Management
                </h3>
                <p className="text-xs text-emerald-100/60">
                  Manage patient appointments easily
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 backdrop-blur-md">
              <div className="rounded-lg bg-emerald-400/20 p-2 text-emerald-300">
                <QrCode size={20} />
              </div>

              <div>
                <h3 className="text-sm font-semibold text-white">
                  Digital Token System
                </h3>
                <p className="text-xs text-emerald-100/60">
                  Organize patient queues efficiently
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 backdrop-blur-md">
              <div className="rounded-lg bg-emerald-400/20 p-2 text-emerald-300">
                <ShieldCheck size={20} />
              </div>

              <div>
                <h3 className="text-sm font-semibold text-white">
                  Secure Hospital Access
                </h3>
                <p className="text-xs text-emerald-100/60">
                  Controlled and secure platform access
                </p>
              </div>
            </div>

          </div>
        </div>

        {/* Footer */}
        <div className="relative z-10 flex shrink-0 items-center gap-3 border-t border-white/10 pt-3 text-xs text-emerald-100/50">
          <div className="h-px flex-1 bg-gradient-to-r from-emerald-300/40 to-transparent" />
          <span>Healthcare made simple</span>
        </div>
      </div>

      {/* RIGHT HOSPITAL REGISTER FORM */}
      <div className="grid min-h-screen place-items-center bg-slate-50 px-4 py-8 lg:min-h-0 lg:overflow-y-auto lg:px-6 lg:py-5">

        <form
          onSubmit={submit}
          className="w-full max-w-3xl rounded-3xl bg-white p-6 shadow-xl sm:p-8"
        >

          <p className="text-sm font-semibold text-green-700">
            Qenova hospital onboarding
          </p>

          <h1 className="mt-1 text-3xl font-black">
            Register your hospital
          </h1>

          <p className="mt-2 text-sm leading-6 text-slate-500">
            Register your hospital to connect with patients and manage
            healthcare services through our platform.
          </p>

          {/* Error message */}
          {err && (
            <div className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">
              {err}
            </div>
          )}

          {/* Success message */}
          {msg && (
            <div className="mt-4 rounded-xl bg-green-50 p-3 text-sm text-green-700">
              {msg}
            </div>
          )}

          {/* Hospital details */}
          <div className="mt-5">

            <h2 className="mb-3 text-sm font-bold text-slate-800">
              Hospital Information
            </h2>

            <div className="grid gap-3 sm:grid-cols-2">

              {fields.slice(0, 8).map(([k, label]) => (
                <input
                  key={k}
                  required
                  type={
                    k === 'email'
                      ? 'email'
                      : 'text'
                  }
                  className="w-full rounded-xl border border-slate-300 p-3 text-sm outline-none transition focus:border-green-600 focus:ring-2 focus:ring-green-100"
                  placeholder={label}
                  value={form[k]}
                  onChange={(e) => set(k, e.target.value)}
                />
              ))}

            </div>
          </div>

          {/* Administrator details */}
          <div className="mt-5">

            <h2 className="mb-3 text-sm font-bold text-slate-800">
              Hospital Administrator Details
            </h2>

            <div className="grid gap-3 sm:grid-cols-2">

              {fields.slice(8).map(([k, label]) => (
                <input
                  key={k}
                  required
                  type={k === 'admin_email' ? 'email' : 'text'}
                  className="w-full rounded-xl border border-slate-300 p-3 text-sm outline-none transition focus:border-green-600 focus:ring-2 focus:ring-green-100"
                  placeholder={label}
                  value={form[k]}
                  onChange={(e) => set(k, e.target.value)}
                />
              ))}

              <input
                required
                minLength={8}
                type="password"
                className="w-full rounded-xl border border-slate-300 p-3 text-sm outline-none transition focus:border-green-600 focus:ring-2 focus:ring-green-100 sm:col-span-2"
                placeholder="Administrator password (8+ characters)"
                value={form.admin_password}
                onChange={(e) => set('admin_password', e.target.value)}
              />

            </div>
          </div>

          {/* Hospital description */}
          <div className="mt-4">
            <textarea
              required
              className="w-full rounded-xl border border-slate-300 p-3 text-sm outline-none transition focus:border-green-600 focus:ring-2 focus:ring-green-100"
              rows="2"
              placeholder="Hospital description"
              value={form.description}
              onChange={(e) => set('description', e.target.value)}
            />
          </div>

          <p className="mt-3 text-xs leading-5 text-slate-500">
            The hospital administrator is created as a Receptionist account
            and remains inactive until the Application Admin approves
            the hospital.
          </p>

          {/* Submit button */}
          <button
            disabled={loading}
            className="mt-5 w-full rounded-xl bg-green-600 p-3 font-semibold text-white transition hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading
              ? 'Submitting...'
              : 'Submit hospital for approval'}
          </button>

          {/* Login link */}
          <p className="mt-5 text-center text-sm text-slate-600">
            Already have an account?{' '}
            <Link
              to="/login"
              className="font-semibold text-green-700 hover:text-green-800"
            >
              Sign in
            </Link>
          </p>

        </form>
      </div>
    </div>
  );
}
