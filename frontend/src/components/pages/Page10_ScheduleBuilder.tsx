import React, { useState, useEffect } from 'react';
import { CalendarDays, Play, ArrowRight, CheckCircle2, AlertTriangle, Clock, User, Table, Calendar } from 'lucide-react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import { api } from '../../api/client';

interface Page10Props {
  transition: any;
  onNext: () => void;
  onRefresh: () => void;
}

export const Page10_ScheduleBuilder: React.FC<Page10Props> = ({ transition, onNext, onRefresh }) => {
  const [events, setEvents] = useState<any[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [viewMode, setViewMode] = useState<'calendar' | 'table'>('calendar');
  const [loading, setLoading] = useState(false);
  const [building, setBuilding] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<any>(null);
  const [buildMessage, setBuildMessage] = useState<string | null>(null);

  const loadData = async () => {
    if (!transition) return;
    setLoading(true);
    try {
      const [calData, sessData] = await Promise.all([
        api.getFullCalendarEvents(transition.id),
        api.getSchedule(transition.id),
      ]);
      setEvents(calData);
      setSessions(sessData);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [transition]);

  const handleAutoBuild = async () => {
    if (!transition) return;
    setBuilding(true);
    setBuildMessage(null);
    try {
      const res = await api.autoBuildSchedule(transition.id, {
        daily_start_hour: 10,
        daily_max_hours: transition.daily_kt_hours || 5.0,
        auto_assign_smes: true,
      });
      setBuildMessage(res.message);
      await loadData();
      onRefresh();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setBuilding(false);
    }
  };

  const handleEventClick = (clickInfo: any) => {
    setSelectedEvent(clickInfo.event);
  };

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
            <div className="p-2 bg-sky-100 rounded-lg text-sky-700">
              <CalendarDays className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Stage 10: Deterministic Schedule Builder</h2>
              <p className="text-sm text-slate-500">
                Sequences L1 → L2 → L3 sessions, respects bank holidays, SME leaves, and eliminates calendar collisions.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {/* View Switcher: Calendar vs Table */}
            <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-lg border border-slate-200">
              <button
                onClick={() => setViewMode('calendar')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center space-x-1.5 transition ${
                  viewMode === 'calendar' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <Calendar className="h-3.5 w-3.5" />
                <span>Calendar View</span>
              </button>
              <button
                onClick={() => setViewMode('table')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center space-x-1.5 transition ${
                  viewMode === 'table' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <Table className="h-3.5 w-3.5" />
                <span>Table Preview</span>
              </button>
            </div>

            <button
              onClick={handleAutoBuild}
              disabled={building}
              className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow"
            >
              <Play className={`h-3.5 w-3.5 ${building ? 'animate-spin' : ''}`} />
              <span>{building ? 'Building Schedule...' : 'Auto-Build Schedule'}</span>
            </button>

            <button
              onClick={onNext}
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow"
            >
              <span>Proceed to Validation</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {buildMessage && (
          <div className="p-3 mb-4 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-lg text-xs font-semibold flex items-center space-x-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            <span>{buildMessage}</span>
          </div>
        )}

        {/* Legend (shown in Calendar view) */}
        {viewMode === 'calendar' && (
          <div className="flex items-center space-x-4 mb-4 text-xs font-medium text-slate-600">
            <span className="flex items-center space-x-1.5">
              <span className="w-3 h-3 rounded bg-blue-600"></span>
              <span>L1 Overview</span>
            </span>
            <span className="flex items-center space-x-1.5">
              <span className="w-3 h-3 rounded bg-purple-600"></span>
              <span>L2 Deep Dive</span>
            </span>
            <span className="flex items-center space-x-1.5">
              <span className="w-3 h-3 rounded bg-emerald-600"></span>
              <span>L3 Operational Handover</span>
            </span>
            <span className="flex items-center space-x-1.5">
              <span className="w-3 h-3 rounded bg-red-600"></span>
              <span>Calendar Conflict</span>
            </span>
          </div>
        )}

        {/* View Mode: Calendar */}
        {viewMode === 'calendar' ? (
          <div className="border border-slate-200 rounded-xl p-4 bg-white text-xs">
            <FullCalendar
              plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
              initialView="timeGridWeek"
              headerToolbar={{
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay',
              }}
              slotMinTime="08:00:00"
              slotMaxTime="20:00:00"
              allDaySlot={false}
              events={events}
              eventClick={handleEventClick}
              initialDate={transition ? transition.start_date : '2026-09-21'}
              height={600}
            />
          </div>
        ) : (
          /* View Mode: Table Preview */
          <div className="border border-slate-200 rounded-xl overflow-hidden text-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-100 text-slate-700 border-b border-slate-200">
                    <th className="py-2.5 px-3 font-bold w-12">Lvl</th>
                    <th className="py-2.5 px-3 font-bold">Session Title</th>
                    <th className="py-2.5 px-3 font-bold">Date & Time</th>
                    <th className="py-2.5 px-3 font-bold">Mode</th>
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
                        <span className={`px-2 py-0.5 rounded font-bold text-[10px] ${
                          s.level === 'L1' ? 'bg-blue-100 text-blue-800' :
                          s.level === 'L2' ? 'bg-purple-100 text-purple-800' :
                          'bg-emerald-100 text-emerald-800'
                        }`}>
                          {s.level}
                        </span>
                      </td>
                      <td className="py-3 px-3 font-semibold text-slate-900">
                        {s.session_title}
                      </td>
                      <td className="py-3 px-3 text-slate-600 whitespace-nowrap">
                        <div className="font-medium text-slate-800">{s.scheduled_date}</div>
                        <div className="text-[11px] text-slate-500">{s.start_time} - {s.end_time}</div>
                      </td>
                      <td className="py-3 px-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${
                          deliveryBadges[s.delivery_mode] || 'bg-slate-100 text-slate-700'
                        }`}>
                          {s.delivery_mode.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="py-3 px-3 font-medium text-slate-700 whitespace-nowrap">
                        {s.duration_hours}h
                      </td>
                      <td className="py-3 px-3">
                        <div className="flex items-center space-x-1.5">
                          <User className="h-3.5 w-3.5 text-sky-600" />
                          <span className="font-semibold text-slate-800">{s.sme_name}</span>
                          {s.sme_level && (
                            <span className="px-1.5 py-0.2 bg-blue-100 text-blue-700 rounded text-[10px] font-bold border border-blue-200">
                              {s.sme_level}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        <div className="flex items-center space-x-1.5">
                          <User className="h-3.5 w-3.5 text-indigo-600" />
                          <span className="font-semibold text-slate-800">{s.receiver_name}</span>
                          {s.receiver_level && (
                            <span className="px-1.5 py-0.2 bg-indigo-100 text-indigo-700 rounded text-[10px] font-bold border border-indigo-200">
                              {s.receiver_level}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-3 whitespace-nowrap">
                        {s.conflict_flags && s.conflict_flags.length > 0 ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-red-100 text-red-800 border border-red-200 flex items-center space-x-1">
                            <AlertTriangle className="h-3 w-3 text-red-600" />
                            <span>Conflict</span>
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-100 text-emerald-800 border border-emerald-200">
                            {s.status}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                  {sessions.length === 0 && (
                    <tr>
                      <td colSpan={8} className="text-center py-8 text-slate-400">
                        No scheduled sessions yet. Click "Auto-Build Schedule" above to generate sessions.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Session Detail Modal */}
        {selectedEvent && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 border border-slate-200 text-xs">
              <div className="flex items-center justify-between mb-3">
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-100 text-slate-800">
                  {selectedEvent.extendedProps.level} Session
                </span>
                <span className="text-slate-400 font-medium">
                  {selectedEvent.extendedProps.duration_hours}h
                </span>
              </div>

              <h3 className="text-sm font-bold text-slate-900 mb-3">{selectedEvent.title}</h3>

              <div className="space-y-2.5 p-3 bg-slate-50 rounded-lg border border-slate-200 mb-4">
                <div className="flex items-center justify-between text-slate-700">
                  <div className="flex items-center space-x-2">
                    <User className="h-3.5 w-3.5 text-sky-600" />
                    <span className="font-semibold">SME: {selectedEvent.extendedProps.sme_name}</span>
                  </div>
                  {selectedEvent.extendedProps.sme_level && (
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded text-[10px] font-bold border border-blue-200">
                      {selectedEvent.extendedProps.sme_level}
                    </span>
                  )}
                </div>
                <div className="flex items-center justify-between text-slate-700">
                  <div className="flex items-center space-x-2">
                    <User className="h-3.5 w-3.5 text-indigo-600" />
                    <span className="font-semibold">Receiver: {selectedEvent.extendedProps.receiver_name}</span>
                  </div>
                  {selectedEvent.extendedProps.receiver_level && (
                    <span className="px-2 py-0.5 bg-indigo-100 text-indigo-800 rounded text-[10px] font-bold border border-indigo-200">
                      {selectedEvent.extendedProps.receiver_level}
                    </span>
                  )}
                </div>
                <div className="flex items-center space-x-2 text-slate-700 pt-1 border-t border-slate-200/60">
                  <Clock className="h-3.5 w-3.5 text-slate-500" />
                  <span>
                    {selectedEvent.start ? selectedEvent.start.toLocaleTimeString() : ''} -{' '}
                    {selectedEvent.end ? selectedEvent.end.toLocaleTimeString() : ''}
                  </span>
                </div>
              </div>

              {selectedEvent.extendedProps.conflicts?.length > 0 && (
                <div className="p-3 bg-red-50 rounded-lg border border-red-200 text-red-800 mb-4">
                  <div className="flex items-center space-x-1.5 font-bold mb-1">
                    <AlertTriangle className="h-3.5 w-3.5 text-red-600" />
                    <span>Detected Slot Conflicts</span>
                  </div>
                  <ul className="list-disc pl-4 space-y-0.5">
                    {selectedEvent.extendedProps.conflicts.map((c: string, i: number) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="flex justify-end">
                <button
                  onClick={() => setSelectedEvent(null)}
                  className="px-4 py-2 bg-slate-900 text-white rounded-lg font-semibold hover:bg-slate-800"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

