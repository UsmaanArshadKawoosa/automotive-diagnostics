import { useState, useMemo, forwardRef } from 'react';
import { Button } from './Form';
import type { Severity, HypothesisStatus, RepairSafetyTier, DiagnosticCheckOutcome } from '../types/api';
import { StatusBadge, CheckStatusBadge } from './Badges';
import { cn } from '../utils/cn';

const SAFETY_TIER_COLORS: Record<RepairSafetyTier, string> = {
  diy_inspection: 'bg-green-500',
  diy_repair: 'bg-amber-500',
  mechanic_recommended: 'bg-orange-500',
  immediate_professional: 'bg-red-500',
};

const SAFETY_TIER_LABELS: Record<RepairSafetyTier, string> = {
  diy_inspection: 'Safe to inspect yourself',
  diy_repair: 'DIY repair may be possible',
  mechanic_recommended: 'Mechanic recommended',
  immediate_professional: 'Seek professional service immediately',
};

const SAFETY_TIER_ACTIONS: Record<RepairSafetyTier, string> = {
  diy_inspection: 'Inspect the component visually and check for obvious issues.',
  diy_repair: 'Repair may be possible with appropriate tools and service manual guidance.',
  mechanic_recommended: 'Schedule service with a qualified mechanic.',
  immediate_professional: 'Do not drive. Contact a professional immediately.',
};

const SEVERITY_COLORS: Record<Severity, string> = {
  low: 'bg-green-500',
  medium: 'bg-amber-500',
  high: 'bg-orange-500',
  critical: 'bg-red-500',
};

const SEVERITY_LABELS: Record<Severity, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
};

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
    safety_tier?: RepairSafetyTier;
    safety_tier_label?: string;
    safety_tier_description?: string;
    safety_tier_reasoning?: string[];
  };
  resultId: string;
  currentStatus: HypothesisStatus;
  onUpdateStatus: (resultId: string, status: HypothesisStatus) => void;
  updating: boolean;
  className?: string;
  isSelected?: boolean;
  onSelect?: () => void;
}

const STATUS_OPTIONS: { value: HypothesisStatus; label: string }[] = [
  { value: 'proposed', label: 'Proposed' },
  { value: 'investigating', label: 'Investigating' },
  { value: 'confirmed', label: 'Confirmed' },
  { value: 'rejected', label: 'Rejected' },
];

export const HypothesisCard = forwardRef<HTMLDivElement, HypothesisCardProps>(({
  hypothesis,
  resultId,
  currentStatus,
  onUpdateStatus,
  updating,
  className,
  isSelected = false,
  onSelect,
}, ref) => {
  const confidencePercent = Math.round(hypothesis.confidence_score * 100);
  const confidenceColor =
    hypothesis.confidence_score >= 0.8
      ? 'bg-green-500'
      : hypothesis.confidence_score >= 0.5
        ? 'bg-amber-500'
        : 'bg-red-500';

  const safetyTier = hypothesis.safety_tier;
  const safetyTierLabel = hypothesis.safety_tier_label || (safetyTier ? SAFETY_TIER_LABELS[safetyTier] : '');
  const safetyTierColor = safetyTier ? SAFETY_TIER_COLORS[safetyTier] : '';
  const safetyTierAction = safetyTier ? SAFETY_TIER_ACTIONS[safetyTier] : '';
  const severityColor = hypothesis.severity ? SEVERITY_COLORS[hypothesis.severity] : '';
  const severityLabel = hypothesis.severity ? SEVERITY_LABELS[hypothesis.severity] : '';

  return (
    <div
      ref={ref}
      className={cn(
        'rounded-lg border border-slate-200 bg-white p-5 transition-all duration-200',
        isSelected && 'border-brand-500 ring-2 ring-brand-500/20',
        onSelect && 'cursor-pointer hover:shadow-md',
        className
      )}
      onClick={onSelect}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="text-sm font-semibold text-slate-900">{hypothesis.fault_description}</h4>
            {hypothesis.severity && (
              <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full text-white', severityColor)}>
                {severityLabel}
              </span>
            )}
            {safetyTier && (
              <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full text-white', safetyTierColor)}>
                {safetyTierLabel}
              </span>
            )}
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
          <h5 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Affected Component</h5>
          <div className="mt-1 space-y-1 text-sm text-slate-700">
            {hypothesis.component_id && (
              <p>
                <span className="font-medium">Component:</span> {hypothesis.component_id.replace(/_/g, ' ')}
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

      {safetyTier && (
        <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-3">
          <div className="flex items-start gap-3">
            <div className={cn('flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center', safetyTierColor)}>
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {safetyTier === 'immediate_professional' && (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                )}
                {safetyTier === 'mechanic_recommended' && (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                )}
                {safetyTier === 'diy_repair' && (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                )}
                {safetyTier === 'diy_inspection' && (
                  <>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </>
                )}
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className={cn('font-medium text-sm', safetyTierColor)}>
                {safetyTierLabel}
              </p>
              <p className="mt-1 text-sm text-slate-600">{safetyTierAction}</p>
              {hypothesis.safety_tier_reasoning && hypothesis.safety_tier_reasoning.length > 0 && (
                <div className="mt-2">
                  <p className="text-xs font-medium text-slate-500">Why:</p>
                  <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-slate-500">
                    {hypothesis.safety_tier_reasoning.map((reason, idx) => (
                      <li key={idx}>{reason}</li>
                    ))}
                  </ul>
                </div>
              )}
              {hypothesis.safety_tier_description && (
                <p className="mt-2 text-xs text-slate-500">{hypothesis.safety_tier_description}</p>
              )}
            </div>
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
});

HypothesisCard.displayName = 'HypothesisCard';

interface CheckOutcomeSectionProps {
  resultId: string;
  checks: DiagnosticCheckOutcome[];
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