import { type ReactNode } from 'react';
import { cn } from '../utils/cn';

interface AlertProps {
  type: 'error' | 'warning' | 'info' | 'success';
  title?: string;
  children: ReactNode;
  className?: string;
}

const ALERT_STYLES: Record<string, string> = {
  error: 'border-error-container/60 bg-error-container/25 text-on-error-container',
  warning: 'border-secondary-container/50 bg-secondary-container/20 text-secondary',
  info: 'border-primary-container/50 bg-primary-container/20 text-primary',
  success: 'border-green-700/50 bg-green-900/30 text-green-300',
};

const ALERT_ICONS: Record<string, ReactNode> = {
  error: (
    <svg className="h-5 w-5 text-error" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
    </svg>
  ),
  warning: (
    <svg className="h-5 w-5 text-secondary" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.88c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.516-2.625l6.28-10.88zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
    </svg>
  ),
  info: (
    <svg className="h-5 w-5 text-primary" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zm-1 9a1 1 0 01-1-1v-1a1 1 0 112 0v1a1 1 0 01-1 1z" clipRule="evenodd" />
    </svg>
  ),
  success: (
    <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clipRule="evenodd" />
    </svg>
  ),
};

export function Alert({ type, title, children, className }: AlertProps) {
  return (
    <div className={cn('rounded-lg border p-4', ALERT_STYLES[type], className)} role="alert" aria-live="polite">
      <div className="flex gap-3">
        <div className="flex-shrink-0" aria-hidden="true">{ALERT_ICONS[type]}</div>
        <div>
          {title && <h3 className="text-sm font-semibold">{title}</h3>}
          <div className="text-sm opacity-90">{children}</div>
        </div>
      </div>
    </div>
  );
}

export function ErrorMessage({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-lg border border-error-container/60 bg-error-container/25 p-4" role="alert" aria-live="polite">
      <div className="flex items-center gap-3">
        <svg className="h-5 w-5 text-error" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
        </svg>
        <div className="flex-1">
          <p className="text-sm font-medium text-on-error-container">{message}</p>
        </div>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="text-sm font-medium text-error hover:text-on-error-container"
          >
            Retry
          </button>
        )}
      </div>
    </div>
  );
}
