import { useOnlineStatus } from '../hooks/useOnlineStatus';

export function OfflineIndicator() {
  const isOnline = useOnlineStatus();

  if (isOnline) return null;

  return (
    <div className="fixed inset-x-0 top-0 z-50">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 shadow-sm" role="status" aria-live="polite">
          <div className="flex items-center gap-3">
            <svg className="h-5 w-5 shrink-0 text-amber-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.88c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.516-2.625l6.28-10.88zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
            </svg>
            <div className="flex-1">
              <p className="text-sm font-medium text-amber-800">You are currently offline</p>
              <p className="mt-0.5 text-xs text-amber-700">
                You can review previously loaded diagnostic results. New diagnoses require a live connection.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
