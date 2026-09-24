import React, { useState, useEffect } from 'react';
import { Scale, Sparkles, ArrowRight, CheckCircle, AlertTriangle, PieChart, Save, Edit3 } from 'lucide-react';
import { api } from '../../api/client';

interface Page7Props {
  transition: any;
  onNext: () => void;
  onRefresh: () => void;
}

export const Page7_CapacityPlanner: React.FC<Page7Props> = ({ transition, onNext, onRefresh }) => {
  const [capacity, setCapacity] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [decomposing, setDecomposing] = useState(false);
  const [decomposeMessage, setDecomposeMessage] = useState<string | null>(null);
  const [domainHours, setDomainHours] = useState<Record<string, number>>({});
  const [savingDomain, setSavingDomain] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  const loadCapacity = async () => {
    if (!transition) return;
    setLoading(true);
    try {
      const data = await api.getCapacity(transition.id);
      setCapacity(data);
      if (data.category_breakdown) {
        setDomainHours(data.category_breakdown);
      }
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCapacity();
  }, [transition]);

  const handleDecompose = async () => {
    if (!transition) return;
    setDecomposing(true);
    setDecomposeMessage(null);
    try {
      const res = await api.decomposeHierarchy(transition.id);
      setDecomposeMessage(res.message);
      await loadCapacity();
      onRefresh();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setDecomposing(false);
    }
  };

  // Real-time update on domain hours change
  const handleHoursChange = (cat: string, val: string) => {
    const num = parseFloat(val) || 0;
    const nextHours = { ...domainHours, [cat]: num };
    setDomainHours(nextHours);

    // Compute updated total generated hours in real-time
    if (capacity) {
      const newTotal = Object.values(nextHours).reduce((a, b) => a + b, 0);
      const target = capacity.target_capacity_hours || 1;
      const ratio = Math.round((newTotal / target) * 1000) / 10;
      const gap = Math.round((target - newTotal) * 10) / 10;
      let status = 'BALANCED';
      if (newTotal < target) status = 'UNDER_ALLOCATED';
      else if (newTotal > target) status = 'OVER_ALLOCATED';

      setCapacity({
        ...capacity,
        generated_hours: Math.round(newTotal * 10) / 10,
        gap_hours: gap,
        balance_ratio_percent: ratio,
        status,
        category_breakdown: nextHours,
      });
    }
  };

  // Persist domain hours to database
  const handlePersistDomainHours = async (cat: string) => {
    if (!transition) return;
    setSavingDomain(cat);
    try {
      const res = await api.updateDomainHours(transition.id, { [cat]: domainHours[cat] });
      setSaveSuccess(`Domain '${cat.replace(/_/g, ' ')}' updated to ${domainHours[cat]}h & persisted to database.`);
      setTimeout(() => setSaveSuccess(null), 3000);
      if (res.capacity) {
        setCapacity(res.capacity);
        setDomainHours(res.capacity.category_breakdown || domainHours);
      }
      onRefresh();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSavingDomain(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-amber-100 rounded-lg text-amber-700">
              <Scale className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Stage 7: Capacity Balancing Engine</h2>
              <p className="text-sm text-slate-500">
                Mandatory full utilization of available KT days through real-time domain effort editing and topic decomposition.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {capacity && capacity.status === 'UNDER_ALLOCATED' && (
              <button
                onClick={handleDecompose}
                disabled={decomposing}
                className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow"
              >
                <Sparkles className="h-3.5 w-3.5" />
                <span>{decomposing ? 'Decomposing Topics...' : 'Auto-Decompose to 100%'}</span>
              </button>
            )}

            <button
              onClick={onNext}
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow"
            >
              <span>Proceed to Sessions</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {decomposeMessage && (
          <div className="p-3 mb-4 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-lg text-xs font-semibold flex items-center space-x-2">
            <CheckCircle className="h-4 w-4 text-emerald-600" />
            <span>{decomposeMessage}</span>
          </div>
        )}

        {saveSuccess && (
          <div className="p-2.5 mb-4 bg-sky-50 text-sky-800 border border-sky-200 rounded-lg text-xs font-medium flex items-center space-x-2">
            <CheckCircle className="h-4 w-4 text-sky-600" />
            <span>{saveSuccess}</span>
          </div>
        )}

        {capacity && (
          <div className="space-y-6 mt-4">
            {/* Main Progress Card */}
            <div className="p-6 bg-slate-50 rounded-xl border border-slate-200">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Capacity Balance Utilization (Real-time Live Sync)
                </span>
                <span className={`text-sm font-bold ${
                  capacity.balance_ratio_percent >= 100 ? 'text-emerald-600' : 'text-amber-600'
                }`}>
                  {capacity.balance_ratio_percent}% Allocated ({capacity.generated_hours}h / {capacity.target_capacity_hours}h)
                </span>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
                <div
                  className={`h-3 rounded-full transition-all duration-300 ${
                    capacity.balance_ratio_percent >= 100 ? 'bg-emerald-500' : 'bg-amber-500'
                  }`}
                  style={{ width: `${Math.min(capacity.balance_ratio_percent, 100)}%` }}
                ></div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 text-center">
                <div className="bg-white p-3 rounded-lg border border-slate-200">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Available KT Days</span>
                  <span className="text-xl font-bold text-slate-900">{capacity.available_kt_days} Days</span>
                </div>
                <div className="bg-white p-3 rounded-lg border border-slate-200">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Target Capacity</span>
                  <span className="text-xl font-bold text-slate-900">{capacity.target_capacity_hours} Hours</span>
                </div>
                <div className="bg-white p-3 rounded-lg border border-slate-200">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Generated Hours</span>
                  <span className="text-xl font-bold text-slate-900">{capacity.generated_hours} Hours</span>
                </div>
                <div className="bg-white p-3 rounded-lg border border-slate-200">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Capacity Status</span>
                  <span className={`text-xs font-bold uppercase block mt-1 ${
                    capacity.status === 'BALANCED' ? 'text-emerald-600' : 'text-amber-600'
                  }`}>
                    {capacity.status}
                  </span>
                </div>
              </div>

              {/* Recommendation alert */}
              <div className={`mt-4 p-3 rounded-lg text-xs flex items-center space-x-2 border ${
                capacity.status === 'BALANCED'
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                  : 'bg-amber-50 text-amber-800 border-amber-200'
              }`}>
                {capacity.status === 'BALANCED' ? (
                  <CheckCircle className="h-4 w-4 shrink-0 text-emerald-600" />
                ) : (
                  <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />
                )}
                <span>{capacity.recommendation}</span>
              </div>
            </div>

            {/* Category Effort Breakdown - Editable with Real-time Recalculation & Persistence */}
            <div className="p-6 bg-white rounded-xl border border-slate-200">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-2 text-xs font-bold text-slate-800 uppercase tracking-wider">
                  <PieChart className="h-4 w-4 text-sky-600" />
                  <span>Effort Hours by Architectural Domain (Editable with Real-Time Recalculation)</span>
                </div>
                <span className="text-[11px] text-slate-400">
                  Edit hours below to immediately recalculate capacity utilization and save to database.
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(capacity.category_breakdown || {}).map(([cat, hrs]: any) => (
                  <div key={cat} className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex flex-col justify-between space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-800 capitalize text-xs">{cat.replace(/_/g, ' ')}</span>
                      <span className="text-[10px] text-slate-400 font-semibold uppercase">Domain Effort</span>
                    </div>

                    <div className="flex items-center space-x-2">
                      <div className="relative flex-1">
                        <input
                          type="number"
                          step="0.5"
                          min="0"
                          value={domainHours[cat] ?? hrs}
                          onChange={(e) => handleHoursChange(cat, e.target.value)}
                          onBlur={() => handlePersistDomainHours(cat)}
                          className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-bold text-slate-900 bg-white focus:ring-2 focus:ring-sky-500 focus:outline-none"
                        />
                        <span className="absolute right-3 top-2 text-[11px] font-bold text-slate-400">hours</span>
                      </div>
                      <button
                        onClick={() => handlePersistDomainHours(cat)}
                        disabled={savingDomain === cat}
                        title="Save and persist domain hours to database"
                        className="px-2.5 py-1.5 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold flex items-center space-x-1 shrink-0"
                      >
                        <Save className="h-3.5 w-3.5" />
                        <span>{savingDomain === cat ? 'Saving...' : 'Save'}</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
