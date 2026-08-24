import { useState, useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Input, Textarea, Button, Select } from '../components/Form';
import { DtcInput } from '../components/DtcInput';
import { HypothesisCard } from '../components/DiagnosticResults';
import { Vehicle3DViewer } from '../components/Vehicle3DViewer';
import { Alert, ErrorMessage } from '../components/Alert';
import { useAnalyze } from '../hooks/useDiagnostics';
import { useOnlineStatus } from '../hooks/useOnlineStatus';
import { useCachedSession } from '../hooks/useCachedSession';
import { VEHICLE_TYPES } from '../config/vehicleTypes';
import { cn } from '../utils/cn';
import type { DiagnosticAnalyzeRequest, DiagnosticHypothesis, DiagnosticResult, DiagnosticConversationMessage } from '../types/api';
import type { HypothesisStatus, VehicleType } from '../types/api';
import type { ComponentHighlight } from '../components/Vehicle3DViewer';

const DTC_REGEX = /^[PCBU][0-9]{4}$/i;

export function DiagnosePage() {
  const navigate = useNavigate();
  const isOnline = useOnlineStatus();
  const { analyze, ...apiState } = useAnalyze();
  const [vin, setVin] = useState('');
  const [make, setMake] = useState('');
  const [model, setModel] = useState('');
  const [year, setYear] = useState('');
  const [vehicleType, setVehicleType] = useState<VehicleType | ''>('');
  const [dtcCodes, setDtcCodes] = useState<string[]>([]);
  const [symptomText, setSymptomText] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [results, setResults] = useState<DiagnosticResult[]>([]);
  const [conversationMessages, setConversationMessages] = useState<DiagnosticConversationMessage[]>([]);
  const [loadingSession, setLoadingSession] = useState(false);
  const [selectedComponent, setSelectedComponent] = useState<{ component_id: string; system_category?: string; vehicle_region?: string } | null>(null);
  const [selectedHypothesisId, setSelectedHypothesisId] = useState<string | null>(null);
  const [followUpQuestion, setFollowUpQuestion] = useState<string | null>(null);
  const [followUpReason, setFollowUpReason] = useState<string | null>(null);
  const [followUpAnswer, setFollowUpAnswer] = useState('');
  const [awaitingFollowUp, setAwaitingFollowUp] = useState(false);
  const hypothesisCardsRef = useRef<Map<string, HTMLDivElement>>(new Map());
  const { cachedSession, isFromCache, saveToCache } = useCachedSession(sessionId);

  useEffect(() => {
    if (apiState.data) {
      const sid = apiState.data.session_id;
      setSessionId(sid);
      loadSessionResults(sid);

      // Handle follow-up question flow
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
       setConversationMessages(session.conversation_messages || []);
       saveToCache({
         session: session,
         results: session.results || [],
         conversation_messages: session.conversation_messages || [],
         evidence: session.evidence || [],
       }, sid);
     } catch {
       // silently ignore, results will be empty
     } finally {
       setLoadingSession(false);
     }
   };

   const validate = useCallback((): string | null => {
     if (!symptomText.trim()) return 'Please describe the symptoms.';
     if (symptomText.length > 4000) return 'Symptoms must not exceed 4000 characters.';
     if (vin && vin.length !== 17) return 'VIN must be exactly 17 characters if provided.';
     if (vin && /[IOQ]/i.test(vin)) return 'VIN cannot contain I, O, or Q.';
     if (year) {
       const yr = Number(year);
       if (yr < 1900 || yr > 2100) return 'Year must be between 1900 and 2100.';
     }
     for (const code of dtcCodes) {
       if (!DTC_REGEX.test(code)) return `Invalid DTC code: ${code}`;
     }
     return null;
   }, [symptomText, vin, year, dtcCodes]);

   const fieldErrors = useCallback(() => {
     const errors: Record<string, string> = {};
     if (!symptomText.trim()) errors.symptomText = 'Please describe the symptoms.';
     else if (symptomText.length > 4000) errors.symptomText = 'Symptoms must not exceed 4000 characters.';
     if (vin && vin.length !== 17) errors.vin = 'VIN must be exactly 17 characters if provided.';
     if (vin && /[IOQ]/i.test(vin)) errors.vin = 'VIN cannot contain I, O, or Q.';
     if (year) {
       const yr = Number(year);
       if (yr < 1900 || yr > 2100) errors.year = 'Year must be between 1900 and 2100.';
     }
     if (dtcCodes.some((code) => !DTC_REGEX.test(code))) {
       errors.dtcCodes = 'One or more DTC codes are invalid.';
     }
     return errors;
   }, [symptomText, vin, year, dtcCodes]);

   const currentErrors = fieldErrors();

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
        vehicle_type: vehicleType || undefined,
        dtc_codes: dtcCodes.length > 0 ? dtcCodes : undefined,
        symptom_text: symptomText.trim(),
        session_id: awaitingFollowUp ? sessionId || undefined : undefined,
        follow_up_answer: awaitingFollowUp ? followUpAnswer.trim() : undefined,
      };
      await analyze(payload);
    },
    [validate, vin, make, model, year, vehicleType, dtcCodes, symptomText, analyze, awaitingFollowUp, sessionId, followUpAnswer, isOnline]
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

  const handleContinueSession = useCallback(async () => {
    if (!sessionId) return;
    await loadSessionResults(sessionId);
    navigate(`/sessions/${sessionId}`);
  }, [sessionId, navigate]);

  const currentVehicleType = (apiState.data?.vehicle?.vehicle_type as VehicleType) || vehicleType || 'sedan';
  const analysisHypotheses: DiagnosticHypothesis[] = apiState.data?.hypotheses || [];
  const hasComponentHighlights = analysisHypotheses.some((h) => h.component_id) || (isFromCache && cachedSession && cachedSession.data.results.some((r) => r.component_id));

  const handle3DComponentSelect = useCallback((component: { component_id: string; system_category?: string; vehicle_region?: string } | null) => {
    setSelectedComponent(component);
    if (component) {
      // Find all hypotheses with matching component_id and select the highest-confidence one
      const matchingHypotheses = analysisHypotheses.filter((h) => h.component_id === component.component_id);
      if (matchingHypotheses.length > 0) {
        const highestConfidence = matchingHypotheses.reduce((max, h) => 
          h.confidence_score > max.confidence_score ? h : max
        );
        const hypothesisIndex = analysisHypotheses.findIndex((h) => h.component_id === component.component_id && h.confidence_score === highestConfidence.confidence_score);
        const hypothesisId = `hypothesis-${hypothesisIndex}`;
        setSelectedHypothesisId(hypothesisId);
        
        // Scroll the selected hypothesis into view
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
  }, [analysisHypotheses]);

  const displayResults = analysisHypotheses.length > 0
    ? analysisHypotheses.map((h, idx) => ({
        ...h,
        id: `hypothesis-${idx}`,
        session_id: sessionId || '',
        hypothesis_status: 'proposed' as HypothesisStatus,
        check_outcomes: [],
      }))
    : isFromCache && cachedSession
      ? cachedSession.data.results.map((r, idx) => ({
          ...r,
          id: r.id || `cached-hypothesis-${idx}`,
          session_id: sessionId || r.id || '',
        }))
      : results;

  return (
    <div className="mx-auto max-w-3xl px-4 sm:px-6">
      <div className="mb-6 sm:mb-8">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-900">New Diagnosis</h1>
        <p className="mt-1 text-sm sm:text-base text-slate-600">
          Enter vehicle information, DTC codes, and symptoms to generate a diagnostic analysis.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-6">
        {localError && (
          <Alert type="error" title="Validation Error">
            {localError}
          </Alert>
        )}

        {apiState.error && (
          <ErrorMessage message={apiState.error} />
        )}

        <div className="rounded-lg border border-slate-200 bg-white p-4 sm:p-5 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900 mb-4">Vehicle Information</h2>
          <div className="grid gap-3 sm:gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Input
              id="make"
              value={make}
              onChange={setMake}
              placeholder="Toyota"
              label="Make"
              maxLength={100}
              disabled={apiState.loading}
            />
            <Input
              id="model"
              value={model}
              onChange={setModel}
              placeholder="Camry"
              label="Model"
              maxLength={100}
              disabled={apiState.loading}
            />
            <Input
              id="year"
              value={year}
              onChange={setYear}
              placeholder="2020"
              label="Year"
              type="number"
              error={currentErrors.year}
              disabled={apiState.loading}
            />
            <Input
              id="vin"
              value={vin}
              onChange={setVin}
              placeholder="1HGCM82633A123456"
              label="VIN (optional)"
              maxLength={17}
              error={currentErrors.vin}
              disabled={apiState.loading}
            />
          </div>
          <div className="mt-3 sm:mt-4">
            <Select
              id="vehicleType"
              value={vehicleType}
              onChange={(val) => setVehicleType(val as VehicleType)}
              options={VEHICLE_TYPES.map((vt) => ({ value: vt, label: vt.charAt(0).toUpperCase() + vt.slice(1) }))}
              placeholder="Select vehicle type"
              label="Vehicle Type"
              helperText="Optional. Helps narrow diagnosis to vehicle-specific patterns."
              disabled={apiState.loading}
            />
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4 sm:p-5 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900 mb-4">Diagnostic Information</h2>
          <div className="space-y-4">
            <DtcInput
              codes={dtcCodes}
              onChange={setDtcCodes}
              error={currentErrors.dtcCodes}
              disabled={apiState.loading}
            />
            <Textarea
              id="symptoms"
              value={symptomText}
              onChange={setSymptomText}
              placeholder="Describe the symptoms you are experiencing. For example: Engine hesitates during acceleration and idles roughly..."
              label="Symptoms"
              required
              maxLength={4000}
              error={currentErrors.symptomText}
              helperText={`${symptomText.length}/4000 characters`}
              disabled={apiState.loading}
            />
          </div>
        </div>

        {awaitingFollowUp && followUpQuestion && (
          <div className="mt-4 sm:mt-6 rounded-lg border border-amber-200 bg-amber-50 p-4 sm:p-5 shadow-sm">
            <h3 className="text-base font-semibold text-amber-900 mb-3">
              Additional Information Needed
            </h3>
            <p className="text-sm text-amber-800 mb-2">{followUpQuestion}</p>
            {followUpReason && (
              <p className="text-xs text-amber-700 mb-4">Why: {followUpReason}</p>
            )}
            <div className="flex flex-col sm:flex-row gap-3">
              <Textarea
                id="followUpAnswer"
                value={followUpAnswer}
                onChange={(value) => setFollowUpAnswer(value)}
                placeholder="Your answer..."
                label="Your Answer"
                required
                maxLength={4000}
                disabled={apiState.loading}
              />
              <Button
                type="button"
                onClick={handleSubmit}
                disabled={apiState.loading || !followUpAnswer.trim()}
                className="min-w-[160px]"
              >
                {apiState.loading ? 'Submitting...' : 'Submit Answer'}
              </Button>
            </div>
          </div>
        )}

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <Button type="submit" disabled={apiState.loading} loading={apiState.loading} className="min-w-[160px]">
            {apiState.loading ? 'Analyzing...' : 'Run Diagnosis'}
          </Button>
          {sessionId && !apiState.loading && !awaitingFollowUp && (
            <Button type="button" variant="secondary" onClick={handleContinueSession}>
              Continue in Session
            </Button>
          )}
        </div>
      </form>

      {loadingSession && (
        <div className="mt-6 sm:mt-8 flex items-center gap-3 rounded-lg border border-dashed border-slate-300 p-4 sm:p-6">
          <svg className="h-5 w-5 animate-spin text-brand-600" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm text-slate-600">Loading session details...</span>
        </div>
      )}

      {((apiState.data && !apiState.loading && !loadingSession) || (isFromCache && cachedSession && !isOnline)) && (
        <div className="mt-6 sm:mt-8 space-y-4 sm:space-y-6">
          {isFromCache && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4" role="status" aria-live="polite">
              <div className="flex items-start gap-3">
                <svg className="h-5 w-5 shrink-0 text-amber-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.88c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.516-2.625l6.28-10.88zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                </svg>
                <div>
                  <p className="text-sm font-medium text-amber-800">Viewing cached session data</p>
                  <p className="mt-0.5 text-xs text-amber-700">
                    This information was loaded previously and may not reflect the current state. Cached on {cachedSession ? new Date(cachedSession.cachedAt).toLocaleString() : ''}.
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
                Session ID: <code className="rounded bg-brand-100 px-1.5 py-0.5 font-mono text-xs break-all">{apiState.data.session_id}</code>
              </p>
              <p className="mt-1 text-sm text-brand-700">
                {apiState.data.hypotheses.length} hypotheses generated
              </p>
              {currentVehicleType && (
                <p className="mt-1 text-sm text-brand-700">
                  Vehicle type: <span className="font-medium capitalize">{currentVehicleType}</span>
                </p>
              )}
            </div>
          )}

          {isFromCache && cachedSession && !apiState.data && (
            <div className="rounded-lg border border-brand-200 bg-brand-50 p-4">
              <h3 className="text-sm font-semibold text-brand-900">
                Cached Session
              </h3>
              <p className="mt-1 text-sm text-brand-700">
                Session ID: <code className="rounded bg-brand-100 px-1.5 py-0.5 font-mono text-xs break-all">{cachedSession.data.session.id}</code>
              </p>
              <p className="mt-1 text-sm text-brand-700">
                {cachedSession.data.results.length} results
              </p>
              <p className="mt-1 text-sm text-brand-700">
                Vehicle: <span className="font-medium capitalize">{cachedSession.data.session.make || 'Unknown'} {cachedSession.data.session.model || ''}</span>
              </p>
            </div>
          )}

           {(conversationMessages.length > 0 || (isFromCache && cachedSession && cachedSession.data.conversation_messages.length > 0)) && (
             <div className="rounded-lg border border-slate-200 bg-white p-4 sm:p-5 shadow-sm">
               <h3 className="text-base font-semibold text-slate-900 mb-3">
                 Conversation History
               </h3>
               <div className="space-y-3 sm:space-y-4">
                 {(isFromCache && cachedSession ? cachedSession.data.conversation_messages : conversationMessages).map((msg) => (
                   <div
                     key={msg.id}
                     className={`flex gap-2 sm:gap-3 ${
                       msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'
                     }`}
                   >
                     <div
                       className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-medium ${
                         msg.role === 'user'
                           ? 'bg-slate-600'
                           : 'bg-brand-600'
                       }`}
                     >
                       {msg.role === 'user' ? 'U' : 'A'}
                     </div>
                     <div
                       className={`flex-1 min-w-0 rounded-lg p-3 ${
                         msg.role === 'user'
                           ? 'bg-slate-100 text-slate-900'
                           : 'bg-brand-50 text-slate-900 border border-brand-100'
                       }`}
                     >
                       <p className="text-sm">{msg.content}</p>
                       <p className="mt-1 text-xs text-slate-400">
                         {new Date(msg.created_at).toLocaleTimeString()}
                       </p>
                     </div>
                   </div>
                 ))}
               </div>
             </div>
           )}

            {hasComponentHighlights && (
              <Vehicle3DViewer
                vehicleType={currentVehicleType}
                highlightedComponents={(isFromCache && cachedSession ? cachedSession.data.results : analysisHypotheses)
                  .filter((h) => h.component_id)
                  .map((h) => ({
                    component_id: h.component_id!,
                    system_category: h.system_category,
                    vehicle_region: h.vehicle_region,
                    safety_tier: h.safety_tier as ComponentHighlight['safety_tier'],
                    safety_tier_label: h.safety_tier_label,
                    safety_tier_description: h.safety_tier_description,
                    safety_tier_reasoning: h.safety_tier_reasoning,
                  }))}
                selectedComponent={selectedComponent}
                onComponentSelect={handle3DComponentSelect}
              />
            )}

            {((apiState.data?.evidence && apiState.data.evidence.length > 0) || (isFromCache && cachedSession && cachedSession.data.evidence.length > 0)) && (
              <div className="rounded-lg border border-slate-200 bg-white p-4 sm:p-5 shadow-sm">
                <h3 className="text-base font-semibold text-slate-900 mb-3">
                  Evidence ({(isFromCache && cachedSession ? cachedSession.data.evidence.length : apiState.data?.evidence?.length || 0)} items)
                </h3>
                <div className="space-y-2 sm:space-y-3">
                  {(isFromCache && cachedSession ? cachedSession.data.evidence : apiState.data?.evidence || []).map((item) => {
                    const similarity = Math.round(item.similarity_score * 100);
                    const similarityColor = similarity >= 80 ? 'text-green-700 bg-green-50' : similarity >= 60 ? 'text-amber-700 bg-amber-50' : 'text-slate-600 bg-slate-50';
                    return (
                      <div key={item.id} className="rounded-md border border-slate-100 bg-slate-50 p-3">
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-xs font-medium uppercase tracking-wider text-slate-500">
                            {item.category}
                          </span>
                          <span className={cn('text-xs font-mono font-medium px-2 py-0.5 rounded-full', similarityColor)}>
                            {similarity}% match
                          </span>
                        </div>
                        <p className="mt-1.5 sm:mt-2 text-sm text-slate-700">{item.content}</p>
                        <div className="mt-1.5 sm:mt-2 flex items-center justify-between gap-3 text-xs text-slate-400">
                          {item.source && (
                            <span>Source: {item.source}</span>
                          )}
                          {item.entry_key && (
                            <span className="font-mono">{item.entry_key}</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

          {displayResults.length > 0 && (
            <div>
              <h3 className="text-base font-semibold text-slate-900 mb-3">
                Hypotheses ({displayResults.length})
              </h3>
              <div className="space-y-3 sm:space-y-4">
                {displayResults.map((result, index) => (
                    <HypothesisCard
                      key={result.id}
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
};
