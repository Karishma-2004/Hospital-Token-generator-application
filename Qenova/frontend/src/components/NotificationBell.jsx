import { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Bell } from 'lucide-react';
import { api } from '../lib/api';

const SEEN_KEY = 'adminPendingSeen';   // how many pending hospitals the admin has already looked at

function timeAgo(iso) {
  const minutes = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  return `${Math.round(hours / 24)} d ago`;
}

/** Bell for the Application Admin: lists hospitals waiting for approval. Opens by itself when a new one arrives. */
export default function NotificationBell() {
  const [data, setData] = useState({ pending_count: 0, pending_hospitals: [] });
  const [open, setOpen] = useState(false);
  const box = useRef(null);
  const location = useLocation();

  async function load() {
    try {
      const r = await api.get('/admin-panel/notifications/');
      setData(r.data);
      const seen = Number(localStorage.getItem(SEEN_KEY) || 0);
      if (r.data.pending_count > seen) setOpen(true);                                  // a registration the admin has not seen yet
      else if (r.data.pending_count < seen) localStorage.setItem(SEEN_KEY, String(r.data.pending_count));   // some were approved
    } catch {
      /* the bell is optional: ignore errors */
    }
  }

  useEffect(() => { load(); }, [location.pathname]);                 // also refreshes when the admin changes page
  useEffect(() => {
    const timer = setInterval(load, 30000);                          // and every 30 seconds
    return () => clearInterval(timer);
  }, []);

  function close() {
    localStorage.setItem(SEEN_KEY, String(data.pending_count));
    setOpen(false);
  }

  useEffect(() => {
    if (!open) return undefined;
    const onClick = (e) => { if (box.current && !box.current.contains(e.target)) close(); };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open, data.pending_count]);

  const count = data.pending_count;
  return (
    <div className="relative" ref={box}>
      <button
        onClick={() => (open ? close() : setOpen(true))}
        className="relative grid h-9 w-9 place-items-center rounded-full bg-slate-100 text-slate-700 hover:bg-slate-200"
        aria-label={`Notifications, ${count} hospitals waiting for approval`}
      >
        <Bell size={18} />
        {count > 0 && (
          <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-red-600 px-1 text-xs font-bold text-white">
            {count > 9 ? '9+' : count}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-30 mt-2 w-80 overflow-hidden rounded-2xl border bg-white shadow-xl">
          <div className="border-b bg-slate-50 px-4 py-3">
            <p className="font-bold">Hospitals waiting for approval</p>
            <p className="text-xs text-slate-500">{count ? `${count} pending` : 'Nothing pending'}</p>
          </div>
          <div className="max-h-72 overflow-y-auto">
            {data.pending_hospitals.map((h) => (
              <Link key={h.id} to="/admin" onClick={close} className="block border-b px-4 py-3 hover:bg-green-50">
                <p className="font-semibold">{h.name}</p>
                <p className="text-xs text-slate-500">{h.city} · Reg. {h.registration_number}</p>
                <p className="mt-0.5 text-xs text-green-700">Registered {timeAgo(h.created_at)} · Review</p>
              </Link>
            ))}
            {!count && <p className="px-4 py-6 text-center text-sm text-slate-500">All caught up.</p>}
          </div>
          <Link to="/admin" onClick={close} className="block bg-green-600 px-4 py-3 text-center text-sm font-semibold text-white">Open approvals</Link>
        </div>
      )}
    </div>
  );
}