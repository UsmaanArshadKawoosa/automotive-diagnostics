import { Link } from 'react-router-dom';

export function MinimalHeader() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-14 items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-slate-900">
              <span className="text-xs font-bold text-white">AD</span>
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-semibold text-slate-900 leading-tight">
                Automotive Diagnostic AI
              </span>
              <span className="text-[10px] text-slate-500 leading-tight hidden sm:block">
                AI-powered vehicle troubleshooting
              </span>
            </div>
          </Link>
          <Link
            to="/"
            className="inline-flex items-center rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          >
            New Diagnosis
          </Link>
        </div>
      </div>
    </header>
  );
}