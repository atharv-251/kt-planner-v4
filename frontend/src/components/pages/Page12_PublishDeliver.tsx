import React, { useState } from 'react';
import { DownloadCloud, FileSpreadsheet, FileText, CheckCircle2, Lock, ShieldCheck } from 'lucide-react';
import { api } from '../../api/client';

interface Page12Props {
  transition: any;
  onRefresh: () => void;
}

export const Page12_PublishDeliver: React.FC<Page12Props> = ({ transition, onRefresh }) => {
  const [publishing, setPublishing] = useState(false);
  const [publishMessage, setPublishMessage] = useState<string | null>(null);

  const handlePublish = async () => {
    if (!transition) return;
    setPublishing(true);
    setPublishMessage(null);
    try {
      const res = await api.publishPlan(transition.id);
      setPublishMessage(res.message);
      onRefresh();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setPublishing(false);
    }
  };

  const isPublished = transition?.status === 'published';

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-indigo-100 rounded-lg text-indigo-700">
              <DownloadCloud className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Stage 12: Publish Transition & Deliverables</h2>
              <p className="text-sm text-slate-500">
                Final transition deliverables, audit reports, and master Excel package.
              </p>
            </div>
          </div>

          {!isPublished ? (
            <button
              onClick={handlePublish}
              disabled={publishing}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow"
            >
              <Lock className="h-3.5 w-3.5" />
              <span>{publishing ? 'Publishing...' : 'Lock & Publish Plan'}</span>
            </button>
          ) : (
            <span className="flex items-center space-x-1.5 bg-emerald-100 text-emerald-800 text-xs font-bold px-3 py-1.5 rounded-lg border border-emerald-300">
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              <span>Plan Published & Finalized</span>
            </span>
          )}
        </div>

        {publishMessage && (
          <div className="p-3 mb-4 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-lg text-xs font-semibold flex items-center space-x-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            <span>{publishMessage}</span>
          </div>
        )}

        {/* Deliverables Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
          {/* Deliverable 1: Excel Master Package */}
          <div className="p-5 bg-slate-50 rounded-xl border border-slate-200 flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-2 text-emerald-700 font-bold text-xs uppercase mb-2">
                <FileSpreadsheet className="h-5 w-5" />
                <span>Deliverable 1: KT Master Transition Package (.xlsx)</span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed mb-3">
                Complete multi-tab executive workbook with styling, gridlines, and formatting:
              </p>
              <ul className="text-xs text-slate-500 space-y-1 pl-4 list-disc mb-4">
                <li>Sheet 1: Executive Transition Summary</li>
                <li>Sheet 2: KT Master Knowledge Hierarchy</li>
                <li>Sheet 3: Confirmable Session Schedule</li>
                <li>Sheet 4: L1/L2/L3 Level Coverage Matrix</li>
                <li>Sheet 5: Readiness Validation Scorecard</li>
              </ul>
            </div>

            {transition && (
              <a
                href={api.getExcelDownloadUrl(transition.id)}
                download
                className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 shadow"
              >
                <DownloadCloud className="h-4 w-4" />
                <span>Download Master Excel Package (.xlsx)</span>
              </a>
            )}
          </div>

          {/* Deliverable 2: Schedule CSV */}
          <div className="p-5 bg-slate-50 rounded-xl border border-slate-200 flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-2 text-sky-700 font-bold text-xs uppercase mb-2">
                <FileText className="h-5 w-5" />
                <span>Deliverable 2: Calendar Schedule (.csv)</span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed mb-3">
                Raw comma-separated schedule file ready for direct calendar ingestion into Outlook or Google Calendar:
              </p>
              <ul className="text-xs text-slate-500 space-y-1 pl-4 list-disc mb-4">
                <li>Session title & KT Level tier</li>
                <li>Scheduled Date & Day of the Week</li>
                <li>Start Time & End Time</li>
                <li>Duration in hours & Delivery mode</li>
                <li>Conflict verification status</li>
              </ul>
            </div>

            {transition && (
              <a
                href={api.getCsvDownloadUrl(transition.id)}
                download
                className="w-full py-2.5 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center space-x-1.5 shadow"
              >
                <DownloadCloud className="h-4 w-4" />
                <span>Download Schedule CSV (.csv)</span>
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

