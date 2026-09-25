import React, { useEffect, useState } from 'react';
import { CalendarPlus, CheckCircle2, Mail, RefreshCw, Send, Upload } from 'lucide-react';
import { api } from '../../api/client';

interface Page13Props {
  transition: any;
}

export const Page13_TeamsKTScheduler: React.FC<Page13Props> = ({ transition }) => {
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [importing, setImporting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dryRun, setDryRun] = useState(false);

  const loadSessions = async () => {
    if (!transition) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getTeamsKTScheduler(transition.id);
      setSessions(data.sessions || []);
    } catch (requestError: any) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, [transition]);

  const sendInvites = async () => {
    if (!transition) return;
    setSending(true);
    setMessage(null);
    setError(null);
    try {
      const result = await api.sendTeamsInvites(transition.id, { dry_run: dryRun });
      setMessage(dryRun
        ? `${result.dry_run_count} invitation${result.dry_run_count === 1 ? '' : 's'} generated for review.`
        : `${result.sent} invitation${result.sent === 1 ? '' : 's'} sent; ${result.skipped} skipped; ${result.failed} failed.`);
    } catch (requestError: any) {
      setError(requestError.message);
    } finally {
      setSending(false);
    }
  };

  const importSchedule = async (file?: File) => {
    if (!transition || !file) return;
    setImporting(true);
    setMessage(null);
    setError(null);
    try {
      const result = await api.importTeamsSchedule(transition.id, file);
      setMessage(`${result.imported} schedule session${result.imported === 1 ? '' : 's'} imported with source attendees.`);
      await loadSessions();
    } catch (requestError: any) {
      setError(requestError.message);
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between mb-5">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-violet-100 rounded-lg text-violet-700"><CalendarPlus className="h-5 w-5" /></div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Module 13: Teams KT Scheduler</h2>
              <p className="text-sm text-slate-500">Generate or send Teams-compatible calendar invitations for scheduled KT sessions.</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="cursor-pointer px-3 py-2 border border-violet-200 text-violet-700 hover:bg-violet-50 rounded-lg text-xs font-semibold flex items-center gap-1.5">
              <Upload className={`h-3.5 w-3.5 ${importing ? 'animate-pulse' : ''}`} />
              {importing ? 'Importing...' : 'Import CSV'}
              <input type="file" accept=".csv,text/csv" className="hidden" disabled={importing} onChange={(event) => { void importSchedule(event.target.files?.[0]); event.currentTarget.value = ''; }} />
            </label>
            <label className="flex items-center gap-2 text-xs font-medium text-slate-700">
              <input type="checkbox" checked={dryRun} onChange={(event) => setDryRun(event.target.checked)} className="h-4 w-4 rounded border-slate-300 text-violet-600" />
              Dry run
            </label>
            <button onClick={loadSessions} disabled={loading} title="Refresh scheduled sessions" className="p-2 text-slate-500 hover:text-slate-900 border border-slate-200 rounded-lg hover:bg-slate-50">
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button onClick={sendInvites} disabled={sending || sessions.length === 0} className="px-4 py-2 bg-violet-600 hover:bg-violet-700 disabled:bg-slate-300 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow">
              <Send className={`h-3.5 w-3.5 ${sending ? 'animate-pulse' : ''}`} />
              <span>{sending ? 'Processing...' : dryRun ? 'Generate Invitations' : 'Send Invitations'}</span>
            </button>
          </div>
        </div>

        {message && <div className="mb-4 p-3 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-lg text-xs font-semibold flex gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-600" />{message}</div>}
        {error && <div className="mb-4 p-3 bg-red-50 text-red-800 border border-red-200 rounded-lg text-xs font-semibold">{error}</div>}

        <div className="overflow-x-auto border border-slate-200 rounded-xl">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100 text-slate-700"><tr><th className="px-3 py-2.5">Session</th><th className="px-3 py-2.5">Level</th><th className="px-3 py-2.5">Schedule</th><th className="px-3 py-2.5">Recipients</th><th className="px-3 py-2.5">Status</th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {sessions.map((session) => <tr key={session.id} className="hover:bg-slate-50"><td className="px-3 py-3 font-semibold text-slate-900">{session.title}</td><td className="px-3 py-3">{session.level}</td><td className="px-3 py-3 text-slate-600">{session.scheduled_date} <span className="whitespace-nowrap">{session.start_time} - {session.end_time}</span></td><td className="px-3 py-3 text-slate-600">{session.recipients.length ? <span className="flex items-center gap-1"><Mail className="h-3.5 w-3.5 text-violet-600" />{session.recipients.join(', ')}</span> : 'No email assigned'}</td><td className="px-3 py-3 capitalize">{session.status}</td></tr>)}
              {!loading && sessions.length === 0 && <tr><td colSpan={5} className="px-3 py-10 text-center text-slate-400">No scheduled KT sessions are available. Build a schedule in Module 10 first.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};