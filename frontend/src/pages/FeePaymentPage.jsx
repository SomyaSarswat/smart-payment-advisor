import React, { useState } from 'react';
import SmartAdvisorScreen from '../components/SmartAdvisorScreen';

/**
 * FeePaymentPage component
 * Mock merchant website for ABC College Fee Payment Portal.
 * Collects student & fee details before handing off to SmartAdvisorScreen AI recommender.
 */
export default function FeePaymentPage({ merchantId = 'college_fee_portal', refreshTrigger }) {
  const [studentName, setStudentName] = useState('Rahul Sharma');
  const [rollNumber, setRollNumber] = useState('CS2026-089');
  const [amount, setAmount] = useState(18000);
  const [showAdvisor, setShowAdvisor] = useState(false);

  // Selected payment method state
  const [selectedMethod, setSelectedMethod] = useState(null);
  
  // Payment processing & modal states
  const [processing, setProcessing] = useState(false);
  const [isSimulationMode, setIsSimulationMode] = useState(false);
  const [paymentStatus, setPaymentStatus] = useState(null); // { type: 'success' | 'error' | 'warning' | 'info', message: string }

  const handleSubmit = (e) => {
    e.preventDefault();
    setShowAdvisor(true);
    setPaymentStatus(null);
    setIsSimulationMode(false);
  };

  const handleMethodSelected = (method, bank) => {
    console.log('User selected payment method:', { method, bank, amount, studentName, rollNumber });
    setSelectedMethod({ method, bank });
    setPaymentStatus({
      type: 'info',
      message: `Selected ${bank ? `${method} (${bank})` : method}. Click 'Proceed to Pay' to execute transaction.`
    });
  };

  const handleProceedPayment = async () => {
    if (!selectedMethod) return;

    setProcessing(true);
    setPaymentStatus({ type: 'info', message: 'Connecting to server & creating order...' });

    try {
      // Step 1: Create Razorpay Order via backend API
      const orderRes = await fetch('http://127.0.0.1:8080/api/create-order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount: Number(amount),
          receipt_id: `rcpt_${Date.now()}`
        })
      });

      if (!orderRes.ok) {
        const errData = await orderRes.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to create order on server');
      }

      const orderData = await orderRes.json();
      console.log('Razorpay Order Response:', orderData);

      // Step 2: Handle missing keys vs real configured keys
      if (orderData.simulation_mode) {
        // Missing keys in .env: Activate Simulation Mode & display persistent warning badge
        setIsSimulationMode(true);
        setPaymentStatus({
          type: 'warning',
          message: '🧪 Simulation Mode — Test keys not configured in backend/.env. Recording mock transaction in database...'
        });

        await verifyPayment({
          razorpay_order_id: orderData.order_id,
          razorpay_payment_id: `pay_sim_${Date.now()}`,
          razorpay_signature: 'simulated_signature'
        }, true);
      } else if (window.Razorpay && orderData.key_id) {
        // Real keys configured in .env: Launch real Razorpay Checkout Widget
        setIsSimulationMode(false);
        setPaymentStatus({
          type: 'info',
          message: '💳 Opening Razorpay Checkout Widget...'
        });
        const options = {
          key: orderData.key_id,
          amount: orderData.amount,
          currency: orderData.currency,
          name: 'Merchant Payment Portal',
          description: `Fee Payment for ${studentName}`,
          order_id: orderData.order_id,
          handler: async function (response) {
            await verifyPayment({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature
            }, false);
          },
          prefill: {
            name: studentName,
            email: 'student@merchant.edu.in'
          },
          theme: {
            color: '#2563eb'
          }
        };
        const rzp = new window.Razorpay(options);
        rzp.on('payment.failed', function (response) {
          setPaymentStatus({
            type: 'error',
            message: `Razorpay Payment Failed: ${response.error.description || 'Transaction declined'}`
          });
          setProcessing(false);
        });
        rzp.open();
      } else {
        throw new Error('Razorpay SDK script not loaded or Key ID missing.');
      }
    } catch (err) {
      console.error('Payment initiation error:', err);
      setPaymentStatus({
        type: 'error',
        message: `Order Creation Failed: ${err.message}`
      });
      setProcessing(false);
    }
  };

  const verifyPayment = async (payload, isSim = false) => {
    try {
      const verifyRes = await fetch('http://127.0.0.1:8080/api/verify-payment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...payload,
          merchant_id: merchantId,
          method: selectedMethod.method,
          bank: selectedMethod.bank,
          amount: Number(amount),
          device: 'Android',
          hour: new Date().getHours()
        })
      });

      const verifyData = await verifyRes.json();
      if (verifyData.verified) {
        if (isSim) {
          setPaymentStatus({
            type: 'warning',
            message: '🧪 SIMULATION VERIFIED: Mock transaction recorded in database! (To test real Razorpay widget, add RAZORPAY_KEY_ID & RAZORPAY_KEY_SECRET in backend/.env)'
          });
        } else {
          setPaymentStatus({
            type: 'success',
            message: '🎉 REAL RAZORPAY PAYMENT VERIFIED: Signature authenticated & recorded in database!'
          });
        }
      } else {
        setPaymentStatus({
          type: 'error',
          message: `⚠️ Payment verification failed: ${verifyData.message}`
        });
      }
    } catch (err) {
      console.error('Verification error:', err);
      setPaymentStatus({
        type: 'error',
        message: `Verification Request Failed: ${err.message}`
      });
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="w-full flex items-center justify-center p-2 sm:p-4">
      <div className="bg-white shadow-xl rounded-2xl p-6 sm:p-8 max-w-lg w-full border border-slate-200">
        {!showAdvisor ? (
          <div>
            <div className="text-center mb-8">
              <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center text-white font-bold text-xl mx-auto mb-3 shadow-md">
                🎓
              </div>
              <h1 className="text-2xl font-bold text-slate-800">
                {merchantId === 'college_fee_portal'
                  ? 'ABC College - Fee Payment Portal'
                  : merchantId === 'ecommerce_store'
                  ? 'E-Commerce Checkout Portal'
                  : 'Electricity Bill Payment Portal'}
              </h1>
              <p className="text-sm text-slate-500 mt-1">Direct Merchant Checkout & Fee Portal</p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                  Customer / Student Name
                </label>
                <input
                  type="text"
                  required
                  value={studentName}
                  onChange={(e) => setStudentName(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-slate-800 transition"
                  placeholder="Enter full name"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                  Account / Roll Number
                </label>
                <input
                  type="text"
                  required
                  value={rollNumber}
                  onChange={(e) => setRollNumber(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-slate-800 transition"
                  placeholder="Enter reference ID"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                  Amount (₹)
                </label>
                <input
                  type="number"
                  required
                  min="1"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-slate-800 font-semibold transition"
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  className="w-full bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold py-3 px-4 rounded-xl shadow-md hover:shadow-lg transition-all duration-200 cursor-pointer flex items-center justify-center gap-2"
                >
                  <span>Pay Now</span>
                  <span className="text-lg">→</span>
                </button>
              </div>
            </form>
          </div>
        ) : (
          <div>
            <button
              onClick={() => {
                setShowAdvisor(false);
                setSelectedMethod(null);
                setPaymentStatus(null);
              }}
              className="mb-4 text-xs font-semibold text-slate-500 hover:text-slate-800 transition flex items-center gap-1 cursor-pointer"
            >
              ← Back to Form
            </button>

            <div className="bg-slate-50 rounded-xl p-3 mb-6 border border-slate-200 text-xs text-slate-600 flex justify-between items-center">
              <div>
                <span className="font-semibold text-slate-800">{studentName}</span> ({rollNumber})
              </div>
              <div className="font-bold text-blue-700 text-sm">
                ₹{Number(amount).toLocaleString('en-IN')}
              </div>
            </div>

            {/* Status Alert Banner */}
            {paymentStatus && (
              <div
                className={`mb-6 p-4 rounded-xl text-sm font-medium border ${
                  paymentStatus.type === 'success'
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                    : paymentStatus.type === 'error'
                    ? 'bg-rose-50 border-rose-200 text-rose-800'
                    : paymentStatus.type === 'warning'
                    ? 'bg-amber-50 border-amber-300 text-amber-900 font-semibold'
                    : 'bg-blue-50 border-blue-200 text-blue-800'
                }`}
              >
                {paymentStatus.message}
              </div>
            )}

            <SmartAdvisorScreen
              key={`${merchantId}-${refreshTrigger || 0}`}
              amount={Number(amount)}
              device="Android"
              merchant_id={merchantId}
              onMethodSelected={handleMethodSelected}
            />

            {/* Action Button */}
            {selectedMethod && (
              <div className="mt-6 pt-4 border-t border-slate-100">
                <button
                  onClick={handleProceedPayment}
                  disabled={processing}
                  className="w-full bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 disabled:opacity-50 text-white font-semibold py-3 px-4 rounded-xl shadow-md hover:shadow-lg transition-all duration-200 cursor-pointer flex items-center justify-center gap-2 text-base"
                >
                  {processing ? (
                    <span>Processing Payment...</span>
                  ) : (
                    <span>Proceed to Pay ₹{Number(amount).toLocaleString('en-IN')}</span>
                  )}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

