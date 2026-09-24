import React, { useEffect, useState } from 'react';
import { BarChart3, FileText, RefreshCw, UploadCloud } from 'lucide-react';
import { api } from '../../api/client';

interface Page14Props {
  transition: any;
}

export const Page14_KTTracker: React.FC<Page14Props> = ({ transition }) => {
  const [transcripts, setTranscripts] = useState<any[]>([]);
  const [activities, setActivities] = useState<any[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  const [selectedTranscript, setSelectedTranscript] = useState('');
  const [selectedActivity, setSelectedActivity] = useState('');

  const loadTranscripts = async () => {
    if (!transition) return;
    setLoading(true);
    setError(null);
    try {
      const [transcriptData, trackerData] = await Promise.all([api.getTeamsTranscripts(transition.id), api.getKTTracker(transition.id)]);
      setTranscripts(transcriptData.transcripts || []);
      setActivities(trackerData.activities || []);
      setSummary(trackerData.summary || null);
    } catch (requestError: any) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTranscripts();
  }, [transition]);

  const uploadTranscript = async () => {
    if (!transition || !file) return;
    setUploading(true);
    setError(null);
    try {
      await api.uploadTeamsTranscript(transition.id, file);
      setFile(null);
      await loadTranscripts();
    } catch (requestError: any) {
      setError(requestError.message);
    } finally {
      setUploading(false);
    }
  };

  const updateActivity = async (activityId: string, payload: any) => {
    if (!transition) return;
    try {
      await api.updateKTTrackerActivity(transition.id, activityId, payload);
      await loadTranscripts();
    } catch (requestError: any) { setError(requestError.message); }
  };

  const runAnalysis = async () => {
    if (!transition || !selectedTranscript || !selectedActivity) return;
    try {
      const result = await api.analyzeTeamsTranscript(transition.id, selectedTranscript, selectedActivity);
      setAnalysis(result.analysis);
      await loadTranscripts();
    } catch (requestError: any) { setError(requestError.message); }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between mb-5">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-teal-100 rounded-lg text-teal-700"><FileText className="h-5 w-5" /></div>
            <div><h2 className="text-lg font-bold text-slate-900">Module 14: KT Tracker</h2><p className="text-sm text-slate-500">Store and track Microsoft Teams WebVTT meeting transcripts for this transition.</p></div>
          </div>
          <button onClick={loadTranscripts} disabled={loading} title="Refresh transcripts" className="p-2 text-slate-500 hover:text-slate-900 border border-slate-200 rounded-lg hover:bg-slate-50"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /></button>
        </div>

        <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex flex-col gap-3 sm:flex-row sm:items-center">
          <input type="file" accept=".vtt,text/vtt" onChange={(event) => setFile(event.target.files?.[0] || null)} className="block w-full text-xs text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-teal-100 file:px-3 file:py-2 file:text-xs file:font-semibold file:text-teal-800 hover:file:bg-teal-200" />
          <button onClick={uploadTranscript} disabled={!file || uploading} className="shrink-0 px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:bg-slate-300 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5"><UploadCloud className="h-3.5 w-3.5" />{uploading ? 'Uploading...' : 'Upload Transcript'}</button>
        </div>
        {error && <div className="mt-4 p-3 bg-red-50 text-red-800 border border-red-200 rounded-lg text-xs font-semibold">{error}</div>}

        {summary && <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-5"><Metric label="Progress" value={`${summary.progress_percent}%`} /><Metric label="Activities" value={summary.total_activities} /><Metric label="Completed" value={summary.completed_activities} /><Metric label="Blocked" value={summary.blocked_activities} /><Metric label="Readiness" value={summary.readiness.replace('_', ' ')} /></div>}

        <div className="mt-5 overflow-x-auto border border-slate-200 rounded-xl">
          <table className="w-full text-left text-xs"><thead className="bg-slate-100 text-slate-700"><tr><th className="px-3 py-2.5">Transcript</th><th className="px-3 py-2.5">Uploaded</th><th className="px-3 py-2.5">Size</th><th className="px-3 py-2.5">Format</th></tr></thead><tbody className="divide-y divide-slate-100">
            {transcripts.map((transcript) => <tr key={transcript.id} className="hover:bg-slate-50"><td className="px-3 py-3 font-semibold text-slate-900">{transcript.file_name}</td><td className="px-3 py-3 text-slate-600">{new Date(transcript.uploaded_at).toLocaleString()}</td><td className="px-3 py-3 text-slate-600">{transcript.file_size.toLocaleString()} bytes</td><td className="px-3 py-3 text-slate-600">{transcript.mime_type}</td></tr>)}
            {!loading && transcripts.length === 0 && <tr><td colSpan={4} className="px-3 py-10 text-center text-slate-400">No Teams transcripts have been uploaded for this transition.</td></tr>}
          </tbody></table>
        </div>

        <div className="mt-6 border border-slate-200 rounded-xl overflow-x-auto"><table className="w-full text-left text-xs"><thead className="bg-slate-100 text-slate-700"><tr><th className="px-3 py-2.5">Activity</th><th className="px-3 py-2.5">Date</th><th className="px-3 py-2.5">Progress</th><th className="px-3 py-2.5">Status</th><th className="px-3 py-2.5">Blocker / risk</th></tr></thead><tbody className="divide-y divide-slate-100">{activities.map((activity) => <tr key={activity.id}><td className="px-3 py-3 font-semibold text-slate-900">{activity.activity_name}</td><td className="px-3 py-3 text-slate-600">{activity.scheduled_date || '-'}</td><td className="px-3 py-3"><input aria-label={`Progress for ${activity.activity_name}`} type="number" min="0" max="100" defaultValue={activity.progress_percent} onBlur={(event) => updateActivity(activity.id, { progress_percent: Number(event.target.value) })} className="w-16 rounded border border-slate-300 px-2 py-1" />%</td><td className="px-3 py-3"><select aria-label={`Status for ${activity.activity_name}`} value={activity.status} onChange={(event) => updateActivity(activity.id, { status: event.target.value })} className="rounded border border-slate-300 px-2 py-1"><option value="planned">Planned</option><option value="in_progress">In progress</option><option value="completed">Completed</option><option value="on_hold">On hold</option><option value="cancelled">Cancelled</option></select></td><td className="px-3 py-3"><input aria-label={`Blocker for ${activity.activity_name}`} defaultValue={activity.blocker || activity.risk} onBlur={(event) => updateActivity(activity.id, { blocker: event.target.value })} placeholder="Add blocker or risk" className="min-w-44 rounded border border-slate-300 px-2 py-1" /></td></tr>)}{!loading && activities.length === 0 && <tr><td colSpan={5} className="px-3 py-10 text-center text-slate-400">Build or import a schedule to create tracker activities.</td></tr>}</tbody></table></div>

        <div className="mt-6 p-4 bg-teal-50 border border-teal-200 rounded-xl"><div className="flex gap-2 items-center text-teal-900 font-semibold text-sm"><BarChart3 className="h-4 w-4" />Transcript topic-coverage analysis</div><div className="mt-3 grid gap-3 md:grid-cols-3"><select value={selectedTranscript} onChange={(event) => setSelectedTranscript(event.target.value)} className="rounded-lg border border-teal-300 bg-white px-3 py-2 text-xs"><option value="">Choose transcript</option>{transcripts.map((transcript) => <option key={transcript.id} value={transcript.id}>{transcript.file_name}</option>)}</select><select value={selectedActivity} onChange={(event) => setSelectedActivity(event.target.value)} className="rounded-lg border border-teal-300 bg-white px-3 py-2 text-xs"><option value="">Choose activity</option>{activities.map((activity) => <option key={activity.id} value={activity.id}>{activity.activity_name}</option>)}</select><button onClick={runAnalysis} disabled={!selectedTranscript || !selectedActivity} className="rounded-lg bg-teal-700 px-3 py-2 text-xs font-semibold text-white disabled:bg-slate-300">Analyze transcript</button></div>{analysis && <div className="mt-3 text-xs text-teal-950"><p className="font-semibold">{analysis.summary || 'No substantive transcript content found.'}</p><p className="mt-1">Covered: {analysis.topics_covered.join(', ') || 'None'} | Partial: {analysis.topics_partially_covered.join(', ') || 'None'} | Missed: {analysis.topics_missed.join(', ') || 'None'}</p></div>}</div>
      </div>
    </div>
  );
};

const Metric = ({ label, value }: { label: string; value: string | number }) => <div className="border border-slate-200 bg-slate-50 rounded-lg px-3 py-2"><div className="text-[10px] uppercase font-bold text-slate-500">{label}</div><div className="mt-1 text-sm font-bold capitalize text-slate-900">{value}</div></div>;