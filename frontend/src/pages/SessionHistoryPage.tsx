import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardBody } from '../components/Card';
import { ErrorMessage } from '../components/Alert';
import { useSessions } from '../hooks/useDiagnostics';

function SessionSkeleton() {
  return (
    <Card>
      <CardBody>
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 space-y-3">
            <div className="h-5 w-48 animate-pulse rounded bg-slate-200" />
            <div className="h-4 w-64 animate-pulse rounded bg-slate-200" />
            <div className="h-4 w-full animate-pulse rounded bg-slate-200" />
          </div>
          <div className="h-16 w-32 animate-pulse rounded bg-slate-200" />
        </div>
      </CardBody>
    </Card>
  );
}

export function SessionHistoryPage() {
  const { loadSessions, ...apiState } = useSessions();

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  return (
    <div className="mx-auto max-w-5xl">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900">Session History</h1>
          <p className="mt-1 text-slate-600">
            Review past diagnostic sessions and their outcomes.
          </p>
        </div>

        {apiState.error && (
          <ErrorMessage message={apiState.error} onRetry={loadSessions} />
        )}

        {apiState.loading && (
          <div className="space-y-4">
            <SessionSkeleton />
            <SessionSkeleton />
            <SessionSkeleton />
          </div>
        )}

        {!apiState.loading && apiState.data && (
          <div className="space-y-4">
            {apiState.data.length === 0 && (
              <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center">
                <p className="text-sm text-slate-500">No diagnostic sessions yet. Run a diagnosis to get started.</p>
                <Link to="/diagnose" className="mt-2 inline-flex items-center text-sm font-medium text-brand-600 hover:text-brand-700">
                  Run a diagnosis →
                </Link>
              </div>
            )}
            {apiState.data.map((session) => {
              const confirmed = session.results.filter((r) => r.hypothesis_status === 'confirmed').length;
              const rejected = session.results.filter((r) => r.hypothesis_status === 'rejected').length;
              const totalChecks = session.results.reduce((acc, r) => acc + r.check_outcomes.length, 0);
              const passedChecks = session.results.reduce(
                (acc, r) => acc + r.check_outcomes.filter((c) => c.status === 'passed').length,
                0
              );
              return (
                <Link key={session.id} to={`/sessions/${session.id}`}>
                  <Card className="transition-shadow hover:shadow-md">
                    <CardBody>
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <h3 className="text-sm font-semibold text-slate-900">
                              Session {session.id.slice(0, 8)}...
                            </h3>
                            <span className="text-xs text-slate-400">
                              {formatDate(session.created_at)}
                            </span>
                          </div>
                          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-slate-600">
                            {session.vin && <span>VIN: {session.vin}</span>}
                            {(session.make || session.model) && (
                              <span>
                                {session.make} {session.model}
                                {session.year ? ` (${session.year})` : ''}
                              </span>
                            )}
                            {session.dtc_codes && (
                              <span className="font-mono text-xs">{session.dtc_codes}</span>
                            )}
                          </div>
                          <p className="mt-1 text-sm text-slate-500 line-clamp-1">
                            {session.symptom_text}
                          </p>
                        </div>
                        <div className="flex shrink-0 flex-col items-end gap-2">
                          <span className="text-xs text-slate-400">
                            {session.results.length} result{session.results.length !== 1 ? 's' : ''}
                          </span>
                          <div className="flex flex-wrap gap-1">
                            {confirmed > 0 && (
                              <span className="rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
                                {confirmed} confirmed
                              </span>
                            )}
                            {rejected > 0 && (
                              <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
                                {rejected} rejected
                              </span>
                            )}
                            {totalChecks > 0 && (
                              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                                {passedChecks}/{totalChecks} checks passed
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </CardBody>
                  </Card>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    );
  }
