import React, { useState, useEffect } from 'react';
import { fetchApi } from '../config/api';

/**
 * SimulatorControl component
 * Provides a control panel to inject real-time bank or payment method failure spikes,
 * demonstrating dynamic AI re-ranking and real-time outage detection.
 * 
 * Props:
 * - merchantId: current selected merchant ID string
 * - onFailureSimulated: callback triggered after a failure spike is injected
 */
export default function SimulatorControl({ merchantId = 'college_fee_portal', onFailureSimulated }) {
  const [selectedMerchant, setSelectedMerchant] = useState(merchantId);
  const [selectedOption, setSelectedOption] = useState('Net Banking|SBI');
  const [failureCount, setFailureCount] = useState(15);
  const [loading, setLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);

  useEffect(() => {
    setSelectedMerchant(merchantId);
  }, [merchantId]);

  const paymentOptions = [
    { label: 'Net Banking - SBI', method: 'Net Banking', bank: 'SBI' },
    { label: 'Net Banking - HDFC', method: 'Net Banking', bank: 'HDFC' },
    { label: 'Credit Card - HDFC', method: 'Credit Card', bank: 'HDFC' },
    { label: 'Credit Card - SBI', method: 'Credit Card', bank: 'SBI' },
    { label: 'Debit Card - SBI', method: 'Debit Card', bank: 'SBI' },
    { label: 'UPI', method: 'UPI', bank: null },
    { label: 'Wallet', method: 'Wallet', bank: null }
  ];

  const handleTriggerOutage = async (e) => {
    e.preventDefault();
    setLoading(true);
    setStatusMessage(null);

    const [method, bank] = selectedOption.split('|');
    const payload = {
      merchant_id: selectedMerchant,
      method: method,
      bank: bank === 'null' || !bank ? null : bank,
      failure_count: Number(failureCount)
    };

    try {
      const res = await fetchApi('/api/simulate-failure', {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        throw new Error(`Server status ${res.status}`);
      }

      const data = await res.json();
      setStatusMessage({
        type: 'success',
        text: `⚡ ${data.message}. Updated success rate for ${payload.method}${payload.bank ? ' (' + payload.bank + ')' : ''}: ${data.details.updated_success_rate}%`
      });

      if (onFailureSimulated) {
        onFailureSimulated(selectedMerchant);
      }
    } catch (err) {
      console.error('Failure simulation error:', err);
      setStatusMessage({
        type: 'error',
        text: `Failed to inject failure spike: ${err.message}`
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white shadow-xl rounded-2xl p-6 border border-slate-200 w-full max-w-xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-amber-500 rounded-xl flex items-center justify-center text-white font-bold text-xl shadow-md">
          ⚡
        </div>
        <div>
          <h2 className="text-xl font-bold text-slate-800">Live Outage & Failure Simulator</h2>
          <p className="text-xs text-slate-500">Inject artificial downtime spikes to test real-time AI re-ranking</p>
        </div>
      </div>

      {statusMessage && (
        <div
          className={`mb-6 p-4 rounded-xl text-sm font-medium border ${
            statusMessage.type === 'success'
              ? 'bg-amber-50 border-amber-300 text-amber-900'
              : 'bg-rose-50 border-rose-200 text-rose-800'
          }`}
        >
          {statusMessage.text}
        </div>
      )}

      <form onSubmit={handleTriggerOutage} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
            Target Merchant
          </label>
          <select
            value={selectedMerchant}
            onChange={(e) => setSelectedMerchant(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-amber-500 text-slate-800 font-medium"
          >
            <option value="college_fee_portal">ABC College Fee Portal</option>
            <option value="ecommerce_store">E-Commerce Store</option>
            <option value="electricity_bill">Electricity Bill Portal</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
            Target Payment Method
          </label>
          <select
            value={selectedOption}
            onChange={(e) => setSelectedOption(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-amber-500 text-slate-800 font-medium"
          >
            {paymentOptions.map((opt, i) => (
              <option key={i} value={`${opt.method}|${opt.bank}`}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <div className="flex justify-between items-center mb-1">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-600">
              Failure Spike Intensity
            </label>
            <span className="text-xs font-bold text-amber-700">{failureCount} Failed Transactions</span>
          </div>
          <input
            type="range"
            min="5"
            max="40"
            step="5"
            value={failureCount}
            onChange={(e) => setFailureCount(Number(e.target.value))}
            className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-amber-500"
          />
        </div>

        <div className="pt-2">
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-amber-600 hover:bg-amber-700 active:bg-amber-800 disabled:opacity-50 text-white font-semibold py-3 px-4 rounded-xl shadow-md hover:shadow-lg transition-all duration-200 cursor-pointer flex items-center justify-center gap-2"
          >
            {loading ? (
              <span>Simulating Outage...</span>
            ) : (
              <span>⚡ Trigger Bank Outage & Failure Spike</span>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
