import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Activity,
  CalendarCheck,
  Hospital,
  QrCode,
} from 'lucide-react';
import { api } from '../lib/api';
import { apiError } from '../lib/errors';

export default function Register() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    password_confirm: '',
    first_name: '',
    last_name: '',
    mobile: '',
  });

  const [code, setCode] = useState('');
  const [step, setStep] = useState('register');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const set = (k, v) => setForm({ ...form, [k]: v });

  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');

    try {
      await api.post('/auth/register/', form);
      setStep('verify');
      setMessage(`A 6-digit verification code was sent to ${form.email}.`);
    } catch (e) {
      setError(
        apiError(
          e,
          'Unable to create account. Check the backend terminal for SMTP errors.'
        )
      );
    } finally {
      setLoading(false);
    }
  }

  async function verify(e) {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const r = await api.post('/auth/verify-email/', {
        email: form.email,
        code,
      });

      setMessage(r.data.detail);
      setTimeout(() => navigate('/login'), 700);
    } catch (e) {
      setError(apiError(e, 'Unable to verify email.'));
    } finally {
      setLoading(false);
    }
  }

  async function resend() {
    setLoading(true);
    setError('');

    try {
      const r = await api.post('/auth/resend-verification/', {
        email: form.email,
      });
      setMessage(r.data.detail);
    } catch (e) {
      setError(apiError(e, 'Unable to send verification code.'));
    } finally {
      setLoading(false);
    }
  }

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
            Your health journey
            <br />
            <span className="text-emerald-300">
              starts here.
            </span>
          </h2>

          <p className="mt-3 max-w-md text-sm leading-6 text-emerald-100/70">
            Create your account and experience a smarter way to manage
            healthcare. Connect with hospitals, book appointments, and
            manage your visits effortlessly.
          </p>

          {/* Feature cards */}
          <div className="mt-5 space-y-2">

            <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 backdrop-blur-md">
              <div className="rounded-lg bg-emerald-400/20 p-2 text-emerald-300">
                <CalendarCheck size={20} />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">
                  Online Appointments
                </h3>
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
                <h3 className="text-sm font-semibold text-white">
                  QR Code Check-in
                </h3>
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
                <h3 className="text-sm font-semibold text-white">
                  Live Queue Tracking
                </h3>
                <p className="text-xs text-emerald-100/60">
                  Monitor your waiting time
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

      {/* RIGHT REGISTER FORM */}
      <div className="grid min-h-screen place-items-center bg-slate-50 px-4 py-8 lg:min-h-0 lg:overflow-y-auto lg:px-6 lg:py-5">

        <div className="w-full max-w-2xl rounded-2xl bg-white p-8 shadow-xl">

          {step === 'register' ? (
            <form onSubmit={submit}>

              <h1 className="text-3xl font-bold">
                Create your account
              </h1>

              <p className="mt-2 text-slate-500">
                Register with your email. We will send a 6-digit verification code.
              </p>

              {error && (
                <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
                  {error}
                </div>
              )}

              <div className="mt-6 grid gap-3 sm:grid-cols-2">

                {[
                  ['username', 'Username'],
                  ['email', 'Email address'],
                  ['first_name', 'First name'],
                  ['last_name', 'Last name'],
                  ['mobile', 'Mobile number'],
                ].map(([key, placeholder]) => (
                  <input
                    key={key}
                    required={key === 'username' || key === 'email'}
                    type={key === 'email' ? 'email' : 'text'}
                    className="rounded-lg border border-slate-300 p-3 outline-none focus:border-green-600"
                    placeholder={placeholder}
                    value={form[key]}
                    onChange={(e) => set(key, e.target.value)}
                  />
                ))}

                <input
                  required
                  type="password"
                  className="rounded-lg border border-slate-300 p-3 outline-none focus:border-green-600"
                  placeholder="Password (8+ characters)"
                  value={form.password}
                  onChange={(e) => set('password', e.target.value)}
                />

                <input
                  required
                  type="password"
                  className="rounded-lg border border-slate-300 p-3 outline-none focus:border-green-600"
                  placeholder="Confirm password"
                  value={form.password_confirm}
                  onChange={(e) => set('password_confirm', e.target.value)}
                />

              </div>

              <button
                disabled={loading}
                className="mt-5 w-full rounded-lg bg-green-600 p-3 font-semibold text-white disabled:opacity-60"
              >
                {loading ? 'Creating account…' : 'Register'}
              </button>

              <p className="mt-5 text-center text-sm text-slate-600">
                Already registered?{' '}
                <Link
                  className="font-semibold text-green-700"
                  to="/login"
                >
                  Sign in
                </Link>
              </p>

            </form>
          ) : (
            <form onSubmit={verify}>

              <h1 className="text-3xl font-bold">
                Verify your email
              </h1>

              <p className="mt-2 text-slate-500">
                Enter the 6-digit code sent to{' '}
                <span className="font-semibold text-slate-700">
                  {form.email}
                </span>.
              </p>

              {error && (
                <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
                  {error}
                </div>
              )}

              {message && (
                <div className="mt-4 rounded-lg bg-green-50 p-3 text-sm text-green-700">
                  {message}
                </div>
              )}

              <input
                required
                inputMode="numeric"
                maxLength={6}
                pattern="[0-9]{6}"
                className="mt-6 w-full rounded-lg border border-slate-300 p-4 text-center text-2xl tracking-[0.5em] outline-none focus:border-green-600"
                placeholder="000000"
                value={code}
                onChange={(e) =>
                  setCode(e.target.value.replace(/\D/g, '').slice(0, 6))
                }
              />

              <button
                disabled={loading || code.length !== 6}
                className="mt-5 w-full rounded-lg bg-green-600 p-3 font-semibold text-white disabled:opacity-60"
              >
                {loading ? 'Verifying…' : 'Verify email'}
              </button>

              <button
                type="button"
                disabled={loading}
                onClick={resend}
                className="mt-3 w-full rounded-lg border border-slate-300 p-3 font-semibold text-slate-700"
              >
                Send a new code
              </button>

              <button
                type="button"
                onClick={() => {
                  setStep('register');
                  setError('');
                  setMessage('');
                }}
                className="mt-3 w-full p-2 text-sm text-green-700"
              >
                Use a different email
              </button>

            </form>
          )}

        </div>
      </div>
    </div>
  );
}
