import { useState, useCallback, useEffect, useRef, useMemo, type FormEvent, type ReactNode } from 'react';
import { Input, Textarea, Button, Select } from '../components/Form';
import { HypothesisCard } from '../components/DiagnosticResults';
import { Vehicle3DViewer } from '../components/Vehicle3DViewer';
import type { ComponentHighlight } from '../components/Vehicle3DViewer';
import { Alert, ErrorMessage } from '../components/Alert';
import { useAnalyze, useAnalyzeInSession } from '../hooks/useDiagnostics';
import { useOnlineStatus } from '../hooks/useOnlineStatus';
import { useCachedSession } from '../hooks/useCachedSession';
import { cn } from '../utils/cn';
import type {
  DiagnosticAnalyzeRequest,
  DiagnosticHypothesis,
  DiagnosticResult,
  HypothesisStatus,
  RepairSafetyTier,
  VehicleType,
} from '../types/api';

const EXAMPLE_SYMPTOMS = [
  'My car makes a grinding noise when braking.',
  'The engine stalls at idle.',
  'The car pulls to the right.',
  'There is a clicking sound when turning.',
  'The temperature keeps rising.',
];

const VEHICLE_TYPE_OPTIONS: { value: VehicleType; label: string }[] = [
  { value: 'sedan', label: 'Sedan' },
  { value: 'suv', label: 'SUV' },
  { value: 'hatchback', label: 'Hatchback' },
  { value: 'pickup', label: 'Pickup' },
  { value: 'van', label: 'Van' },
];

const FUEL_TYPE_OPTIONS = [
  { value: 'gasoline', label: 'Gasoline' },
  { value: 'diesel', label: 'Diesel' },
  { value: 'hybrid', label: 'Hybrid' },
  { value: 'electric', label: 'Electric' },
  { value: 'other', label: 'Other / Not sure' },
];

const TRANSMISSION_OPTIONS = [
  { value: 'automatic', label: 'Automatic' },
  { value: 'manual', label: 'Manual' },
  { value: 'cvt', label: 'CVT' },
  { value: 'other', label: 'Other / Not sure' },
];

const SAFETY_ORDER: Record<RepairSafetyTier, number> = {
  diy_inspection: 0,
  diy_repair: 1,
  mechanic_recommended: 2,
  immediate_professional: 3,
};

const SAFETY_BANNER: Record<RepairSafetyTier, { label: string; description: string; classes: string }> = {
  diy_inspection: {
    label: 'Safe to inspect yourself',
    description: 'You can visually inspect this area. No disassembly or hazardous work is required.',
    classes: 'border-green-200 bg-green-50 text-green-800',
  },
  diy_repair: {
    label: 'DIY repair may be possible',
    description: 'With the right tools and guidance, this may be safe to address yourself.',
    classes: 'border-amber-200 bg-amber-50 text-amber-800',
  },
  mechanic_recommended: {
    label: 'Mechanic recommended',
    description: 'A qualified mechanic should handle this to avoid further damage or safety risk.',
    classes: 'border-orange-200 bg-orange-50 text-orange-800',
  },
  immediate_professional: {
    label: 'Seek professional service immediately',
    description: 'Do not drive the vehicle. Contact a professional right away.',
    classes: 'border-red-200 bg-red-50 text-red-800',
  },
};

function Section({
  title,
  subtitle,
  children,
  className,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn('scroll-mt-20', className)}>
      <div className="mb-3 sm:mb-4">
        <h2 className="text-base sm:text-lg font-semibold text-slate-900">{title}</h2>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {children}
    </section>
  );
}

export function DiagnosePage() {
  const isOnline = useOnlineStatus();
  const { analyze, ...apiState } = useAnalyze();
  const { analyzeInSession, ...sessionApiState } = useAnalyzeInSession();

  const [vehicleType, setVehicleType] = useState<VehicleType>('sedan');
  const [year, setYear] = useState('');
  const [fuelType, setFuelType] = useState('');
  const [transmission, setTransmission] = useState('');
  const [symptomText, setSymptomText] = useState('');
  const [showContext, setShowContext] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [results, setResults] = useState<DiagnosticResult[]>([]);
  const [loadingSession, setLoadingSession] = useState(false);
  const [selectedHypothesisId, setSelectedHypothesisId] = useState<string | null>(null);

  const [followUpQuestion, setFollowUpQuestion] = useState<string | null>(null);
  const [followUpReason, setFollowUpReason] = useState<string | null>(null);
  const [followUpAnswer, setFollowUpAnswer] = useState('');
  const [awaitingFollowUp, setAwaitingFollowUp] = useState(false);

  const [selectedComponent, setSelectedComponent] = useState<ComponentHighlight | null>(null);
  const hypothesisCardsRef = useRef<Map<string, HTMLDivElement>>(new Map());
  const { cachedSession, isFromCache, saveToCache } = useCachedSession(sessionId);

  useEffect(() => {
    if (apiState.data) {
      const sid = apiState.data.session_id;
      setSessionId(sid);
      loadSessionResults(sid);

      if (apiState.data.status === 'needs_more_information') {
        setFollowUpQuestion(apiState.data.follow_up_question || '');
        setFollowUpReason(apiState.data.follow_up_reason || '');
        setAwaitingFollowUp(true);
        setFollowUpAnswer('');
      } else {
        setFollowUpQuestion(null);
        setFollowUpReason(null);
        setAwaitingFollowUp(false);
      }
    }
  }, [apiState.data]);

  useEffect(() => {
    if (sessionApiState.data) {
      const sid = sessionApiState.data.session_id;
      setSessionId(sid);
      loadSessionResults(sid);

      if (sessionApiState.data.status === 'needs_more_information') {
        setFollowUpQuestion(sessionApiState.data.follow_up_question || '');
        setFollowUpReason(sessionApiState.data.follow_up_reason || '');
        setAwaitingFollowUp(true);
        setFollowUpAnswer('');
      } else {
        setFollowUpQuestion(null);
        setFollowUpReason(null);
        setAwaitingFollowUp(false);
      }
    }
  }, [sessionApiState.data]);

  const loadSessionResults = useCallback(
    async (sid: string) => {
      setLoadingSession(true);
      try {
        const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        const res = await fetch(`${base}/api/v1/diagnostics/sessions/${sid}`);
        if (!res.ok) throw new Error('Failed to load session');
        const session = await res.json();
        setResults(session.results || []);
        saveToCache(
          {
            session: session,
            results: session.results || [],
            conversation_messages: session.conversation_messages || [],
            evidence: session.evidence || [],
          },
          sid
        );
      } catch (err) {
        setLocalError(err instanceof Error ? err.message : 'Failed to load session results');
      } finally {
        setLoadingSession(false);
      }
    },
    [saveToCache]
  );

  const validate = useCallback((): string | null => {
    if (!symptomText.trim()) return "Please describe what's happening with your vehicle.";
    if (symptomText.length > 4000) return 'Description must not exceed 4000 characters.';
    if (year) {
      const yr = Number(year);
      if (!Number.isFinite(yr) || yr < 1900 || yr > 2100) return 'Year must be between 1900 and 2100.';
    }
    return null;
  }, [symptomText, year]);

  const handleSubmit = useCallback(
    async (e?: FormEvent) => {
      e?.preventDefault();
      if (!isOnline) {
        setLocalError('A live connection is required to run a diagnosis. Please check your network connection and try again.');
        return;
      }
      const validationError = validate();
      if (validationError) {
        setLocalError(validationError);
        return;
      }
      setLocalError(null);
      const payload: DiagnosticAnalyzeRequest = {
        vehicle_type: vehicleType || undefined,
        year: year ? Number(year) : undefined,
        fuel_type: fuelType || undefined,
        transmission: transmission || undefined,
        symptom_text: symptomText.trim(),
        follow_up_answer: awaitingFollowUp ? followUpAnswer.trim() : undefined,
      };
      if (awaitingFollowUp && sessionId) {
        await analyzeInSession(sessionId, payload);
      } else {
        await analyze(payload);
      }
    },
    [validate, vehicleType, year, fuelType, transmission, symptomText, analyze, analyzeInSession, awaitingFollowUp, sessionId, followUpAnswer, isOnline]
  );

  const handleOutcomeUpdate = useCallback(
    async (resultId: string, status: HypothesisStatus) => {
      const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const res = await fetch(`${base}/api/v1/diagnostics/results/${resultId}/outcome`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hypothesis_status: status }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to update outcome');
      }
      const updated = await res.json();
      setResults((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
    },
    []
  );

  const handleConfirmedFix = useCallback(
    async (resultId: string, confirmedFault: string) => {
      const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const res = await fetch(`${base}/api/v1/diagnostics/results/${resultId}/confirmed-case`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmed_fault: confirmedFault, is_verified: true }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to save confirmed diagnosis');
      }
    },
    []
  );

  const handleStartNew = useCallback(() => {
    setSymptomText('');
    setVehicleType('sedan');
    setYear('');
    setFuelType('');
    setTransmission('');
    setShowContext(false);
    setLocalError(null);
    setSessionId(null);
    setResults([]);
    setSelectedComponent(null);
    setSelectedHypothesisId(null);
    setFollowUpQuestion(null);
    setFollowUpReason(null);
    setFollowUpAnswer('');
    setAwaitingFollowUp(false);
    apiState.reset();
    sessionApiState.reset();
  }, [apiState, sessionApiState]);

  const analysisHypotheses = useMemo<DiagnosticHypothesis[]>(
    () => sessionApiState.data?.hypotheses || apiState.data?.hypotheses || [],
    [sessionApiState.data, apiState.data]
  );

  const responseVehicleType = (() => {
    const v = apiState.data?.vehicle?.vehicle_type || sessionApiState.data?.vehicle?.vehicle_type;
    return (v as VehicleType) || vehicleType || 'sedan';
  })();

  const hasComponentHighlights = analysisHypotheses.some((h) => h.component_id);
  const highlightedComponents = analysisHypotheses
    .filter((h): h is DiagnosticHypothesis & { component_id: string } => !!h.component_id)
    .map((h) => ({
      component_id: h.component_id!,
      system_category: h.system_category,
      vehicle_region: h.vehicle_region,
      safety_tier: h.safety_tier as ComponentHighlight['safety_tier'] | undefined,
      safety_tier_label: h.safety_tier_label,
      safety_tier_description: h.safety_tier_description,
      safety_tier_reasoning: h.safety_tier_reasoning,
    }));

  const handle3DComponentSelect = useCallback(
    (component: { component_id: string; system_category?: string; vehicle_region?: string } | null) => {
      setSelectedComponent(component);
      if (component) {
        const matchingHypotheses = analysisHypotheses.filter((h) => h.component_id === component.component_id);
        if (matchingHypotheses.length > 0) {
          const highestConfidence = matchingHypotheses.reduce((max, h) =>
            h.confidence_score > max.confidence_score ? h : max
          );
          const hypothesisIndex = analysisHypotheses.findIndex(
            (h) => h.component_id === component.component_id && h.confidence_score === highestConfidence.confidence_score
          );
          const realResultId = results[hypothesisIndex]?.id;
          const hypothesisId = realResultId || `hypothesis-${hypothesisIndex}`;
          setSelectedHypothesisId(hypothesisId);
          requestAnimationFrame(() => {
            const card = hypothesisCardsRef.current.get(hypothesisId);
            if (card) {
              card.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
          });
        }
      } else {
        setSelectedHypothesisId(null);
      }
    },
    [analysisHypotheses, results]
  );

  const displayResults = useMemo(() => {
    if (analysisHypotheses.length > 0 && results.length > 0) {
      return analysisHypotheses.map((h, idx) => ({
        ...h,
        id: results[idx]?.id || `hypothesis-${idx}`,
        session_id: sessionId || '',
        hypothesis_status: (results[idx]?.hypothesis_status || 'proposed') as HypothesisStatus,
        check_outcomes: results[idx]?.check_outcomes || [],
      }));
    }
    if (analysisHypotheses.length > 0) {
      return analysisHypotheses.map((h, idx) => ({
        ...h,
        id: `hypothesis-${idx}`,
        session_id: sessionId || '',
        hypothesis_status: 'proposed' as HypothesisStatus,
        check_outcomes: [],
      }));
    }
    if (isFromCache && cachedSession) {
      return cachedSession.data.results.map((r, idx) => ({
        ...r,
        id: r.id || `cached-hypothesis-${idx}`,
        session_id: sessionId || r.id || '',
      }));
    }
    return results;
  }, [analysisHypotheses, results, sessionId, isFromCache, cachedSession]);

  const isAnalyzing = apiState.loading || sessionApiState.loading;
  const hasReport =
    ((apiState.data || sessionApiState.data) && !isAnalyzing && !loadingSession) ||
    (isFromCache && cachedSession && !isOnline && !isAnalyzing);

  const topHypothesis = analysisHypotheses[0];
  const overallSafetyTier = useMemo<RepairSafetyTier | null>(() => {
    const tiers = analysisHypotheses
      .map((h) => h.safety_tier)
      .filter((t): t is RepairSafetyTier => !!t);
    if (tiers.length === 0) return null;
    return tiers.reduce((worst, t) => (SAFETY_ORDER[t] > SAFETY_ORDER[worst] ? t : worst), tiers[0]);
  }, [analysisHypotheses]);

  const confidenceLabel = (score: number) =>
    score >= 0.8 ? 'High' : score >= 0.5 ? 'Medium' : 'Low';

  const vehicleContextSummary = useMemo(() => {
    const parts: string[] = [];
    if (vehicleType) parts.push(VEHICLE_TYPE_OPTIONS.find((o) => o.value === vehicleType)?.label || vehicleType);
    if (year) parts.push(year);
    if (fuelType) parts.push(FUEL_TYPE_OPTIONS.find((o) => o.value === fuelType)?.label || fuelType);
    if (transmission) parts.push(TRANSMISSION_OPTIONS.find((o) => o.value === transmission)?.label || transmission);
    return parts.join(' ');
  }, [vehicleType, year, fuelType, transmission]);

  return (
    <div className="mx-auto max-w-4xl px-4 sm:px-6">
      {/* Hero */}
      <header className="pt-10 pb-8 sm:pt-14 sm:pb-10 text-center">
        <h1 className="text-2xl sm:text-4xl font-bold tracking-tight text-slate-900">
          Know what's wrong before you reach the workshop.
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-sm sm:text-base text-slate-600">
          Describe what your vehicle is doing and get a structured, safety-first diagnostic assessment with likely
          causes, recommended checks, repair guidance, and a mechanic-ready report.
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs sm:text-sm text-slate-500">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-brand-500" aria-hidden="true" />
            Safety prioritized
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-brand-500" aria-hidden="true" />
            Evidence explained
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-brand-500" aria-hidden="true" />
            Repair guidance
          </span>
        </div>
      </header>

      {/* Diagnostic input */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">What's happening with your vehicle?</h2>
          <p className="mt-1 text-sm text-slate-500">
            Describe the symptoms in your own words. You don't need to know the technical cause.
          </p>

          <div className="mt-4">
            <Textarea
              id="symptoms"
              value={symptomText}
              onChange={setSymptomText}
              placeholder="Example: My car shakes when I accelerate and the engine feels weaker than usual..."
              label=""
              required
              maxLength={4000}
              error={localError && !symptomText.trim() ? "Please describe the symptoms." : undefined}
              helperText={`${symptomText.length}/4000 characters`}
              disabled={isAnalyzing}
              rows={5}
            />
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {EXAMPLE_SYMPTOMS.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => setSymptomText(example)}
                disabled={isAnalyzing}
                className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900 disabled:opacity-50"
              >
                {example}
              </button>
            ))}
          </div>

          <div className="mt-4">
            <button
              type="button"
              onClick={() => setShowContext((v) => !v)}
              className="text-sm font-medium text-brand-600 hover:text-brand-700"
            >
              {showContext ? 'Hide vehicle details' : 'Add vehicle details (optional)'}
            </button>

            {showContext && (
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <Select
                  id="vehicleType"
                  value={vehicleType}
                  onChange={(v) => setVehicleType(v as VehicleType)}
                  options={VEHICLE_TYPE_OPTIONS}
                  label="Vehicle type"
                  disabled={isAnalyzing}
                />
                <Input
                  id="year"
                  value={year}
                  onChange={setYear}
                  placeholder="2020"
                  label="Approximate year"
                  type="number"
                  disabled={isAnalyzing}
                />
                <Select
                  id="fuelType"
                  value={fuelType}
                  onChange={setFuelType}
                  options={[{ value: '', label: 'Not sure' }, ...FUEL_TYPE_OPTIONS]}
                  placeholder="Not sure"
                  label="Fuel type"
                  disabled={isAnalyzing}
                />
                <Select
                  id="transmission"
                  value={transmission}
                  onChange={setTransmission}
                  options={[{ value: '', label: 'Not sure' }, ...TRANSMISSION_OPTIONS]}
                  placeholder="Not sure"
                  label="Transmission"
                  disabled={isAnalyzing}
                />
              </div>
            )}
          </div>
        </div>

        {localError && (
          <Alert type="error" title="Something went wrong">
            {localError}
          </Alert>
        )}
        {(apiState.error || sessionApiState.error) && (
          <ErrorMessage message={apiState.error || sessionApiState.error || ''} />
        )}

        {/* Follow-up question state */}
        {awaitingFollowUp && followUpQuestion && (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 sm:p-6 shadow-sm">
            <h3 className="text-base font-semibold text-amber-900">One more thing</h3>
            <p className="mt-2 text-sm text-amber-800">{followUpQuestion}</p>
            {followUpReason && <p className="mt-1 text-xs text-amber-700">{followUpReason}</p>}
            <div className="mt-4">
              <Textarea
                id="followUpAnswer"
                value={followUpAnswer}
                onChange={(value) => setFollowUpAnswer(value)}
                placeholder="Your answer..."
                label=""
                required
                maxLength={4000}
                disabled={isAnalyzing}
                rows={3}
              />
            </div>
            <div className="mt-3 flex justify-end">
              <Button
                type="button"
                onClick={handleSubmit}
                disabled={isAnalyzing || !followUpAnswer.trim()}
                loading={isAnalyzing}
              >
                {isAnalyzing ? 'Analyzing...' : 'Continue Diagnosis'}
              </Button>
            </div>
          </div>
        )}

        {/* Primary action */}
        <div className="flex items-center gap-3">
          <Button type="submit" disabled={isAnalyzing} loading={isAnalyzing} className="px-6 text-sm">
            {isAnalyzing ? 'Analyzing...' : 'Diagnose Vehicle'}
          </Button>
          {hasReport && (
            <Button type="button" variant="secondary" onClick={handleStartNew} disabled={isAnalyzing}>
              Start New Diagnosis
            </Button>
          )}
        </div>
      </form>

      {/* Loading experience */}
      {isAnalyzing && !awaitingFollowUp && (
        <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-3">
            <svg className="h-5 w-5 animate-spin text-brand-600" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <span className="text-sm font-medium text-slate-700">Analyzing your vehicle</span>
          </div>
          <ul className="mt-4 space-y-2 text-sm text-slate-500">
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-brand-400" aria-hidden="true" />
              Understanding your symptoms
            </li>
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-brand-400" aria-hidden="true" />
              Checking diagnostic evidence
            </li>
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-brand-400" aria-hidden="true" />
              Assessing possible causes
            </li>
            <li className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-brand-400" aria-hidden="true" />
              Preparing recommendations
            </li>
          </ul>
        </div>
      )}

      {/* Empty state */}
      {!hasReport && !isAnalyzing && !awaitingFollowUp && (
        <div className="mt-8 rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
          <p className="text-sm font-medium text-slate-600">Your diagnostic report will appear here</p>
          <p className="mx-auto mt-1 max-w-md text-xs text-slate-500">
            Possible causes, urgency, recommended checks, repair guidance, and a mechanic-ready summary.
          </p>
        </div>
      )}

      {/* Report */}
      {hasReport && displayResults.length > 0 && (
        <div className="mt-8 space-y-8">
          {isFromCache && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4" role="status" aria-live="polite">
              <div className="flex items-start gap-3">
                <svg className="h-5 w-5 shrink-0 text-amber-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path
                    fillRule="evenodd"
                    d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.88c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.516-2.625l6.28-10.88zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 9a1 1 0 100-2 1 1 0 000 2z"
                    clipRule="evenodd"
                  />
                </svg>
                <div>
                  <p className="text-sm font-medium text-amber-800">Viewing previous results</p>
                  <p className="mt-0.5 text-xs text-amber-700">
                    This information was loaded previously. Cached on {cachedSession ? new Date(cachedSession.cachedAt).toLocaleString() : ''}.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Summary */}
          <Section title="Diagnostic Assessment" subtitle="A structured overview of the most likely issue and how serious it is.">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6 shadow-sm">
              <div className="grid gap-5 sm:grid-cols-3">
                <div className="sm:col-span-2">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Most likely issue</p>
                  <p className="mt-1 text-lg font-semibold text-slate-900">{topHypothesis?.fault_description}</p>
                  {topHypothesis?.repair_suggestion && (
                    <p className="mt-3 text-sm text-slate-600">{topHypothesis.repair_suggestion}</p>
                  )}
                  {topHypothesis?.recommended_checks?.length ? (
                    <p className="mt-3 text-sm text-slate-600">
                      <span className="font-medium text-slate-700">Recommended next step: </span>
                      {topHypothesis.recommended_checks[0]}
                    </p>
                  ) : null}
                </div>
                <div className="space-y-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Confidence</p>
                    <p className="mt-1 text-sm font-medium text-slate-900">
                      {topHypothesis ? `${confidenceLabel(topHypothesis.confidence_score)} (${Math.round(topHypothesis.confidence_score * 100)}%)` : '—'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Severity</p>
                    <p className="mt-1 text-sm font-medium text-slate-900">{topHypothesis?.severity ? topHypothesis.severity.charAt(0).toUpperCase() + topHypothesis.severity.slice(1) : '—'}</p>
                  </div>
                </div>
              </div>

              {overallSafetyTier && (
                <div className={cn('mt-5 rounded-xl border p-4', SAFETY_BANNER[overallSafetyTier].classes)}>
                  <p className="text-sm font-semibold">{SAFETY_BANNER[overallSafetyTier].label}</p>
                  <p className="mt-1 text-xs">{SAFETY_BANNER[overallSafetyTier].description}</p>
                </div>
              )}

              <div className="mt-5 flex flex-wrap items-center gap-x-6 gap-y-1 text-sm text-slate-500">
                <span>
                  <span className="font-medium text-slate-700">{displayResults.length}</span>{' '}
                  {displayResults.length === 1 ? 'possible cause' : 'possible causes'}
                </span>
                {vehicleContextSummary && (
                  <span>
                    Vehicle: <span className="font-medium text-slate-700">{vehicleContextSummary}</span>
                  </span>
                )}
              </div>
            </div>
          </Section>

          {/* Possible causes */}
          <Section title="Possible Causes" subtitle="Ranked by likelihood, with supporting evidence and recommended checks.">
            <div className="space-y-4">
              {displayResults.map((result, index) => (
                <HypothesisCard
                  key={`hypothesis-${index}`}
                  ref={(el) => {
                    if (el) {
                      hypothesisCardsRef.current.set(result.id, el);
                    } else {
                      hypothesisCardsRef.current.delete(result.id);
                    }
                  }}
                  hypothesis={{
                    fault_description: result.fault_description,
                    confidence_score: result.confidence_score,
                    severity: (result.severity || 'low') as 'low',
                    supporting_evidence: result.supporting_evidence,
                    recommended_checks: result.recommended_checks,
                    repair_suggestion: result.repair_suggestion,
                    component_id: result.component_id,
                    system_category: result.system_category,
                    vehicle_region: result.vehicle_region,
                    safety_tier: result.safety_tier as RepairSafetyTier | undefined,
                    safety_tier_label: result.safety_tier_label,
                    safety_tier_description: result.safety_tier_description,
                    safety_tier_reasoning: result.safety_tier_reasoning,
                    differential_rank: result.differential_rank,
                    evidence_quality: result.evidence_quality,
                    diy_repair: result.diy_repair as import('../types/api').DIYRepairGuidance | null | undefined,
                    resources: result.resources as import('../types/api').ResourceLink[] | undefined,
                  }}
                  resultId={result.id}
                  currentStatus={(result.hypothesis_status || 'proposed') as HypothesisStatus}
                  onUpdateStatus={handleOutcomeUpdate}
                  onConfirmedFix={handleConfirmedFix}
                  updating={false}
                  isSelected={selectedHypothesisId === result.id}
                  onSelect={() => setSelectedHypothesisId(result.id)}
                  isTopHypothesis={index === 0}
                />
              ))}
            </div>
          </Section>

          {/* Affected areas / 3D */}
          {hasComponentHighlights && (
            <Section
              title="Affected Areas"
              subtitle="Explore the components associated with the diagnostic assessment."
            >
              <Vehicle3DViewer
                vehicleType={responseVehicleType}
                highlightedComponents={highlightedComponents}
                selectedComponent={selectedComponent}
                onComponentSelect={handle3DComponentSelect}
              />
            </Section>
          )}

          {/* Mechanic-ready summary */}
          <MechanicSummary
            vehicleContext={vehicleContextSummary}
            symptomText={symptomText}
            hypotheses={analysisHypotheses}
          />

          <div className="flex items-center justify-center pt-2">
            <Button type="button" variant="secondary" onClick={handleStartNew} disabled={isAnalyzing}>
              Start New Diagnosis
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function MechanicSummary({
  vehicleContext,
  symptomText,
  hypotheses,
}: {
  vehicleContext: string;
  symptomText: string;
  hypotheses: DiagnosticHypothesis[];
}) {
  const [copied, setCopied] = useState(false);

  const summaryText = useMemo(() => {
    const lines: string[] = [];
    lines.push('AUTOMOTIVE DIAGNOSTIC SUMMARY');
    lines.push('');
    if (vehicleContext) lines.push(`Vehicle: ${vehicleContext}`);
    lines.push(`Reported symptoms: ${symptomText}`);
    lines.push('');
    lines.push('LIKELY CAUSES');
    hypotheses.forEach((h, idx) => {
      const conf = Math.round(h.confidence_score * 100);
      lines.push(
        `${idx + 1}. ${h.fault_description} (confidence: ${conf}%, severity: ${h.severity || 'unknown'})`
      );
      if (h.recommended_checks?.length) {
        lines.push(`   Recommended checks: ${h.recommended_checks.join('; ')}`);
      }
      if (h.safety_tier_label) {
        lines.push(`   Safety: ${h.safety_tier_label}`);
      }
    });
    lines.push('');
    lines.push('SAFETY LEVEL');
    const worst = hypotheses
      .map((h) => h.safety_tier)
      .filter((t): t is RepairSafetyTier => !!t)
      .sort((a, b) => SAFETY_ORDER[b] - SAFETY_ORDER[a])[0];
    lines.push(worst ? SAFETY_BANNER[worst].label : 'Not assessed');
    return lines.join('\n');
  }, [vehicleContext, symptomText, hypotheses]);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(summaryText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }, [summaryText]);

  return (
    <Section title="Mechanic-Ready Summary" subtitle="A clean summary you can hand to a workshop.">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6 shadow-sm">
        <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-slate-700">
          {summaryText}
        </pre>
        <div className="mt-4">
          <Button type="button" variant="secondary" onClick={handleCopy}>
            {copied ? 'Copied!' : 'Copy Summary'}
          </Button>
        </div>
      </div>
    </Section>
  );
}
