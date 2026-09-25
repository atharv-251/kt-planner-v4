import React, { useEffect, useRef, useState } from 'react';
import { ArrowRight, Check, Clock3, FileText, Loader2, RefreshCw, Save, Search, Sparkles, UploadCloud, Users, X } from 'lucide-react';
import { api } from '../../api/client';

interface Excerpt { text: string; speaker: string; start: string; end: string }
interface Transcript { id: string; file_name: string; uploaded_at: string }
interface MeetingDetails {
  speakers: string[]; duration_minutes: number; highlights: Excerpt[]; questions: Excerpt[];
  actions: Excerpt[]; concerns: Excerpt[]; documents_mentioned: Excerpt[];
  excerpt_totals?: Record<string, number>;
}
interface Meeting extends MeetingDetails { transcript: Transcript; meeting_date: string }
interface Activity {
  id: string; activity_name: string; scheduled_date: string; status: string; progress_percent: number;
  blocker: string; risk: string; notes: string; planned_hours: number;
  manual_evidence: Record<string, any>;
  transcript_analysis: { meeting_reviews?: Record<string, Meeting> } | null;
}
interface Candidate { id: string; activity_name: string; scheduled_date: string; suggested: boolean; same_day: boolean; reason: string }
interface AIFinding {
  kind: 'risk' | 'open_issue'; priority: 'high' | 'medium' | 'low'; status: 'open' | 'uncertain';
  title: string; detail: string; next_call_question: string; suggested_action: string; evidence: Excerpt[];
}
interface AIAssessment { summary: string; findings: AIFinding[]; analyzed_at: string; source: 'ai' }
interface Review { transcript: Transcript; meeting_date: string; details: MeetingDetails; activities: Candidate[]; ai_analysis?: AIAssessment | null }

const inputStyle = 'w-full min-w-0 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500';
const primaryStyle = 'inline-flex items-center justify-center gap-2 rounded-md bg-teal-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50';
const today = () => {
  const current = new Date();
  return `${current.getFullYear()}-${String(current.getMonth() + 1).padStart(2, '0')}-${String(current.getDate()).padStart(2, '0')}`;
};
const labelStatus = (status: string) => status.replace(/_/g, ' ');
const delayed = (activity: Activity) => activity.scheduled_date < today() && !['completed', 'cancelled'].includes(activity.status);

export const Page14_KTTracker: React.FC<{ transition: any }> = ({ transition }) => transition
  ? <TrackerWorkspace key={transition.id} transitionId={transition.id} />
  : <p className="p-6 text-sm text-slate-500">No transition selected.</p>;

function TrackerWorkspace({ transitionId }: { transitionId: string }) {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [transcripts, setTranscripts] = useState<Transcript[]>([]);
  const [meetingDate, setMeetingDate] = useState(today);
  const [file, setFile] = useState<File | null>(null);
  const [existingId, setExistingId] = useState('');
  const [review, setReview] = useState<Review | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [tab, setTab] = useState<'meetings' | 'activities'>('meetings');
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('all');
  const [matchQuery, setMatchQuery] = useState('');
  const [showAll, setShowAll] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const active = useRef(true);

  const refresh = async () => {
    const [tracker, documents] = await Promise.all([api.getKTTracker(transitionId), api.getTeamsTranscripts(transitionId)]);
    if (!active.current) return;
    setActivities(tracker.activities);
    setTranscripts(documents.transcripts);
  };

  useEffect(() => {
    active.current = true;
    setBusy('Loading');
    refresh().catch((failure) => { if (active.current) setError(failure.message); })
      .finally(() => { if (active.current) setBusy(''); });
    return () => { active.current = false; };
  }, [transitionId]);

  const perform = async (name: string, action: () => Promise<void>) => {
    setBusy(name); setError(''); setNotice('');
    try { await action(); }
    catch (failure) { if (active.current) setError(failure instanceof Error ? failure.message : 'Request failed. Please retry.'); }
    finally { if (active.current) setBusy(''); }
  };

  const preview = async (documentId: string, date: string) => {
    const result: Review = await api.reviewKTMeeting(transitionId, documentId, date);
    if (!active.current) return;
    setReview(result);
    const linked = activities.filter((activity) => activity.transcript_analysis?.meeting_reviews?.[documentId]).map((activity) => activity.id);
    setSelectedIds(linked.length ? linked : result.activities.filter((activity) => activity.same_day).map((activity) => activity.id));
    setMatchQuery(''); setShowAll(!!linked.length);
  };

  const readTranscript = () => perform('Reading transcript', async () => {
    let documentId = existingId;
    if (file) {
      const uploaded = await api.uploadTeamsTranscript(transitionId, file);
      documentId = uploaded.transcript.id;
      if (!active.current) return;
      setExistingId(documentId); setFile(null);
      if (fileInput.current) fileInput.current.value = '';
      await refresh();
    }
    await preview(documentId, meetingDate);
  });

  const confirm = () => review && perform('Saving meeting', async () => {
    await api.confirmKTMeeting(transitionId, review.transcript.id, review.meeting_date, selectedIds);
    await refresh();
    if (!active.current) return;
    setNotice(`Meeting saved to ${selectedIds.length} ${selectedIds.length === 1 ? 'activity' : 'activities'}.`);
    setReview(null); setExistingId('');
  });

  const meetings = Object.values(activities.reduce<Record<string, Meeting>>((result, activity) => ({
    ...result, ...(activity.transcript_analysis?.meeting_reviews || {}),
  }), {})).sort((first, second) => second.meeting_date.localeCompare(first.meeting_date));
  const visibleActivities = activities.filter((activity) => activity.activity_name.toLowerCase().includes(query.toLowerCase()) && (
    filter === 'all' || (filter === 'delayed' ? delayed(activity) : filter === 'pending' ? !['completed', 'cancelled'].includes(activity.status) : activity.status === filter)
  ));
  const candidates = review?.activities.filter((activity) => (showAll || activity.suggested || selectedIds.includes(activity.id) || matchQuery) && activity.activity_name.toLowerCase().includes(matchQuery.toLowerCase())) || [];

  return <div className="min-w-0 bg-white text-slate-900">
    <header className="border-b border-slate-200 px-5 py-5 sm:px-7">
      <div className="flex items-center justify-between gap-3">
        <div><p className="text-xs font-semibold uppercase text-teal-700">Stage 14: Knowledge transfer</p><h2 className="mt-1 text-xl font-bold">KT Tracker</h2></div>
        <button type="button" aria-label="Refresh tracker" title="Refresh tracker" disabled={!!busy} onClick={() => perform('Refreshing', refresh)} className="rounded-md border border-slate-200 p-2 hover:bg-slate-50 disabled:opacity-50"><RefreshCw className={`h-4 w-4 ${busy === 'Refreshing' ? 'animate-spin' : ''}`} /></button>
      </div>
      <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-500">
        <span><strong className="text-slate-900">{activities.filter((activity) => activity.status === 'completed').length}/{activities.length}</strong> completed</span>
        <span><strong className="text-amber-700">{activities.filter(delayed).length}</strong> delayed</span>
        <span><strong className="text-teal-700">{meetings.length}</strong> meetings reviewed</span>
      </div>
    </header>

    <section className="border-b border-slate-200 bg-slate-50/70 px-5 py-5 sm:px-7">
      <h3 className="mb-3 text-sm font-semibold">New meeting</h3>
      <fieldset disabled={!!busy || !!review} className="grid min-w-0 items-end gap-4 md:grid-cols-[170px_minmax(0,1fr)_auto] disabled:opacity-60">
        <label className="grid gap-1.5 text-xs font-medium">Meeting date<input aria-label="Meeting date" type="date" required value={meetingDate} onChange={(event) => setMeetingDate(event.target.value)} className={inputStyle} /></label>
        <label className="grid min-w-0 gap-1.5 text-xs font-medium">Teams transcript (.vtt)<input ref={fileInput} aria-label="Teams transcript" type="file" accept=".vtt,text/vtt" onChange={(event) => { setFile(event.target.files?.[0] || null); setExistingId(''); }} className="block w-full min-w-0 text-sm text-slate-600 file:mr-3 file:rounded-md file:border file:border-slate-300 file:bg-white file:px-3 file:py-2 file:text-sm file:text-slate-800" /></label>
        <button type="button" disabled={(!file && !existingId) || !meetingDate || !!busy || !!review} onClick={readTranscript} className={primaryStyle}><UploadCloud className="h-4 w-4" />Read transcript</button>
      </fieldset>
      {transcripts.length > 0 && !review && <details className="mt-3 text-xs text-slate-600"><summary className="w-fit cursor-pointer py-1">Previously uploaded transcripts ({transcripts.length})</summary><select aria-label="Previously uploaded transcript" disabled={!!busy} value={existingId} onChange={(event) => { setExistingId(event.target.value); setFile(null); if (fileInput.current) fileInput.current.value = ''; }} className={`${inputStyle} mt-2 max-w-xl`}><option value="">Choose a transcript</option>{transcripts.map((transcript) => <option key={transcript.id} value={transcript.id}>{transcript.file_name} ({new Date(transcript.uploaded_at).toLocaleString()})</option>)}</select></details>}
    </section>

    <div aria-live="polite" className="px-5 sm:px-7">
      {busy && <p role="status" className="flex items-center gap-2 py-3 text-sm text-teal-700"><Loader2 className="h-4 w-4 animate-spin" />{busy}...</p>}
      {error && <p role="alert" className="my-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800 break-words">{error}</p>}
      {notice && <p role="status" className="flex items-center gap-2 py-3 text-sm text-teal-700"><Check className="h-4 w-4" />{notice}</p>}
    </div>

    {review ? <section className="px-5 py-5 sm:px-7">
      <div className="flex items-start justify-between gap-3"><div className="min-w-0"><p className="text-xs font-semibold text-teal-700">REVIEW MEETING / {review.meeting_date}</p><h3 className="mt-1 break-words text-base font-semibold">{review.transcript.file_name}</h3></div><button disabled={!!busy} title="Close review" aria-label="Close review" onClick={() => setReview(null)} className="p-2"><X className="h-4 w-4" /></button></div>
      <MeetingContent details={review.details} />
      <MeetingAIAnalysis key={review.transcript.id} transitionId={transitionId} documentId={review.transcript.id} initial={review.ai_analysis} disabled={!!busy} />
      <div className="mt-6 border-t border-slate-200 pt-5">
        <h3 className="text-sm font-semibold">Activities to update <span className="ml-2 font-normal text-slate-500">{selectedIds.length} selected</span></h3>
        <div className="my-3 flex flex-wrap items-center gap-3"><input aria-label="Find an activity to link" type="search" value={matchQuery} onChange={(event) => setMatchQuery(event.target.value)} className={`${inputStyle} max-w-sm`} placeholder="Find an activity" /><label className="flex items-center gap-2 text-xs text-slate-600"><input type="checkbox" checked={showAll} onChange={(event) => setShowAll(event.target.checked)} />All scheduled activities</label></div>
        <div className="max-h-64 overflow-y-auto divide-y divide-slate-100 border-y border-slate-200">
          {candidates.map((activity) => <label key={activity.id} className="flex cursor-pointer items-start gap-3 py-3 pr-2 text-sm hover:bg-slate-50"><input type="checkbox" disabled={!!busy} checked={selectedIds.includes(activity.id)} onChange={(event) => setSelectedIds((current) => event.target.checked ? [...current, activity.id] : current.filter((id) => id !== activity.id))} className="mt-1 accent-teal-700" /><span className="min-w-0"><span className="block break-words font-medium">{activity.activity_name}</span><span className="mt-1 block text-xs text-slate-500">{activity.scheduled_date} / {activity.reason}</span></span></label>)}
          {!candidates.length && <p className="py-5 text-sm text-slate-500">No suggested matches for this day.</p>}
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3"><p className="text-xs text-slate-500">Planned activities become in progress. Completion and acceptance remain unchanged.</p><button disabled={!!busy || !selectedIds.length} onClick={confirm} className={primaryStyle}><Check className="h-4 w-4" />Confirm meeting</button></div>
      </div>
    </section> : <section className="px-5 py-5 sm:px-7">
      <div role="tablist" aria-label="Tracker views" className="flex gap-6 border-b border-slate-200">
        {(['meetings', 'activities'] as const).map((view) => <button key={view} role="tab" aria-selected={tab === view} onClick={() => setTab(view)} className={`border-b-2 pb-3 text-sm font-semibold capitalize ${tab === view ? 'border-teal-700 text-teal-800' : 'border-transparent text-slate-500'}`}>{view} <span className="ml-1 font-normal">{view === 'meetings' ? meetings.length : activities.length}</span></button>)}
      </div>
      {tab === 'meetings' ? <div className="divide-y divide-slate-200">
        {!meetings.length && !busy && <div className="flex items-center gap-3 py-10 text-slate-500"><FileText className="h-8 w-8 text-teal-600" /><div><p className="text-sm font-medium text-slate-700">No reviewed meetings yet</p><p className="mt-1 text-xs">{transcripts.length} uploaded transcripts available</p></div></div>}
        {meetings.map((meeting) => <details key={meeting.transcript.id} className="py-4"><summary className="cursor-pointer text-sm"><span className="ml-2 break-words font-semibold">{meeting.transcript.file_name}</span><span className="mt-1 block pl-5 text-xs text-slate-500">{meeting.meeting_date} / {meeting.duration_minutes} min / {meeting.speakers.length} speakers</span></summary><MeetingContent details={meeting} /><MeetingAIAnalysis transitionId={transitionId} documentId={meeting.transcript.id} disabled={!!busy} /><p className="mt-4 text-xs text-slate-500">Linked activities: {activities.filter((activity) => activity.transcript_analysis?.meeting_reviews?.[meeting.transcript.id]).map((activity) => activity.activity_name).join('; ')}</p><button disabled={!!busy} onClick={() => perform('Opening review', () => preview(meeting.transcript.id, meeting.meeting_date))} className="mt-3 inline-flex items-center gap-2 text-xs font-semibold text-teal-700">Review activity links<ArrowRight className="h-3 w-3" /></button></details>)}
      </div> : <div>
        <div className="my-4 flex flex-col gap-3 sm:flex-row"><label className="relative min-w-0 flex-1"><Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" /><input aria-label="Search activities" type="search" placeholder="Search activities" value={query} onChange={(event) => setQuery(event.target.value)} className={`${inputStyle} pl-9`} /></label><select aria-label="Filter activities" value={filter} onChange={(event) => setFilter(event.target.value)} className={`${inputStyle} sm:w-44`}><option value="all">All activities</option><option value="planned">Planned</option><option value="pending">Pending</option><option value="delayed">Delayed</option><option value="completed">Completed</option></select></div>
        <div className="divide-y divide-slate-200">{visibleActivities.map((activity) => <details key={activity.id} className="py-3"><summary className="cursor-pointer text-sm"><span className="ml-2 break-words font-medium">{activity.activity_name}</span><span className="mt-1 flex flex-wrap gap-x-4 gap-y-1 pl-5 text-xs text-slate-500"><span>{activity.scheduled_date}</span><span className={delayed(activity) ? 'text-amber-700' : 'capitalize'}>{delayed(activity) ? 'Delayed' : labelStatus(activity.status)}</span><span>{Object.keys(activity.transcript_analysis?.meeting_reviews || {}).length} meetings</span></span></summary><ActivityDetails activity={activity} busy={!!busy} onSave={(payload) => perform('Saving activity', async () => { await api.updateKTTrackerActivity(transitionId, activity.id, payload); await refresh(); if (active.current) setNotice('Activity updated.'); })} /></details>)}</div>
        {!visibleActivities.length && !busy && <p className="py-8 text-sm text-slate-500">No activities found.</p>}
      </div>}
    </section>}
  </div>;
}

function MeetingAIAnalysis({ transitionId, documentId, initial, disabled }: {
  transitionId: string; documentId: string; initial?: AIAssessment | null; disabled: boolean;
}) {
  const [assessment, setAssessment] = useState<AIAssessment | null>(initial || null);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState('');
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const analyze = async () => {
    setAnalyzing(true); setError('');
    try {
      const result = await api.analyzeKTMeetingFollowups(transitionId, documentId, !!assessment);
      if (mounted.current) setAssessment(result);
    } catch (failure) {
      if (mounted.current) setError(failure instanceof Error ? failure.message : 'AI analysis failed. Please retry.');
    } finally { if (mounted.current) setAnalyzing(false); }
  };
  return <section aria-label="AI follow-up analysis" className="mt-5 border-y border-teal-200 bg-teal-50/40 px-3 py-4 sm:px-4">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h4 className="text-sm font-semibold text-teal-950">Risks & next-call agenda</h4>
      <button type="button" onClick={analyze} disabled={disabled || analyzing} title="Analyze this transcript using the configured AI provider" className={primaryStyle}>
        {analyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
        {analyzing ? 'Analyzing...' : assessment ? 'Run again' : 'AI analysis'}
      </button>
    </div>
    {analyzing && <p role="status" className="mt-3 text-xs text-teal-800">Reviewing the full transcript for risks and unresolved issues...</p>}
    {error && <p role="alert" className="mt-3 break-words text-sm text-red-700">{error}</p>}
    {assessment && <div className="mt-4">
      <p className="text-sm leading-relaxed text-slate-700">{assessment.summary}</p>
      <p className="mt-2 text-xs text-slate-500">AI assessment / {new Date(assessment.analyzed_at).toLocaleString()} / Pending human review</p>
      {!assessment.findings.length ? <p className="mt-4 text-sm text-slate-600">No supported follow-ups identified. This is not a readiness or acceptance sign-off.</p> : <>
        <div className="mt-4 divide-y divide-teal-100">
          {[...assessment.findings].sort((first, second) => ['high', 'medium', 'low'].indexOf(first.priority) - ['high', 'medium', 'low'].indexOf(second.priority)).map((finding, index) => <details key={index} className="py-3">
            <summary className="cursor-pointer text-sm font-semibold"><span className={`mr-2 text-xs uppercase ${finding.priority === 'high' ? 'text-red-700' : finding.priority === 'medium' ? 'text-amber-700' : 'text-slate-600'}`}>{finding.priority}</span>{finding.title}<span className="mt-1 block pl-5 text-xs font-normal text-slate-500">{finding.kind === 'risk' ? 'Risk' : 'Open issue'} / {finding.status === 'uncertain' ? 'Resolution unclear' : 'Reported open'}</span></summary>
            <p className="mt-3 text-sm text-slate-700">{finding.detail}</p><Excerpts items={finding.evidence} />
          </details>)}
        </div>
        <h5 className="mt-5 text-sm font-semibold text-teal-950">Proposed next-call agenda</h5>
        <ol className="mt-3 list-decimal space-y-4 pl-5 text-sm">{assessment.findings.map((finding, index) => <li key={index} className="pl-1"><p className="font-medium text-slate-800">{finding.next_call_question}</p><p className="mt-1 text-xs leading-relaxed text-slate-600">{finding.suggested_action}</p></li>)}</ol>
      </>}
    </div>}
  </section>;
}

function MeetingContent({ details }: { details: MeetingDetails }) {
  return <div className="mt-4 min-w-0">
    <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-600"><span className="inline-flex items-center gap-2"><Clock3 className="h-4 w-4" />{details.duration_minutes} min transcript span (estimate)</span><span className="inline-flex items-center gap-2"><Users className="h-4 w-4" />{details.speakers.length} speakers heard</span></div>
    <h4 className="mt-5 text-sm font-semibold">Discussion highlights</h4>
    <Excerpts items={details.highlights} />
    <div className="mt-4 divide-y divide-slate-200 border-y border-slate-200">
      <details className="py-3 text-sm"><summary className="cursor-pointer font-medium">Speakers ({details.speakers.length})</summary><ul className="mt-2 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">{details.speakers.map((speaker) => <li key={speaker}>{speaker}</li>)}</ul></details>
      <EvidenceSection label="Follow-up statements" items={details.actions} total={details.excerpt_totals?.actions} />
      <EvidenceSection label="Questions raised" items={details.questions} total={details.excerpt_totals?.questions} />
      <EvidenceSection label="Potential concerns" items={details.concerns} total={details.excerpt_totals?.concerns} />
      <EvidenceSection label="Documents mentioned" items={details.documents_mentioned} total={details.excerpt_totals?.documents_mentioned} />
    </div>
  </div>;
}

function EvidenceSection({ label, items, total = items.length }: { label: string; items: Excerpt[]; total?: number }) {
  return <details className="py-3 text-sm"><summary className="cursor-pointer font-medium">{label} <span className="ml-1 text-slate-400">{total}</span></summary>{total > items.length && <p className="mt-2 text-xs text-slate-500">First {items.length} excerpts of {total}</p>}<Excerpts items={items} /></details>;
}

function Excerpts({ items }: { items: Excerpt[] }) {
  return items.length ? <ul className="mt-3 max-h-80 space-y-4 overflow-y-auto pr-2">{items.map((item, index) => <li key={`${item.start}-${index}`} className="border-l-2 border-teal-200 pl-3"><p className="break-words text-sm leading-relaxed text-slate-700">{item.text}</p><p className="mt-1 text-xs text-slate-500">{item.start} - {item.end} / {item.speaker || 'Unknown speaker'}</p></li>)}</ul> : <p className="py-3 text-xs text-slate-500">None identified in the transcript.</p>;
}

function ActivityDetails({ activity, busy, onSave }: { activity: Activity; busy: boolean; onSave: (payload: any) => Promise<void> }) {
  const evidence = activity.manual_evidence || {};
  const [status, setStatus] = useState(activity.status);
  const [notes, setNotes] = useState(evidence.session_notes || activity.notes || '');
  const [readiness, setReadiness] = useState(evidence.readiness || 'not_assessed');
  const [accepted, setAccepted] = useState(!!evidence.final_acceptance);
  const [shadowing, setShadowing] = useState(!!evidence.shadowing_completed);
  const [reverseShadowing, setReverseShadowing] = useState(!!evidence.reverse_shadowing_completed);
  useEffect(() => { setStatus(activity.status); }, [activity.status]);
  return <div className="mt-4 pl-5">
    <dl className="grid gap-2 text-xs text-slate-600 sm:grid-cols-2"><div><dt className="font-semibold">Planned / recorded hours</dt><dd>{activity.planned_hours} / {evidence.actual_hours ?? 'Not recorded'}</dd></div><div><dt className="font-semibold">Recorded attendees</dt><dd className="break-words">{evidence.attendees?.join('; ') || 'Not recorded'}</dd></div>{activity.blocker && <div><dt className="font-semibold">Blocker</dt><dd>{activity.blocker}</dd></div>}{activity.risk && <div><dt className="font-semibold">Risk</dt><dd>{activity.risk}</dd></div>}{evidence.open_questions?.length > 0 && <div><dt className="font-semibold">Open questions</dt><dd>{evidence.open_questions.join('; ')}</dd></div>}{evidence.documents_delivered?.length > 0 && <div><dt className="font-semibold">Delivered documents</dt><dd>{evidence.documents_delivered.join('; ')}</dd></div>}</dl>
    {Object.values(activity.transcript_analysis?.meeting_reviews || {}).map((meeting) => <details key={meeting.transcript.id} className="mt-4 border-t border-slate-200 pt-3"><summary className="cursor-pointer break-words text-xs font-semibold">{meeting.meeting_date} / {meeting.transcript.file_name}</summary><MeetingContent details={meeting} /></details>)}
    <details className="mt-4 border-t border-slate-200 pt-3"><summary className="cursor-pointer text-xs font-semibold text-teal-700">Corrections & sign-off</summary><form onSubmit={(event) => { event.preventDefault(); onSave({ status, session_notes: notes, readiness, final_acceptance: accepted, shadowing_completed: shadowing, reverse_shadowing_completed: reverseShadowing }); }}><fieldset disabled={busy} className="mt-4 space-y-3"><div className="grid gap-3 sm:grid-cols-2"><label className="grid gap-1 text-xs">Status<select value={status} onChange={(event) => setStatus(event.target.value)} className={inputStyle}>{['planned', 'in_progress', 'completed', 'on_hold', 'cancelled'].map((value) => <option key={value} value={value}>{labelStatus(value)}</option>)}</select></label><label className="grid gap-1 text-xs">Readiness<select value={readiness} onChange={(event) => setReadiness(event.target.value)} className={inputStyle}>{['not_assessed', 'not_ready', 'partially_ready', 'ready', 'accepted'].map((value) => <option key={value} value={value}>{labelStatus(value)}</option>)}</select></label></div><label className="grid gap-1 text-xs">Notes<textarea rows={3} maxLength={4000} value={notes} onChange={(event) => setNotes(event.target.value)} className={inputStyle} /></label><div className="flex flex-wrap gap-4 text-xs"><label className="flex items-center gap-2"><input type="checkbox" checked={shadowing} onChange={(event) => setShadowing(event.target.checked)} />Shadowing complete</label><label className="flex items-center gap-2"><input type="checkbox" checked={reverseShadowing} onChange={(event) => setReverseShadowing(event.target.checked)} />Reverse-shadowing complete</label><label className="flex items-center gap-2"><input type="checkbox" checked={accepted} onChange={(event) => setAccepted(event.target.checked)} />Final acceptance received</label></div><button type="submit" className={primaryStyle}><Save className="h-4 w-4" />Save changes</button></fieldset></form></details>
  </div>;
}