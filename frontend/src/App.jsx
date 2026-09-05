import React, { useState } from 'react';
import FeePaymentPage from './pages/FeePaymentPage';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import SimulatorControl from './components/SimulatorControl';

/**
 * Main App component with Multi-Merchant Switcher, Navigation Tabs,
 * and integrated AI Smart Payment Advisor platform views.
 */
function App() {
  const [activeMerchant, setActiveMerchant] = useState('college_fee_portal');
  const [activeTab, setActiveTab] = useState('portal'); // 'portal' | 'dashboard' | 'simulator'
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleFailureSimulated = () => {
    // Increment trigger counter to force re-fetch in FeePaymentPage/SmartAdvisorScreen and Analytics
    setRefreshTrigger((prev) => prev + 1);
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

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 md:p-8">
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
              <h3 className="text-center font-bold text-slate-700 text-sm uppercase tracking-wider mb-4">
                Live Re-Ranking Test View for {activeMerchant}
              </h3>
              <FeePaymentPage merchantId={activeMerchant} refreshTrigger={refreshTrigger} />
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-500">
        Smart Payment Advisor — Powered by FastAPI & React
      </footer>
    </div>
  );
}

export default App;
