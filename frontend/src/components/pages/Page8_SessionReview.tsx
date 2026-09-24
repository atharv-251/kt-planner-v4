import React, { useState, useEffect } from 'react';
import { ListOrdered, ArrowRight, UserCheck, Clock, Calendar, CheckCircle } from 'lucide-react';
import { api } from '../../api/client';

interface Page8Props {
  transition: any;
  onNext: () => void;
  onRefresh: () => void;
}

export const Page8_SessionReview: React.FC<Page8Props> = ({ transition, onNext, onRefresh }) => {
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const loadSessions = async () => {
    if (!transition) return;
    setLoading(true);
    try {
      const data = await api.getSchedule(transition.id);
      setSessions(data);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, [transition]);

  const deliveryBadges: Record<string, string> = {
    workshop: 'bg-sky-100 text-sky-800 border-sky-200',
    hands_on: 'bg-purple-100 text-purple-800 border-purple-200',
    shadowing: 'bg-teal-100 text-teal-800 border-teal-200',
    reverse_shadowing: 'bg-amber-100 text-amber-800 border-amber-200',
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-indigo-100 rounded-lg text-indigo-700">
              <ListOrdered className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Stage 8: Granular Session Inventory</h2>
              <p className="text-sm text-slate-500">
                Detailed catalogue of sessions ready for conflict-free calendar slotting.
              </p>
            </div>
          </div>

          <button
            onClick={onNext}
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow"
          >
            <span>Proceed to Availability & Conflicts</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="overflow-x-auto mt-4">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-100 text-slate-700 border-b border-slate-200">
                <th className="py-2.5 px-3 font-bold w-12">Lvl</th>
                <th className="py-2.5 px-3 font-bold">Session Title</th>
                <th className="py-2.5 px-3 font-bold">Delivery Mode</th>
                <th className="py-2.5 px-3 font-bold">Duration</th>
                <th className="py-2.5 px-3 font-bold">Assigned SME</th>
                <th className="py-2.5 px-3 font-bold">Assigned Receiver</th>
                <th className="py-2.5 px-3 font-bold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sessions.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50/80">
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded font-bold text-[10px] bg-slate-200 text-slate-800">
                      {s.level}
                    </span>
                  </td>
                  <td className="py-3 px-3 font-semibold text-slate-900">
                    {s.session_title}
                  </td>
                  <td className="py-3 px-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${
                      deliveryBadges[s.delivery_mode] || 'bg-slate-100 text-slate-700'
                    }`}>
                      {s.delivery_mode.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="py-3 px-3 font-medium text-slate-700">
                    {s.duration_hours} Hours
                  </td>
                  <td className="py-3 px-3">
                    <div className="flex items-center space-x-1.5 text-slate-700">
                      <UserCheck className="h-3.5 w-3.5 text-sky-600" />
                      <span className="font-semibold">{s.sme_name}</span>
                      {s.sme_level && (
                        <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-[10px] font-bold border border-blue-200">
                          {s.sme_level}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-3 px-3">
                    <div className="flex items-center space-x-1.5 text-slate-700">
                      <UserCheck className="h-3.5 w-3.5 text-indigo-600" />
                      <span className="font-semibold">{s.receiver_name}</span>
                      {s.receiver_level && (
                        <span className="px-1.5 py-0.5 bg-indigo-100 text-indigo-700 rounded text-[10px] font-bold border border-indigo-200">
                          {s.receiver_level}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-100 text-emerald-800 border border-emerald-200">
                      {s.status}
                    </span>
                  </td>
                </tr>
              ))}
              {sessions.length === 0 && (
                <tr>
                  <td colSpan={7} className="text-center py-8 text-slate-400">
                    Sessions will appear here once scheduled. Proceed to Schedule Builder (Stage 10) to auto-build sessions.
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

