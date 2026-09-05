import React, { useState, useEffect } from 'react';

/**
 * SmartAdvisorScreen component
 * 
 * This component is designed to be platform-agnostic. It only needs 
 * merchant_id, amount, and device as inputs — all payment method 
 * availability and success-rate logic is resolved by the backend API. 
 * This means the same component could theoretically be embedded in 
 * any merchant website by simply passing their merchant_id.
 * 
 * Props:
 * - amount: numerical transaction amount
 * - device: user's device platform (e.g. "Android")
 * - merchant_id: merchant identifier string (e.g. "college_fee_portal")
 * - onMethodSelected: callback function (method, bank) => void called when user selects an option
 */
export default function SmartAdvisorScreen({ amount, device, merchant_id, onMethodSelected }) {
  const [recommendations, setRecommendations] = useState([]);
  const [selectedOption, setSelectedOption] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    const payload = {
      merchant_id: merchant_id,
      amount: Number(amount),
      device: device
    };

    fetch('http://127.0.0.1:8080/api/get-recommendations', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Server returned status ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        if (isMounted) {
          const recs = data.recommendations || [];
          setRecommendations(recs);
          // Auto-select the top recommended option if available
          if (recs.length > 0) {
            const top = recs[0];
            setSelectedOption({ method: top.method, bank: top.bank });
          }
          setLoading(false);
        }
      })
      .catch((err) => {
        console.error('Failed to fetch payment recommendations:', err);
        if (isMounted) {
          setError('Unable to load recommendations, please try again');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [amount, device, merchant_id]);

  const handleCardClick = (item) => {
    setSelectedOption({ method: item.method, bank: item.bank });
    if (onMethodSelected) {
      onMethodSelected(item.method, item.bank);
    }
  };

  // Helper to determine success rate badge styling based on threshold
  const getBadgeStyle = (rate) => {
    if (rate >= 80) {
      return 'bg-emerald-100 text-emerald-800 border-emerald-200';
    } else if (rate >= 50) {
      return 'bg-amber-100 text-amber-800 border-amber-200';
    } else {
      return 'bg-rose-100 text-rose-800 border-rose-200';
    }
  };

  return (
    <div className="w-full max-w-xl mx-auto">
      <div className="mb-6 text-center">
        <h2 className="text-2xl font-bold text-slate-800">Choose your payment method</h2>
        <p className="text-sm text-slate-500 mt-1">Live success rates based on real-time data</p>
      </div>

      {loading && (
        <div className="flex flex-col items-center justify-center py-12 space-y-4">
          <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-slate-600 font-medium">Analyzing live payment success rates...</p>
        </div>
      )}

      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-center my-4">
          <p className="text-rose-700 font-medium">{error}</p>
        </div>
      )}

      {!loading && !error && (
        <div className="space-y-4">
          {recommendations.map((item, index) => {
            const displayName = item.bank ? `${item.method} - ${item.bank}` : item.method;
            const isRec = item.is_recommended;
            const isSelected = selectedOption?.method === item.method && selectedOption?.bank === item.bank;
            const successPct = typeof item.success_rate === 'number' 
              ? item.success_rate.toFixed(1) 
              : item.success_rate;

            return (
              <div
                key={index}
                onClick={() => handleCardClick(item)}
                className={`relative rounded-xl p-4 transition-all duration-200 cursor-pointer shadow-xs hover:shadow-md ${
                  isSelected
                    ? 'ring-2 ring-blue-600 border-blue-600 bg-blue-50/50 shadow-md'
                    : isRec
                    ? 'border-2 border-emerald-500 bg-emerald-50/30 hover:border-emerald-600'
                    : 'border border-slate-200 bg-white hover:border-blue-300'
                }`}
              >
                {/* Badges Header */}
                <div className="flex items-center gap-2 mb-2">
                  {isRec && (
                    <span className="inline-flex items-center gap-1 bg-emerald-600 text-white text-xs font-semibold px-2.5 py-0.5 rounded-full shadow-xs">
                      ✅ Recommended
                    </span>
                  )}
                  {isSelected && (
                    <span className="inline-flex items-center gap-1 bg-blue-600 text-white text-xs font-semibold px-2.5 py-0.5 rounded-full shadow-xs">
                      ✓ Selected
                    </span>
                  )}
                </div>

                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-slate-800 text-base flex items-center gap-2">
                      <span>{displayName}</span>
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {item.fee > 0 ? `₹${item.fee} fee` : 'No extra fee'}
                    </p>
                  </div>

                  {/* Success Rate Badge */}
                  <div className={`px-3 py-1 rounded-full text-xs font-bold border ${getBadgeStyle(item.success_rate)}`}>
                    {successPct}% success
                  </div>
                </div>

                {/* AI Explanation Reason */}
                {item.reason && (
                  <p className="text-xs text-slate-500 italic mt-2.5 border-t border-slate-100 pt-2">
                    💡 {item.reason}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

