import React, { useState, useEffect } from 'react';
import { FileText, CheckCircle, AlertTriangle, ArrowRight, Sparkles, ShieldCheck, Layers, Sliders } from 'lucide-react';
import { api } from '../../api/client';

interface Page2Props {
  transition: any;
  onNext: () => void;
  onRefresh: () => void;
}

export const Page2_ProfileReview: React.FC<Page2Props> = ({ transition, onNext, onRefresh }) => {
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [approving, setApproving] = useState(false);
  const [savingCategory, setSavingCategory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedFeedback, setSavedFeedback] = useState<string | null>(null);

  const loadProfile = async () => {
    if (!transition) return;
    setLoading(true);
    try {
      const data = await api.getProfile(transition.id);
      setProfile(data);
    } catch (e: any) {
      // Profile not generated yet
      setProfile(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, [transition]);

  const handleGenerate = async () => {
    if (!transition) return;
    setGenerating(true);
    setError(null);
    try {
      const p = await api.generateProfile(transition.id);
      setProfile(p);
      onRefresh();
    } catch (err: any) {
      setError(err.message || 'Generation failed');
    } finally {
      setGenerating(false);
    }
  };

  const handleCategoryChange = async (newCategory: string) => {
    if (!profile || !transition) return;
    setSavingCategory(true);
    try {
      const updated = await api.updateProfile(transition.id, {
        project_category: newCategory,
      });
      setProfile(updated);
      setSavedFeedback('Project Category updated successfully.');
      setTimeout(() => setSavedFeedback(null), 3000);
      onRefresh();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSavingCategory(false);
    }
  };

  const handleLevelToggle = async (level: string) => {
    if (!profile || !transition) return;
    const currentLevels = profile.intended_levels || ['L1', 'L2', 'L3'];
    let nextLevels: string[];

    if (currentLevels.includes(level)) {
      if (currentLevels.length === 1) {
        alert('At least one intended level must remain selected.');
        return;
      }
      nextLevels = currentLevels.filter((l: string) => l !== level);
    } else {
      nextLevels = [...currentLevels, level].sort();
    }

    setSavingCategory(true);
    try {
      const updated = await api.updateProfile(transition.id, {
        intended_levels: nextLevels,
      });
      setProfile(updated);
      setSavedFeedback(`Intended Levels updated to: ${nextLevels.join(', ')}`);
      setTimeout(() => setSavedFeedback(null), 3000);
      onRefresh();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSavingCategory(false);
    }
  };

  const handleApprove = async () => {
    if (!transition) return;
    setApproving(true);
    try {
      const p = await api.approveProfile(transition.id, { approved_by: 'Transition Lead Architect' });
      setProfile(p);
      onRefresh();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setApproving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-indigo-100 rounded-lg text-indigo-700">
              <FileText className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Stage 2: Project Profile Review & Governance</h2>
              <p className="text-sm text-slate-500">Synthesized by Project Profile Agent with full evidence traceability.</p>
            </div>
          </div>

          {!profile ? (
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow"
            >
              <Sparkles className="h-3.5 w-3.5" />
              <span>{generating ? 'Agent Synthesizing...' : 'Run Profile Agent'}</span>
            </button>
          ) : (
            <div className="flex items-center space-x-3">
              {profile.is_approved ? (
                <span className="flex items-center space-x-1.5 bg-emerald-100 text-emerald-800 text-xs font-semibold px-3 py-1.5 rounded-lg border border-emerald-300">
                  <ShieldCheck className="h-4 w-4 text-emerald-600" />
                  <span>Approved by {profile.approved_by}</span>
                </span>
              ) : (
                <button
                  onClick={handleApprove}
                  disabled={approving}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow"
                >
                  <CheckCircle className="h-3.5 w-3.5" />
                  <span>{approving ? 'Signing off...' : 'Approve Profile'}</span>
                </button>
              )}
              <button
                onClick={onNext}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow"
              >
                <span>Continue</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
        </div>

        {error && (
          <div className="p-3 mb-4 bg-red-50 text-red-700 border border-red-200 rounded-lg text-sm">
            {error}
          </div>
        )}

        {savedFeedback && (
          <div className="p-2.5 mb-4 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-lg text-xs font-medium flex items-center space-x-2">
            <CheckCircle className="h-4 w-4 text-emerald-600 shrink-0" />
            <span>{savedFeedback}</span>
          </div>
        )}

        {profile ? (
          <div className="space-y-6 mt-4">
            {/* Project Category & Intended Support/Development Levels */}
            <div className="p-5 bg-gradient-to-r from-slate-50 to-indigo-50/40 rounded-xl border border-indigo-100 shadow-sm">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Editable Radio: Project Category */}
                <div>
                  <div className="flex items-center space-x-1.5 mb-2">
                    <Sliders className="h-4 w-4 text-indigo-600" />
                    <label className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                      Project Category (Extracted & Editable)
                    </label>
                  </div>
                  <p className="text-[11px] text-slate-500 mb-3">
                    Extracted from transition document. Determines the operational scope of the KT engagement.
                  </p>
                  <div className="flex items-center space-x-4 bg-white p-3 rounded-lg border border-slate-200">
                    <label className="flex items-center space-x-2 cursor-pointer text-xs font-semibold text-slate-700">
                      <input
                        type="radio"
                        name="project_category"
                        value="ams_operations"
                        checked={profile.project_category === 'ams_operations'}
                        onChange={() => handleCategoryChange('ams_operations')}
                        className="text-indigo-600 focus:ring-indigo-500 h-4 w-4"
                      />
                      <span>AMS</span>
                    </label>

                    <label className="flex items-center space-x-2 cursor-pointer text-xs font-semibold text-slate-700">
                      <input
                        type="radio"
                        name="project_category"
                        value="development_and_ams"
                        checked={profile.project_category === 'development_and_ams'}
                        onChange={() => handleCategoryChange('development_and_ams')}
                        className="text-indigo-600 focus:ring-indigo-500 h-4 w-4"
                      />
                      <span>Both</span>
                    </label>

                    <label className="flex items-center space-x-2 cursor-pointer text-xs font-semibold text-slate-700">
                      <input
                        type="radio"
                        name="project_category"
                        value="development"
                        checked={profile.project_category === 'development'}
                        onChange={() => handleCategoryChange('development')}
                        className="text-indigo-600 focus:ring-indigo-500 h-4 w-4"
                      />
                      <span>Development</span>
                    </label>
                  </div>
                </div>

                {/* Checkbox: Intended Support/Development Levels */}
                <div>
                  <div className="flex items-center space-x-1.5 mb-2">
                    <Layers className="h-4 w-4 text-indigo-600" />
                    <label className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                      Intended Support / Development Levels
                    </label>
                  </div>
                  <p className="text-[11px] text-slate-500 mb-3">
                    Strictly limits the SME/Receiver roles in Stage 4 and selectable KT Level Matrix combinations in Stage 6.
                  </p>
                  <div className="flex items-center space-x-6 bg-white p-3 rounded-lg border border-slate-200">
                    {['L1', 'L2', 'L3'].map((lvl) => {
                      const checked = (profile.intended_levels || ['L1', 'L2', 'L3']).includes(lvl);
                      return (
                        <label key={lvl} className="flex items-center space-x-2 cursor-pointer text-xs font-semibold text-slate-700">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => handleLevelToggle(lvl)}
                            className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 h-4 w-4"
                          />
                          <span className="px-2 py-0.5 rounded font-bold text-[11px] bg-slate-100 text-slate-800">
                            {lvl}
                          </span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Core Info */}
              <div className="space-y-4">
                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2 text-xs">
                  <span className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Project Name</span>
                  <p className="text-sm font-semibold text-slate-900">{profile.project_name}</p>
                  <span className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Business Purpose</span>
                  <p className="text-slate-600 leading-relaxed">{profile.business_purpose}</p>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-slate-500 block text-[10px] uppercase font-bold">Criticality</span>
                    <span className="font-semibold text-slate-800">{profile.criticality}</span>
                  </div>
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <span className="text-slate-500 block text-[10px] uppercase font-bold">Support Model</span>
                    <span className="font-semibold text-slate-800">{profile.support_model}</span>
                  </div>
                </div>

                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2 text-xs">
                  <span className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Technology Stack</span>
                  <div className="flex flex-wrap gap-1.5">
                    {profile.technology_stack?.map((t: string, i: number) => (
                      <span key={i} className="px-2 py-0.5 bg-sky-100 text-sky-800 rounded font-medium border border-sky-200">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2 text-xs">
                  <span className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Environments</span>
                  <div className="flex flex-wrap gap-1.5">
                    {profile.environments?.map((e: string, i: number) => (
                      <span key={i} className="px-2 py-0.5 bg-purple-100 text-purple-800 rounded font-medium border border-purple-200">
                        {e}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Evidence & Gaps */}
              <div className="space-y-4">
                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2 text-xs">
                  <span className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">Source Evidence Citations</span>
                  <ul className="list-disc pl-4 space-y-1 text-slate-600">
                    {profile.evidence_citations?.map((c: string, i: number) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                </div>

                <div className="p-4 bg-amber-50/70 rounded-xl border border-amber-200 space-y-2 text-xs">
                  <div className="flex items-center space-x-1.5 text-amber-800 font-bold text-[10px] uppercase tracking-wider">
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
                    <span>Identified Evidence Gaps</span>
                  </div>
                  <ul className="list-disc pl-4 space-y-1 text-amber-900">
                    {profile.evidence_gaps?.map((g: string, i: number) => (
                      <li key={i}>{g}</li>
                    ))}
                  </ul>
                </div>

                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2 text-xs">
                  <span className="font-bold text-slate-700 uppercase tracking-wider text-[10px]">SLAs & KPIs</span>
                  <ul className="list-disc pl-4 space-y-1 text-slate-600">
                    {profile.kpis_slas?.map((s: string, i: number) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-12 text-slate-400">
            <FileText className="h-12 w-12 mx-auto mb-2 text-slate-300" />
            <p className="text-sm">Click "Run Profile Agent" to extract and structure the project profile.</p>
          </div>
        )}
      </div>
    </div>
  );
};
