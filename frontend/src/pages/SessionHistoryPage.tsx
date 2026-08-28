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
            <div className="h-5 w-48 animate-pulse rounded bg-surface-container-high" />
            <div className="h-4 w-64 animate-pulse rounded bg-surface-container-high" />
            <div className="h-4 w-full animate-pulse rounded bg-surface-container-high" />
          </div>
          <div className="h-16 w-32 animate-pulse rounded bg-surface-container-high" />
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
          <h1 className="text-2xl font-bold text-on-surface">Session History</h1>
          <p className="mt-1 text-on-surface-variant">
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
              <div className="rounded-lg border border-dashed border-outline-variant p-8 text-center">
                <p className="text-sm text-on-surface-variant">No diagnostic sessions yet. Run a diagnosis to get started.</p>
                <Link to="/diagnose" className="mt-2 inline-flex items-center text-sm font-medium text-primary hover:text-primary-fixed-dim">
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
                            <h3 className="text-sm font-semibold text-on-surface">
                              Session {session.id.slice(0, 8)}...
                            </h3>
                            <span className="text-xs text-on-surface-variant">
                              {formatDate(session.created_at)}
                            </span>
                          </div>
                          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-on-surface-variant">
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
                          <p className="mt-1 text-sm text-on-surface-variant line-clamp-1">
                            {session.symptom_text}
                          </p>
                        </div>
                        <div className="flex shrink-0 flex-col items-end gap-2">
                          <span className="text-xs text-on-surface-variant">
                            {session.results.length} result{session.results.length !== 1 ? 's' : ''}
                          </span>
                          <div className="flex flex-wrap gap-1">
                            {confirmed > 0 && (
                              <span className="rounded-full bg-green-900/30 px-2 py-0.5 text-xs font-medium text-green-300">
                                {confirmed} confirmed
                              </span>
                            )}
                            {rejected > 0 && (
                              <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
                                {rejected} rejected
                              </span>
                            )}
                            {totalChecks > 0 && (
                              <span className="rounded-full bg-surface-container-high px-2 py-0.5 text-xs font-medium text-on-surface-variant">
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
