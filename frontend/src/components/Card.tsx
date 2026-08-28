import type { ReactNode } from 'react';
import { cn } from '../utils/cn';

interface CardProps {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-lg border border-outline-variant bg-surface-container shadow-sm',
        className
      )}
    >
      {children}
    </div>
  );
}

interface CardHeaderProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}

export function CardHeader({ title, subtitle, action }: CardHeaderProps) {
  return (
    <div className="flex items-start justify-between border-b border-outline-variant px-5 py-4">
      <div>
        <h3 className="font-headline-md text-base font-semibold text-on-surface">{title}</h3>
        {subtitle && <p className="mt-0.5 text-sm text-on-surface-variant">{subtitle}</p>}
      </div>
      {action && <div className="ml-4">{action}</div>}
    </div>
  );
}

interface CardBodyProps {
  children: ReactNode;
  className?: string;
}

export function CardBody({ children, className }: CardBodyProps) {
  return <div className={cn('px-5 py-4 text-on-surface', className)}>{children}</div>;
}
