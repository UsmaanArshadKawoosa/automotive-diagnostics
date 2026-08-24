import { useEffect, useCallback, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Card, CardHeader, CardBody } from '../components/Card';
import { Input, Textarea, Button } from '../components/Form';
import { DtcInput } from '../components/DtcInput';
import { ErrorMessage } from '../components/Alert';
import { HypothesisCard, CheckOutcomeSection } from '../components/DiagnosticResults';
import { useSession, useUpdateOutcome, useCreateCheck, useUpdateCheck, useAnalyzeInSession } from '../hooks/useDiagnostics';
import { useOnlineStatus } from '../hooks/useOnlineStatus';
import { useCachedSession } from '../hooks/useCachedSession';
import type { DiagnosticResult, HypothesisStatus, DiagnosticCheckOutcomeUpdate, DiagnosticAnalyzeRequest } from '../types/api';

const DTC_REGEX = /^[PCBU][0-9]{4}$/i;

export function SessionDetailPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const isOnline = useOnlineStatus();
  const { loadSession, ...apiState } = useSession();
  const { updateOutcome, ...outcomeState } = useUpdateOutcome();
  const { createCheck, ...createCheckState } = useCreateCheck();
  const { updateCheck, ...updateCheckState } = useUpdateCheck();
  const { analyzeInSession, ...followUpState } = useAnalyzeInSession();
  const [results, setResults] = useState<DiagnosticResult[]>([]);
  const [symptomText, setSymptomText] = useState('');
  const [dtcCodes, setDtcCodes] = useState<string[]>([]);
  const [make, setMake] = useState('');
  const [model, setModel] = useState('');
  const [year, setYear] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);
  const { cachedSession, isFromCache, saveToCache } = useCachedSession(sessionId || null);

  useEffect(() => {
    if (sessionId) loadSession(sessionId);
  }, [sessionId, loadSession]);

  useEffect(() => {
    if (apiState.data) {
      setResults(apiState.data.results || []);
      if (sessionId) {
        saveToCache({
          session: {
            ...apiState.data,
            vin: apiState.data.vin ?? null,
            make: apiState.data.make ?? null,
            model: apiState.data.model ?? null,
            year: apiState.data.year ?? null,
            dtc_codes: apiState.data.dtc_codes ?? null,
          },
          results: apiState.data.results || [],
          conversation_messages: apiState.data.conversation_messages || [],
          evidence: [],
        }, sessionId);
      }
    }
  }, [apiState.data, sessionId, saveToCache]);

  const refresh = useCallback(async () => {
    if (!sessionId) return;
    await loadSession(sessionId);
  }, [sessionId, loadSession]);

  const handleOutcomeUpdate = useCallback(
    async (resultId: string, status: HypothesisStatus) => {
      await updateOutcome(resultId, { hypothesis_status: status });
      await refresh();
    },
    [updateOutcome, refresh]
  );

  const handleCreateCheck = useCallback(
    async (resultId: string, description: string) => {
      await createCheck(resultId, { check_description: description });
      await refresh();
    },
    [createCheck, refresh]
  );

  const handleUpdateCheck = useCallback(
    async (outcomeId: string, status: string, observedResult?: string) => {
      const payload: DiagnosticCheckOutcomeUpdate = { status: status as any };
      if (observedResult) payload.observed_result = observedResult;
      await updateCheck(outcomeId, payload);
      await refresh();
    },
    [updateCheck, refresh]
  );

  const validateFollowUp = useCallback((): string | null => {
    if (!symptomText.trim()) return 'Please describe additional symptoms.';
    if (symptomText.length > 4000) return 'Symptoms must not exceed 4000 characters.';
    if (year) {
      const yr = Number(year);
      if (yr < 1900 || yr > 2100) return 'Year must be between 1900 and 2100.';
    }
    for (const code of dtcCodes) {
      if (!DTC_REGEX.test(code)) return `Invalid DTC code: ${code}`;
    }
    return null;
  }, [symptomText, year, dtcCodes]);

  const handleFollowUpSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!sessionId) return;
      if (!isOnline) {
        setLocalError('A live connection is required to run a follow-up diagnosis. Please check your network connection and try again.');
        return;
      }
      const validationError = validateFollowUp();
      if (validationError) {
        setLocalError(validationError);
        return;
      }
      setLocalError(null);
      const payload: DiagnosticAnalyzeRequest = {
        session_id: sessionId,
        make: make || undefined,
        model: model || undefined,
        year: year ? Number(year) : undefined,
        dtc_codes: dtcCodes.length > 0 ? dtcCodes : undefined,
        symptom_text: symptomText.trim(),
      };
      await analyzeInSession(sessionId, payload);
      setSymptomText('');
      setDtcCodes([]);
      setMake('');
      setModel('');
      setYear('');
    },
    [sessionId, validateFollowUp, make, model, year, dtcCodes, symptomText, analyzeInSession, isOnline]
  );

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  if (apiState.loading) {
    return (
      <div className="mx-auto max-w-4xl">
        <div className="mb-6 flex items-center justify-between">
          <div className="h-8 w-48 animate-pulse rounded bg-slate-200" />
          <div className="h-9 w-36 animate-pulse rounded bg-slate-200" />
        </div>
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-1 space-y-6">
            <div className="h-48 animate-pulse rounded-lg border border-slate-200 bg-slate-100" />
            <div className="h-32 animate-pulse rounded-lg border border-slate-200 bg-slate-100" />
          </div>
          <div className="lg:col-span-2 space-y-6">
            <div className="h-32 animate-pulse rounded-lg border border-slate-200 bg-slate-100" />
            <div className="h-64 animate-pulse rounded-lg border border-slate-200 bg-slate-100" />
          </div>
        </div>
      </div>
    );
  }

  if (apiState.error || !apiState.data) {
    if (isFromCache && cachedSession) {
      const session = cachedSession.data.session;
      return (
        <div className="mx-auto max-w-4xl">
          <div className="mb-4">
            <button type="button" onClick={() => navigate('/sessions')} className="text-sm text-brand-600 hover:text-brand-700">
              ← Back to Sessions
            </button>
          </div>
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 mb-6" role="status" aria-live="polite">
            <div className="flex items-start gap-3">
              <svg className="h-5 w-5 shrink-0 text-amber-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.88c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.516-2.625l6.28-10.88zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
              </svg>
              <div>
                <p className="text-sm font-medium text-amber-800">Viewing cached session data</p>
                <p className="mt-0.5 text-xs text-amber-700">
                  This information was loaded previously and may not reflect the current state. Cached on {new Date(cachedSession.cachedAt).toLocaleString()}.
                </p>
              </div>
            </div>
          </div>
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-1 space-y-6">
              <Card>
                <CardHeader title="Vehicle Information" />
                <CardBody>
                  <dl className="space-y-3 text-sm">
                    {session.vin && (
                      <div>
                        <dt className="text-slate-500">VIN</dt>
                        <dd className="mt-0.5 font-mono text-slate-900">{session.vin}</dd>
                      </div>
                    )}
                    {session.make && (
                      <div>
                        <dt className="text-slate-500">Make</dt>
                        <dd className="mt-0.5 text-slate-900">{session.make}</dd>
                      </div>
                    )}
                    {session.model && (
                      <div>
                        <dt className="text-slate-500">Model</dt>
                        <dd className="mt-0.5 text-slate-900">{session.model}</dd>
                      </div>
                    )}
                    {session.year && (
                      <div>
                        <dt className="text-slate-500">Year</dt>
                        <dd className="mt-0.5 text-slate-900">{session.year}</dd>
                      </div>
                    )}
                  </dl>
                </CardBody>
              </Card>
              <Card>
                <CardHeader title="Session Details" />
                <CardBody>
                  <dl className="space-y-3 text-sm">
                    <div>
                      <dt className="text-slate-500">Created</dt>
                      <dd className="mt-0.5 text-slate-900">{new Date(session.created_at).toLocaleString()}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-500">Updated</dt>
                      <dd className="mt-0.5 text-slate-900">{new Date(session.updated_at).toLocaleString()}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-500">Session ID</dt>
                      <dd className="mt-0.5 break-all font-mono text-xs text-slate-600">{session.id}</dd>
                    </div>
                  </dl>
                </CardBody>
              </Card>
            </div>
            <div className="lg:col-span-2 space-y-6">
              <Card>
                <CardHeader title="Symptoms" />
                <CardBody>
                  <p className="text-sm text-slate-700 whitespace-pre-wrap">{session.symptom_text}</p>
                  {session.dtc_codes && (
                    <div className="mt-3">
                      <span className="text-xs font-medium uppercase tracking-wider text-slate-500">DTC Codes</span>
                      <div className="mt-1.5 flex flex-wrap gap-2">
                        {session.dtc_codes.split(',').map((code) => (
                          <span key={code.trim()} className="rounded-md bg-brand-50 px-2 py-1 font-mono text-sm text-brand-700 ring-1 ring-inset ring-brand-700/10">
                            {code.trim()}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </CardBody>
              </Card>
              {cachedSession.data.results.length > 0 && (
                <div>
                  <h3 className="text-base font-semibold text-slate-900 mb-3">
                    Diagnostic Results ({cachedSession.data.results.length})
                  </h3>
                  <div className="space-y-4">
                    {cachedSession.data.results.map((result) => (
                      <div key={result.id}>
                        <HypothesisCard
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
                          onUpdateStatus={async () => {}}
                          updating={false}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      );
    }
    return (
      <div className="mx-auto max-w-3xl">
        <div className="mb-4">
          <button type="button" onClick={() => navigate('/sessions')} className="text-sm text-brand-600 hover:text-brand-700">
            ← Back to Sessions
          </button>
        </div>
        <ErrorMessage message={apiState.error || 'Session not found'} onRetry={refresh} />
      </div>
    );
  }

  const session = apiState.data;

  return (
    <div className="mx-auto max-w-4xl">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <button type="button" onClick={() => navigate('/sessions')} className="text-sm text-brand-600 hover:text-brand-700">
              ← Back to Sessions
            </button>
            <h1 className="mt-2 text-2xl font-bold text-slate-900">
              Session {session.id.slice(0, 8)}...
            </h1>
          </div>
          <Link
            to={`/diagnose`}
            className="inline-flex items-center rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            New Diagnosis
          </Link>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-1 space-y-6">
            <Card>
              <CardHeader title="Vehicle Information" />
              <CardBody>
                <dl className="space-y-3 text-sm">
                  {session.vin && (
                    <div>
                      <dt className="text-slate-500">VIN</dt>
                      <dd className="mt-0.5 font-mono text-slate-900">{session.vin}</dd>
                    </div>
                  )}
                  {session.make && (
                    <div>
                      <dt className="text-slate-500">Make</dt>
                      <dd className="mt-0.5 text-slate-900">{session.make}</dd>
                    </div>
                  )}
                  {session.model && (
                    <div>
                      <dt className="text-slate-500">Model</dt>
                      <dd className="mt-0.5 text-slate-900">{session.model}</dd>
                    </div>
                  )}
                  {session.year && (
                    <div>
                      <dt className="text-slate-500">Year</dt>
                      <dd className="mt-0.5 text-slate-900">{session.year}</dd>
                    </div>
                  )}
                </dl>
              </CardBody>
            </Card>

            <Card>
              <CardHeader title="Session Details" />
              <CardBody>
                <dl className="space-y-3 text-sm">
                  <div>
                    <dt className="text-slate-500">Created</dt>
                    <dd className="mt-0.5 text-slate-900">{formatDate(session.created_at)}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Updated</dt>
                    <dd className="mt-0.5 text-slate-900">{formatDate(session.updated_at)}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Session ID</dt>
                    <dd className="mt-0.5 break-all font-mono text-xs text-slate-600">{session.id}</dd>
                  </div>
                </dl>
              </CardBody>
            </Card>
          </div>

          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader title="Symptoms" />
              <CardBody>
                <p className="text-sm text-slate-700 whitespace-pre-wrap">{session.symptom_text}</p>
                {session.dtc_codes && (
                  <div className="mt-3">
                    <span className="text-xs font-medium uppercase tracking-wider text-slate-500">DTC Codes</span>
                    <div className="mt-1.5 flex flex-wrap gap-2">
                      {session.dtc_codes.split(',').map((code) => (
                        <span key={code.trim()} className="rounded-md bg-brand-50 px-2 py-1 font-mono text-sm text-brand-700 ring-1 ring-inset ring-brand-700/10">
                          {code.trim()}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </CardBody>
            </Card>

            {results.length > 0 && (
              <div>
                <h3 className="text-base font-semibold text-slate-900 mb-3">
                  Diagnostic Results ({results.length})
                </h3>
                <div className="space-y-4">
                  {results.map((result) => (
                    <div key={result.id}>
                      <HypothesisCard
                        hypothesis={{
                          fault_description: result.fault_description,
                          confidence_score: result.confidence_score,
                          severity: result.severity || 'low',
                          supporting_evidence: result.supporting_evidence,
                          recommended_checks: result.recommended_checks,
                          repair_suggestion: result.repair_suggestion,
                        }}
                        resultId={result.id}
                        currentStatus={result.hypothesis_status}
                        onUpdateStatus={handleOutcomeUpdate}
                        updating={outcomeState.loading}
                      />
                      <CheckOutcomeSection
                        resultId={result.id}
                        checks={result.check_outcomes}
                        recommended_checks={result.recommended_checks}
                        onCreateCheck={handleCreateCheck}
                        onUpdateCheck={handleUpdateCheck}
                        loading={createCheckState.loading || updateCheckState.loading}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {results.length === 0 && (
              <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center">
                <p className="text-sm text-slate-500">No diagnostic results yet for this session.</p>
              </div>
            )}

            <Card>
              <CardHeader title="Continue Diagnosis" subtitle="Add additional symptoms or DTC codes for follow-up analysis" />
              <CardBody>
                <form onSubmit={handleFollowUpSubmit} className="space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <Input
                      id="follow-make"
                      value={make}
                      onChange={setMake}
                      placeholder="Toyota"
                      label="Make"
                      maxLength={100}
                    />
                    <Input
                      id="follow-model"
                      value={model}
                      onChange={setModel}
                      placeholder="Camry"
                      label="Model"
                      maxLength={100}
                    />
                    <Input
                      id="follow-year"
                      value={year}
                      onChange={setYear}
                      placeholder="2020"
                      label="Year"
                      type="number"
                    />
                  </div>
                  <DtcInput codes={dtcCodes} onChange={setDtcCodes} />
                  <Textarea
                    id="follow-symptoms"
                    value={symptomText}
                    onChange={setSymptomText}
                    placeholder="Describe additional symptoms or changes since the last diagnosis..."
                    label="Additional Symptoms"
                    required
                    maxLength={4000}
                  />
                  {localError && (
                    <p className="text-sm text-red-600">{localError}</p>
                  )}
                  {followUpState.error && (
                    <ErrorMessage message={followUpState.error} />
                  )}
                  <Button type="submit" disabled={followUpState.loading}>
                    {followUpState.loading ? 'Analyzing...' : 'Run Follow-up Diagnosis'}
                  </Button>
                </form>
              </CardBody>
            </Card>
          </div>
        </div>
      </div>
    );
  }
