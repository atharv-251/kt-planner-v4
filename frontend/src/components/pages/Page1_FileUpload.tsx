import React, { useState } from 'react';
import { Upload, FileCheck, ArrowRight, Play, AlertCircle, Sparkles } from 'lucide-react';
import { api } from '../../api/client';

interface Page1Props {
  transition: any;
  onNext: () => void;
  onRefresh: () => void;
}

export const Page1_FileUpload: React.FC<Page1Props> = ({ transition, onNext, onRefresh }) => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [extractResult, setExtractResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !transition) return;
    setUploading(true);
    setError(null);
    try {
      await api.uploadDocument(transition.id, file);
      onRefresh();
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleTriggerExtraction = async () => {
    if (!transition) return;
    setExtracting(true);
    setError(null);
    try {
      const res = await api.triggerExtraction(transition.id);
      setExtractResult(res);
      onRefresh();
    } catch (err: any) {
      setError(err.message || 'Extraction failed');
    } finally {
      setExtracting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center space-x-3 mb-4">
          <div className="p-2 bg-sky-100 rounded-lg text-sky-700">
            <Upload className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900">Stage 1: Document Intake & External Extraction</h2>
            <p className="text-sm text-slate-500">Every transition starts with uploading transition workbooks and documents.</p>
          </div>
        </div>

        {error && (
          <div className="p-3 mb-4 bg-red-50 text-red-700 border border-red-200 rounded-lg text-sm flex items-center space-x-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Upload Area */}
          <div className="border-2 border-dashed border-slate-200 rounded-xl p-6 text-center hover:border-sky-400 transition-colors bg-slate-50/50">
            <input
              type="file"
              id="file-upload"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            <label htmlFor="file-upload" className="cursor-pointer block">
              <Upload className="h-10 w-10 text-slate-400 mx-auto mb-3" />
              <p className="text-sm font-medium text-slate-700">Click to upload transition documents</p>
              <p className="text-xs text-slate-400 mt-1">Supports .xlsx, .docx, .pdf, .json</p>
            </label>
            {file && (
              <div className="mt-4 p-2 bg-white rounded border border-slate-200 text-xs font-medium text-slate-700 flex items-center justify-between">
                <span className="truncate">{file.name}</span>
                <span className="text-slate-400">({(file.size / 1024).toFixed(1)} KB)</span>
              </div>
            )}
            <button
              onClick={handleUpload}
              disabled={!file || uploading}
              className="mt-4 w-full py-2 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-300 text-white rounded-lg text-xs font-semibold transition shadow-sm"
            >
              {uploading ? 'Uploading File...' : 'Upload Document'}
            </button>
          </div>

          {/* Canonical Extraction Trigger */}
          <div className="border border-slate-200 rounded-xl p-6 flex flex-col justify-between bg-gradient-to-br from-white to-sky-50/30">
            <div>
              <div className="flex items-center space-x-2 text-sky-700 font-semibold text-sm mb-2">
                <Sparkles className="h-4 w-4" />
                <span>External AI Extraction Adapter</span>
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Connects to the external extraction service or canonical transition parser (pre-configured with <code className="bg-sky-100 px-1 rounded text-sky-800">KT_Extract-1789932244532.json</code>).
              </p>
              
              <div className="mt-4 bg-white p-3 rounded-lg border border-slate-200 text-xs space-y-1">
                <div className="flex justify-between">
                  <span className="text-slate-500">Document Parser:</span>
                  <span className="font-semibold text-slate-800">Openpyxl / Canonical Extractor</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Target Schema:</span>
                  <span className="font-semibold text-slate-800">Normalized Transition Payload</span>
                </div>
              </div>
            </div>

            <button
              onClick={handleTriggerExtraction}
              disabled={extracting}
              className="mt-6 w-full py-2.5 bg-sky-600 hover:bg-sky-700 disabled:bg-sky-300 text-white rounded-lg text-xs font-semibold flex items-center justify-center space-x-2 transition shadow-sm"
            >
              <Play className={`h-3.5 w-3.5 ${extracting ? 'animate-spin' : ''}`} />
              <span>{extracting ? 'Extracting Documents...' : 'Trigger Document Extraction'}</span>
            </button>
          </div>
        </div>

        {extractResult && (
          <div className="mt-6 p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <FileCheck className="h-6 w-6 text-emerald-600" />
              <div>
                <p className="text-xs font-bold text-emerald-900">{extractResult.message}</p>
                <p className="text-xs text-emerald-700">Project: <span className="font-semibold">{extractResult.project_name}</span> | Topics: <span className="font-semibold">{extractResult.total_topics}</span></p>
              </div>
            </div>
            <button
              onClick={onNext}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow"
            >
              <span>Proceed to Profile Review</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

