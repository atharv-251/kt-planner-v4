import React, { useState, useEffect } from 'react';
import { Award, Sparkles, ArrowRight, CheckCircle2, Edit2, Check, X } from 'lucide-react';
import { api } from '../../api/client';

interface Page6Props {
  transition: any;
  onNext: () => void;
  onRefresh: () => void;
}

export const Page6_KTLevelMatrix: React.FC<Page6Props> = ({ transition, onNext, onRefresh }) => {
  const [evaluations, setEvaluations] = useState<any[]>([]);
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<any>({});

  const loadData = async () => {
    if (!transition) return;
    setLoading(true);
    try {
      const [data, pData] = await Promise.all([
        api.getKTLevels(transition.id),
        api.getProfile(transition.id).catch(() => null),
      ]);
      setEvaluations(data);
      setProfile(pData);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [transition]);

  const intendedLevels: string[] = profile?.intended_levels || ['L1', 'L2', 'L3'];

  // Allowed combinations based on selected intended levels
  const allowedCombinations = React.useMemo(() => {
    const res: string[] = [];
    intendedLevels.forEach((l) => res.push(l));
    if (intendedLevels.includes('L1') && intendedLevels.includes('L2')) res.push('L1+L2');
    if (intendedLevels.includes('L1') && intendedLevels.includes('L3')) res.push('L1+L3');
    if (intendedLevels.includes('L2') && intendedLevels.includes('L3')) res.push('L2+L3');
    if (intendedLevels.includes('L1') && intendedLevels.includes('L2') && intendedLevels.includes('L3')) res.push('L1+L2+L3');
    return res;
  }, [intendedLevels]);

  const handleRunEvaluation = async () => {
    if (!transition) return;
    setEvaluating(true);
    try {
      await api.evaluateKTLevels(transition.id);
      await loadData();
      onRefresh();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setEvaluating(false);
    }
  };

  const startEdit = (ev: any) => {
    setEditingId(ev.id);
    setEditForm({
      level_scope: ev.level_scope,
      applicability: ev.applicability,
      learning_objective: ev.learning_objective,
      expected_outcome: ev.expected_outcome,
      justification: ev.justification,
    });
  };

  const saveEdit = async (evId: string) => {
    try {
      await api.updateKTLevel(transition.id, evId, editForm);
      setEditingId(null);
      loadData();
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-purple-100 rounded-lg text-purple-700">
              <Award className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Stage 6: KT Level Evaluation Matrix (L1/L2/L3)</h2>
              <p className="text-sm text-slate-500">
                Every granular topic is evaluated for learning objectives, exit criteria, and evidence backing.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={handleRunEvaluation}
              disabled={evaluating}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow"
            >
              <Sparkles className="h-3.5 w-3.5" />
              <span>{evaluating ? 'Agent Evaluating...' : 'Evaluate KT Levels'}</span>
            </button>

            <button
              onClick={onNext}
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow"
            >
              <span>Proceed to Capacity</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        <div className="overflow-x-auto mt-4">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-100 text-slate-700 border-b border-slate-200">
                <th className="py-2.5 px-3 font-bold w-1/5">Granular Topic Name</th>
                <th className="py-2.5 px-3 font-bold w-24">Level Scope</th>
                <th className="py-2.5 px-3 font-bold w-24">Applicability</th>
                <th className="py-2.5 px-3 font-bold">Learning Objective</th>
                <th className="py-2.5 px-3 font-bold">Expected Outcome</th>
                <th className="py-2.5 px-3 font-bold text-right w-16">Edit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {evaluations.map((ev) => {
                const isEditing = editingId === ev.id;
                return (
                  <tr key={ev.id} className="hover:bg-slate-50/80">
                    <td className="py-3 px-3">
                      <span className="font-semibold text-slate-900 block">{ev.node_name}</span>
                      <span className="text-[10px] text-slate-400 uppercase">{ev.node_type}</span>
                    </td>

                    <td className="py-3 px-3">
                      {isEditing ? (
                        <select
                          value={editForm.level_scope}
                          onChange={(e) => setEditForm({ ...editForm, level_scope: e.target.value })}
                          className="px-2 py-1 border rounded text-xs bg-white font-semibold"
                        >
                          {allowedCombinations.map((combo) => (
                            <option key={combo} value={combo}>{combo}</option>
                          ))}
                        </select>
                      ) : (
                        <span className="px-2 py-0.5 rounded font-bold text-[10px] bg-purple-100 text-purple-800 border border-purple-200">
                          {ev.level_scope}
                        </span>
                      )}
                    </td>

                    <td className="py-3 px-3">
                      {isEditing ? (
                        <select
                          value={editForm.applicability}
                          onChange={(e) => setEditForm({ ...editForm, applicability: e.target.value })}
                          className="px-2 py-1 border rounded text-xs bg-white"
                        >
                          <option value="applicable">Applicable</option>
                          <option value="not_applicable">Not Applicable</option>
                          <option value="conditional">Conditional</option>
                        </select>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold capitalize bg-emerald-50 text-emerald-700 border border-emerald-200">
                          {ev.applicability}
                        </span>
                      )}
                    </td>

                    <td className="py-3 px-3 text-slate-700 leading-relaxed">
                      {isEditing ? (
                        <textarea
                          rows={2}
                          value={editForm.learning_objective}
                          onChange={(e) => setEditForm({ ...editForm, learning_objective: e.target.value })}
                          className="w-full p-1 border rounded text-xs"
                        />
                      ) : (
                        ev.learning_objective
                      )}
                    </td>

                    <td className="py-3 px-3 text-slate-600 leading-relaxed">
                      {isEditing ? (
                        <textarea
                          rows={2}
                          value={editForm.expected_outcome}
                          onChange={(e) => setEditForm({ ...editForm, expected_outcome: e.target.value })}
                          className="w-full p-1 border rounded text-xs"
                        />
                      ) : (
                        ev.expected_outcome
                      )}
                    </td>

                    <td className="py-3 px-3 text-right">
                      {isEditing ? (
                        <div className="flex items-center justify-end space-x-1">
                          <button
                            onClick={() => saveEdit(ev.id)}
                            className="p-1 bg-emerald-600 text-white rounded hover:bg-emerald-700"
                          >
                            <Check className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => setEditingId(null)}
                            className="p-1 bg-slate-200 text-slate-600 rounded hover:bg-slate-300"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => startEdit(ev)}
                          className="p-1 text-slate-400 hover:text-slate-700 rounded hover:bg-slate-100"
                        >
                          <Edit2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
              {evaluations.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-slate-400">
                    No KT levels evaluated yet. Click "Evaluate KT Levels" to invoke Agent 3.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

