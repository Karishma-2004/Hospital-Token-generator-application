
import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Activity,
  CalendarCheck,
  Hospital,
  QrCode
} from 'lucide-react';
import { api, setTokens } from '../lib/api';
import { apiError } from '../lib/errors';

export default function Login({ onLogin }) {
  const [form, setForm] = useState({
    username: '',
    password: ''
  });

  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const nav = useNavigate();
  const location = useLocation();

  async function submit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const r = await api.post('/auth/token/', form);
      setTokens(r.data);

      const me = await api.get('/auth/me/');
      onLogin(me.data);

      const role = me.data.effective_role || me.data.role;
      const from = location.state?.from;

      if (from) {
        nav(from);
        return;
      }

      if (role === 'ADMIN') nav('/admin/dashboard');
      else if (role === 'RECEPTIONIST') nav('/reception');
      else if (role === 'DOCTOR') nav('/doctor-dashboard');
      else nav('/hospitals');

    } catch (e) {
      setError(apiError(e, 'Login failed.'));
    } finally {
      setLoading(false);
    }
  }

  // LOGIN FORM - UNCHANGED
  const card = (
    <form
      onSubmit={submit}
      className="w-full max-w-md rounded-3xl bg-white p-8 shadow-xl"
    >
      <p className="text-sm font-semibold text-green-700">
        Qenova
      </p>

      <h1 className="mt-1 text-3xl font-black">
        Welcome back
      </h1>

      <p className="mt-2 text-slate-500">
        Sign in with your assigned account.
      </p>

      {error && (
        <div className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <input
        required
        className="mt-6 w-full rounded-xl border p-3"
        placeholder="Username or email username"
        value={form.username}
        onChange={(e) =>
          setForm({ ...form, username: e.target.value })
        }
      />

      <input
        required
        type="password"
        className="mt-3 w-full rounded-xl border p-3"
        placeholder="Password"
        value={form.password}
        onChange={(e) =>
          setForm({ ...form, password: e.target.value })
        }
      />

      <button
        disabled={loading}
        className="mt-5 w-full rounded-xl bg-green-600 p-3 font-semibold text-white disabled:opacity-60"
      >
        {loading ? 'Signing in...' : 'Sign in'}
      </button>

      <div className="mt-4 flex justify-between text-sm">
        <Link
          className="text-green-700"
          to="/forgot-password"
        >
          Forgot password?
        </Link>

        <Link
          className="text-green-700"
          to="/resend-verification"
        >
          Verify email
        </Link>
      </div>

      <div className="mt-6 border-t pt-5 text-center text-sm">
        <p>
          New user?{' '}
          <Link
            className="font-semibold text-green-700"
            to="/register"
          >
            Create user account
          </Link>
        </p>

        <p className="mt-2">
          Hospital?{' '}
          <Link
            className="font-semibold text-green-700"
            to="/hospital-register"
          >
            Register hospital
          </Link>
        </p>
      </div>
    </form>
  );

  return (
    <div className="grid min-h-screen lg:h-screen lg:grid-cols-2 lg:overflow-hidden">

      {/* UPDATED BACKGROUND UI */}
      <div className="relative hidden min-h-0 overflow-hidden bg-gradient-to-br from-slate-950 via-emerald-950 to-green-900 px-8 py-6 text-white lg:flex lg:flex-col lg:justify-between xl:px-12">

        {/* Background circles */}
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
            Care that
            <br />
            <span className="text-emerald-300">
              moves with you.
            </span>
          </h2>

          <p className="mt-3 max-w-md text-sm leading-6 text-emerald-100/70">
            Experience a smarter way to manage healthcare.
            Book appointments, track your queue, and connect
            with hospitals effortlessly.
          </p>

          {/* Feature cards */}
          <div className="mt-5 space-y-2">

            <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 backdrop-blur-md">
              <div className="rounded-lg bg-emerald-400/20 p-2 text-emerald-300">
                <CalendarCheck size={20} />
              </div>

              <div>
                <p className="text-sm font-semibold">
                  Online Appointments
                </p>

                <p className="text-xs text-emerald-100/60">
                  Book doctor visits anytime
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 backdrop-blur-md">
              <div className="rounded-lg bg-emerald-400/20 p-2 text-emerald-300">
                <QrCode size={20} />
              </div>

              <div>
                <p className="text-sm font-semibold">
                  QR Code Check-in
                </p>

                <p className="text-xs text-emerald-100/60">
                  Quick and convenient registration
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 backdrop-blur-md">
              <div className="rounded-lg bg-emerald-400/20 p-2 text-emerald-300">
                <Activity size={20} />
              </div>

              <div>
                <p className="text-sm font-semibold">
                  Live Queue Tracking
                </p>

                <p className="text-xs text-emerald-100/60">
                  Monitor your waiting time
                </p>
              </div>
            </div>

          </div>
        </div>

        {/* Bottom section */}
        <div className="relative z-10 flex shrink-0 items-center gap-3 border-t border-white/10 pt-3 text-xs text-emerald-100/50">
          <div className="h-px flex-1 bg-gradient-to-r from-emerald-300/40 to-transparent" />

          <span>
            Healthcare made simple
          </span>
        </div>

      </div>

      {/* ORIGINAL FORM SIDE - UNCHANGED */}
      <div className="grid place-items-center bg-slate-50 px-4 py-10">
        {card}
      </div>

    </div>
  );
}
