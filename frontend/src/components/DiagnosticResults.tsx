import { useState, useMemo, forwardRef } from 'react';
import { Button } from './Form';
import type { Severity, HypothesisStatus, RepairSafetyTier, DiagnosticCheckOutcome, DIYRepairGuidance, ResourceLink } from '../types/api';
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
    differential_rank?: number;
    evidence_quality?: string;
    diy_repair?: DIYRepairGuidance | null;
    resources?: ResourceLink[];
  };
  resultId: string;
  currentStatus: HypothesisStatus;
  onUpdateStatus: (resultId: string, status: HypothesisStatus) => void;
  onConfirmedFix?: (resultId: string, fault: string) => void;
  updating: boolean;
  className?: string;
  isSelected?: boolean;
  onSelect?: () => void;
  isTopHypothesis?: boolean;
}

const STATUS_OPTIONS: { value: HypothesisStatus; label: string }[] = [
  { value: 'proposed', label: 'Proposed' },
  { value: 'investigating', label: 'Investigating' },
  { value: 'confirmed', label: 'Confirmed' },
  { value: 'rejected', label: 'Rejected' },
];

interface DIYRepairSectionProps {
  diy: DIYRepairGuidance;
}

function DIYRepairSection({ diy }: DIYRepairSectionProps) {
  const suitabilityColors: Record<string, string> = {
    'Recommended for DIY': 'border-green-700/40 bg-green-900/30 text-green-300',
    'Possible with caution': 'border-secondary-container/40 bg-secondary-container/20 text-secondary',
    'Professional recommended': 'border-error-container/40 bg-error-container/25 text-on-error-container',
  };

  const difficultyColors: Record<string, string> = {
    easy: 'bg-green-900/40 text-green-300',
    moderate: 'bg-secondary-container/25 text-secondary',
    advanced: 'bg-error-container/25 text-on-error-container',
  };

  return (
    <div className="mt-4 rounded-lg border border-outline-variant bg-surface-container-high overflow-hidden">
      <div className="border-b border-outline-variant px-4 py-3 bg-surface-container">
        <h5 className="text-sm font-semibold text-on-surface">
          {diy.suitable ? 'DIY Repair Guide' : 'Professional Service Recommended'}
        </h5>
        <div className="mt-1 flex items-center gap-2 flex-wrap">
          {diy.suitability && (
            <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full', suitabilityColors[diy.suitability] || 'bg-surface-container-high text-on-surface-variant')}>
              {diy.suitability}
            </span>
          )}
          {diy.difficulty && (
            <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full', difficultyColors[diy.difficulty] || 'bg-surface-container-high text-on-surface-variant')}>
              {diy.difficulty.charAt(0).toUpperCase() + diy.difficulty.slice(1)}
            </span>
          )}
          {diy.estimated_time && (
            <span className="text-xs text-on-surface-variant">
              Est. time: {diy.estimated_time}
            </span>
          )}
        </div>
      </div>

      <div className="p-4 space-y-4">
        {(diy.tools?.length ?? 0) > 0 && (
          <div>
            <h6 className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant mb-1">Tools Required</h6>
            <ul className="list-disc space-y-1 pl-4 text-sm text-on-surface-variant">
              {diy.tools?.map((tool, idx) => (
                <li key={idx}>{tool}</li>
              ))}
            </ul>
          </div>
        )}

        {(diy.parts?.length ?? 0) > 0 && (
          <div>
            <h6 className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant mb-1">Parts / Materials</h6>
            <ul className="list-disc space-y-1 pl-4 text-sm text-on-surface-variant">
              {diy.parts?.map((part, idx) => (
                <li key={idx}>{part}</li>
              ))}
            </ul>
          </div>
        )}

        {(diy.safety_warnings?.length ?? 0) > 0 && (
          <div className="rounded-md border border-error-container/40 bg-error-container/25 p-3">
            <h6 className="text-xs font-semibold uppercase tracking-wider text-on-error-container mb-1">Safety Precautions</h6>
            <ul className="list-disc space-y-1 pl-4 text-sm text-on-error-container">
              {diy.safety_warnings?.map((warning, idx) => (
                <li key={idx}>{warning}</li>
              ))}
            </ul>
          </div>
        )}

        {(diy.preparation_steps?.length ?? 0) > 0 && (
          <div>
            <h6 className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant mb-1">Preparation</h6>
            <ol className="list-decimal space-y-1 pl-4 text-sm text-on-surface-variant">
              {diy.preparation_steps?.map((step, idx) => (
                <li key={idx}>{step}</li>
              ))}
            </ol>
          </div>
        )}

        {(diy.steps?.length ?? 0) > 0 && (
          <div>
            <h6 className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant mb-1">Steps</h6>
            <ol className="list-decimal space-y-1 pl-4 text-sm text-on-surface-variant">
              {diy.steps?.map((step, idx) => (
                <li key={idx}>{step}</li>
              ))}
            </ol>
          </div>
        )}

        {(diy.verification_steps?.length ?? 0) > 0 && (
          <div>
            <h6 className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant mb-1">After Repair — Verification</h6>
            <ol className="list-decimal space-y-1 pl-4 text-sm text-on-surface-variant">
              {diy.verification_steps?.map((step, idx) => (
                <li key={idx}>{step}</li>
              ))}
            </ol>
          </div>
        )}

        {(diy.professional_help_conditions?.length ?? 0) > 0 && (
          <div className="rounded-md border border-secondary-container/40 bg-secondary-container/20 p-3">
            <h6 className="text-xs font-semibold uppercase tracking-wider text-secondary mb-1">When to Seek Professional Help</h6>
            <ul className="list-disc space-y-1 pl-4 text-sm text-secondary">
              {diy.professional_help_conditions?.map((condition, idx) => (
                <li key={idx}>{condition}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

export const HypothesisCard = forwardRef<HTMLDivElement, HypothesisCardProps>(({
  hypothesis,
  resultId,
  currentStatus,
  onUpdateStatus,
  onConfirmedFix,
  updating,
  className,
  isSelected = false,
  onSelect,
  isTopHypothesis = false,
}, ref) => {
  const confidencePercent = Math.round(hypothesis.confidence_score * 100);
  const confidenceColor =
    hypothesis.confidence_score >= 0.8
      ? 'bg-green-500'
      : hypothesis.confidence_score >= 0.5
        ? 'bg-amber-500'
        : 'bg-red-500';

  const confidenceLabel =
    hypothesis.confidence_score >= 0.8
      ? 'High confidence'
      : hypothesis.confidence_score >= 0.5
        ? 'Medium confidence'
        : 'Low confidence';

  const safetyTier = hypothesis.safety_tier;
  const safetyTierLabel = hypothesis.safety_tier_label || (safetyTier ? SAFETY_TIER_LABELS[safetyTier] : '');
  const safetyTierColor = safetyTier ? SAFETY_TIER_COLORS[safetyTier] : '';
  const safetyTierAction = safetyTier ? SAFETY_TIER_ACTIONS[safetyTier] : '';
  const severityColor = hypothesis.severity ? SEVERITY_COLORS[hypothesis.severity] : '';
  const severityLabel = hypothesis.severity ? SEVERITY_LABELS[hypothesis.severity] : '';
  const differentialRank = hypothesis.differential_rank;
  const evidenceQuality = hypothesis.evidence_quality;

  const [showDetails, setShowDetails] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState(false);

  const handleConfirmed = () => {
    setFeedbackGiven(true);
    onConfirmedFix?.(resultId, hypothesis.fault_description);
    onUpdateStatus(resultId, 'confirmed');
  };

  const handleRejected = () => {
    setFeedbackGiven(true);
    onUpdateStatus(resultId, 'rejected');
  };

  return (
    <div
      ref={ref}
      className={cn(
        'rounded-lg border p-4 sm:p-5 transition-all duration-200',
        isTopHypothesis
          ? 'border-primary/60 bg-surface-container-high shadow-md shadow-primary/10'
          : 'border-outline-variant bg-surface-container hover:border-outline',
        isSelected && 'ring-2 ring-primary/40',
        onSelect && 'cursor-pointer',
        className
      )}
      onClick={onSelect}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            {isTopHypothesis && (
              <span className="inline-flex items-center rounded-md bg-primary-container/25 px-2 py-0.5 text-xs font-semibold text-primary ring-1 ring-inset ring-primary/20">
                Top Hypothesis
              </span>
            )}
            {differentialRank && (
              <span className="inline-flex items-center rounded-md bg-surface-container-high px-2 py-0.5 text-xs font-medium text-on-surface-variant ring-1 ring-inset ring-outline-variant">
                #{differentialRank}
              </span>
            )}
            <h4 className="text-sm font-semibold text-on-surface">{hypothesis.fault_description}</h4>
          </div>
          <div className="mt-2 flex items-center gap-2 flex-wrap">
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
            {evidenceQuality && (
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-surface-container-high text-on-surface-variant ring-1 ring-inset ring-outline-variant">
                {evidenceQuality} evidence
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
          <span className="text-on-surface-variant">Confidence</span>
          <div className="flex items-center gap-2">
            <span className="text-xs text-on-surface-variant">{confidenceLabel}</span>
            <span className="font-medium text-on-surface">{confidencePercent}%</span>
          </div>
        </div>
        <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-surface-container-low">
          <div
            className={cn('h-full rounded-full transition-all duration-500', confidenceColor)}
            style={{ width: `${confidencePercent}%` }}
          />
        </div>
      </div>

      {(hypothesis.component_id || hypothesis.system_category || hypothesis.vehicle_region) && (
        <div className={cn('mt-4 rounded-md border p-3', isTopHypothesis ? 'border-primary/30 bg-surface-container-high' : 'border-outline-variant bg-surface-container-low')}>
          <h5 className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Affected Component</h5>
          <div className="mt-1 space-y-1 text-sm text-on-surface-variant">
            {hypothesis.component_id && (
              <p>
                <span className="font-medium text-on-surface">Component:</span> {hypothesis.component_id.replace(/_/g, ' ')}
              </p>
            )}
            {hypothesis.system_category && (
              <p>
                <span className="font-medium text-on-surface">System:</span> {hypothesis.system_category.replace(/_/g, ' ')}
              </p>
            )}
            {hypothesis.vehicle_region && (
              <p>
                <span className="font-medium text-on-surface">Location:</span> {hypothesis.vehicle_region.replace(/_/g, ' ')}
              </p>
            )}
          </div>
        </div>
      )}

      {safetyTier && (
        <div className={cn('mt-4 rounded-md border p-3', isTopHypothesis ? 'border-primary/30 bg-surface-container-high' : 'border-outline-variant bg-surface-container-low')}>
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
              <p className="mt-1 text-sm text-on-surface-variant">{safetyTierAction}</p>
              {hypothesis.safety_tier_reasoning && hypothesis.safety_tier_reasoning.length > 0 && (
                <div className="mt-2">
                  <p className="text-xs font-medium text-on-surface-variant">Why:</p>
                  <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-on-surface-variant">
                    {hypothesis.safety_tier_reasoning.map((reason, idx) => (
                      <li key={idx}>{reason}</li>
                    ))}
                  </ul>
                </div>
              )}
              {hypothesis.safety_tier_description && (
                <p className="mt-2 text-xs text-on-surface-variant">{hypothesis.safety_tier_description}</p>
              )}
            </div>
          </div>
        </div>
      )}

      {hypothesis.repair_suggestion && (
        <div className="mt-4">
          <h5 className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Repair Suggestion</h5>
          <p className="mt-1 text-sm text-on-surface-variant">{hypothesis.repair_suggestion}</p>
        </div>
      )}

      {hypothesis.diy_repair && (
        <DIYRepairSection diy={hypothesis.diy_repair} />
      )}

      {hypothesis.resources && hypothesis.resources.length > 0 && (
        <div className="mt-4">
          <h5 className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant mb-2">Helpful Resources</h5>
          <div className="space-y-3">
            {hypothesis.resources.map((resource, idx) => (
              <a
                key={idx}
                href={resource.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block text-sm text-primary hover:text-primary-fixed-dim"
              >
                <span className="font-medium">{resource.title}</span>
                {resource.type === 'youtube' ? (
                  <span className="ml-1 font-medium">— Watch Guide →</span>
                ) : (
                  <span className="ml-1 font-medium">— View Guide →</span>
                )}
                <span className="block text-xs text-on-surface-variant">{resource.source}</span>
              </a>
            ))}
          </div>
        </div>
      )}

      {hypothesis.supporting_evidence.length > 0 && (
        <div className="mt-4">
          <h5 className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Supporting Evidence</h5>
          <ul className="mt-1.5 space-y-1.5 text-sm text-on-surface-variant">
            {hypothesis.supporting_evidence.map((item, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-outline" aria-hidden="true" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {hypothesis.recommended_checks.length > 0 && (
        <div className="mt-4 rounded-md border border-secondary-container/40 bg-secondary-container/15 p-3">
          <h5 className="text-xs font-semibold uppercase tracking-wider text-secondary">What to check next</h5>
          <ul className="mt-1.5 space-y-1.5 text-sm text-secondary">
            {hypothesis.recommended_checks.map((check, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-secondary" aria-hidden="true" />
                <span>{check}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {!feedbackGiven && (
        <div className="mt-5 pt-4 border-t border-outline-variant">
          <h5 className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant mb-2">
            Was this helpful?
          </h5>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="primary"
              onClick={handleConfirmed}
              disabled={updating}
              className="min-h-[44px]"
            >
              Yes, this was the problem
            </Button>
            <Button
              variant="secondary"
              onClick={handleRejected}
              disabled={updating}
              className="min-h-[44px]"
            >
              Something else was wrong
            </Button>
          </div>
        </div>
      )}

      {feedbackGiven && (
        <div className="mt-5 pt-4 border-t border-outline-variant">
          <p className="text-sm text-on-surface-variant">Thanks for your feedback! This helps improve future diagnoses.</p>
        </div>
      )}

      <div className="mt-4">
        <button
          type="button"
          onClick={() => setShowDetails(!showDetails)}
          className="text-sm text-primary hover:text-primary-fixed-dim font-medium"
        >
          {showDetails ? 'Hide technical details' : 'Show technical details'}
        </button>
        {showDetails && (
          <div className="mt-3 space-y-3">
            {hypothesis.supporting_evidence.length > 0 && (
              <div>
                <h5 className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant mb-2">Supporting Evidence</h5>
                <ul className="space-y-1.5 text-sm text-on-surface-variant">
                  {hypothesis.supporting_evidence.map((item, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-outline" aria-hidden="true" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {(hypothesis.component_id || hypothesis.system_category || hypothesis.vehicle_region) && (
              <div className="rounded-md border p-3 bg-surface-container-low">
                <h5 className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant mb-2">Technical Details</h5>
                <div className="space-y-1 text-sm text-on-surface-variant">
                  {hypothesis.component_id && (
                    <p><span className="font-medium text-on-surface">Component:</span> {hypothesis.component_id.replace(/_/g, ' ')}</p>
                  )}
                  {hypothesis.system_category && (
                    <p><span className="font-medium text-on-surface">System:</span> {hypothesis.system_category.replace(/_/g, ' ')}</p>
                  )}
                  {hypothesis.vehicle_region && (
                    <p><span className="font-medium text-on-surface">Location:</span> {hypothesis.vehicle_region.replace(/_/g, ' ')}</p>
                  )}
                </div>
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              {STATUS_OPTIONS.map((option) => (
                <Button
                  key={option.value}
                  variant={currentStatus === option.value ? 'primary' : 'secondary'}
                  onClick={() => onUpdateStatus(resultId, option.value)}
                  disabled={updating || currentStatus === option.value}
                  className="min-h-[44px]"
                >
                  {option.label}
                </Button>
              ))}
            </div>
          </div>
        )}
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
    <div className="mt-4 rounded-lg border border-outline-variant bg-surface-container-high">
      <div className="border-b border-outline-variant px-4 py-3">
        <h5 className="text-sm font-semibold text-on-surface">Diagnostic Check Outcomes</h5>
      </div>

      {pendingRecommendations.length > 0 && (
        <div className="border-b border-outline-variant px-4 py-3 bg-surface-container">
          <p className="text-xs font-medium uppercase tracking-wider text-on-surface-variant mb-2">
            Recommended Checks
          </p>
          <div className="space-y-2">
            {pendingRecommendations.map((desc, idx) => (
              <div key={idx} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <span className="text-sm text-on-surface-variant">{desc}</span>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => handleStartRecommendation(desc)}
                  disabled={loading}
                  className="w-full sm:w-auto"
                >
                  Start Check
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="divide-y divide-outline-variant">
        {checks.length === 0 && pendingRecommendations.length === 0 && (
          <p className="px-4 py-3 text-sm text-on-surface-variant">No check outcomes recorded yet.</p>
        )}
        {checks.map((check) => (
          <div key={check.id} className="px-4 py-3">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-on-surface">{check.check_description}</span>
                  <CheckStatusBadge status={check.status} />
                </div>
                {check.observed_result && (
                  <p className="mt-1 text-sm text-on-surface-variant">
                    <span className="font-medium">Result:</span> {check.observed_result}
                  </p>
                )}
                {check.technician_note && (
                  <p className="mt-1 text-sm text-on-surface-variant italic">{check.technician_note}</p>
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
                    className="rounded-md border border-outline-variant px-2.5 py-2 text-xs font-medium text-on-surface-variant hover:bg-surface-container-highest disabled:opacity-50 min-h-[44px]"
                  >
                    Mark {nextStatus.charAt(0).toUpperCase() + nextStatus.slice(1)}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="border-t border-outline-variant px-4 py-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={newCheck}
            onChange={(e) => setNewCheck(e.target.value)}
            placeholder="Add a diagnostic check..."
            className="block flex-1 rounded-md border border-outline-variant bg-surface-container-lowest px-3 py-2.5 text-sm text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary min-h-[44px]"
          />
          <Button size="sm" onClick={handleCreate} disabled={loading || !newCheck.trim()} className="min-h-[44px]">
            Add
          </Button>
        </div>
      </div>
    </div>
  );
}
