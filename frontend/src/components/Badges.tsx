import type { Severity } from '../types/api';
import { cn } from '../utils/cn';

const SEVERITY_CONFIG: Record<Severity, { label: string; bg: string; text: string; ring: string }> = {
  low: {
    label: 'Low',
    bg: 'bg-green-50',
    text: 'text-green-700',
    ring: 'ring-green-600/20',
  },
  medium: {
    label: 'Medium',
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    ring: 'ring-amber-600/20',
  },
  high: {
    label: 'High',
    bg: 'bg-red-50',
    text: 'text-red-700',
    ring: 'ring-red-600/20',
  },
  critical: {
    label: 'Critical',
    bg: 'bg-red-100',
    text: 'text-red-900',
    ring: 'ring-red-700/20',
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
  proposed: { label: 'Proposed', bg: 'bg-slate-100', text: 'text-slate-700' },
  investigating: { label: 'Investigating', bg: 'bg-blue-50', text: 'text-blue-700' },
  confirmed: { label: 'Confirmed', bg: 'bg-green-50', text: 'text-green-700' },
  rejected: { label: 'Rejected', bg: 'bg-red-50', text: 'text-red-700' },
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
  recommended: { label: 'Recommended', bg: 'bg-slate-100', text: 'text-slate-600' },
  performed: { label: 'Performed', bg: 'bg-blue-50', text: 'text-blue-700' },
  passed: { label: 'Passed', bg: 'bg-green-50', text: 'text-green-700' },
  failed: { label: 'Failed', bg: 'bg-red-50', text: 'text-red-700' },
};

export function CheckStatusBadge({ status }: { status: string }) {
  const config = CHECK_CONFIG[status] || CHECK_CONFIG.recommended;
  return (
    <span className={cn('inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium', config.bg, config.text)}>
      {config.label}
    </span>
  );
}
