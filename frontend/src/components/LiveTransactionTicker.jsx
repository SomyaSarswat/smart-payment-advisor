import React, { useState, useEffect, useRef } from 'react';
import { fetchApi } from '../config/api';

/**
 * LiveTransactionTicker Component
 * 
 * Provides a real-time animated transaction ticker streaming live transactions across the platform.
 * 
 * CRITICAL LABELING REQUIREMENT:
 * Clearly communicates to users that this ticker displays "Platform-wide Simulated Traffic" 
 * across the entire system, preventing confusion with the user's individual payment.
 */
export default function LiveTransactionTicker({ activeMerchant }) {
  const [transactions, setTransactions] = useState([]);
  const [userPaymentIds, setUserPaymentIds] = useState([]);
  const [isPaused, setIsPaused] = useState(false);
  const tickerContainerRef = useRef(null);

  // Load user payment IDs from localStorage & custom event listener
  useEffect(() => {
    const loadUserIds = () => {
      try {
        const saved = JSON.parse(localStorage.getItem('user_payment_ids') || '[]');
        setUserPaymentIds(saved);
      } catch (e) {
        console.error('Failed to parse user_payment_ids:', e);
      }
    };
    loadUserIds();

    const handleUserPayment = (e) => {
      if (e.detail) {
        setUserPaymentIds((prev) => [...prev, e.detail]);
      }
    };

    window.addEventListener('user_payment_completed', handleUserPayment);
    return () => window.removeEventListener('user_payment_completed', handleUserPayment);
  }, []);

  // Fetch initial recent transactions from backend API
  useEffect(() => {
    const merchantParam = activeMerchant || 'college_fee_portal';
    fetchApi(`/api/analytics/${merchantParam}`)
      .then((res) => res.json())
      .then((data) => {
        if (data && data.recent_transactions) {
          setTransactions(data.recent_transactions.slice(0, 15));
        }
      })
      .catch((err) => console.warn('[LiveTicker] Initial fetch warning:', err));
  }, [activeMerchant]);

  // WebSocket real-time subscription for live transaction stream
  useEffect(() => {
    let ws = null;
    let reconnectTimer = null;
    let isCancelled = false;

    const connectWS = () => {
      try {
        const wsHost = window.location.hostname || '127.0.0.1';
        const wsPort = '8080';
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${wsHost}:${wsPort}/ws/live-feed`;

        ws = new WebSocket(wsUrl);

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'NEW_TRANSACTION' && msg.data) {
              setTransactions((prev) => {
                const newTx = msg.data;
                // Avoid duplicates
                if (prev.some((tx) => tx.id === newTx.id)) return prev;
                return [newTx, ...prev.slice(0, 19)];
              });
            } else if (msg.type === 'FAILURE_SIMULATED' && msg.data) {
              // Trigger refresh on simulated spike
              fetchApi(`/api/analytics/${activeMerchant || 'college_fee_portal'}`)
                .then((res) => res.json())
                .then((d) => {
                  if (d && d.recent_transactions) {
                    setTransactions(d.recent_transactions.slice(0, 15));
                  }
                })
                .catch(() => {});
            }
          } catch (e) {
            console.error('[LiveTicker WS] Error parsing event:', e);
          }
        };

        ws.onclose = () => {
          if (!isCancelled) {
            reconnectTimer = setTimeout(connectWS, 4000);
          }
        };
      } catch (err) {
        console.error('[LiveTicker WS] Setup error:', err);
        if (!isCancelled) {
          reconnectTimer = setTimeout(connectWS, 5000);
        }
      }
    };

    connectWS();

    return () => {
      isCancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    };
  }, [activeMerchant]);

  return (
    <div className="w-full bg-slate-900 border-b border-slate-800 text-white shadow-inner py-2 px-3 sm:px-6">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-2.5">
        
        {/* Prominent Stream Labeling Header */}
        <div className="flex items-center gap-2.5 shrink-0">
          <div className="flex items-center gap-1.5 bg-blue-950/80 border border-blue-700/60 px-2.5 py-1 rounded-lg text-xs font-semibold text-blue-300">
            <span className="w-2 h-2 rounded-full bg-blue-400 animate-ping"></span>
            <span>🌐 Live Platform Traffic</span>
          </div>
          <span className="text-[11px] text-slate-400 font-medium hidden lg:inline-block">
            (Simulated Platform-Wide Feed — <span className="text-slate-300 italic">Not limited to your payment</span>)
          </span>
        </div>

        {/* Live Transaction Horizontal Ticker Scroll Area */}
        <div
          ref={tickerContainerRef}
          onMouseEnter={() => setIsPaused(true)}
          onMouseLeave={() => setIsPaused(false)}
          className="flex-1 overflow-x-auto no-scrollbar flex items-center gap-2 py-0.5"
        >
          {transactions.length === 0 ? (
            <span className="text-xs text-slate-500 italic">Waiting for live platform traffic stream...</span>
          ) : (
            transactions.map((tx) => {
              const isUserTx = userPaymentIds.includes(tx.id);
              const isSuccess = tx.status === 'success';
              const timeStr = tx.timestamp
                ? new Date(tx.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                : 'just now';

              return (
                <div
                  key={tx.id || `${tx.method}-${Date.now()}-${Math.random()}`}
                  className={`inline-flex items-center gap-2 px-3 py-1 rounded-xl text-xs whitespace-nowrap transition-all duration-300 border ${
                    isUserTx
                      ? 'bg-amber-500/20 border-amber-400 text-amber-200 ring-2 ring-amber-400/50 shadow-md font-bold'
                      : isSuccess
                      ? 'bg-slate-800/90 border-slate-700/80 text-slate-200 hover:border-slate-600'
                      : 'bg-rose-950/40 border-rose-800/80 text-rose-200 hover:border-rose-700'
                  }`}
                >
                  {isUserTx && (
                    <span className="bg-amber-500 text-slate-950 text-[10px] font-black px-1.5 py-0.5 rounded-md uppercase tracking-wider">
                      ⭐ YOUR PAYMENT
                    </span>
                  )}
                  <span className="text-slate-400 text-[10px] font-mono">{timeStr}</span>
                  <span className="font-semibold text-slate-100">
                    {tx.method} {tx.bank ? `(${tx.bank})` : ''}
                  </span>
                  <span className="font-bold text-slate-300">₹{Number(tx.amount || 0).toLocaleString('en-IN')}</span>
                  <span
                    className={`px-1.5 py-0.2 rounded text-[10px] font-extrabold ${
                      isSuccess
                        ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                        : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                    }`}
                  >
                    {isSuccess ? '✓ SUCCESS' : '✕ FAILED'}
                  </span>
                </div>
              );
            })
          )}
        </div>

        {/* Small Ticker Info Badge */}
        <div className="hidden sm:flex items-center gap-1.5 text-[10px] text-slate-400 shrink-0 bg-slate-800/50 px-2.5 py-1 rounded-lg border border-slate-700/40">
          <span>ℹ️ Platform-wide stream</span>
        </div>

      </div>
    </div>
  );
}
