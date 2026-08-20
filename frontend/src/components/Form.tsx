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
        'block text-sm font-medium text-slate-700',
        required && "after:ml-0.5 after:text-red-500 after:content-['*']"
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
          'block w-full rounded-md border px-3 py-2 text-sm shadow-sm transition-colors',
          'placeholder:text-slate-400',
          'focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500',
          error
            ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
            : 'border-slate-300',
          disabled && 'bg-slate-50 text-slate-500',
          className
        )}
      />
      {error && <p className="text-sm text-red-600">{error}</p>}
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
          'block w-full rounded-md border px-3 py-2 text-sm shadow-sm transition-colors',
          'placeholder:text-slate-400',
          'focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500',
          'resize-y',
          error
            ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
            : 'border-slate-300',
          disabled && 'bg-slate-50 text-slate-500'
        )}
      />
      {error && <p className="text-sm text-red-600">{error}</p>}
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
          'block w-full rounded-md border px-3 py-2 text-sm shadow-sm transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500',
          disabled && 'bg-slate-50 text-slate-500',
          'border-slate-300 bg-white text-slate-900',
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
    'inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';
  const sizes = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
  };
  const variants = {
    primary: 'bg-brand-600 text-white hover:bg-brand-700 focus:ring-brand-500',
    secondary: 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 focus:ring-brand-500',
    danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
    ghost: 'text-slate-600 hover:bg-slate-100',
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
