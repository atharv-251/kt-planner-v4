import React, { useState, useEffect } from 'react';
import { Settings, Save, ArrowRight, Calculator, Globe, Clock, Info, CheckCircle, AlertTriangle, Moon } from 'lucide-react';
import { api } from '../../api/client';

interface Page3Props {
  transition: any;
  onNext: () => void;
  onRefresh: () => void;
}

export const Page3_Settings: React.FC<Page3Props> = ({ transition, onNext, onRefresh }) => {
  const [countries, setCountries] = useState<string[]>([]);
  const [formData, setFormData] = useState({
    name: '',
    total_duration_days: 60,
    shadow_days: 10,
    reverse_shadow_days: 10,
    daily_kt_hours: 5.0,
    start_date: '2026-09-20',
    end_date: '2026-10-30',
    // Countries (Timezone calculated automatically considering DST)
    sme_country: 'India',
    receiver_country: 'CzechRepublic',
    // Custom Shift Hours Toggle
    custom_shifts_enabled: false,
    sme_shift_start: '08:00',
    sme_shift_end: '17:00',
    receiver_shift_start: '08:00',
    receiver_shift_end: '17:00',
  });

  const [shiftOverlap, setShiftOverlap] = useState<any>(null);
  const [loadingOverlap, setLoadingOverlap] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  useEffect(() => {
    if (transition) {
      setFormData({
        name: transition.name || '',
        total_duration_days: transition.total_duration_days || 60,
        shadow_days: transition.shadow_days || 10,
        reverse_shadow_days: transition.reverse_shadow_days || 10,
        daily_kt_hours: transition.daily_kt_hours || 5.0,
        start_date: transition.start_date || '2026-09-20',
        end_date: transition.end_date || '2026-10-30',
        sme_country: transition.sme_country || 'India',
        receiver_country: transition.receiver_country || 'CzechRepublic',
        custom_shifts_enabled: transition.custom_shifts_enabled || false,
        sme_shift_start: transition.sme_shift_start ? String(transition.sme_shift_start).substring(0, 5) : '08:00',
        sme_shift_end: transition.sme_shift_end ? String(transition.sme_shift_end).substring(0, 5) : '17:00',
        receiver_shift_start: transition.receiver_shift_start ? String(transition.receiver_shift_start).substring(0, 5) : '08:00',
        receiver_shift_end: transition.receiver_shift_end ? String(transition.receiver_shift_end).substring(0, 5) : '17:00',
      });
    }

    api.getCountries().then((res) => {
      if (res && res.countries) setCountries(res.countries);
    }).catch(() => {});
  }, [transition]);

  // Compulsory calculation of Shift Overlap
  const fetchOverlap = async () => {
    if (!transition) return;
    setLoadingOverlap(true);
    try {
      const data = await api.getShiftOverlap(transition.id, formData.start_date);
      setShiftOverlap(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingOverlap(false);
    }
  };

  useEffect(() => {
    if (transition?.id) {
      fetchOverlap();
    }
  }, [transition?.id, formData.sme_country, formData.receiver_country, formData.custom_shifts_enabled, formData.sme_shift_start, formData.sme_shift_end, formData.receiver_shift_start, formData.receiver_shift_end]);

  const availableDays = Math.max(0, formData.total_duration_days - formData.shadow_days - formData.reverse_shadow_days);
  const targetHours = (availableDays * formData.daily_kt_hours).toFixed(1);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!transition) return;
    setSaving(true);
    setSavedMessage(null);
    try {
      await api.updateSettings(transition.id, {
        ...formData,
        sme_shift_start: `${formData.sme_shift_start}:00`,
        sme_shift_end: `${formData.sme_shift_end}:00`,
        receiver_shift_start: `${formData.receiver_shift_start}:00`,
        receiver_shift_end: `${formData.receiver_shift_end}:00`,
      });
      setSavedMessage('Configuration, auto-calculated timezones, and capacity targets updated successfully!');
      await fetchOverlap();
      onRefresh();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-slate-100 rounded-lg text-slate-700">
              <Settings className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Stage 3: Transition & Capacity Configuration</h2>
              <p className="text-sm text-slate-500">
                Automatic DST-aware timezone resolution, shift overlap calculation, and deterministic capacity balancing.
              </p>
            </div>
          </div>

          <button
            onClick={onNext}
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow"
          >
            <span>Proceed to SMEs & People</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>

        {savedMessage && (
          <div className="p-3 mb-4 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-lg text-xs font-medium flex items-center space-x-2">
            <CheckCircle className="h-4 w-4 text-emerald-600" />
            <span>{savedMessage}</span>
          </div>
        )}

        {/* Live Equation Banner */}
        <div className="p-4 bg-gradient-to-r from-sky-900 to-indigo-900 rounded-xl text-white shadow mb-6">
          <div className="flex items-center space-x-2 text-sky-300 text-xs font-semibold uppercase tracking-wider mb-2">
            <Calculator className="h-4 w-4" />
            <span>Deterministic Capacity Engine Formula</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center mt-3">
            <div className="bg-white/10 backdrop-blur p-3 rounded-lg border border-white/10">
              <span className="text-xs text-sky-200 block">Available KT Days</span>
              <span className="text-2xl font-bold">{availableDays} Days</span>
              <span className="text-[10px] text-slate-300 block mt-0.5">
                {formData.total_duration_days} - {formData.shadow_days} (Shadow) - {formData.reverse_shadow_days} (Rev Shadow)
              </span>
            </div>
            <div className="bg-white/10 backdrop-blur p-3 rounded-lg border border-white/10">
              <span className="text-xs text-sky-200 block">Daily KT Hours</span>
              <span className="text-2xl font-bold">{formData.daily_kt_hours}h / day</span>
              <span className="text-[10px] text-slate-300 block mt-0.5">Target session load</span>
            </div>
            <div className="bg-white/10 backdrop-blur p-3 rounded-lg border border-white/10">
              <span className="text-xs text-sky-200 block">Target KT Capacity</span>
              <span className="text-2xl font-bold text-sky-300">{targetHours} Hours</span>
              <span className="text-[10px] text-slate-300 block mt-0.5">Must be 100% utilized</span>
            </div>
          </div>
        </div>

        <form onSubmit={handleSave} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Left Column: Transition Metadata */}
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Transition Project Name
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-medium focus:ring-2 focus:ring-sky-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Start Date
                  </label>
                  <input
                    type="date"
                    value={formData.start_date}
                    onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-medium focus:ring-2 focus:ring-sky-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    End Date
                  </label>
                  <input
                    type="date"
                    value={formData.end_date}
                    onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-medium focus:ring-2 focus:ring-sky-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Total Days
                  </label>
                  <input
                    type="number"
                    value={formData.total_duration_days}
                    onChange={(e) => setFormData({ ...formData, total_duration_days: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-medium focus:ring-2 focus:ring-sky-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Shadow Days
                  </label>
                  <input
                    type="number"
                    value={formData.shadow_days}
                    onChange={(e) => setFormData({ ...formData, shadow_days: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-medium focus:ring-2 focus:ring-sky-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Rev. Shadow
                  </label>
                  <input
                    type="number"
                    value={formData.reverse_shadow_days}
                    onChange={(e) => setFormData({ ...formData, reverse_shadow_days: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-medium focus:ring-2 focus:ring-sky-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Daily KT Session Hours
                </label>
                <input
                  type="number"
                  step="0.5"
                  value={formData.daily_kt_hours}
                  onChange={(e) => setFormData({ ...formData, daily_kt_hours: parseFloat(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-medium focus:ring-2 focus:ring-sky-500 focus:outline-none"
                />
                <p className="text-[11px] text-slate-400 mt-1">Recommended 4.0 - 5.0 hours/day for knowledge retention.</p>
              </div>
            </div>

            {/* Right Column: Country Selection & Automatic Timezone Resolution (No manual timezone input) */}
            <div className="space-y-4">
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-4">
                <div className="flex items-center space-x-2 text-xs font-bold text-slate-800 uppercase tracking-wider">
                  <Globe className="h-4 w-4 text-sky-600" />
                  <span>SME & Receiver Country Locations</span>
                </div>
                <p className="text-[11px] text-slate-500">
                  Select the country of SME and Receiver. Timezones and Daylight Saving Time (DST) offsets are automatically calculated.
                </p>

                {/* SME Country Dropdown */}
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    SME Country
                  </label>
                  <select
                    value={formData.sme_country}
                    onChange={(e) => setFormData({ ...formData, sme_country: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-medium bg-white focus:ring-2 focus:ring-sky-500 focus:outline-none"
                  >
                    {countries.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>

                  {shiftOverlap?.sme && (
                    <div className="mt-1.5 flex items-center space-x-2 text-[11px] text-slate-600">
                      <span className="font-semibold text-slate-800">Timezone:</span>
                      <code className="bg-slate-200 px-1.5 py-0.5 rounded text-slate-700">
                        {shiftOverlap.sme.timezone} ({shiftOverlap.sme.utc_offset})
                      </code>
                      <span className={`px-2 py-0.2 rounded text-[10px] font-bold ${
                        shiftOverlap.sme.is_dst ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'
                      }`}>
                        {shiftOverlap.sme.is_dst ? 'DST Active' : 'Standard Time'}
                      </span>
                    </div>
                  )}
                </div>

                {/* Receiver Country Dropdown */}
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Receiver Country
                  </label>
                  <select
                    value={formData.receiver_country}
                    onChange={(e) => setFormData({ ...formData, receiver_country: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs font-medium bg-white focus:ring-2 focus:ring-sky-500 focus:outline-none"
                  >
                    {countries.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>

                  {shiftOverlap?.receiver && (
                    <div className="mt-1.5 flex items-center space-x-2 text-[11px] text-slate-600">
                      <span className="font-semibold text-slate-800">Timezone:</span>
                      <code className="bg-slate-200 px-1.5 py-0.5 rounded text-slate-700">
                        {shiftOverlap.receiver.timezone} ({shiftOverlap.receiver.utc_offset})
                      </code>
                      <span className={`px-2 py-0.2 rounded text-[10px] font-bold ${
                        shiftOverlap.receiver.is_dst ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'
                      }`}>
                        {shiftOverlap.receiver.is_dst ? 'DST Active' : 'Standard Time'}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Shift Hours Customization Toggle */}
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Clock className="h-4 w-4 text-indigo-600" />
                    <span className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                      Shift Hours Configuration
                    </span>
                    <div className="group relative">
                      <Info className="h-3.5 w-3.5 text-slate-400 cursor-pointer hover:text-slate-600" />
                      <div className="absolute left-1/2 -translate-x-1/2 bottom-6 hidden group-hover:block w-64 p-2 bg-slate-900 text-white text-[11px] rounded shadow-lg z-20">
                        Default shift is 08:00 to 17:00 (8 AM - 5 PM) in each stakeholder's local timezone. Toggle on to customize working hours if your team operates in a different shift window.
                      </div>
                    </div>
                  </div>

                  {/* Toggle Switch */}
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.custom_shifts_enabled}
                      onChange={(e) => setFormData({ ...formData, custom_shifts_enabled: e.target.checked })}
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-slate-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600"></div>
                    <span className="ml-2 text-xs font-semibold text-slate-700">
                      {formData.custom_shifts_enabled ? 'Custom Shifts' : 'Standard 8-5 Shift'}
                    </span>
                  </label>
                </div>

                {formData.custom_shifts_enabled ? (
                  <div className="grid grid-cols-2 gap-4 pt-2 border-t border-slate-200 text-xs">
                    <div>
                      <span className="font-bold text-slate-700 block mb-1">SME Shift ({formData.sme_country})</span>
                      <div className="flex items-center space-x-1">
                        <input
                          type="time"
                          value={formData.sme_shift_start}
                          onChange={(e) => setFormData({ ...formData, sme_shift_start: e.target.value })}
                          className="w-full px-2 py-1 border rounded text-xs"
                        />
                        <span>-</span>
                        <input
                          type="time"
                          value={formData.sme_shift_end}
                          onChange={(e) => setFormData({ ...formData, sme_shift_end: e.target.value })}
                          className="w-full px-2 py-1 border rounded text-xs"
                        />
                      </div>
                    </div>

                    <div>
                      <span className="font-bold text-slate-700 block mb-1">Receiver Shift ({formData.receiver_country})</span>
                      <div className="flex items-center space-x-1">
                        <input
                          type="time"
                          value={formData.receiver_shift_start}
                          onChange={(e) => setFormData({ ...formData, receiver_shift_start: e.target.value })}
                          className="w-full px-2 py-1 border rounded text-xs"
                        />
                        <span>-</span>
                        <input
                          type="time"
                          value={formData.receiver_shift_end}
                          onChange={(e) => setFormData({ ...formData, receiver_shift_end: e.target.value })}
                          className="w-full px-2 py-1 border rounded text-xs"
                        />
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-[11px] text-slate-500 italic">
                    Using standard 08:00 AM - 05:00 PM shift hours in each team's respective local timezone.
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Compulsory Shift Overlap Calculation Banner */}
          {shiftOverlap && (
            <div className={`p-4 rounded-xl border ${
              shiftOverlap.has_overlap && shiftOverlap.overlap_hours >= formData.daily_kt_hours
                ? 'bg-emerald-50 border-emerald-200 text-emerald-950'
                : 'bg-amber-50 border-amber-200 text-amber-950'
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  {shiftOverlap.has_overlap && shiftOverlap.overlap_hours >= formData.daily_kt_hours ? (
                    <CheckCircle className="h-5 w-5 text-emerald-600" />
                  ) : (
                    <AlertTriangle className="h-5 w-5 text-amber-600" />
                  )}
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wider">
                      Compulsory Timezone & Shift Overlap Calculation
                    </h3>
                    <p className="text-xs mt-0.5 font-medium">
                      {shiftOverlap.has_overlap ? (
                        <>
                          Available Overlap Window: <strong>{shiftOverlap.overlap_hours} hours/day</strong>.
                          SME ({shiftOverlap.sme.country}): <strong>{shiftOverlap.sme.overlap_start_local} – {shiftOverlap.sme.overlap_end_local}</strong> |
                          Receiver ({shiftOverlap.receiver.country}): <strong>{shiftOverlap.receiver.overlap_start_local} – {shiftOverlap.receiver.overlap_end_local}</strong>
                        </>
                      ) : (
                        <span className="text-red-700 font-semibold">
                          No overlapping working hours between {shiftOverlap.sme.country} and {shiftOverlap.receiver.country}! Please adjust custom shift hours.
                        </span>
                      )}
                    </p>
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-xs font-bold block">
                    {shiftOverlap.overlap_hours}h Overlap
                  </span>
                  <span className="text-[10px] text-slate-500 block">
                    Daily target: {formData.daily_kt_hours}h
                  </span>
                </div>
              </div>
            </div>
          )}

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={saving}
              className="px-5 py-2.5 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow"
            >
              <Save className="h-4 w-4" />
              <span>{saving ? 'Saving...' : 'Save Configuration & Calculate Targets'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
