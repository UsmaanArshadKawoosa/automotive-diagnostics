import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Input, Textarea, Button } from '../components/Form';
import { HypothesisCard } from '../components/DiagnosticResults';
import { Vehicle3DViewer } from '../components/Vehicle3DViewer';
import { Alert, ErrorMessage } from '../components/Alert';
import { useAnalyze, useAnalyzeInSession } from '../hooks/useDiagnostics';
import { useOnlineStatus } from '../hooks/useOnlineStatus';
import { useCachedSession } from '../hooks/useCachedSession';
import { cn } from '../utils/cn';
import type { DiagnosticAnalyzeRequest, DiagnosticHypothesis, DiagnosticResult, VehicleType } from '../types/api';
import type { HypothesisStatus } from '../types/api';

export function DiagnosePage() {
  const navigate = useNavigate();
  const isOnline = useOnlineStatus();
  const { analyze, ...apiState } = useAnalyze();
  const { analyzeInSession } = useAnalyzeInSession();
  const [make, setMake] = useState('');
  const [model, setModel] = useState('');
  const [year, setYear] = useState('');
  const [symptomText, setSymptomText] = useState('');
  const [checkEngineLight, setCheckEngineLight] = useState<string>('');
  const [dtcCodes, setDtcCodes] = useState<string[]>([]);
  const [vin, setVin] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [results, setResults] = useState<DiagnosticResult[]>([]);
  const [loadingSession, setLoadingSession] = useState(false);
  const [selectedHypothesisId, setSelectedHypothesisId] = useState<string | null>(null);
  const [followUpQuestion, setFollowUpQuestion] = useState<string | null>(null);
  const [followUpReason, setFollowUpReason] = useState<string | null>(null);
  const [followUpAnswer, setFollowUpAnswer] = useState('');
  const [awaitingFollowUp, setAwaitingFollowUp] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [selectedComponent, setSelectedComponent] = useState<import('../components/Vehicle3DViewer').ComponentHighlight | null>(null);
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

  const loadSessionResults = async (sid: string) => {
    setLoadingSession(true);
    try {
      const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const res = await fetch(`${base}/api/v1/diagnostics/sessions/${sid}`);
      if (!res.ok) throw new Error('Failed to load session');
      const session = await res.json();
      setResults(session.results || []);
      saveToCache({
        session: session,
        results: session.results || [],
        conversation_messages: session.conversation_messages || [],
        evidence: session.evidence || [],
      }, sid);
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : 'Failed to load session results');
    } finally {
      setLoadingSession(false);
    }
  };

  const validate = useCallback((): string | null => {
    if (!symptomText.trim()) return 'Please describe what\'s happening with your car.';
    if (symptomText.length > 4000) return 'Description must not exceed 4000 characters.';
    if (vin && vin.length !== 17) return 'VIN must be exactly 17 characters if provided.';
    if (vin && /[IOQ]/i.test(vin)) return 'VIN cannot contain I, O, or Q.';
    if (year) {
      const yr = Number(year);
      if (yr < 1900 || yr > 2100) return 'Year must be between 1900 and 2100.';
    }
    for (const code of dtcCodes) {
      if (!/^[PCBU][0-9]{4}$/i.test(code)) return `Invalid code: ${code}`;
    }
    return null;
  }, [symptomText, vin, year, dtcCodes]);

  const handleSubmit = useCallback(
    async (e?: React.FormEvent) => {
      e?.preventDefault();
      if (!isOnline) {
        setLocalError('A live connection is required to run a new diagnosis. Please check your network connection and try again.');
        return;
      }
      const validationError = validate();
      if (validationError) {
        setLocalError(validationError);
        return;
      }
      setLocalError(null);
      const payload: DiagnosticAnalyzeRequest = {
        vin: vin ? vin.toUpperCase() : undefined,
        make: make || undefined,
        model: model || undefined,
        year: year ? Number(year) : undefined,
        vehicle_type: undefined,
        dtc_codes: dtcCodes.length > 0 ? dtcCodes : undefined,
        symptom_text: symptomText.trim(),
        follow_up_answer: awaitingFollowUp
          ? followUpAnswer.trim()
          : undefined,
      };
      if (awaitingFollowUp && sessionId) {
        await analyzeInSession(sessionId, payload);
      } else {
        await analyze(payload);
      }
    },
    [validate, vin, make, model, year, dtcCodes, symptomText, analyze, awaitingFollowUp, sessionId, followUpAnswer, isOnline]
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
        body: JSON.stringify({
          confirmed_fault: confirmedFault,
          is_verified: true,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to save confirmed diagnosis');
      }
    },
    []
  );

  const handleContinueSession = useCallback(async () => {
    if (!sessionId) return;
    await loadSessionResults(sessionId);
    navigate(`/sessions/${sessionId}`);
  }, [sessionId, navigate]);

  const analysisHypotheses: DiagnosticHypothesis[] = apiState.data?.hypotheses || [];
  const currentVehicleType = (apiState.data?.vehicle?.vehicle_type as VehicleType) || 'sedan';
  const hasComponentHighlights = analysisHypotheses.some((h) => h.component_id);
  const highlightedComponents = analysisHypotheses
    .filter((h): h is DiagnosticHypothesis & { component_id: string } => !!h.component_id)
    .map((h) => ({
      component_id: h.component_id!,
      system_category: h.system_category,
      vehicle_region: h.vehicle_region,
      safety_tier: h.safety_tier as import('../components/Vehicle3DViewer').ComponentHighlight['safety_tier'] | undefined,
      safety_tier_label: h.safety_tier_label,
      safety_tier_description: h.safety_tier_description,
      safety_tier_reasoning: h.safety_tier_reasoning,
    }));

  const handle3DComponentSelect = useCallback((component: { component_id: string; system_category?: string; vehicle_region?: string } | null) => {
    setSelectedComponent(component);
    if (component) {
      const matchingHypotheses = analysisHypotheses.filter((h) => h.component_id === component.component_id);
      if (matchingHypotheses.length > 0) {
        const highestConfidence = matchingHypotheses.reduce((max, h) => 
          h.confidence_score > max.confidence_score ? h : max
        );
        const hypothesisIndex = analysisHypotheses.findIndex((h) => h.component_id === component.component_id && h.confidence_score === highestConfidence.confidence_score);
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
  }, [analysisHypotheses, results]);

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

  const showResults = (apiState.data && !apiState.loading && !loadingSession) || (isFromCache && cachedSession && !isOnline);
  const isAnalyzing = apiState.loading;

  return (
    <div className="mx-auto max-w-3xl px-4 sm:px-6">
      <div className="mb-6 sm:mb-8">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-900">What's wrong with your car?</h1>
        <p className="mt-1 text-sm sm:text-base text-slate-600">
          Tell us about your car and what you're experiencing. We'll help you figure it out.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-6">
        {localError && (
          <Alert type="error" title="Something went wrong">
            {localError}
          </Alert>
        )}

        {apiState.error && (
          <ErrorMessage message={apiState.error} />
        )}

        <div className="rounded-lg border border-slate-200 bg-white p-4 sm:p-5 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900 mb-4">Tell us about your car</h2>
          <div className="grid gap-3 sm:gap-4 sm:grid-cols-3">
            <Input
              id="make"
              value={make}
              onChange={setMake}
              placeholder="Toyota"
              label="Make"
              maxLength={100}
              disabled={isAnalyzing}
              required
            />
            <Input
              id="model"
              value={model}
              onChange={setModel}
              placeholder="Camry"
              label="Model"
              maxLength={100}
              disabled={isAnalyzing}
              required
            />
            <Input
              id="year"
              value={year}
              onChange={setYear}
              placeholder="2020 (optional)"
              label="Year"
              type="number"
              disabled={isAnalyzing}
            />
          </div>

          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="mt-3 text-sm text-brand-600 hover:text-brand-700 font-medium"
          >
            {showAdvanced ? 'Hide optional details' : 'Add more details (optional)'}
          </button>

          {showAdvanced && (
            <div className="mt-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Is the check-engine light on?
                </label>
                <div className="flex gap-3">
                  {['Yes', 'No', 'Not sure'].map((option) => (
                    <button
                      key={option}
                      type="button"
                      onClick={() => setCheckEngineLight(option.toLowerCase())}
                      className={cn(
                        'flex-1 rounded-md border px-3 py-2.5 text-sm font-medium transition-colors min-h-[44px]',
                        checkEngineLight === option.toLowerCase()
                          ? 'border-brand-500 bg-brand-50 text-brand-700'
                          : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-50'
                      )}
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </div>

              <Input
                id="vin"
                value={vin}
                onChange={setVin}
                placeholder="1HGCM82633A123456 (optional)"
                label="VIN"
                maxLength={17}
                disabled={isAnalyzing}
                helperText="Optional. Helps with a more vehicle-specific diagnosis."
              />

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Have a diagnostic code? (optional)
                </label>
                <p className="text-xs text-slate-500 mb-2">
                  Your code may look something like P0171.
                </p>
                <Input
                  id="dtc"
                  value={dtcCodes.join(', ')}
                  onChange={(value) => {
                    const codes = value.split(',').map(c => c.trim().toUpperCase()).filter(c => /^[PCBU][0-9]{4}$/i.test(c));
                    setDtcCodes(codes);
                  }}
                  placeholder="P0171"
                  label=""
                  disabled={isAnalyzing}
                />
              </div>
            </div>
          )}
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4 sm:p-5 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900 mb-4">What's wrong?</h2>
          <Textarea
            id="symptoms"
            value={symptomText}
            onChange={setSymptomText}
            placeholder="Tell us what you're experiencing. For example: My car takes a long time to start and sometimes stalls..."
            label=""
            required
            maxLength={4000}
            error={localError && !symptomText.trim() ? 'Please describe the symptoms.' : undefined}
            helperText={`${symptomText.length}/4000 characters`}
            disabled={isAnalyzing}
            rows={4}
          />
        </div>

        {awaitingFollowUp && followUpQuestion && (
          <div className="mt-4 sm:mt-6 rounded-lg border border-amber-200 bg-amber-50 p-4 sm:p-5 shadow-sm">
            <h3 className="text-base font-semibold text-amber-900 mb-3">
              We need a little more information
            </h3>
            <p className="text-sm text-amber-800 mb-2">{followUpQuestion}</p>
            {followUpReason && (
              <p className="text-xs text-amber-700 mb-4">{followUpReason}</p>
            )}
            <div className="flex flex-col sm:flex-row gap-3">
              <Textarea
                id="followUpAnswer"
                value={followUpAnswer}
                onChange={(value) => setFollowUpAnswer(value)}
                placeholder="Your answer..."
                label=""
                required
                maxLength={4000}
                disabled={isAnalyzing}
              />
              <Button
                type="button"
                onClick={handleSubmit}
                disabled={isAnalyzing || !followUpAnswer.trim()}
                className="min-w-[160px]"
              >
                {isAnalyzing ? 'Submitting...' : 'Submit Answer'}
              </Button>
            </div>
          </div>
        )}

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <Button type="submit" disabled={isAnalyzing} loading={isAnalyzing} className="min-w-[160px]">
            {isAnalyzing ? 'Analyzing...' : 'Diagnose my car'}
          </Button>
          {sessionId && !isAnalyzing && !awaitingFollowUp && (
            <Button type="button" variant="secondary" onClick={handleContinueSession}>
              Continue in Session
            </Button>
          )}
        </div>
      </form>

      {isAnalyzing && (
        <div className="mt-6 sm:mt-8 space-y-3">
          <div className="flex items-center gap-3 rounded-lg border border-dashed border-slate-300 p-4 sm:p-6">
            <svg className="h-5 w-5 animate-spin text-brand-600" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <span className="text-sm text-slate-600">Looking at your symptoms...</span>
          </div>
          <div className="flex items-center gap-3 rounded-lg border border-dashed border-slate-300 p-4 sm:p-6">
            <svg className="h-5 w-5 animate-spin text-brand-600" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <span className="text-sm text-slate-600">Checking common causes...</span>
          </div>
          <div className="flex items-center gap-3 rounded-lg border border-dashed border-slate-300 p-4 sm:p-6">
            <svg className="h-5 w-5 animate-spin text-brand-600" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <span className="text-sm text-slate-600">Preparing your diagnosis...</span>
          </div>
        </div>
      )}

      {showResults && (
        <div className="mt-6 sm:mt-8 space-y-4 sm:space-y-6">
          {isFromCache && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4" role="status" aria-live="polite">
              <div className="flex items-start gap-3">
                <svg className="h-5 w-5 shrink-0 text-amber-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.88c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.516-2.625l6.28-10.88zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
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

          {apiState.data && (
            <div className="rounded-lg border border-brand-200 bg-brand-50 p-4">
              <h3 className="text-sm font-semibold text-brand-900">
                Analysis Complete
              </h3>
              <p className="mt-1 text-sm text-brand-700">
                {apiState.data.hypotheses.length} possible {apiState.data.hypotheses.length === 1 ? 'cause' : 'causes'} found
              </p>
            </div>
          )}

          {hasComponentHighlights && (
            <Vehicle3DViewer
              vehicleType={currentVehicleType}
              highlightedComponents={highlightedComponents}
              selectedComponent={selectedComponent}
              onComponentSelect={handle3DComponentSelect}
            />
          )}

          {displayResults.length > 0 && (
            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-3">
                {displayResults.length === 1 ? 'Most likely cause' : 'Possible causes'}
              </h3>
              <div className="space-y-3 sm:space-y-4">
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
                      safety_tier: result.safety_tier as import('../types/api').RepairSafetyTier | undefined,
                      safety_tier_label: result.safety_tier_label,
                      safety_tier_description: result.safety_tier_description,
                      safety_tier_reasoning: result.safety_tier_reasoning,
                      differential_rank: result.differential_rank,
                      evidence_quality: result.evidence_quality,
                    }}
                    resultId={result.id}
                    currentStatus={(result.hypothesis_status || 'proposed') as import('../types/api').HypothesisStatus}
                    onUpdateStatus={handleOutcomeUpdate}
                    onConfirmedFix={handleConfirmedFix}
                    updating={false}
                    isSelected={selectedHypothesisId === result.id}
                    onSelect={() => setSelectedHypothesisId(result.id)}
                    isTopHypothesis={index === 0}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}








