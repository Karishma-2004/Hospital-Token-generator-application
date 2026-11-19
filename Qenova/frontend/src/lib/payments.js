import { api } from './api';

function loadRazorpay() {
  return new Promise((resolve, reject) => {
    if (window.Razorpay) {
      resolve();
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.onload = resolve;
    script.onerror = () => reject(new Error('Could not load the payment window. Check your internet connection.'));
    document.body.appendChild(script);
  });
}

/**
 * Pays the consultation fee of one appointment.
 * Works with the demo gateway (a confirm box, no money moves) and with Razorpay Checkout,
 * depending on PAYMENT_PROVIDER on the server. Resolves when the server has marked it PAID.
 */
export async function payForAppointment(appointment, user) {
  const { data: order } = await api.post(`/appointments/${appointment.id}/pay/`);
  const verify = (body) => api.post(`/appointments/${appointment.id}/pay/verify/`, body);

  if (order.provider === 'razorpay') {
    await loadRazorpay();
    return new Promise((resolve, reject) => {
      const checkout = new window.Razorpay({
        key: order.key_id,
        amount: order.amount_paise,
        currency: order.currency,
        order_id: order.order_id,
        name: 'Qenova',
        description: `Consultation fee - token #${appointment.token_number}`,
        prefill: {
          name: [user?.first_name, user?.last_name].filter(Boolean).join(' '),
          email: user?.email || '',
          contact: user?.mobile || '',
        },
        handler: async (response) => {
          try {
            await verify({
              order_id: response.razorpay_order_id,
              payment_id: response.razorpay_payment_id,
              signature: response.razorpay_signature,
            });
            resolve();
          } catch (e) {
            reject(e);
          }
        },
        modal: { ondismiss: () => reject(new Error('Payment cancelled.')) },
      });
      checkout.on('payment.failed', (response) => reject(new Error(response.error?.description || 'Payment failed.')));
      checkout.open();
    });
  }

  const ok = window.confirm(
    `Demo payment: pay INR ${order.amount} for token #${appointment.token_number}?\n(The demo gateway does not charge any money.)`
  );
  if (!ok) throw new Error('Payment cancelled.');
  await verify({ order_id: order.order_id, payment_id: '', signature: 'mock-signature' });
}
