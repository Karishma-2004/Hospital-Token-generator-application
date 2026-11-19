import { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { QRCodeCanvas } from 'qrcode.react';
import { api } from '../lib/api';
import { apiError } from '../lib/errors';
import { payForAppointment } from '../lib/payments';
import { downloadPrescriptionPdf } from '../lib/prescriptionPdf';
import QueueStatus from '../components/QueueStatus';

const PAYMENT_BADGE = {
  PAID: 'bg-green-100 text-green-700',
  UNPAID: 'bg-amber-100 text-amber-800',
  REFUND_DUE: 'bg-purple-100 text-purple-700',
  NOT_REQUIRED: 'bg-slate-100 text-slate-500',
};
const PAYMENT_LABEL = { PAID: 'Paid', UNPAID: 'Unpaid', REFUND_DUE: 'Refund due', NOT_REQUIRED: 'No fee' };

export default function Appointments({ user }) {
  const [appointments, setAppointments] = useState([]);
  const [selected, setSelected] = useState(null);
  const [newDate, setNewDate] = useState('');
  const [newTime, setNewTime] = useState('');
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');
  const [paying, setPaying] = useState(null);
  const location = useLocation();
  const qrBox = useRef(null);   // wraps the QR canvas so it can be saved or shared as a picture

  const load = () => api.get('/appointments/').then((r) => setAppointments(r.data.results || r.data));
  useEffect(() => {
    load();
    if (location.state?.booked) setSelected(location.state.booked);
  }, []);

  const say = (text) => { setMsg(text); setError(''); };
  const fail = (text) => { setError(text); setMsg(''); };

  async function cancel(id) {
    if (!window.confirm('Cancel this appointment?')) return;
    try {
      await api.delete(`/appointments/${id}/`);
      load();
      say('Appointment cancelled.');
    } catch (e) {
      fail(apiError(e, 'Unable to cancel.'));
    }
  }

  async function reschedule(id) {
    try {
      await api.put(`/appointments/${id}/`, { appointment_date: newDate, appointment_time: newTime });
      setSelected(null);
      say('Appointment rescheduled.');
      load();
    } catch (e) {
      fail(apiError(e, 'Unable to reschedule.'));
    }
  }

  async function pay(a) {
    setPaying(a.id);
    try {
      await payForAppointment(a, user);
      const r = await api.get('/appointments/');
      const list = r.data.results || r.data;
      setAppointments(list);
      setNewDate('');
      setSelected(list.find((x) => x.id === a.id) || null);   // shows the QR ticket the payment just created
      say(`Payment received for token #${a.token_number}. Your QR ticket is ready below. A receipt was sent to your email.`);
    } catch (e) {
      fail(apiError(e, e.message || 'Payment failed.'));
    } finally {
      setPaying(null);
    }
  }

  const doctorName = (a) => `Dr. ${a.doctor_detail?.user?.first_name || ''} ${a.doctor_detail?.user?.last_name || ''}`.trim();
  const fileName = (a) => `medibook-ticket-token-${a.token_number}.png`;

  // Builds a PNG "ticket": the QR plus token, hospital, doctor and time, ready to save or send
  async function ticketBlob(a) {
    const qr = qrBox.current?.querySelector('canvas');
    if (!qr) throw new Error('The QR code is not ready yet.');
    const canvas = document.createElement('canvas');
    canvas.width = 640;
    canvas.height = 860;
    const g = canvas.getContext('2d');
    g.fillStyle = '#ffffff';
    g.fillRect(0, 0, 640, 860);
    g.fillStyle = '#15803d';
    g.fillRect(0, 0, 640, 96);
    g.fillStyle = '#ffffff';
    g.font = 'bold 38px sans-serif';
    g.fillText('Qenova appointment', 36, 62);
    g.imageSmoothingEnabled = false;                 // keeps the QR squares sharp
    g.drawImage(qr, 120, 130, 400, 400);
    g.fillStyle = '#0f172a';
    g.textAlign = 'center';
    g.font = 'bold 56px sans-serif';
    g.fillText(`Token #${a.token_number}`, 320, 610);
    g.font = '28px sans-serif';
    g.fillText(a.hospital_name, 320, 662);
    g.fillText(doctorName(a), 320, 704);
    g.fillText(`${a.appointment_date}  ·  ${String(a.appointment_time).slice(0, 5)}`, 320, 746);
    g.fillStyle = '#64748b';
    g.font = '22px sans-serif';
    g.fillText('Show this QR at the reception desk. It works once.', 320, 808);
    return new Promise((resolve, reject) =>
      canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('Unable to create the picture.'))), 'image/png')
    );
  }

  async function downloadTicket(a) {
    try {
      const blob = await ticketBlob(a);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName(a);
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      fail(e.message || 'Unable to download the ticket.');
    }
  }

  async function shareTicket(a) {
    try {
      const blob = await ticketBlob(a);
      const file = new File([blob], fileName(a), { type: 'image/png' });
      const text = `Qenova appointment\nToken #${a.token_number}\n${a.hospital_name}\n${doctorName(a)}\n${a.appointment_date} ${String(a.appointment_time).slice(0, 5)}`;
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({ files: [file], title: 'Qenova ticket', text });   // phones: opens the share sheet with WhatsApp
        return;
      }
      // browsers that cannot share a picture: save it, then open WhatsApp with the details as text
      await downloadTicket(a);
      window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank', 'noopener');
      say('The ticket picture was saved. Attach it in the WhatsApp chat that just opened.');
    } catch (e) {
      if (e?.name !== 'AbortError') fail(e.message || 'Unable to share the ticket.');
    }
  }

  async function downloadRx(a) {
    try {
      const r = await api.get(`/appointments/${a.id}/prescription/`);
      downloadPrescriptionPdf(r.data);
    } catch (e) {
      fail(apiError(e, 'Unable to download the prescription.'));
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-10">
      <h1 className="text-4xl font-black">My Appointments</h1>
      <QueueStatus />
      {msg && <div className="mt-4 rounded-xl bg-green-50 p-3 text-sm text-green-700">{msg}</div>}
      {error && <div className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      {selected && (
        <div className="mt-6 flex flex-col gap-6 rounded-2xl bg-green-50 p-6 md:flex-row md:items-center">
          <div>
            <p className="text-sm text-green-700">Booking confirmed</p>
            <h2 className="mt-1 text-2xl font-black">Token #{selected.token_number}</h2>
            <p className="mt-2">{selected.hospital_name} · {selected.doctor_detail?.user?.first_name} {selected.doctor_detail?.user?.last_name}</p>
            <p className="text-sm text-slate-600">{selected.appointment_date} · {selected.appointment_time}</p>
          </div>
          {selected.qr_payload ? (
            <div className="flex flex-col items-center gap-3">
              <div ref={qrBox} className="rounded-xl bg-white p-3">
                <QRCodeCanvas value={selected.qr_payload} size={220} level="H" />
              </div>
              <div className="flex flex-wrap justify-center gap-2">
                <button onClick={() => downloadTicket(selected)} className="rounded-lg border bg-white px-4 py-2 text-sm font-semibold">Download QR</button>
                <button onClick={() => shareTicket(selected)} className="rounded-lg bg-green-600 px-4 py-2 text-sm font-semibold text-white">Share on WhatsApp</button>
              </div>
            </div>
          ) : selected.payment_status === 'UNPAID' && selected.status !== 'CANCELLED' ? (
            <div className="max-w-xs text-sm">
              <p className="font-semibold text-amber-800">Pay INR {selected.fee} to get your QR ticket.</p>
              <button
                disabled={paying === selected.id}
                onClick={() => pay(selected)}
                className="mt-2 rounded-lg bg-green-600 px-4 py-2 font-semibold text-white disabled:opacity-50"
              >
                {paying === selected.id ? 'Paying…' : `Pay INR ${selected.fee}`}
              </button>
            </div>
          ) : (
            <p className="max-w-[150px] text-sm text-slate-600">QR already used, or no check-in needed.</p>
          )}
        </div>
      )}

      <div className="mt-7 overflow-hidden rounded-2xl border bg-white">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="p-4">Hospital</th><th className="p-4">Doctor</th><th className="p-4">Date</th>
                <th className="p-4">Time</th><th className="p-4">Token</th><th className="p-4">Status</th>
                <th className="p-4">Fee</th><th className="p-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {appointments.map((a) => (
                <tr key={a.id} className="border-t">
                  <td className="p-4">{a.hospital_name}</td>
                  <td className="p-4">Dr. {a.doctor_detail?.user?.first_name} {a.doctor_detail?.user?.last_name}</td>
                  <td className="p-4">{a.appointment_date}</td>
                  <td className="p-4">{a.appointment_time}</td>
                  <td className="p-4 font-bold">#{a.token_number}</td>
                  <td className="p-4">{a.status}</td>
                  <td className="p-4">
                    {a.payment_status !== 'NOT_REQUIRED' && <p className="mb-1 font-semibold">INR {a.fee}</p>}
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${PAYMENT_BADGE[a.payment_status] || ''}`}>
                      {PAYMENT_LABEL[a.payment_status] || a.payment_status}
                    </span>
                  </td>
                  <td className="p-4">
                    <div className="flex flex-wrap gap-2">
                      {a.payment_status === 'UNPAID' && a.status !== 'CANCELLED' && (
                        <button
                          disabled={paying === a.id}
                          onClick={() => pay(a)}
                          className="rounded-lg bg-green-600 px-3 py-2 font-semibold text-white disabled:opacity-50"
                        >
                          {paying === a.id ? 'Paying…' : `Pay INR ${a.fee}`}
                        </button>
                      )}
                      {a.has_prescription && (
                        <>
                          <Link to={`/prescriptions/${a.id}`} className="rounded-lg bg-purple-50 px-3 py-2 text-purple-700">Prescription</Link>
                          <button onClick={() => downloadRx(a)} className="rounded-lg bg-purple-600 px-3 py-2 font-semibold text-white">Download PDF</button>
                        </>
                      )}
                      {a.status === 'BOOKED' && (
                        <>
                          <button onClick={() => cancel(a.id)} className="rounded-lg bg-red-50 px-3 py-2 text-red-700">Cancel</button>
                          <button
                            onClick={() => { setSelected(a); setNewDate(a.appointment_date); setNewTime(a.appointment_time); }}
                            className="rounded-lg bg-blue-50 px-3 py-2 text-blue-700"
                          >
                            Reschedule
                          </button>
                        </>
                      )}
                      {a.status !== 'CANCELLED' && (
                        <button onClick={() => { setSelected(a); setNewDate(''); }} className="rounded-lg bg-green-50 px-3 py-2 text-green-700">QR ticket</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!appointments.length && <p className="p-8 text-center text-slate-500">No appointments yet.</p>}
        </div>
      </div>

      {selected && selected.id && newDate && (
        <div className="mt-6 rounded-2xl border bg-white p-6">
          <h2 className="font-bold">Reschedule appointment #{selected.token_number}</h2>
          <div className="mt-4 flex flex-col gap-3 md:flex-row">
            <input type="date" value={newDate} onChange={(e) => setNewDate(e.target.value)} className="rounded-xl border p-3" />
            <input type="time" value={newTime} onChange={(e) => setNewTime(e.target.value)} className="rounded-xl border p-3" />
            <button onClick={() => reschedule(selected.id)} className="rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white">Save new slot</button>
            <button onClick={() => setSelected(null)} className="rounded-xl border px-5 py-3">Close</button>
          </div>
        </div>
      )}
    </div>
  );
}