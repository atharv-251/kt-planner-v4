const API_BASE = '/api/v1';

export async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const res = await fetch(url, { ...options, headers });
  if (!res.ok) {
    let errorDetail = 'API request failed';
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || JSON.stringify(errJson);
    } catch {
      errorDetail = await res.text();
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export const api = {
  // Transitions
  listTransitions: () => request<any[]>('/transitions'),
  getTransition: (id: string) => request<any>(`/transitions/${id}`),
  createTransition: (payload: any) => request<any>('/transitions', { method: 'POST', body: JSON.stringify(payload) }),
  updateSettings: (id: string, payload: any) => request<any>(`/transitions/${id}/settings`, { method: 'PUT', body: JSON.stringify(payload) }),
  getShiftOverlap: (id: string, targetDate?: string) => request<any>(`/transitions/${id}/shift-overlap${targetDate ? `?target_date=${targetDate}` : ''}`),
  updateDomainHours: (id: string, domainHours: Record<string, number>) => request<any>(`/transitions/${id}/domain-hours`, { method: 'PUT', body: JSON.stringify({ domain_hours: domainHours }) }),

  // Documents & Extraction
  uploadDocument: (id: string, file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return request<any>(`/transitions/${id}/upload`, { method: 'POST', body: fd });
  },
  getDocuments: (id: string) => request<any[]>(`/transitions/${id}/documents`),
  triggerExtraction: (id: string) => request<any>(`/transitions/${id}/extract`, { method: 'POST' }),
  getRawExtraction: (id: string) => request<any>(`/transitions/${id}/raw-extraction`),

  // Project Profile
  generateProfile: (id: string) => request<any>(`/transitions/${id}/profile/generate`, { method: 'POST' }),
  getProfile: (id: string) => request<any>(`/transitions/${id}/profile`),
  updateProfile: (id: string, payload: any) => request<any>(`/transitions/${id}/profile`, { method: 'PUT', body: JSON.stringify(payload) }),
  approveProfile: (id: string, payload: any) => request<any>(`/transitions/${id}/profile/approve`, { method: 'POST', body: JSON.stringify(payload) }),

  // Knowledge Hierarchy
  generateHierarchy: (id: string) => request<any>(`/transitions/${id}/hierarchy/generate`, { method: 'POST' }),
  getHierarchy: (id: string, view = 'nested') => request<any[]>(`/transitions/${id}/hierarchy?view=${view}`),
  decomposeHierarchy: (id: string) => request<any>(`/transitions/${id}/hierarchy/decompose`, { method: 'POST' }),

  // KT Levels
  evaluateKTLevels: (id: string) => request<any>(`/transitions/${id}/levels/evaluate`, { method: 'POST' }),
  getKTLevels: (id: string) => request<any[]>(`/transitions/${id}/levels`),
  updateKTLevel: (id: string, evalId: string, payload: any) => request<any>(`/transitions/${id}/levels/${evalId}`, { method: 'PUT', body: JSON.stringify(payload) }),

  // Stakeholders & Calendars
  listStakeholders: (id: string) => request<any[]>(`/transitions/${id}/stakeholders`),
  createStakeholder: (id: string, payload: any) => request<any>(`/transitions/${id}/stakeholders`, { method: 'POST', body: JSON.stringify(payload) }),
  deleteStakeholder: (id: string, stakeholderId: string) => request<any>(`/transitions/${id}/stakeholders/${stakeholderId}`, { method: 'DELETE' }),
  addLeave: (id: string, smeId: string, payload: any) => request<any>(`/transitions/${id}/stakeholders/${smeId}/leaves`, { method: 'POST', body: JSON.stringify(payload) }),
  uploadCalendarCsv: (id: string, smeId: string, file: File, mask = false) => {
    const fd = new FormData();
    fd.append('file', file);
    return request<any>(`/transitions/${id}/stakeholders/${smeId}/calendar-csv?mask_subjects=${mask}`, { method: 'POST', body: fd });
  },

  // Availability & Holidays
  getAvailability: (id: string) => request<any>(`/transitions/${id}/availability`),
  getHolidays: (id: string) => request<any>(`/transitions/${id}/availability/holidays`),
  getCountries: () => request<{ countries: string[] }>('/transitions/dummy/availability/countries'),

  // Scheduling
  autoBuildSchedule: (id: string, payload: any) => request<any>(`/transitions/${id}/schedule/auto-build`, { method: 'POST', body: JSON.stringify(payload) }),
  getSchedule: (id: string) => request<any[]>(`/transitions/${id}/schedule`),
  getFullCalendarEvents: (id: string) => request<any[]>(`/transitions/${id}/schedule/fullcalendar`),
  updateSession: (id: string, sessId: string, payload: any) => request<any>(`/transitions/${id}/schedule/sessions/${sessId}`, { method: 'PUT', body: JSON.stringify(payload) }),

  // Governance & Validation
  getValidation: (id: string) => request<any>(`/transitions/${id}/validation`),
  refineWithNL: (id: string, prompt: string) => request<any>(`/transitions/${id}/refine`, { method: 'POST', body: JSON.stringify({ prompt }) }),
  getPatches: (id: string) => request<any[]>(`/transitions/${id}/patches`),
  publishPlan: (id: string) => request<any>(`/transitions/${id}/publish`, { method: 'POST' }),

  // Exports
  getCapacity: (id: string) => request<any>(`/transitions/${id}/export/capacity`),
  getExcelDownloadUrl: (id: string) => `${API_BASE}/transitions/${id}/export/xlsx`,
  getCsvDownloadUrl: (id: string) => `${API_BASE}/transitions/${id}/export/csv`,

  // Teams KT Scheduler
  getTeamsKTScheduler: (id: string) => request<any>(`/transitions/${id}/teams-kt-scheduler`),
  sendTeamsInvites: (id: string, payload: any) => request<any>(`/transitions/${id}/teams-kt-scheduler/invites`, { method: 'POST', body: JSON.stringify(payload) }),

  // KT Tracker
  getTeamsTranscripts: (id: string) => request<any>(`/transitions/${id}/kt-tracker/transcripts`),
  uploadTeamsTranscript: (id: string, file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return request<any>(`/transitions/${id}/kt-tracker/transcripts`, { method: 'POST', body: fd });
  },

  // Controlled SQL Gateway
  querySQL: (query: string, params: any = {}) => request<any>('/database/query', { method: 'POST', body: JSON.stringify({ query, params }) }),
};

