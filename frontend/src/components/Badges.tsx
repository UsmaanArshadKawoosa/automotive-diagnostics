import type { Severity } from '../types/api';
import { cn } from '../utils/cn';

const SEVERITY_CONFIG: Record<Severity, { label: string; bg: string; text: string; ring: string }> = {
  low: {
    label: 'Low',
    bg: 'bg-green-900/40',
    text: 'text-green-300',
    ring: 'ring-green-500/30',
  },
  medium: {
    label: 'Medium',
    bg: 'bg-secondary-container/25',
    text: 'text-secondary',
    ring: 'ring-secondary/30',
  },
  high: {
    label: 'High',
    bg: 'bg-error-container/30',
    text: 'text-error',
    ring: 'ring-error/30',
  },
  critical: {
    label: 'Critical',
    bg: 'bg-error-container',
    text: 'text-on-error-container',
    ring: 'ring-error/40',
  },
};

export function SeverityBadge({ severity }: { severity?: Severity | null }) {
  if (!severity) return null;
  const config = SEVERITY_CONFIG[severity];
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset',
        config.bg,
        config.text,
        config.ring
      )}
    >
      {config.label}
    </span>
  );
}

const STATUS_CONFIG: Record<string, { label: string; bg: string; text: string }> = {
  proposed: { label: 'Proposed', bg: 'bg-surface-container-high', text: 'text-on-surface-variant' },
  investigating: { label: 'Investigating', bg: 'bg-primary-container/25', text: 'text-primary' },
  confirmed: { label: 'Confirmed', bg: 'bg-green-900/40', text: 'text-green-300' },
  rejected: { label: 'Rejected', bg: 'bg-error-container/25', text: 'text-error' },
};

export function StatusBadge({ status }: { status: string }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.proposed;
  return (
    <span className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium', config.bg, config.text)}>
      {config.label}
    </span>
  );
}

const CHECK_CONFIG: Record<string, { label: string; bg: string; text: string }> = {
  recommended: { label: 'Recommended', bg: 'bg-surface-container-high', text: 'text-on-surface-variant' },
  performed: { label: 'Performed', bg: 'bg-primary-container/25', text: 'text-primary' },
  passed: { label: 'Passed', bg: 'bg-green-900/40', text: 'text-green-300' },
  failed: { label: 'Failed', bg: 'bg-error-container/25', text: 'text-error' },
};

export function CheckStatusBadge({ status }: { status: string }) {
  const config = CHECK_CONFIG[status] || CHECK_CONFIG.recommended;
  return (
    <span className={cn('inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium', config.bg, config.text)}>
      {config.label}
    </span>
  );
}
