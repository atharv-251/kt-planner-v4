import React, { lazy, Suspense, useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Stepper } from './components/Stepper';
import { Page1_FileUpload } from './components/pages/Page1_FileUpload';
import { Page2_ProfileReview } from './components/pages/Page2_ProfileReview';
import { Page3_Settings } from './components/pages/Page3_Settings';
import { Page4_Stakeholders } from './components/pages/Page4_Stakeholders';
import { Page5_KnowledgeHierarchy } from './components/pages/Page5_KnowledgeHierarchy';
import { Page6_KTLevelMatrix } from './components/pages/Page6_KTLevelMatrix';
import { Page7_CapacityPlanner } from './components/pages/Page7_CapacityPlanner';
import { Page8_SessionReview } from './components/pages/Page8_SessionReview';
import { Page9_AvailabilityConflict } from './components/pages/Page9_AvailabilityConflict';
import { Page10_ScheduleBuilder } from './components/pages/Page10_ScheduleBuilder';
import { Page11_ValidationApproval } from './components/pages/Page11_ValidationApproval';
import { Page12_PublishDeliver } from './components/pages/Page12_PublishDeliver';
import { Page13_TeamsKTScheduler } from './components/pages/Page13_TeamsKTScheduler';
import { Page14_KTTracker } from './components/pages/Page14_KTTracker';
import { PlusCircle, Layers } from 'lucide-react';
import { api } from './api/client';

const Page15_Analytics = lazy(() => import('./components/pages/Page15_Analytics').then((module) => ({ default: module.Page15_Analytics })));

export function App() {
  const [transitions, setTransitions] = useState<any[]>([]);
  const [activeTransition, setActiveTransition] = useState<any>(null);
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTransName, setNewTransName] = useState('Test Application Name KT');

  const loadTransitions = async () => {
    setLoading(true);
    try {
      const list = await api.listTransitions();
      setTransitions(list);
      if (list.length > 0 && !activeTransition) {
        setActiveTransition(list[0]);
      } else if (activeTransition) {
        const updated = list.find((t) => t.id === activeTransition.id);
        if (updated) setActiveTransition(updated);
      }
    } catch (err) {
      console.error('Failed to load transitions', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTransitions();
  }, []);

  const handleCreateTransition = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const created = await api.createTransition({
        name: newTransName,
        category: 'development_and_ams',
        start_date: '2026-09-20',
        end_date: '2026-10-30',
        total_duration_days: 60,
        shadow_days: 10,
        reverse_shadow_days: 10,
        daily_kt_hours: 5.0,
        primary_country: 'India',
      });
      setShowCreateModal(false);
      await loadTransitions();
      setActiveTransition(created);
      setCurrentStep(1);
    } catch (err: any) {
      alert(err.message);
    }
  };

  const renderActivePage = () => {
    if (!activeTransition) {
      return (
        <div className="text-center py-24">
          <Layers className="h-16 w-16 text-slate-300 mx-auto mb-4" />
          <h2 className="text-lg font-bold text-slate-700">No Active Transition Project</h2>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-6">
            Create a transition shell to begin uploading transition workbooks and extracting knowledge.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2.5 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold shadow"
          >
            Create Transition Shell
          </button>
        </div>
      );
    }

    switch (currentStep) {
      case 1:
        return <Page1_FileUpload transition={activeTransition} onNext={() => setCurrentStep(2)} onRefresh={loadTransitions} />;
      case 2:
        return <Page2_ProfileReview transition={activeTransition} onNext={() => setCurrentStep(3)} onRefresh={loadTransitions} />;
      case 3:
        return <Page3_Settings transition={activeTransition} onNext={() => setCurrentStep(4)} onRefresh={loadTransitions} />;
      case 4:
        return <Page4_Stakeholders transition={activeTransition} onNext={() => setCurrentStep(5)} onRefresh={loadTransitions} />;
      case 5:
        return <Page5_KnowledgeHierarchy transition={activeTransition} onNext={() => setCurrentStep(6)} onRefresh={loadTransitions} />;
      case 6:
        return <Page6_KTLevelMatrix transition={activeTransition} onNext={() => setCurrentStep(7)} onRefresh={loadTransitions} />;
      case 7:
        return <Page7_CapacityPlanner transition={activeTransition} onNext={() => setCurrentStep(8)} onRefresh={loadTransitions} />;
      case 8:
        return <Page8_SessionReview transition={activeTransition} onNext={() => setCurrentStep(9)} onRefresh={loadTransitions} />;
      case 9:
        return <Page9_AvailabilityConflict transition={activeTransition} onNext={() => setCurrentStep(10)} onRefresh={loadTransitions} />;
      case 10:
        return <Page10_ScheduleBuilder transition={activeTransition} onNext={() => setCurrentStep(11)} onRefresh={loadTransitions} />;
      case 11:
        return <Page11_ValidationApproval transition={activeTransition} onNext={() => setCurrentStep(12)} onRefresh={loadTransitions} />;
      case 12:
        return <Page12_PublishDeliver transition={activeTransition} onRefresh={loadTransitions} />;
      case 13:
        return <Page13_TeamsKTScheduler transition={activeTransition} />;
      case 14:
        return <Page14_KTTracker transition={activeTransition} />;
      case 15:
        return <Suspense fallback={<p role="status">Loading analytics...</p>}><Page15_Analytics key={activeTransition.id} transition={activeTransition} onNavigate={setCurrentStep} /></Suspense>;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-100">
      <Navbar
        transition={activeTransition}
        currentStep={currentStep}
        onRefresh={loadTransitions}
        loading={loading}
      />

      {/* Transition Selector Bar */}
      <div className="bg-slate-800 text-slate-300 px-4 py-2 border-b border-slate-700 text-xs">
        <div className="max-w-7xl mx-auto flex flex-wrap gap-2 items-center justify-between">
          <div className="flex min-w-0 max-w-full items-center space-x-2">
            <span className="text-slate-400 shrink-0">Select Transition:</span>
            <select
              value={activeTransition?.id || ''}
              onChange={(e) => {
                const sel = transitions.find((t) => t.id === e.target.value);
                if (sel) setActiveTransition(sel);
              }}
              className="min-w-0 bg-slate-700 text-white text-xs rounded px-2 py-1 border border-slate-600 focus:outline-none"
            >
              {transitions.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} ({t.status})
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center space-x-1 text-sky-400 hover:text-sky-300 font-semibold"
          >
            <PlusCircle className="h-4 w-4" />
            <span>New Transition Shell</span>
          </button>
        </div>
      </div>

      <Stepper
        currentStep={currentStep}
        onSelectStep={(s) => setCurrentStep(s)}
      />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6">
        {renderActivePage()}
      </main>

      {/* Create Transition Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 border border-slate-200 text-xs">
            <h3 className="text-sm font-bold text-slate-900 mb-4">Create New Transition Shell</h3>
            <form onSubmit={handleCreateTransition} className="space-y-4">
              <div>
                <label className="block text-slate-700 font-semibold mb-1">Transition Project Name</label>
                <input
                  type="text"
                  required
                  value={newTransName}
                  onChange={(e) => setNewTransName(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none"
                />
              </div>
              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 border border-slate-200 rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg font-semibold"
                >
                  Create Shell
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;

