import { useState, useMemo } from 'react';
import { Button } from './Form';
import type { Severity, HypothesisStatus } from '../types/api';
import { SeverityBadge, StatusBadge, CheckStatusBadge } from './Badges';
import { cn } from '../utils/cn';

interface HypothesisCardProps {
  hypothesis: {
    fault_description: string;
    confidence_score: number;
    severity: Severity;
    supporting_evidence: string[];
    recommended_checks: string[];
    repair_suggestion: string | null;
    component_id?: string;
    system_category?: string;
    vehicle_region?: string;
  };
  resultId: string;
  currentStatus: HypothesisStatus;
  onUpdateStatus: (resultId: string, status: HypothesisStatus) => void;
  updating: boolean;
  className?: string;
}

const STATUS_OPTIONS: { value: HypothesisStatus; label: string }[] = [
  { value: 'proposed', label: 'Proposed' },
  { value: 'investigating', label: 'Investigating' },
  { value: 'confirmed', label: 'Confirmed' },
  { value: 'rejected', label: 'Rejected' },
];

export function HypothesisCard({ hypothesis, resultId, currentStatus, onUpdateStatus, updating, className }: HypothesisCardProps) {
  const confidencePercent = Math.round(hypothesis.confidence_score * 100);
  const confidenceColor =
    hypothesis.confidence_score >= 0.8
      ? 'bg-green-500'
      : hypothesis.confidence_score >= 0.5
        ? 'bg-amber-500'
        : 'bg-red-500';

  return (
    <div className={cn('rounded-lg border border-slate-200 bg-white p-5', className)}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="text-sm font-semibold text-slate-900">{hypothesis.fault_description}</h4>
            <SeverityBadge severity={hypothesis.severity} />
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <StatusBadge status={currentStatus} />
        </div>
      </div>

       <div className="mt-4">
         <div className="flex items-center justify-between text-sm">
           <span className="text-slate-600">Confidence</span>
           <span className="font-medium text-slate-900">{confidencePercent}%</span>
         </div>
         <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-slate-100">
           <div
             className={cn('h-full rounded-full transition-all duration-500', confidenceColor)}
             style={{ width: `${confidencePercent}%` }}
           />
         </div>
       </div>

       {(hypothesis.component_id || hypothesis.system_category || hypothesis.vehicle_region) && (
         <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-3">
           <h5 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Component</h5>
           <div className="mt-1 space-y-1 text-sm text-slate-700">
             {hypothesis.component_id && (
               <p>
                 <span className="font-medium">ID:</span> {hypothesis.component_id.replace(/_/g, ' ')}
               </p>
             )}
             {hypothesis.system_category && (
               <p>
                 <span className="font-medium">System:</span> {hypothesis.system_category.replace(/_/g, ' ')}
               </p>
             )}
             {hypothesis.vehicle_region && (
               <p>
                 <span className="font-medium">Location:</span> {hypothesis.vehicle_region.replace(/_/g, ' ')}
               </p>
             )}
           </div>
         </div>
       )}

      {hypothesis.repair_suggestion && (
        <div className="mt-4">
          <h5 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Repair Suggestion</h5>
          <p className="mt-1 text-sm text-slate-700">{hypothesis.repair_suggestion}</p>
        </div>
      )}

      {hypothesis.supporting_evidence.length > 0 && (
        <div className="mt-4">
          <h5 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Supporting Evidence</h5>
          <ul className="mt-1.5 list-disc space-y-1 pl-4 text-sm text-slate-600">
            {hypothesis.supporting_evidence.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {hypothesis.recommended_checks.length > 0 && (
        <div className="mt-4">
          <h5 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Recommended Checks</h5>
          <ul className="mt-1.5 list-disc space-y-1 pl-4 text-sm text-slate-600">
            {hypothesis.recommended_checks.map((check, idx) => (
              <li key={idx}>{check}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-5 pt-4 border-t border-slate-100">
        <h5 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
          Update Status
        </h5>
        <div className="flex flex-wrap gap-2">
          {STATUS_OPTIONS.map((option) => (
            <Button
              key={option.value}
              variant={currentStatus === option.value ? 'primary' : 'secondary'}
              onClick={() => onUpdateStatus(resultId, option.value)}
              disabled={updating || currentStatus === option.value}
            >
              {option.label}
            </Button>
          ))}
        </div>
      </div>
    </div>
  );
}

interface CheckOutcomeSectionProps {
  resultId: string;
  checks: import('../types/api').DiagnosticCheckOutcome[];
  recommended_checks?: string[];
  onCreateCheck: (resultId: string, description: string) => void;
  onUpdateCheck: (outcomeId: string, status: string, observedResult?: string) => void;
  loading: boolean;
}

const STATUS_FLOW: Record<string, string[]> = {
  recommended: ['performed'],
  performed: ['passed', 'failed'],
  passed: [],
  failed: [],
};

export function CheckOutcomeSection({
  resultId,
  checks,
  recommended_checks = [],
  onCreateCheck,
  onUpdateCheck,
  loading,
}: CheckOutcomeSectionProps) {
  const [newCheck, setNewCheck] = useState('');

  const completedDescriptions = useMemo(
    () => new Set(checks.map((c) => c.check_description)),
    [checks]
  );

  const pendingRecommendations = useMemo(
    () => recommended_checks.filter((desc) => !completedDescriptions.has(desc)),
    [recommended_checks, completedDescriptions]
  );

  const handleCreate = () => {
    if (!newCheck.trim()) return;
    onCreateCheck(resultId, newCheck.trim());
    setNewCheck('');
  };

  const handleStartRecommendation = (description: string) => {
    onCreateCheck(resultId, description);
  };

  const availableNext = (status: string) => STATUS_FLOW[status] || [];

  return (
    <div className="mt-4 rounded-lg border border-slate-200 bg-white">
      <div className="border-b border-slate-100 px-4 py-3">
        <h5 className="text-sm font-semibold text-slate-900">Diagnostic Check Outcomes</h5>
      </div>

      {pendingRecommendations.length > 0 && (
        <div className="border-b border-slate-100 px-4 py-3 bg-slate-50">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500 mb-2">
            Recommended Checks
          </p>
          <div className="space-y-2">
            {pendingRecommendations.map((desc, idx) => (
              <div key={idx} className="flex items-center justify-between gap-3">
                <span className="text-sm text-slate-700">{desc}</span>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => handleStartRecommendation(desc)}
                  disabled={loading}
                >
                  Start Check
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="divide-y divide-slate-100">
        {checks.length === 0 && pendingRecommendations.length === 0 && (
          <p className="px-4 py-3 text-sm text-slate-500">No check outcomes recorded yet.</p>
        )}
        {checks.map((check) => (
          <div key={check.id} className="px-4 py-3">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-slate-900">{check.check_description}</span>
                  <CheckStatusBadge status={check.status} />
                </div>
                {check.observed_result && (
                  <p className="mt-1 text-sm text-slate-600">
                    <span className="font-medium">Result:</span> {check.observed_result}
                  </p>
                )}
                {check.technician_note && (
                  <p className="mt-1 text-sm text-slate-500 italic">{check.technician_note}</p>
                )}
              </div>
            </div>
            {availableNext(check.status).length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {availableNext(check.status).map((nextStatus) => (
                  <button
                    key={nextStatus}
                    type="button"
                    onClick={() => onUpdateCheck(check.id, nextStatus)}
                    disabled={loading}
                    className="rounded-md border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
                  >
                    Mark {nextStatus.charAt(0).toUpperCase() + nextStatus.slice(1)}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="border-t border-slate-100 px-4 py-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={newCheck}
            onChange={(e) => setNewCheck(e.target.value)}
            placeholder="Add a diagnostic check..."
            className="block flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
          />
          <Button size="sm" onClick={handleCreate} disabled={loading || !newCheck.trim()}>
            Add
          </Button>
        </div>
      </div>
    </div>
  );
}
