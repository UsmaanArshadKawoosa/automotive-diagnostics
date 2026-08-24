import { useState, useCallback } from 'react';
import { Label, Input, Button } from './Form';
import { cn } from '../utils/cn';

interface DtcInputProps {
  codes: string[];
  onChange: (codes: string[]) => void;
  error?: string;
  disabled?: boolean;
}

export function DtcInput({ codes, onChange, error, disabled }: DtcInputProps) {
  const [inputValue, setInputValue] = useState('');

  const handleAdd = useCallback(() => {
    const trimmed = inputValue.trim().toUpperCase();
    if (!trimmed) return;
    if (/^[PCBU][0-9]{4}$/.test(trimmed) && !codes.includes(trimmed)) {
      onChange([...codes, trimmed]);
      setInputValue('');
    }
  }, [inputValue, codes, onChange]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAdd();
    }
  };

  const handleRemove = (code: string) => {
    onChange(codes.filter((c) => c !== code));
  };

  return (
    <div className="space-y-2">
      <Label htmlFor="dtc" required={false}>Diagnostic Trouble Codes (DTC)</Label>
      <div className="flex gap-2">
        <Input
          id="dtc"
          value={inputValue}
          onChange={setInputValue}
          onKeyDown={handleKeyDown}
          placeholder="e.g. P0300"
          maxLength={5}
          error={error}
          helperText="Format: P, C, B, or U followed by 4 digits"
          className="font-mono"
          disabled={disabled}
        />
        <Button type="button" onClick={handleAdd} variant="secondary" className="shrink-0 min-w-[44px]" disabled={disabled}>
          Add
        </Button>
      </div>
      {codes.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {codes.map((code) => (
            <span
              key={code}
              className={cn(
                'inline-flex items-center gap-1 rounded-md bg-brand-50 px-2.5 py-1 text-sm font-medium text-brand-700 ring-1 ring-inset ring-brand-700/10'
              )}
            >
              <span className="font-mono">{code}</span>
               <button
                 type="button"
                 onClick={() => handleRemove(code)}
                 className="ml-0.5 text-brand-400 hover:text-brand-600 min-w-[44px] min-h-[44px] flex items-center justify-center"
                 aria-label={`Remove ${code}`}
                 disabled={disabled}
               >
                <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
                </svg>
              </button>
            </span>
          ))}
        </div>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}
