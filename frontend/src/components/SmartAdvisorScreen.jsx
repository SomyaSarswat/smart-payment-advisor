import React, { useState, useEffect, useCallback, useRef } from 'react';
import { fetchApi } from '../config/api';

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
function formatRelativeTime(timestampStr, now) {
  if (!timestampStr) return 'just now';
  const computedDate = new Date(timestampStr);
  const diffSec = Math.max(0, Math.floor((now - computedDate) / 1000));
  if (diffSec === 0) return 'just now';
  if (diffSec < 60) return `${diffSec} second${diffSec === 1 ? '' : 's'} ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin} minute${diffMin > 1 ? 's' : ''} ago`;
  return computedDate.toLocaleTimeString();
}

export default function SmartAdvisorScreen({ amount, device, merchant_id, onMethodSelected }) {
  const [recommendations, setRecommendations] = useState([]);
  const [selectedOption, setSelectedOption] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isOfflineMode, setIsOfflineMode] = useState(false);
  const [nowTicker, setNowTicker] = useState(Date.now());
  const [modelInfo, setModelInfo] = useState(null);

  useEffect(() => {
    const timer = setInterval(() => {
      setNowTicker(Date.now());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Fetch ML model metadata on component mount
  useEffect(() => {
    let isMounted = true;
    fetchApi('/api/model-info')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (isMounted && data) {
          setModelInfo(data);
        }
      })
      .catch((err) => {
        console.warn('Failed to load ML model info:', err);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Maintain reference to onMethodSelected to avoid infinite re-render loops when parent state updates
  const onMethodSelectedRef = useRef(onMethodSelected);
  useEffect(() => {
    onMethodSelectedRef.current = onMethodSelected;
  }, [onMethodSelected]);

  // Maintain reference to selectedOption to preserve user selection during background WebSocket updates
  const selectedOptionRef = useRef(selectedOption);
  useEffect(() => {
    selectedOptionRef.current = selectedOption;
  }, [selectedOption]);

  // Fallback payment options in case backend API is temporarily offline
  const fallbackOptions = [
    { method: 'Debit Card', bank: 'SBI', success_rate: 85.0, fee: 0, reason: 'Standard merchant default option', sample_info: 'Platform default', data_points: 0, confidence_level: 'estimated', is_recommended: true },
    { method: 'UPI', bank: null, success_rate: 80.0, fee: 0, reason: 'Standard merchant default option', sample_info: 'Platform default', data_points: 0, confidence_level: 'estimated', is_recommended: false },
    { method: 'Credit Card', bank: 'HDFC', success_rate: 75.0, fee: 15, reason: 'Standard merchant default option', sample_info: 'Platform default', data_points: 0, confidence_level: 'estimated', is_recommended: false },
    { method: 'Net Banking', bank: 'SBI', success_rate: 70.0, fee: 5, reason: 'Standard merchant default option', sample_info: 'Platform default', data_points: 0, confidence_level: 'estimated', is_recommended: false }
  ];

  const loadRecommendations = useCallback((isBackground = false) => {
    let isMounted = true;

    // Do not fire API call until amount is genuinely valid (> 0)
    const numAmount = Number(amount);
    if (!amount || isNaN(numAmount) || numAmount <= 0) {
      setLoading(false);
      setError('Please enter a valid positive payment amount (> ₹0)');
      return () => { isMounted = false; };
    }

    if (!isBackground) {
      setLoading(true);
    }
    setError(null);
    setIsOfflineMode(false);

    const validMerchantId = merchant_id || 'college_fee_portal';
    const validDevice = device || 'Desktop';

    const payload = {
      merchant_id: validMerchantId,
      amount: numAmount,
      device: validDevice
    };

    fetchApi('/api/get-recommendations', {
      method: 'POST',
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
          if (recs.length > 0) {
            setRecommendations(recs);
            const top = recs[0];
            
            // On initial non-background load, or if no option selected yet, set top option
            if (!isBackground || !selectedOptionRef.current) {
              setSelectedOption({ method: top.method, bank: top.bank });
              if (onMethodSelectedRef.current) {
                onMethodSelectedRef.current(top.method, top.bank);
              }
            }
            setLoading(false);
          } else {
            setIsOfflineMode(true);
            setRecommendations(fallbackOptions);
            if (!isBackground || !selectedOptionRef.current) {
              setSelectedOption({ method: fallbackOptions[0].method, bank: fallbackOptions[0].bank });
              if (onMethodSelectedRef.current) {
                onMethodSelectedRef.current(fallbackOptions[0].method, fallbackOptions[0].bank);
              }
            }
            setLoading(false);
          }
        }
      })
      .catch((err) => {
        console.error('Failed to fetch payment recommendations:', err);
        if (isMounted) {
          setIsOfflineMode(true);
          setError(`Unable to connect to AI recommendation service: ${err.message || 'Network error'}`);
          setRecommendations(fallbackOptions);
          if (!isBackground || !selectedOptionRef.current) {
            setSelectedOption({ method: fallbackOptions[0].method, bank: fallbackOptions[0].bank });
            if (onMethodSelectedRef.current) {
              onMethodSelectedRef.current(fallbackOptions[0].method, fallbackOptions[0].bank);
            }
          }
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [amount, device, merchant_id]);

  useEffect(() => {
    const cleanup = loadRecommendations(false);
    return cleanup;
  }, [loadRecommendations]);

  // Real-time WebSocket Subscription for Live Recommendation Auto-Refresh
  useEffect(() => {
    let ws = null;
    let reconnectTimer = null;
    let isCancelled = false;

    const connectWebSocket = () => {
      try {
        const wsHost = window.location.hostname || '127.0.0.1';
        const wsPort = '8080';
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${wsHost}:${wsPort}/ws/live-feed`;

        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          console.log('[SmartAdvisorScreen WS] Connected to live transaction feed at', wsUrl);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'NEW_TRANSACTION' || data.type === 'FAILURE_SIMULATED') {
              loadRecommendations(true);
            } else if (data.type === 'MODEL_RETRAINED') {
              if (data.data) {
                setModelInfo(data.data);
              }
              loadRecommendations(true);
            }
          } catch (e) {
            console.error('[SmartAdvisorScreen WS] Error parsing message:', e);
          }
        };

        ws.onerror = (err) => {
          console.warn('[SmartAdvisorScreen WS] Connection error:', err);
        };

        ws.onclose = () => {
          if (!isCancelled) {
            reconnectTimer = setTimeout(connectWebSocket, 3000);
          }
        };
      } catch (err) {
        console.error('[SmartAdvisorScreen WS] Connection setup failed:', err);
        if (!isCancelled) {
          reconnectTimer = setTimeout(connectWebSocket, 5000);
        }
      }
    };

    connectWebSocket();

    return () => {
      isCancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    };
  }, [loadRecommendations]);

  const handleCardClick = (item) => {
    setSelectedOption({ method: item.method, bank: item.bank });
    if (onMethodSelectedRef.current) {
      onMethodSelectedRef.current(item.method, item.bank);
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
        <div className="flex items-center justify-center gap-2 mt-1.5 flex-wrap">
          <p className="text-sm text-slate-500">Live success rates based on real-time data</p>
          {modelInfo && (
            <span
              className="inline-flex items-center gap-1 bg-slate-100 text-slate-600 text-[11px] font-medium px-2.5 py-0.5 rounded-full border border-slate-200 shadow-2xs"
              title={`Trained on ${modelInfo.training_sample_count?.toLocaleString()} transactions | Test Accuracy: ${modelInfo.test_accuracy}% | Test ROC-AUC: ${modelInfo.test_auc}`}
            >
              🤖 ML-enhanced (accuracy: {modelInfo.test_accuracy}%, trained on {modelInfo.training_sample_count?.toLocaleString()} txns)
            </span>
          )}
        </div>
      </div>

      {loading && (
        <div className="flex flex-col items-center justify-center py-12 space-y-4">
          <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-slate-600 font-medium">Analyzing live payment success rates...</p>
        </div>
      )}

      {/* Prominent Offline Mode Alert Banner */}
      {isOfflineMode && (
        <div className="bg-amber-50 border-2 border-amber-400 rounded-xl p-4 my-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-amber-900 shadow-sm">
          <div className="flex items-center gap-2">
            <span className="text-xl">📶</span>
            <div>
              <span className="font-bold block text-xs uppercase tracking-wider text-amber-800">
                OFFLINE MODE — AI Server Unreachable
              </span>
              <span className="text-xs text-amber-700">
                Displaying standard default payment options while AI re-ranking service is offline.
              </span>
            </div>
          </div>
          <button
            onClick={loadRecommendations}
            className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white font-semibold rounded-lg shadow-xs transition cursor-pointer text-xs whitespace-nowrap"
          >
            🔄 Retry Advisor
          </button>
        </div>
      )}

      {/* Validation Error Banner (e.g. invalid amount) */}
      {!isOfflineMode && error && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 my-4 flex items-center justify-between gap-3 text-rose-800 text-xs sm:text-sm">
          <div className="flex items-center gap-2">
            <span className="text-lg">⚠️</span>
            <span>{error}</span>
          </div>
          <button
            onClick={loadRecommendations}
            className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white font-semibold rounded-lg shadow-xs transition cursor-pointer text-xs whitespace-nowrap"
          >
            🔄 Retry
          </button>
        </div>
      )}

      {!loading && (
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
                  {isOfflineMode && (
                    <span className="inline-flex items-center gap-1 bg-slate-200 text-slate-700 text-[10px] font-semibold px-2 py-0.5 rounded-md">
                      Standard Default
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

                  {/* Success Rate Badge + Trend Arrow Indicator + Confidence Interval & Freshness */}
                  <div className="flex flex-col items-end gap-1">
                    <div className="flex items-center gap-1.5">
                      {item.trend === 'up' && (
                        <span className="inline-flex items-center gap-0.5 text-xs font-bold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded-md border border-emerald-300 shadow-2xs" title={`Success rate increased by +${item.rate_change}% since previous evaluation`}>
                          ↑ +{item.rate_change}%
                        </span>
                      )}
                      {item.trend === 'down' && (
                        <span className="inline-flex items-center gap-0.5 text-xs font-bold text-rose-700 bg-rose-100 px-2 py-0.5 rounded-md border border-rose-300 shadow-2xs" title={`Success rate dropped by ${item.rate_change}% since previous evaluation`}>
                          ↓ {item.rate_change}%
                        </span>
                      )}
                      {item.trend === 'stable' && (
                        <span className="inline-flex items-center gap-0.5 text-xs font-medium text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded-md border border-slate-200" title="Success rate is stable compared to previous evaluation">
                          → 0.0%
                        </span>
                      )}

                      <div className={`px-3 py-1 rounded-full text-xs font-bold border ${getBadgeStyle(item.success_rate)}`}>
                        {successPct}% {item.confidence_interval ? `± ${item.confidence_interval}%` : ''}
                      </div>
                    </div>

                    {item.computed_at && (
                      <span className="text-[10px] text-slate-400 font-medium tracking-tight">
                        computed {formatRelativeTime(item.computed_at, nowTicker)}
                      </span>
                    )}
                  </div>
                </div>


                {/* AI Explanation Reason & Data Sample Tooltip */}
                {item.reason && (
                  <div className="mt-2.5 border-t border-slate-100 pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-xs">
                    <p className="text-slate-600 font-medium italic">
                      💡 {item.reason}
                    </p>
                    {item.sample_info && (
                      <span className="text-[11px] text-slate-400 not-italic font-sans bg-slate-100 px-2 py-0.5 rounded-md inline-block self-start sm:self-auto" title={item.sample_info}>
                        📊 {item.sample_info}
                      </span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}



