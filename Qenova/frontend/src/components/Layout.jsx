import { Link, useNavigate } from 'react-router-dom';
import { Hospital, LogOut, ClipboardList, ShieldCheck, Stethoscope, LayoutDashboard, Users } from 'lucide-react';
import { logout } from '../lib/api';
import NotificationBell from './NotificationBell';

export default function Layout({ children, user }) {
  const nav = useNavigate();
  const role = user?.effective_role || user?.role;
  const link = 'flex items-center gap-1 hover:text-green-700';
  return <div className="min-h-screen bg-slate-50">
    <header className="sticky top-0 z-20 border-b bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-6 py-4">
        <Link to="/" className="flex items-center gap-2 text-xl font-black text-green-700"><Hospital /> Qenova</Link>
        <nav className="flex flex-wrap items-center gap-4 text-sm">
          {role === 'ADMIN' && <NotificationBell />}
          {role !== 'DOCTOR' && role !== 'RECEPTIONIST' && <Link to="/hospitals" className="hover:text-green-700">Hospitals</Link>}
          {role === 'USER' && <Link to="/appointments" className="hover:text-green-700">My Appointments</Link>}
          {role === 'ADMIN' && <Link to="/admin/dashboard" className={link}><LayoutDashboard size={16}/> Dashboard</Link>}
          {role === 'ADMIN' && <Link to="/admin" className={link}><ShieldCheck size={16}/> Approvals</Link>}
          {role === 'ADMIN' && <Link to="/admin/users" className={link}><Users size={16}/> Users</Link>}
          {role === 'RECEPTIONIST' && <Link to="/reception" className={link}><ClipboardList size={16}/> Reception desk</Link>}
          {role === 'RECEPTIONIST' && <Link to="/receptionist" className="hover:text-green-700">Manage hospital</Link>}
          {role === 'DOCTOR' && <Link to="/doctor-dashboard" className={link}><Stethoscope size={16}/> Doctor</Link>}
          {user ? <><span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600">{user.first_name || user.username}</span><button onClick={()=>{logout();nav('/login')}} className="flex items-center gap-1 text-slate-600"><LogOut size={16}/> Logout</button></> : <Link to="/login" className="rounded-lg bg-green-600 px-4 py-2 font-semibold text-white">Sign in</Link>}
        </nav>
      </div>
    </header>
    <main>{children}</main>
  </div>;
}