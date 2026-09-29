import React, { useState, useEffect } from 'react';
import { fetchApi } from '../config/api';

/**
 * AnalyticsDashboard component
 * Visualizes real-time transaction metrics, global success rates, top failing payment options,
 * fee savings, and recent transaction log stream from SQLite database.
 * 
 * Props:
 * - merchantId: current selected merchant ID string or "all"
 */
export default function AnalyticsDashboard({ merchantId = 'college_fee_portal' }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [lastFetchTime, setLastFetchTime] = useState(null);
  const [nowTicker, setNowTicker] = useState(Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNowTicker(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const formatLastUpdated = (fetchTime) => {
    if (!fetchTime) return 'just now';
    const diffSec = Math.max(0, Math.floor((nowTicker - fetchTime) / 1000));
    if (diffSec === 0) return 'just now';
    if (diffSec < 60) return `${diffSec}s ago`;
    return `${Math.floor(diffSec / 60)}m ago`;
  };

  const fetchAnalytics = (isInitial = false) => {
    if (isInitial) setLoading(true);
    else setRefreshing(true);
    setError(null);

    fetchApi(`/api/analytics/${merchantId}`)
      .then((res) => {
        if (!res.ok) throw new Error(`Server returned status ${res.status}`);
        return res.json();
      })
      .then((analyticsData) => {
        setData(analyticsData);
        setLastFetchTime(Date.now());
        setLoading(false);
        setRefreshing(false);
      })
      .catch((err) => {
        console.error('Analytics fetch error:', err);
        setError(err.message || '⚠️ Cannot reach server — please check backend is running');
        setLoading(false);
        setRefreshing(false);
      });
  };

  useEffect(() => {
    fetchAnalytics(true);
    const interval = setInterval(() => {
      fetchAnalytics(false);
    }, 5000);

    return () => clearInterval(interval);
  }, [merchantId]);

  return (
    <div className="w-full max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Merchant Payment Analytics</h2>
          <p className="text-xs text-slate-500 mt-1">
            Real-time transaction stream & AI performance monitoring for{' '}
            <span className="font-semibold text-blue-600">{merchantId}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          {lastFetchTime && (
            <span className="text-xs text-slate-400 font-medium hidden sm:inline-block">
              Updated {formatLastUpdated(lastFetchTime)}
            </span>
          )}
          <button
            onClick={() => fetchAnalytics(false)}
            disabled={refreshing}
            className="bg-slate-100 hover:bg-slate-200 active:bg-slate-300 text-slate-700 text-xs font-semibold px-4 py-2.5 rounded-xl border border-slate-300 transition cursor-pointer flex items-center gap-2 self-start sm:self-auto"
          >
            <span className={refreshing ? 'animate-spin' : ''}>🔄</span>
            <span>{refreshing ? 'Refreshing...' : 'Refresh Data'}</span>
          </button>
        </div>
      </div>

      {loading && (
        <div className="flex flex-col items-center justify-center py-16 bg-white rounded-2xl border border-slate-200 space-y-3">
          <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-slate-600 font-medium">Loading live payment metrics...</p>
        </div>
      )}

      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-center">
          <p className="text-rose-700 font-medium text-sm">{error}</p>
        </div>
      )}

      {!loading && !error && data && (
        <>
          {/* Stat Cards Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Card 1: Total Transactions */}
            <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider">Total Volume</span>
                <span className="text-lg">📊</span>
              </div>
              <div className="text-3xl font-extrabold text-slate-900">{data.total_transactions}</div>
              <p className="text-xs text-slate-500 mt-1">Total recorded transactions</p>
            </div>

            {/* Card 2: Global Success Rate */}
            <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider">Success Rate</span>
                <span className="text-lg">📈</span>
              </div>
              <div className="text-3xl font-extrabold text-emerald-600">{data.global_success_rate}%</div>
              <p className="text-xs text-slate-500 mt-1">Average system completion</p>
            </div>

            {/* Card 3: Top Failing Method */}
            <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider">Top Failing Method</span>
                <span className="text-lg">⚠️</span>
              </div>
              <div className="text-lg font-bold text-rose-600 truncate">{data.top_failing_method}</div>
              <p className="text-xs text-slate-500 mt-1">Highest downtime concentration</p>
            </div>

            {/* Card 4: Fee Savings */}
            <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-200">
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider">Total Fee Savings</span>
                <span className="text-lg">💰</span>
              </div>
              <div className="text-3xl font-extrabold text-blue-600">
                ₹{Number(data.total_merchant_fee_savings).toLocaleString('en-IN')}
              </div>
              <p className="text-xs text-slate-500 mt-1">Saved via AI payment routing</p>
            </div>
          </div>

          {/* Recent Transaction Log Stream Table */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h3 className="font-bold text-slate-800 text-lg flex items-center gap-2">
                  <span>Live Transaction Log Stream</span>
                  <span className="text-[11px] font-semibold text-blue-600 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-md">
                    Platform-wide Stream
                  </span>
                </h3>
                <p className="text-xs text-slate-400">
                  Showing last {data.recent_transactions.length} records • Updated {formatLastUpdated(lastFetchTime)}
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full font-semibold border border-emerald-200 self-start sm:self-auto">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span>Live Feed Active</span>
              </div>
            </div>

            {/* Platform-wide Simulated Traffic Clarification Banner */}
            <div className="bg-blue-50/80 border-b border-blue-100 px-6 py-2.5 text-xs text-blue-900 flex items-center gap-2">
              <span className="text-sm">🌐</span>
              <div>
                <span className="font-bold">Platform-wide simulated traffic: </span>
                <span className="text-blue-800">
                  This log displays simulated system-wide transactions across all users & gateways (not limited to your individual payment).
                </span>
              </div>
            </div>


            {data.recent_transactions.length === 0 ? (
              /* Friendly Empty State Illustration for Zero Transactions */
              <div className="p-12 text-center flex flex-col items-center justify-center space-y-3">
                <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center text-slate-400 text-3xl">
                  💳
                </div>
                <h4 className="text-base font-bold text-slate-700">No Transactions Recorded Yet</h4>
                <p className="text-xs text-slate-500 max-w-sm">
                  There are no transactions in the database for merchant <span className="font-semibold">{merchantId}</span>. 
                  Execute a payment from Checkout Portal or launch the background simulator to generate live feed records.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-700">
                  <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-500 border-b border-slate-200">
                    <tr>
                      <th className="px-6 py-3">ID</th>
                      <th className="px-6 py-3">Timestamp</th>
                      <th className="px-6 py-3">Payment Method</th>
                      <th className="px-6 py-3">Amount</th>
                      <th className="px-6 py-3">Status</th>
                      <th className="px-6 py-3">Error Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.recent_transactions.map((tx) => {
                      const isSuccess = tx.status === 'success';
                      const timeFormatted = new Date(tx.timestamp).toLocaleTimeString('en-IN', {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit'
                      });

                      return (
                        <tr key={tx.id} className="hover:bg-slate-50/80 transition">
                          <td className="px-6 py-3.5 font-mono text-xs text-slate-500">#{tx.id}</td>
                          <td className="px-6 py-3.5 text-xs text-slate-600 whitespace-nowrap">{timeFormatted}</td>
                          <td className="px-6 py-3.5 font-medium text-slate-900">
                            {tx.method} {tx.bank ? `(${tx.bank})` : ''}
                          </td>
                          <td className="px-6 py-3.5 font-semibold text-slate-800">
                            ₹{Number(tx.amount).toLocaleString('en-IN')}
                          </td>
                          <td className="px-6 py-3.5 whitespace-nowrap">
                            <span
                              className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold ${
                                isSuccess
                                  ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                                  : 'bg-rose-100 text-rose-800 border border-rose-200'
                              }`}
                            >
                              {isSuccess ? '✓ SUCCESS' : '✕ FAILED'}
                            </span>
                          </td>
                          <td className="px-6 py-3.5 text-xs text-slate-500 font-mono">
                            {tx.error_code || '—'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
