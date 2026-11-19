import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Download, Printer } from 'lucide-react';
import { api } from '../lib/api';
import { apiError } from '../lib/errors';
import { downloadPrescriptionPdf } from '../lib/prescriptionPdf';

/** Read-only prescription for the patient and the treating doctor. */
export default function PrescriptionView() {
  const { appointmentId } = useParams();
  const nav = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get(`/appointments/${appointmentId}/prescription/`)
      .then((r) => setData(r.data))
      .catch((e) => setError(apiError(e, 'Unable to load the prescription.')));
  }, [appointmentId]);

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <div className="rounded-xl bg-red-50 p-4 text-red-700">{error}</div>
        <button onClick={() => nav(-1)} className="mt-4 rounded-lg border px-4 py-2">Back</button>
      </div>
    );
  }
  if (!data) return <p className="p-10 text-center text-slate-500">Loading prescription…</p>;

  const { prescription: rx, appointment, doctor, hospital } = data;
  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <button onClick={() => nav(-1)} className="rounded-lg border bg-white px-4 py-2">Back</button>
        <div className="flex gap-2">
          <button onClick={() => window.print()} className="flex items-center gap-2 rounded-lg border bg-white px-4 py-2"><Printer size={16} /> Print</button>
          <button onClick={() => downloadPrescriptionPdf(data)} className="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 font-semibold text-white"><Download size={16} /> Download PDF</button>
        </div>
      </div>

      <div className="mt-6 rounded-2xl border bg-white p-8 shadow-sm print:border-0 print:shadow-none">
        <h1 className="text-2xl font-black text-green-700">{hospital.name}</h1>
        <p className="text-sm text-slate-500">{[hospital.address, hospital.city].filter(Boolean).join(', ')} · {hospital.phone}</p>
        <hr className="my-4" />
        <div className="flex flex-wrap justify-between gap-4">
          <div>
            <p className="text-lg font-bold">{doctor.name}</p>
            <p className="text-sm text-slate-500">{doctor.specialization} · {doctor.department}</p>
            <p className="text-sm text-slate-500">Reg. no: {doctor.registration_number}</p>
          </div>
          <div className="text-right">
            <p className="font-semibold">{appointment.patient_name}</p>
            <p className="text-sm text-slate-500">{appointment.appointment_date} · Token #{appointment.token_number}</p>
          </div>
        </div>
        <hr className="my-4" />

        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Diagnosis</p>
        <p className="mt-1 whitespace-pre-wrap">{rx.diagnosis}</p>
        {rx.notes && (<><p className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">Clinical notes</p><p className="mt-1 whitespace-pre-wrap">{rx.notes}</p></>)}

        <p className="mt-6 text-3xl font-black">Rx</p>
        <div className="mt-2 space-y-3">
          {rx.items.map((item, index) => (
            <div key={index} className="rounded-xl bg-slate-50 p-4">
              <p className="font-bold">{index + 1}. {item.medicine}</p>
              <p className="text-sm text-slate-600">{[item.dosage, item.frequency, item.duration].filter(Boolean).join('  ·  ')}</p>
              {item.instructions && <p className="text-sm text-slate-500">{item.instructions}</p>}
            </div>
          ))}
          {!rx.items.length && <p className="text-slate-500">No medicines prescribed.</p>}
        </div>

        {rx.advice && (<><p className="mt-6 text-xs font-semibold uppercase tracking-wide text-slate-500">Advice</p><p className="mt-1 whitespace-pre-wrap">{rx.advice}</p></>)}
        {rx.follow_up_date && <p className="mt-6 font-semibold">Follow-up on {rx.follow_up_date}</p>}
      </div>
    </div>
  );
}
