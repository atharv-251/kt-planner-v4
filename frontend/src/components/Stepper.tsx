import React from 'react';
import {
  Upload, FileText, Settings, Users, Network, Award,
  Scale, ListOrdered, CalendarCheck, CalendarDays, ShieldCheck, DownloadCloud, CalendarPlus, ClipboardList, ChartNoAxesCombined
} from 'lucide-react';

export interface StepItem {
  id: number;
  label: string;
  icon: React.ReactNode;
}

export const STEPS: StepItem[] = [
  { id: 1, label: 'File Upload', icon: <Upload className="h-4 w-4" /> },
  { id: 2, label: 'Profile Review', icon: <FileText className="h-4 w-4" /> },
  { id: 3, label: 'Settings', icon: <Settings className="h-4 w-4" /> },
  { id: 4, label: 'SMEs & People', icon: <Users className="h-4 w-4" /> },
  { id: 5, label: 'Hierarchy', icon: <Network className="h-4 w-4" /> },
  { id: 6, label: 'KT Levels', icon: <Award className="h-4 w-4" /> },
  { id: 7, label: 'Capacity', icon: <Scale className="h-4 w-4" /> },
  { id: 8, label: 'Sessions', icon: <ListOrdered className="h-4 w-4" /> },
  { id: 9, label: 'Availability', icon: <CalendarCheck className="h-4 w-4" /> },
  { id: 10, label: 'Scheduler', icon: <CalendarDays className="h-4 w-4" /> },
  { id: 11, label: 'Validation', icon: <ShieldCheck className="h-4 w-4" /> },
  { id: 12, label: 'Deliverables', icon: <DownloadCloud className="h-4 w-4" /> },
  { id: 13, label: 'Teams Scheduler', icon: <CalendarPlus className="h-4 w-4" /> },
  { id: 14, label: 'KT Tracker', icon: <ClipboardList className="h-4 w-4" /> },
  { id: 15, label: 'Dashboard / Analytics', icon: <ChartNoAxesCombined className="h-4 w-4" /> },
];

interface StepperProps {
  currentStep: number;
  onSelectStep: (stepId: number) => void;
  maxStepUnlocked?: number;
}

export const Stepper: React.FC<StepperProps> = ({ currentStep, onSelectStep, maxStepUnlocked = 15 }) => {
  return (
    <div className="bg-white border-b border-slate-200 shadow-sm sticky top-16 z-40">
      <div className="max-w-7xl mx-auto px-4 overflow-x-auto py-2.5">
        <div className="flex items-center space-x-1 min-w-max">
          {STEPS.map((step, idx) => {
            const isActive = currentStep === step.id;
            const isCompleted = currentStep > step.id;
            const isSelectable = step.id <= maxStepUnlocked;

            return (
              <React.Fragment key={step.id}>
                <button
                  onClick={() => isSelectable && onSelectStep(step.id)}
                  disabled={!isSelectable}
                  className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-sky-600 text-white shadow-sm ring-2 ring-sky-600/30'
                      : isCompleted
                      ? 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                      : 'text-slate-400 hover:text-slate-600 cursor-not-allowed opacity-75'
                  }`}
                >
                  <span className={`${isActive ? 'text-white' : isCompleted ? 'text-sky-600' : 'text-slate-400'}`}>
                    {step.icon}
                  </span>
                  <span>{step.id}. {step.label}</span>
                </button>
                {idx < STEPS.length - 1 && (
                  <div className="w-2 h-px bg-slate-200"></div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
};

