import React, { useState, useEffect } from 'react';
import { Users, UserPlus, Calendar, Upload, ArrowRight, Trash2, Shield, EyeOff, CheckCircle2 } from 'lucide-react';
import { api } from '../../api/client';

interface Page4Props {
  transition: any;
  onNext: () => void;
  onRefresh: () => void;
}

export const Page4_Stakeholders: React.FC<Page4Props> = ({ transition, onNext, onRefresh }) => {
  const [stakeholders, setStakeholders] = useState<any[]>([]);
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedSmeForCal, setSelectedSmeForCal] = useState<string | null>(null);
  const [calFile, setCalFile] = useState<File | null>(null);
  const [maskSubjects, setMaskSubjects] = useState(false);
  const [uploadingCal, setUploadingCal] = useState(false);

  // New Stakeholder form (strictly 2 roles: sme and receiver; level from intended levels)
  const [newSme, setNewSme] = useState({
    name: '',
    email: '',
    role: 'sme',
    level: 'L1',
  });

  // Leave form
  const [selectedSmeForLeave, setSelectedSmeForLeave] = useState<string | null>(null);
  const [leaveData, setLeaveData] = useState({
    start_date: '2026-10-05',
    end_date: '2026-10-07',
    reason: 'Annual Leave',
  });

  const loadData = async () => {
    if (!transition) return;
    setLoading(true);
    try {
      const [sData, pData] = await Promise.all([
        api.listStakeholders(transition.id),
        api.getProfile(transition.id).catch(() => null),
      ]);
      setStakeholders(sData);
      setProfile(pData);
      const levels = pData?.intended_levels || ['L1', 'L2', 'L3'];
      if (levels.length > 0 && !levels.includes(newSme.level)) {
        setNewSme((prev) => ({ ...prev, level: levels[0] }));
      }
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

  const handleAddStakeholder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSme.name || !transition) return;
    try {
      await api.createStakeholder(transition.id, newSme);
      setShowAddModal(false);
      setNewSme({ name: '', email: '', role: 'sme', level: intendedLevels[0] || 'L1' });
      loadData();
      onRefresh();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleAddLeave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSmeForLeave || !transition) return;
    try {
      await api.addLeave(transition.id, selectedSmeForLeave, leaveData);
      setSelectedSmeForLeave(null);
      loadData();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleUploadCalendar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSmeForCal || !calFile || !transition) return;
    setUploadingCal(true);
    try {
      const res = await api.uploadCalendarCsv(transition.id, selectedSmeForCal, calFile, maskSubjects);
      alert(res.message);
      setSelectedSmeForCal(null);
      setCalFile(null);
      loadData();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setUploadingCal(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-emerald-100 rounded-lg text-emerald-700">
              <Users className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Stage 4: SMEs & Receivers Roster</h2>
              <p className="text-sm text-slate-500">
                Manage SMEs and Receivers with strictly configured support/development levels ({intendedLevels.join(', ')}).
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={() => setShowAddModal(true)}
              className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow"
            >
              <UserPlus className="h-3.5 w-3.5" />
              <span>Add Stakeholder</span>
            </button>
            <button
              onClick={onNext}
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow"
            >
              <span>Proceed to Hierarchy</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {/* Intended Levels Guard Indicator */}
        <div className="p-3 mb-4 bg-indigo-50 border border-indigo-200 rounded-lg text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Shield className="h-4 w-4 text-indigo-600" />
            <span>
              <strong>Active KT Rules Scope:</strong> Only roles <strong>SME</strong> and <strong>Receiver</strong> are accepted. Member levels are restricted to Stage 2 intended levels: <strong>{intendedLevels.join(', ')}</strong>.
            </span>
          </div>
        </div>

        {/* Stakeholder Table */}
        <div className="overflow-x-auto mt-4">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-100 text-slate-700 border-b border-slate-200">
                <th className="py-2.5 px-3 font-bold">Stakeholder Name</th>
                <th className="py-2.5 px-3 font-bold">Role</th>
                <th className="py-2.5 px-3 font-bold">Level</th>
                <th className="py-2.5 px-3 font-bold">Scheduled Leaves</th>
                <th className="py-2.5 px-3 font-bold">Outlook Busy Events</th>
                <th className="py-2.5 px-3 font-bold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {stakeholders.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50/80">
                  <td className="py-3 px-3">
                    <span className="font-semibold text-slate-900 block">{s.name}</span>
                    <span className="text-[11px] text-slate-400">{s.email || 'No email provided'}</span>
                  </td>
                  <td className="py-3 px-3">
                    <span className={`px-2.5 py-0.5 rounded font-bold text-[10px] uppercase border ${
                      s.role === 'sme'
                        ? 'bg-sky-100 text-sky-800 border-sky-200'
                        : 'bg-purple-100 text-purple-800 border-purple-200'
                    }`}>
                      {s.role === 'sme' ? 'SME (Teacher)' : 'Receiver (Student)'}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded font-bold text-[11px] bg-slate-100 text-slate-800 border border-slate-300">
                      {s.level || 'L1'}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <div className="flex items-center space-x-2">
                      <span className="text-slate-600 font-medium">
                        {s.leaves?.length || 0} Leaves
                      </span>
                      <button
                        onClick={() => setSelectedSmeForLeave(s.id)}
                        className="text-[10px] text-sky-600 hover:text-sky-800 font-bold underline"
                      >
                        + Add Leave
                      </button>
                    </div>
                  </td>
                  <td className="py-3 px-3">
                    <div className="flex items-center space-x-2">
                      <span className="text-slate-600 font-medium">
                        {s.calendar_event_count || 0} Events
                      </span>
                      <button
                        onClick={() => setSelectedSmeForCal(s.id)}
                        className="text-[10px] text-emerald-600 hover:text-emerald-800 font-bold underline flex items-center space-x-0.5"
                      >
                        <Upload className="h-3 w-3" />
                        <span>Upload CSV</span>
                      </button>
                    </div>
                  </td>
                  <td className="py-3 px-3 text-right">
                    <button
                      onClick={async () => {
                        if (confirm(`Remove ${s.name}?`)) {
                          await api.deleteStakeholder(transition.id, s.id);
                          loadData();
                        }
                      }}
                      className="text-red-500 hover:text-red-700 p-1"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
              {stakeholders.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400">
                    No stakeholders registered. Click "Add Stakeholder" to add SMEs and Receivers.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Member Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 border border-slate-200">
            <h3 className="text-sm font-bold text-slate-900 mb-4">Add Stakeholder (SME or Receiver)</h3>
            <form onSubmit={handleAddStakeholder} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Ramesh Kumar"
                  value={newSme.name}
                  onChange={(e) => setNewSme({ ...newSme, name: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Email</label>
                <input
                  type="email"
                  placeholder="ramesh@company.com"
                  value={newSme.email}
                  onChange={(e) => setNewSme({ ...newSme, email: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-sky-500 focus:outline-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Role (Strictly 2 Roles)</label>
                  <select
                    value={newSme.role}
                    onChange={(e) => setNewSme({ ...newSme, role: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white focus:outline-none"
                  >
                    <option value="sme">SME (Teacher)</option>
                    <option value="receiver">Receiver (Team Member)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Level (Stage 2 Scope)</label>
                  <select
                    value={newSme.level}
                    onChange={(e) => setNewSme({ ...newSme, level: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white focus:outline-none"
                  >
                    {intendedLevels.map((lvl) => (
                      <option key={lvl} value={lvl}>{lvl}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 border border-slate-200 rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg font-semibold"
                >
                  Save Stakeholder
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Leave Modal */}
      {selectedSmeForLeave && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 border border-slate-200 text-xs">
            <h3 className="text-sm font-bold text-slate-900 mb-4">Record Stakeholder Leave</h3>
            <form onSubmit={handleAddLeave} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">Start Date</label>
                  <input
                    type="date"
                    required
                    value={leaveData.start_date}
                    onChange={(e) => setLeaveData({ ...leaveData, start_date: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-700 font-semibold mb-1">End Date</label>
                  <input
                    type="date"
                    required
                    value={leaveData.end_date}
                    onChange={(e) => setLeaveData({ ...leaveData, end_date: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none"
                  />
                </div>
              </div>
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Reason</label>
                <input
                  type="text"
                  value={leaveData.reason}
                  onChange={(e) => setLeaveData({ ...leaveData, reason: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none"
                />
              </div>
              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedSmeForLeave(null)}
                  className="px-4 py-2 border border-slate-200 rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg font-semibold"
                >
                  Record Leave
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Upload Outlook Calendar Modal */}
      {selectedSmeForCal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 border border-slate-200 text-xs">
            <h3 className="text-sm font-bold text-slate-900 mb-2">Import Outlook CSV Calendar</h3>
            <p className="text-slate-500 mb-4">
              Supported Headers: <code className="bg-slate-100 px-1 py-0.5 rounded text-slate-700">Subject, Start Date, Start Time, End Date, End Time, All day event, Reminder on/off</code>
            </p>

            <form onSubmit={handleUploadCalendar} className="space-y-4">
              <input
                type="file"
                accept=".csv"
                required
                onChange={(e) => setCalFile(e.target.files?.[0] || null)}
                className="w-full text-xs"
              />

              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="mask"
                  checked={maskSubjects}
                  onChange={(e) => setMaskSubjects(e.target.checked)}
                  className="rounded text-sky-600 focus:ring-0"
                />
                <label htmlFor="mask" className="text-slate-700 font-medium flex items-center space-x-1 cursor-pointer">
                  <EyeOff className="h-3.5 w-3.5 text-slate-500" />
                  <span>Mask Event Subjects for Privacy</span>
                </label>
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedSmeForCal(null)}
                  className="px-4 py-2 border border-slate-200 rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploadingCal || !calFile}
                  className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg font-semibold"
                >
                  {uploadingCal ? 'Importing...' : 'Upload & Process'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
