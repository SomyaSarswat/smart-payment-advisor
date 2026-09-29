import React, { useState } from 'react';
import FeePaymentPage from './pages/FeePaymentPage';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import SimulatorControl from './components/SimulatorControl';
import LiveTransactionTicker from './components/LiveTransactionTicker';

/**
 * Global Error Boundary Component to catch unexpected rendering exceptions
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Uncaught React Rendering Exception:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 max-w-xl mx-auto my-12 bg-rose-50 border border-rose-200 rounded-2xl text-center shadow-lg">
          <div className="w-12 h-12 bg-rose-600 rounded-xl flex items-center justify-center text-white text-2xl mx-auto mb-4">
            ⚠️
          </div>
          <h2 className="text-xl font-bold text-rose-900 mb-2">Application Encountered an Error</h2>
          <p className="text-sm text-rose-700 mb-6">
            An unexpected error occurred: {this.state.error?.message || 'Unknown UI error'}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-5 py-2.5 bg-rose-600 hover:bg-rose-700 text-white font-semibold rounded-xl shadow-xs transition cursor-pointer"
          >
            🔄 Reload Application
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

/**
 * Main App component with Multi-Merchant Switcher, Navigation Tabs,
 * and integrated AI Smart Payment Advisor platform views.
 */
function App() {
  const [activeMerchant, setActiveMerchant] = useState('college_fee_portal');
  const [activeTab, setActiveTab] = useState('portal'); // 'portal' | 'dashboard' | 'simulator'
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleFailureSimulated = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  const getMerchantDisplayName = (id) => {
    switch (id) {
      case 'college_fee_portal': return 'ABC College Fee Portal';
      case 'ecommerce_store': return 'E-Commerce Store';
      case 'electricity_bill': return 'Electricity Bill Portal';
      default: return id;
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col text-slate-800">
      {/* Global Navigation Header */}
      <header className="bg-slate-900 text-white sticky top-0 z-50 shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3.5 flex flex-col md:flex-row md:items-center justify-between gap-4">
          
          {/* Logo / Brand */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center font-black text-white text-lg shadow-sm">
              AI
            </div>
            <div>
              <h1 className="font-bold text-lg leading-tight tracking-wide text-white">Smart Payment Advisor</h1>
              <p className="text-[11px] text-blue-300 font-medium">Payment Routing & Reliability Intelligence</p>
            </div>
          </div>

          {/* Controls: Merchant Switcher + View Navigation Tabs */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            
            {/* Multi-Merchant Dropdown Switcher */}
            <div className="flex items-center gap-2 bg-slate-800 px-3 py-1.5 rounded-xl border border-slate-700">
              <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Merchant:</span>
              <select
                value={activeMerchant}
                onChange={(e) => setActiveMerchant(e.target.value)}
                className="bg-transparent text-xs font-bold text-blue-300 focus:outline-none cursor-pointer pr-2"
              >
                <option value="college_fee_portal" className="bg-slate-900 text-white">ABC College Fee Portal</option>
                <option value="ecommerce_store" className="bg-slate-900 text-white">E-Commerce Store</option>
                <option value="electricity_bill" className="bg-slate-900 text-white">Electricity Bill Portal</option>
              </select>
            </div>

            {/* Navigation Tabs */}
            <div className="flex items-center bg-slate-800/80 p-1 rounded-xl border border-slate-700/80">
              <button
                onClick={() => setActiveTab('portal')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer flex items-center gap-1.5 ${
                  activeTab === 'portal'
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-slate-300 hover:text-white'
                }`}
              >
                <span>💳</span>
                <span>Checkout Portal</span>
              </button>

              <button
                onClick={() => setActiveTab('dashboard')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer flex items-center gap-1.5 ${
                  activeTab === 'dashboard'
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-slate-300 hover:text-white'
                }`}
              >
                <span>📊</span>
                <span>Analytics</span>
              </button>

              <button
                onClick={() => setActiveTab('simulator')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer flex items-center gap-1.5 ${
                  activeTab === 'simulator'
                    ? 'bg-amber-600 text-white shadow-xs'
                    : 'text-slate-300 hover:text-white'
                }`}
              >
                <span>⚡</span>
                <span>Simulator</span>
              </button>
            </div>

          </div>

        </div>
      </header>

      {/* Live Transaction Ticker Bar with explicit platform-wide labeling */}
      <LiveTransactionTicker activeMerchant={activeMerchant} />

      {/* Main Content Area Wrapped in Error Boundary */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 md:p-8">

        <ErrorBoundary>
          {activeTab === 'portal' && (
            <FeePaymentPage merchantId={activeMerchant} refreshTrigger={refreshTrigger} />
          )}

          {activeTab === 'dashboard' && (
            <AnalyticsDashboard key={`${activeMerchant}-${refreshTrigger}`} merchantId={activeMerchant} />
          )}

          {activeTab === 'simulator' && (
            <div className="space-y-8">
              <SimulatorControl merchantId={activeMerchant} onFailureSimulated={handleFailureSimulated} />
              <div className="border-t border-slate-200 pt-8">
                <div className="bg-slate-900 text-white rounded-2xl p-5 shadow-lg mb-6 border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-amber-500/20 border border-amber-500/30 rounded-xl flex items-center justify-center text-amber-400 text-xl font-bold">
                      👁️
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-white flex items-center gap-2">
                        <span>Live Impact Preview</span>
                        <span className="text-xs bg-blue-500/20 text-blue-300 font-semibold px-2.5 py-0.5 rounded-full border border-blue-400/30">
                          {getMerchantDisplayName(activeMerchant)}
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Real-time AI recommendation re-ranking live preview
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-950/60 border border-emerald-800/80 px-3 py-1.5 rounded-lg font-medium">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                    <span>Live Re-Ranking Active</span>
                  </div>
                </div>
                <FeePaymentPage merchantId={activeMerchant} refreshTrigger={refreshTrigger} />
              </div>
            </div>
          )}
        </ErrorBoundary>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-500">
        Smart Payment Advisor — Powered by FastAPI & React
      </footer>
    </div>
  );
}

export default App;
