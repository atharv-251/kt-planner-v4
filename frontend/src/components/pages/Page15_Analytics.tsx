import { useEffect, useState } from 'react';
import { Activity, AlertTriangle, ArrowUpRight, ChevronLeft, ChevronRight, Download, Filter, Info, RefreshCw, RotateCcw, Search, ShieldCheck } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api, AnalyticsFinding, AnalyticsSession, AnalyticsSnapshot } from '../../api/client';
import './analytics.css';

const EMPTY_FILTERS = { start_date: '', end_date: '', domain: '', level: '', sme_id: '', receiver_id: '', status: '' };
const STATUS_COLORS: Record<string, string> = { completed: '#0d9488', in_progress: '#0284c7', planned: '#94a3b8', on_hold: '#e11d48' };
const label = (value: string) => value.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
const number = (value: number | null, suffix = '') => value === null ? 'N/A' : `${value.toLocaleString(undefined, { maximumFractionDigits: 1 })}${suffix}`;

function exportSessions(sessions: AnalyticsSession[], transitionName: string) {
  const fields: (keyof AnalyticsSession)[] = ['title', 'date', 'domain', 'level', 'sme', 'receiver', 'status', 'progress', 'hours', 'actual_hours', 'accepted', 'blocker', 'risk'];
  const cell = (value: unknown) => {
    const text = String(value ?? '');
    return `"${(/^[\s]*[=+@-]/.test(text) ? "'" + text : text).replace(/"/g, '""')}"`;
  };
  const csv = [fields.map(cell).join(','), ...sessions.map((session) => fields.map((field) => cell(session[field])).join(','))].join('\r\n');
  const url = URL.createObjectURL(new Blob(['\uFEFF', csv], { type: 'text/csv;charset=utf-8;' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = `${transitionName.replace(/[^a-z0-9_-]/gi, '_')}-analytics.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

export function Page15_Analytics({ transition, onNavigate }: { transition: { id: string; name: string }; onNavigate: (step: number) => void }) {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [data, setData] = useState<AnalyticsSnapshot | null>(null);
  const [options, setOptions] = useState<AnalyticsSnapshot['options'] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  const [scope, setScope] = useState<'sessions' | 'transition'>('sessions');
  const [severity, setSeverity] = useState('');
  const [source, setSource] = useState('');
  const [search, setSearch] = useState('');
  const [riskPage, setRiskPage] = useState(0);
  const [sessionPage, setSessionPage] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    setRiskPage(0);
    setSessionPage(0);
    if (filters.start_date && filters.end_date && filters.start_date > filters.end_date) {
      setError('Start date must be on or before end date.');
      setLoading(false);
      return () => controller.abort();
    }
    api.getAnalytics(transition.id, filters, controller.signal).then((snapshot) => {
      if (!controller.signal.aborted) { setData(snapshot); setOptions(snapshot.options); }
    }).catch((failure) => {
      if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : 'Unable to load analytics.');
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [transition.id, filters, revision]);

  const selectFilter = (key: keyof typeof EMPTY_FILTERS, value: string) => setFilters((previous) => ({ ...previous, [key]: value }));
  const allFindings = data ? scope === 'sessions' ? data.findings : data.project_findings : [];
  const findings = allFindings.filter((item) => (!severity || item.severity === severity) && (!source || item.source === source)
    && `${item.title} ${item.detail} ${item.owner} ${item.action}`.toLowerCase().includes(search.toLowerCase()));
  const riskPages = Math.max(1, Math.ceil(findings.length / 8));
  const currentRiskPage = Math.min(riskPage, riskPages - 1);
  const sessionPages = Math.max(1, Math.ceil((data?.sessions.length || 0) / 10));
  const activeFilters = Object.values(filters).filter(Boolean).length;
  const metrics = data?.metrics;
  const filterSelect = (title: string, key: keyof typeof EMPTY_FILTERS, choices: { id: string; name: string }[]) => (
    <label className="analytics-field"><span>{title}</span><select aria-label={title} value={filters[key]} onChange={(event) => selectFilter(key, event.target.value)}>
      <option value="">All {title.toLowerCase()}s</option>{choices.map((choice) => <option value={choice.id} key={choice.id}>{choice.name}</option>)}
    </select></label>
  );

  return <div className="analytics" aria-busy={loading}>
    <header className="analytics-heading">
      <div className="min-w-0"><div className="analytics-eyebrow"><Activity size={14} /> TRANSITION INTELLIGENCE</div><h1>Executive overview</h1><p className="analytics-project">{transition.name}</p></div>
      <div className="analytics-heading-actions">
        <span className="analytics-updated">{data && !loading && !error ? `Updated ${new Date(data.generated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'Live snapshot'}</span>
        <button className="analytics-icon" title="Refresh analytics" aria-label="Refresh analytics" onClick={() => setRevision((value) => value + 1)} disabled={loading}><RefreshCw size={17} className={loading ? 'animate-spin' : ''} /></button>
        <button className="analytics-command" disabled={!data || loading || !!error || !data.sessions.length} onClick={() => data && exportSessions(data.sessions, transition.name)}><Download size={16} /> Export CSV</button>
      </div>
    </header>

    <section className="analytics-filters" aria-label="Delivery filters">
      <div className="analytics-section-heading"><h2><Filter size={15} /> Delivery scope {activeFilters > 0 && <span className="analytics-count">{activeFilters}</span>}</h2><button className="analytics-text-button" onClick={() => setFilters(EMPTY_FILTERS)} disabled={!activeFilters}><RotateCcw size={14} /> Reset filters</button></div>
      <div className="analytics-filter-grid">
        <label className="analytics-field"><span>From date</span><input aria-label="From date" type="date" value={filters.start_date} onChange={(event) => selectFilter('start_date', event.target.value)} /></label>
        <label className="analytics-field"><span>To date</span><input aria-label="To date" type="date" value={filters.end_date} onChange={(event) => selectFilter('end_date', event.target.value)} /></label>
        {filterSelect('Domain', 'domain', (options?.domains || []).map((value) => ({ id: value, name: value })))}
        {filterSelect('KT level', 'level', (options?.levels || []).map((value) => ({ id: value, name: value })))}
        {filterSelect('SME', 'sme_id', options?.smes || [])}
        {filterSelect('Receiver', 'receiver_id', options?.receivers || [])}
        {filterSelect('Status', 'status', (options?.statuses || []).map((value) => ({ id: value, name: label(value) })))}
      </div>
    </section>

    {error ? <div role="alert" className="analytics-error"><AlertTriangle size={20} /><div><h2>Analytics unavailable</h2><p>{error}</p></div><button className="analytics-command" onClick={() => setRevision((value) => value + 1)}>Retry</button></div>
      : loading ? <div role="status" className="analytics-loading"><RefreshCw size={22} className="animate-spin" /> Loading executive snapshot...</div>
      : data && metrics && <>
        <div className="analytics-scope-line"><span><span className={`analytics-dot ${metrics.health === 'Blocked' ? 'danger' : metrics.health === 'At risk' ? 'warning' : 'neutral'}`} />{metrics.health}</span><span>{metrics.total} active sessions in scope <span className="analytics-divider">/</span> As of {data.as_of} <span className="analytics-divider">/</span> {data.transition.timezone}</span></div>
        <section className="analytics-kpis" aria-label="Executive metrics">
          <Metric name="KT completion" value={number(metrics.completion_percent, '%')} detail={`${number(metrics.earned_hours)} / ${number(metrics.planned_hours)} planned hours`} color="teal" tooltip="Scheduled-hour-weighted recorded progress. Cancelled sessions excluded. N/A when planned hours are zero; not acceptance or verified hours worked." />
          <Metric name="Completed sessions" value={`${metrics.completed} / ${metrics.total}`} detail="Recorded completion status" color="blue" />
          <Metric name="Blocked activities" value={String(metrics.blocked)} detail="Blocker recorded or on hold" color="red" />
          <Metric name="Risk / issue signals" value={String(metrics.risk_findings)} detail="Recorded, derived & AI advisory" color="amber" tooltip="Separate signals may refer to the same underlying issue. AI findings remain advisory and may have been resolved since analysis." />
          <Metric name="Overdue activities" value={String(metrics.overdue)} detail="Past scheduled date, unfinished" color="amber" />
          <Metric name="Final acceptance" value={`${metrics.accepted} / ${metrics.total}`} detail="Explicit tracker sign-off" color="teal" />
        </section>

        {!metrics.total && <div className="analytics-empty"><Activity size={24} /><h2>No sessions in this scope</h2><p>{activeFilters ? 'No active sessions match the selected filters.' : 'No active KT sessions are scheduled for this transition.'}</p><button className="analytics-text-button" onClick={() => activeFilters ? setFilters(EMPTY_FILTERS) : onNavigate(10)}>{activeFilters ? 'Reset filters' : 'Open schedule'}<ArrowUpRight size={15} /></button></div>}

        {metrics.total > 0 && <>
          <div className="analytics-chart-grid">
            <section className="analytics-chart-section" aria-label="Session status chart">
              <div className="analytics-section-heading"><h2>Session status</h2><span className="analytics-muted">{metrics.total} sessions</span></div>
              <div className="analytics-chart" role="img" aria-label={data.status_distribution.map((item) => `${label(item.name)}: ${item.value}`).join(', ')}>
                <ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data.status_distribution} dataKey="value" nameKey="name" innerRadius={60} outerRadius={86} paddingAngle={2} isAnimationActive={false}>
                  {data.status_distribution.map((item) => <Cell key={item.name} fill={STATUS_COLORS[item.name] || '#64748b'} />)}
                </Pie><Tooltip formatter={(value, name) => [value, label(String(name))]} /></PieChart></ResponsiveContainer>
              </div>
              <ul className="analytics-legend">{data.status_distribution.map((item) => <li key={item.name}><span><i style={{ background: STATUS_COLORS[item.name] || '#64748b' }} />{label(item.name)}</span><strong>{item.value}</strong></li>)}</ul>
            </section>
            <section className="analytics-chart-section analytics-delivery-chart" aria-label="Delivery by scheduled date">
              <div className="analytics-section-heading"><h2>Delivery by scheduled date</h2><span title="Current recorded progress grouped by each session's scheduled date, not a historical completion trend." aria-label="Current progress by scheduled date"><Info size={15} /></span></div>
              <p className="analytics-chart-subtitle">Planned vs progress-equivalent hours</p>
              <div className="analytics-chart analytics-chart-wide">
                <ResponsiveContainer width="100%" height="100%"><LineChart data={data.timeline} margin={{ top: 12, right: 18, left: -20, bottom: 5 }} accessibilityLayer>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" /><XAxis dataKey="date" tickFormatter={(value: string) => value.slice(5)} minTickGap={30} tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} /><Tooltip /><Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line type="linear" dataKey="planned" name="Planned hours" stroke="#94a3b8" strokeWidth={2} strokeDasharray="4 4" dot={{ r: 3 }} isAnimationActive={false} />
                  <Line type="linear" dataKey="earned" name="Progress-equivalent hours" stroke="#0d9488" strokeWidth={3} dot={{ r: 3 }} isAnimationActive={false} />
                </LineChart></ResponsiveContainer>
              </div>
            </section>
          </div>
          <section className="analytics-section" aria-label="Domain delivery">
            <div className="analytics-section-heading"><h2>Domain delivery</h2><span className="analytics-muted">Current progress / planned hours</span></div>
            <div className="analytics-domain-grid">
              <div className="analytics-domain-chart" style={{ height: Math.max(170, data.domains.length * 48) }}>
                <ResponsiveContainer width="100%" height="100%"><BarChart data={data.domains} layout="vertical" margin={{ left: 4, right: 20, bottom: 5 }} accessibilityLayer>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" tick={{ fontSize: 11 }} /><YAxis type="category" dataKey="name" width={105} tick={{ fontSize: 10 }} tickFormatter={(value: string) => value.length > 16 ? value.slice(0, 15) + '...' : value} /><Tooltip /><Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="planned" name="Planned hours" fill="#cbd5e1" barSize={10} isAnimationActive={false} /><Bar dataKey="earned" name="Progress-equivalent hours" fill="#0d9488" barSize={10} isAnimationActive={false} />
                </BarChart></ResponsiveContainer>
              </div>
              <div className="analytics-domain-list">{data.domains.map((domain) => <div key={domain.name}><div><strong>{domain.name}</strong><span>{number(domain.completion, '%')}</span></div><progress max={100} value={domain.completion || 0} aria-label={`${domain.name} completion`} /><small>{number(domain.earned)}h / {number(domain.planned)}h</small></div>)}</div>
            </div>
          </section>
          <section className="analytics-evidence-strip" aria-label="Evidence and readiness">
            <Evidence name="Transcript-linked" value={metrics.evidenced} total={metrics.total} />
            <Evidence name="Invitations recorded sent" value={metrics.invited} total={metrics.total} />
            <Evidence name="Shadowing confirmed" value={metrics.shadowing} total={metrics.total} />
            <Evidence name="Reverse shadowing confirmed" value={metrics.reverse_shadowing} total={metrics.total} />
            <div><span>Actual hours recorded</span><strong>{number(metrics.actual_hours)}h</strong><small>{metrics.untracked} sessions without tracker records</small></div>
          </section>
        </>}

        <section className="analytics-section" aria-label="Risk and mitigation register">
          <div className="analytics-section-heading"><h2><AlertTriangle size={17} /> Risks, blockers & next actions</h2><span className="analytics-muted">Suggested mitigations / human review</span></div>
          <div className="analytics-register-tools">
            <div className="analytics-segments" role="group" aria-label="Risk scope">
              <button aria-pressed={scope === 'sessions'} onClick={() => { setScope('sessions'); setSource(''); setRiskPage(0); }}>Filtered sessions <span>{data.findings.length}</span></button>
              <button aria-pressed={scope === 'transition'} onClick={() => { setScope('transition'); setSource(''); setRiskPage(0); }}>Transition-wide <span>{data.project_findings.length}</span></button>
            </div>
            <label className="analytics-search"><Search size={15} /><input aria-label="Search risks" placeholder="Search risks or actions" value={search} onChange={(event) => { setSearch(event.target.value); setRiskPage(0); }} /></label>
            <select aria-label="Risk severity" value={severity} onChange={(event) => { setSeverity(event.target.value); setRiskPage(0); }}><option value="">All severities</option>{['high', 'medium', 'low'].map((value) => <option key={value} value={value}>{label(value)}</option>)}</select>
            <select aria-label="Risk source" value={source} onChange={(event) => { setSource(event.target.value); setRiskPage(0); }}><option value="">All sources</option>{Array.from(new Set(allFindings.map((item) => item.source))).sort().map((value) => <option key={value}>{value}</option>)}</select>
          </div>
          <div className="analytics-scope-caption">{scope === 'transition' ? 'Transition-wide: profile constraints, validation checks and unlinked AI assessments. Outside delivery filters.' : 'Session-linked: recorded blockers, scheduling signals and saved AI assessments. Delivery filters applied.'}</div>
          {!findings.length ? <div className="analytics-empty compact"><ShieldCheck size={24} /><h3>No matching risk signals</h3><p>No recorded findings match this scope. This is not a readiness certification.</p></div>
            : <div className="analytics-risk-list">{findings.slice(currentRiskPage * 8, currentRiskPage * 8 + 8).map((item) => <RiskItem key={item.id} item={item} onNavigate={onNavigate} />)}</div>}
          {riskPages > 1 && <Pager page={currentRiskPage} pages={riskPages} total={findings.length} onChange={setRiskPage} name="risks" />}
        </section>

        <section className="analytics-section" aria-label="Transition-wide readiness">
          <div className="analytics-section-heading"><h2><ShieldCheck size={17} /> Transition readiness</h2><span className="analytics-muted">All 14 stages / outside delivery filters</span></div>
          <div className="analytics-capacity-band"><div><span>Curriculum allocation</span><strong>{number(data.capacity.generated_hours)}h</strong></div><div><span>Transition target</span><strong>{number(data.capacity.target_capacity_hours)}h</strong></div><div><span>Capacity gap</span><strong>{number(data.capacity.gap_hours)}h</strong></div><p>{data.capacity.recommendation}</p></div>
          <div className="analytics-stage-grid">{data.stages.map((stage) => <button className="analytics-stage" key={stage.step} onClick={() => onNavigate(stage.step)} title={`Open ${stage.name}`}>
            <span className={`analytics-stage-number ${stage.ready ? 'ready' : ''}`}>{stage.step.toString().padStart(2, '0')}</span><span><strong>{stage.name}</strong><small>{stage.detail}</small><em className={stage.ready ? 'ready' : ''}>{stage.ready ? 'Recorded' : 'Needs review'}</em></span><ArrowUpRight size={15} />
          </button>)}</div>
        </section>

        <section className="analytics-section" aria-label="Sessions in scope">
          <div className="analytics-section-heading"><h2>Session detail</h2><button className="analytics-text-button" onClick={() => onNavigate(14)}>Open KT Tracker <ArrowUpRight size={15} /></button></div>
          <div className="analytics-table-scroll"><table><thead><tr><th>Session / scheduled date</th><th>Domain / level</th><th>SME / receiver</th><th>Status</th><th>Progress</th><th>Acceptance</th></tr></thead><tbody>
            {data.sessions.slice(sessionPage * 10, sessionPage * 10 + 10).map((session) => <tr key={session.id}><td><strong>{session.title}</strong><small>{session.date}{session.overdue ? ' / Overdue' : ''}</small></td><td>{session.domain}<small>{session.level}</small></td><td>{session.sme}<small>{session.receiver}</small></td><td><span className={`analytics-status ${session.status}`}>{label(session.status)}</span></td><td><strong>{session.progress}%</strong><small>{number(session.hours)}h planned</small></td><td>{session.accepted ? 'Signed off' : 'Pending'}</td></tr>)}
          </tbody></table></div>
          {!data.sessions.length && <p className="analytics-scope-caption">No sessions in scope.</p>}
          <Pager page={sessionPage} pages={sessionPages} total={data.sessions.length} onChange={setSessionPage} name="sessions" />
        </section>
      </>}
  </div>;
}

function Metric({ name, value, detail, color, tooltip }: { name: string; value: string; detail: string; color: string; tooltip?: string }) {
  return <div className={`analytics-metric ${color}`}><div><span>{name}</span>{tooltip && <span tabIndex={0} title={tooltip} aria-label={tooltip}><Info size={13} /></span>}</div><strong>{value}</strong><small>{detail}</small></div>;
}

function Evidence({ name, value, total }: { name: string; value: number; total: number }) {
  return <div><span>{name}</span><strong>{value}<small> / {total}</small></strong><progress max={total || 1} value={value} aria-label={name} /></div>;
}

function RiskItem({ item, onNavigate }: { item: AnalyticsFinding; onNavigate: (step: number) => void }) {
  return <details className={`analytics-risk ${item.severity}`}><summary><span className={`analytics-priority ${item.severity}`}>{label(item.severity)}</span><span className="analytics-risk-title"><strong>{item.title}</strong><small>{label(item.kind)} / {item.source} / {item.certainty}</small></span><ChevronRight size={16} /></summary><div className="analytics-risk-body">
    <div><h3>Observation</h3><p>{item.detail}</p><small>Session SME: {item.owner} / Mitigation owner not assigned</small>{item.document && <small>Source: {item.document}{item.analyzed_at ? ` / Analyzed ${new Date(item.analyzed_at).toLocaleString()}` : ''}</small>}</div>
    <div><h3>Suggested mitigation</h3><p>{item.action || 'Review with the transition lead and agree a next action.'}</p>{item.next_call_question && <p><strong>Next call: </strong>{item.next_call_question}</p>}<button className="analytics-text-button" onClick={() => onNavigate(item.step)}>Review source <ArrowUpRight size={14} /></button></div>
    {item.evidence.length > 0 && <div className="analytics-quotes"><h3>Transcript evidence</h3>{item.evidence.map((quote, index) => <blockquote key={index}><p>{quote.text}</p><cite>{quote.speaker || 'Speaker unknown'} / {quote.start} - {quote.end}</cite></blockquote>)}</div>}
  </div></details>;
}

function Pager({ page, pages, total, onChange, name }: { page: number; pages: number; total: number; onChange: (page: number) => void; name: string }) {
  return <div className="analytics-pager"><span>{total} {name} / Page {page + 1} of {pages}</span><div><button className="analytics-icon" aria-label={`Previous ${name} page`} title="Previous page" disabled={page === 0} onClick={() => onChange(page - 1)}><ChevronLeft size={16} /></button><button className="analytics-icon" aria-label={`Next ${name} page`} title="Next page" disabled={page + 1 >= pages} onClick={() => onChange(page + 1)}><ChevronRight size={16} /></button></div></div>;
}