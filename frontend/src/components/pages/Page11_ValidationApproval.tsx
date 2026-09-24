import React, { useState, useEffect } from 'react';
import { ShieldCheck, Sparkles, CheckCircle2, XCircle, AlertTriangle, ArrowRight, History, Send } from 'lucide-react';
import { api } from '../../api/client';

interface Page11Props {
  transition: any;
  onNext: () => void;
  onRefresh: () => void;
}

export const Page11_ValidationApproval: React.FC<Page11Props> = ({ transition, onNext, onRefresh }) => {
  const [validation, setValidation] = useState<any>(null);
  const [patches, setPatches] = useState<any[]>([]);
  const [prompt, setPrompt] = useState('');
  const [refining, setRefining] = useState(false);
  const [loading, setLoading] = useState(false);

  const loadValidation = async () => {
    if (!transition) return;
    setLoading(true);
    try {
      const val = await api.getValidation(transition.id);
      const ptchs = await api.getPatches(transition.id);
      setValidation(val);
      setPatches(ptchs);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadValidation();
  }, [transition]);

  const handleRefine = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || !transition) return;
    setRefining(true);
    try {
      const res = await api.refineWithNL(transition.id, prompt);
      alert(res.message);
      setPrompt('');
      await loadValidation();
      onRefresh();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setRefining(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-emerald-100 rounded-lg text-emerald-700">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Stage 11: Validation Scorecard & Refinement</h2>
              <p className="text-sm text-slate-500">
                Authoritative compliance audit testing hierarchy completeness, KT level coverage, and zero conflicts.
              </p>
            </div>
          </div>

          <button
            onClick={onNext}
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow"
          >
            <span>Proceed to Publish & Deliver</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* Validation Scorecard Banner */}
        {validation && (
          <div className="p-5 rounded-xl border mb-6 bg-slate-50 border-slate-200">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Governance Status</span>
                <div className="flex items-center space-x-2 mt-1">
                  <span className={`text-2xl font-black ${
                    validation.overall_status === 'PASS' ? 'text-emerald-600' : 'text-amber-600'
                  }`}>
                    {validation.overall_status}
                  </span>
                  <span className="text-sm font-semibold text-slate-600">
                    ({validation.score_percent}% Readiness Score)
                  </span>
                </div>
              </div>

              <div className="flex space-x-4 text-xs text-center font-bold">
                <div className="px-3 py-1.5 bg-white rounded-lg border border-slate-200">
                  <span className="text-slate-400 block text-[10px]">TOTAL CHECKS</span>
                  <span className="text-slate-800">{validation.total_checks}</span>
                </div>
                <div className="px-3 py-1.5 bg-emerald-50 text-emerald-800 rounded-lg border border-emerald-200">
                  <span className="text-emerald-600 block text-[10px]">PASSED</span>
                  <span>{validation.passed_checks}</span>
                </div>
                <div className="px-3 py-1.5 bg-red-50 text-red-800 rounded-lg border border-red-200">
                  <span className="text-red-600 block text-[10px]">FAILED</span>
                  <span>{validation.failed_checks}</span>
                </div>
              </div>
            </div>

            {/* Checklist Items */}
            <div className="mt-4 space-y-2">
              {validation.checks?.map((chk: any, i: number) => (
                <div
                  key={i}
                  className={`p-3 rounded-lg border text-xs flex items-center justify-between ${
                    chk.passed
                      ? 'bg-white border-slate-200 text-slate-800'
                      : 'bg-red-50 border-red-200 text-red-900'
                  }`}
                >
                  <div className="flex items-center space-x-2.5">
                    {chk.passed ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-600 shrink-0" />
                    )}
                    <div>
                      <span className="font-bold block">{chk.check_name}</span>
                      <span className="text-slate-500 text-[11px]">{chk.message}</span>
                    </div>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    chk.passed ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {chk.passed ? 'PASS' : chk.severity}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Natural Language Refinement Input (Agent 5) */}
        <div className="p-5 bg-gradient-to-r from-sky-50 to-indigo-50/50 rounded-xl border border-sky-200 mb-6">
          <div className="flex items-center space-x-2 text-sky-900 font-bold text-xs uppercase tracking-wider mb-2">
            <Sparkles className="h-4 w-4 text-sky-600" />
            <span>Agent 5: Natural Language Plan Refinement</span>
          </div>
          <p className="text-xs text-slate-600 mb-3">
            Ask the AI refinement agent to modify durations, swap topics, or reallocate SME sessions without regenerating the entire plan.
          </p>

          <form onSubmit={handleRefine} className="flex space-x-2">
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g., Increase Java architecture session to 4 hours and assign to Dev Sharma"
              className="flex-1 px-3 py-2 border border-slate-300 rounded-lg text-xs font-medium focus:ring-2 focus:ring-sky-500 focus:outline-none bg-white"
            />
            <button
              type="submit"
              disabled={refining || !prompt.trim()}
              className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow"
            >
              <Send className="h-3.5 w-3.5" />
              <span>{refining ? 'Applying Patch...' : 'Apply Refinement'}</span>
            </button>
          </form>
        </div>

        {/* Patch Version History */}
        {patches.length > 0 && (
          <div className="border border-slate-200 rounded-xl overflow-hidden text-xs">
            <div className="bg-slate-100 px-4 py-2.5 font-bold text-slate-700 flex items-center space-x-1.5">
              <History className="h-4 w-4 text-slate-500" />
              <span>Version Audit & Patch Log</span>
            </div>
            <div className="divide-y divide-slate-100 max-h-48 overflow-y-auto">
              {patches.map((p) => (
                <div key={p.id} className="p-3 flex items-center justify-between hover:bg-slate-50">
                  <div>
                    <span className="font-bold text-slate-900">Version {p.version_number}</span>
                    <span className="text-slate-500 text-[11px] block">{p.nl_prompt || p.patch_type}</span>
                  </div>
                  <span className="text-[10px] text-slate-400">
                    {new Date(p.applied_at).toLocaleString()} by {p.applied_by}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

