import React, { useEffect, useState } from 'react';
import { FileText, RefreshCw, UploadCloud } from 'lucide-react';
import { api } from '../../api/client';

interface Page14Props {
  transition: any;
}

export const Page14_KTTracker: React.FC<Page14Props> = ({ transition }) => {
  const [transcripts, setTranscripts] = useState<any[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTranscripts = async () => {
    if (!transition) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getTeamsTranscripts(transition.id);
      setTranscripts(data.transcripts || []);
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

        <div className="mt-5 overflow-x-auto border border-slate-200 rounded-xl">
          <table className="w-full text-left text-xs"><thead className="bg-slate-100 text-slate-700"><tr><th className="px-3 py-2.5">Transcript</th><th className="px-3 py-2.5">Uploaded</th><th className="px-3 py-2.5">Size</th><th className="px-3 py-2.5">Format</th></tr></thead><tbody className="divide-y divide-slate-100">
            {transcripts.map((transcript) => <tr key={transcript.id} className="hover:bg-slate-50"><td className="px-3 py-3 font-semibold text-slate-900">{transcript.file_name}</td><td className="px-3 py-3 text-slate-600">{new Date(transcript.uploaded_at).toLocaleString()}</td><td className="px-3 py-3 text-slate-600">{transcript.file_size.toLocaleString()} bytes</td><td className="px-3 py-3 text-slate-600">{transcript.mime_type}</td></tr>)}
            {!loading && transcripts.length === 0 && <tr><td colSpan={4} className="px-3 py-10 text-center text-slate-400">No Teams transcripts have been uploaded for this transition.</td></tr>}
          </tbody></table>
        </div>
      </div>
    </div>
  );
};