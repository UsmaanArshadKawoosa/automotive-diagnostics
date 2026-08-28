import type { ReactNode } from 'react';
import { cn } from '../utils/cn';

interface LabelProps {
  children: ReactNode;
  htmlFor?: string;
  required?: boolean;
}

export function Label({ children, htmlFor, required }: LabelProps) {
  return (
    <label
      htmlFor={htmlFor}
      className={cn(
        'block text-sm font-medium text-on-surface-variant',
        required && "after:ml-0.5 after:text-secondary after:content-['*']"
      )}
    >
      {children}
    </label>
  );
}

interface InputProps {
  id?: string;
  value: string | number;
  onChange: (value: string) => void;
  placeholder?: string;
  label?: string;
  required?: boolean;
  type?: 'text' | 'number' | 'email';
  maxLength?: number;
  error?: string;
  helperText?: string;
  disabled?: boolean;
  onKeyDown?: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  className?: string;
}

export function Input({
  id,
  value,
  onChange,
  placeholder,
  label,
  required,
  type = 'text',
  maxLength,
  error,
  helperText,
  disabled,
  onKeyDown,
  className,
}: InputProps) {
  return (
    <div className="space-y-1.5">
      {label && <Label htmlFor={id} required={required}>{label}</Label>}
      <input
        id={id}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        maxLength={maxLength}
        disabled={disabled}
        className={cn(
          'block w-full rounded-md border bg-surface-container-lowest px-3 py-2.5 text-sm text-on-surface shadow-sm transition-colors min-h-[44px]',
          'placeholder:text-on-surface-variant/70',
          'focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary',
          error
            ? 'border-error focus:ring-error/50 focus:border-error'
            : 'border-outline-variant',
          disabled && 'cursor-not-allowed opacity-50',
          className
        )}
      />
      {(error || helperText) && (
        <p className={cn('text-xs', error ? 'text-error' : 'text-on-surface-variant')}>
          {error || helperText}
        </p>
      )}
    </div>
  );
}

interface TextareaProps {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  label?: string;
  required?: boolean;
  rows?: number;
  maxLength?: number;
  error?: string;
  helperText?: string;
  disabled?: boolean;
}

export function Textarea({
  id,
  value,
  onChange,
  placeholder,
  label,
  required,
  rows = 4,
  maxLength,
  error,
  helperText,
  disabled,
}: TextareaProps) {
  return (
    <div className="space-y-1.5">
      {label && <Label htmlFor={id} required={required}>{label}</Label>}
      <textarea
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        maxLength={maxLength}
        disabled={disabled}
        className={cn(
          'block w-full rounded-md border bg-surface-container-lowest px-3 py-2.5 text-sm text-on-surface shadow-sm transition-colors min-h-[44px]',
          'placeholder:text-on-surface-variant/70',
          'focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary',
          'resize-y',
          error
            ? 'border-error focus:ring-error/50 focus:border-error'
            : 'border-outline-variant',
          disabled && 'cursor-not-allowed opacity-50'
        )}
      />
      {(error || helperText) && (
        <p className={cn('text-xs', error ? 'text-error' : 'text-on-surface-variant')}>
          {error || helperText}
        </p>
      )}
    </div>
  );
}

interface SelectProps {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  placeholder?: string;
  label?: string;
  required?: boolean;
  helperText?: string;
  disabled?: boolean;
  className?: string;
}

export function Select({
  id,
  value,
  onChange,
  options,
  placeholder,
  label,
  required,
  helperText,
  disabled,
  className,
}: SelectProps) {
  return (
    <div className="space-y-1.5">
      {label && <Label htmlFor={id} required={required}>{label}</Label>}
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className={cn(
          'block w-full rounded-md border bg-surface-container-lowest px-3 py-2.5 text-sm text-on-surface shadow-sm transition-colors min-h-[44px]',
          'focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary',
          disabled && 'cursor-not-allowed opacity-50',
          'border-outline-variant',
          className
        )}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {helperText && <p className="text-xs text-on-surface-variant">{helperText}</p>}
    </div>
  );
}

interface ButtonProps {
  children: ReactNode;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  disabled?: boolean;
  loading?: boolean;
  size?: 'sm' | 'md';
  className?: string;
}

export function Button({
  children,
  onClick,
  type = 'button',
  variant = 'primary',
  disabled,
  loading,
  size = 'md',
  className,
}: ButtonProps) {
  const base =
    'inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-50 disabled:cursor-not-allowed min-h-[44px]';
  const sizes = {
    sm: 'px-3 py-2 text-xs min-h-[40px]',
    md: 'px-4 py-2.5 text-sm',
  };
  const variants = {
    primary: 'bg-primary-container text-on-primary-container hover:bg-primary-fixed shadow-sm active:scale-[0.98]',
    secondary: 'bg-surface-container-high text-on-surface border border-outline-variant hover:bg-surface-container-highest active:scale-[0.98]',
    danger: 'bg-error-container text-on-error-container hover:bg-error active:scale-[0.98]',
    ghost: 'text-on-surface-variant hover:bg-surface-container-high',
  };
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={cn(base, sizes[size], variants[variant], className)}
    >
      {loading && (
        <svg
          className="h-4 w-4 animate-spin"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
      )}
      {children}
    </button>
  );
}
