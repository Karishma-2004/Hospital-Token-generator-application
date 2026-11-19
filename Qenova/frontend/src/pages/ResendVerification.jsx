import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import { apiError } from '../lib/errors';

export default function ResendVerification() {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault(); setMessage(''); setError(''); setLoading(true);
    try { const response = await api.post('/auth/resend-verification/', { email }); setMessage(response.data.detail); }
    catch (err) { setError(apiError(err, 'Unable to resend verification email.')); }
    finally { setLoading(false); }
  }

  return <div className="min-h-screen grid place-items-center bg-slate-50 p-4"><form onSubmit={submit} className="w-full max-w-md rounded-2xl bg-white p-8 shadow-xl"><h1 className="text-3xl font-bold">Resend verification</h1><p className="mt-2 text-slate-500">Enter your registered email address.</p>{error && <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}{message && <div className="mt-4 rounded-lg bg-green-50 p-3 text-sm text-green-700">{message}</div>}<input required type="email" className="mt-6 w-full rounded-lg border border-slate-300 p-3" placeholder="Email address" value={email} onChange={e => setEmail(e.target.value)} /><button disabled={loading} className="mt-5 w-full rounded-lg bg-green-600 p-3 font-semibold text-white disabled:opacity-60">{loading ? 'Sending…' : 'Send verification email'}</button><p className="mt-5 text-center text-sm"><Link className="text-green-700" to="/login">Back to sign in</Link></p></form></div>;
}
