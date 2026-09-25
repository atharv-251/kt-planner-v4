import React from 'react';
import { Layers, Calendar, CheckCircle2, ShieldCheck, Database, RefreshCw } from 'lucide-react';

interface NavbarProps {
  transition: any;
  currentStep: number;
  onRefresh: () => void;
  loading: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ transition, currentStep, onRefresh, loading }) => {
  return (
    <header className="bg-slate-900 text-white sticky top-0 z-50 border-b border-slate-800 shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center shadow">
            <Layers className="h-6 w-6 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg tracking-tight">KT PLANNER</span>
              <span className="hidden sm:inline text-xs uppercase bg-sky-500/20 text-sky-300 font-semibold px-2 py-0.5 rounded border border-sky-500/30">
                Enterprise v4
              </span>
            </div>
            <p className="hidden sm:block text-xs text-slate-400">AI Transition Planning & Orchestration Platform</p>
          </div>
        </div>

        {transition && (
          <div className="flex items-center space-x-4 text-xs">
            <div className="hidden md:flex items-center space-x-2 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700">
              <span className="text-slate-400">Active Transition:</span>
              <span className="font-semibold text-white max-w-[180px] truncate">{transition.name}</span>
            </div>

            <div className="hidden lg:flex items-center space-x-2 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700">
              <Calendar className="h-3.5 w-3.5 text-sky-400" />
              <span className="text-slate-300">{transition.available_kt_days} KT Days</span>
              <span className="text-slate-500">|</span>
              <span className="text-sky-400 font-medium">{transition.target_capacity_hours}h Target</span>
            </div>

            <div className="hidden sm:flex items-center space-x-1.5 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="font-medium capitalize text-emerald-300">{transition.status.replace(/_/g, ' ')}</span>
            </div>

            <button
              onClick={onRefresh}
              disabled={loading}
              title="Refresh Data"
              className="p-1.5 text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors border border-slate-700"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};

