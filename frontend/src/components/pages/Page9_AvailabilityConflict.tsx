import React, { useState, useEffect } from 'react';
import { CalendarCheck, ArrowRight, AlertCircle, CheckCircle2, ShieldAlert, Globe } from 'lucide-react';
import { api } from '../../api/client';

interface Page9Props {
  transition: any;
  onNext: () => void;
  onRefresh: () => void;
}

export const Page9_AvailabilityConflict: React.FC<Page9Props> = ({ transition, onNext, onRefresh }) => {
  const [availability, setAvailability] = useState<any>(null);
  const [holidaysData, setHolidaysData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!transition) return;
    setLoading(true);
    Promise.all([
      api.getAvailability(transition.id),
      api.getHolidays(transition.id),
    ]).then(([avail, hols]) => {
      setAvailability(avail);
      setHolidaysData(hols);
    }).catch(console.error).finally(() => setLoading(false));
  }, [transition]);

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-teal-100 rounded-lg text-teal-700">
              <CalendarCheck className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Stage 9: Availability Matrix & Bank Holidays</h2>
              <p className="text-sm text-slate-500">
                Merges Bank Holidays from <code className="text-slate-700 font-mono">holidays.json</code>, SME leaves, and imported Outlook calendars.
              </p>
            </div>
          </div>

          <button
            onClick={onNext}
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow"
          >
            <span>Proceed to Schedule Builder</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* Bank Holidays Card */}
        {holidaysData && (
          <div className="p-5 bg-gradient-to-r from-slate-900 to-indigo-950 text-white rounded-xl shadow mb-6">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2 text-xs text-sky-300 font-bold uppercase tracking-wider">
                <Globe className="h-4 w-4" />
                <span>Authoritative Bank Holidays for {holidaysData.country} (holidays.json)</span>
              </div>
              <div className="flex items-center space-x-2">
                {holidaysData.sme_country && (
                  <span className="text-[10px] bg-blue-500/20 text-blue-300 border border-blue-500/30 px-2 py-0.5 rounded font-semibold">
                    SME: {holidaysData.sme_country}
                  </span>
                )}
                {holidaysData.receiver_country && holidaysData.receiver_country !== holidaysData.sme_country && (
                  <span className="text-[10px] bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded font-semibold">
                    Receiver: {holidaysData.receiver_country}
                  </span>
                )}
                <span className="text-xs bg-white/10 px-2.5 py-0.5 rounded-full border border-white/10">
                  {holidaysData.total_holidays} Holidays in Transition Period
                </span>
              </div>
            </div>

            {holidaysData.total_holidays > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 mt-3">
                {Object.entries(holidaysData.holidays).map(([dt, name]: any) => (
                  <div key={dt} className="p-2.5 bg-white/10 rounded-lg border border-white/10 text-xs flex items-center justify-between">
                    <div>
                      <span className="font-bold text-sky-300 block">{dt}</span>
                      <span className="text-slate-200 truncate block max-w-[180px]">{name}</span>
                    </div>
                    <span className="text-[10px] bg-red-500/20 text-red-300 border border-red-500/30 px-1.5 py-0.5 rounded uppercase font-bold">
                      Exclusion
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400 mt-2">
                No bank holidays fall inside this transition timeline. All weekdays are eligible working days.
              </p>
            )}
          </div>
        )}

        {/* Day by day availability grid */}
        <div className="border border-slate-200 rounded-xl overflow-hidden mt-4 text-xs">
          <div className="bg-slate-100 px-4 py-2.5 font-bold text-slate-700 flex justify-between">
            <span>Transition Day & Calendar Status</span>
            <span>SME Team Availability Heatmap</span>
          </div>

          {availability && availability.days ? (
            <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto">
              {availability.days.map((day: any) => {
                const isWorking = day.status === 'WORKING_DAY';
                const isHol = day.status === 'BANK_HOLIDAY';

                return (
                  <div key={day.date} className={`p-3 flex items-center justify-between ${
                    isHol ? 'bg-red-50/50' : !isWorking ? 'bg-slate-50/70' : 'bg-white'
                  }`}>
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-slate-800">{day.date}</span>
                      <span className="text-slate-400 text-[11px]">({day.day_of_week})</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        isWorking ? 'bg-emerald-100 text-emerald-800' : isHol ? 'bg-red-100 text-red-800' : 'bg-slate-200 text-slate-600'
                      }`}>
                        {day.status.replace(/_/g, ' ')}
                      </span>
                      {day.holiday_name && (
                        <span className="text-red-700 font-semibold text-[11px]">
                          - {day.holiday_name}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center space-x-2">
                      {Object.entries(day.sme_statuses || {}).map(([smeId, stat]: any) => (
                        <span
                          key={smeId}
                          title={`${stat.reason} (Available: ${stat.available_hours ?? 0}h)`}
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                            stat.available
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              : 'bg-red-50 text-red-700 border-red-200'
                          }`}
                        >
                          {stat.available ? '✓ Avail' : '✗ Busy'}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-12 text-slate-400">Loading availability matrix...</div>
          )}
        </div>
      </div>
    </div>
  );
};

