import { useEffect } from 'react';
import { Card, CardHeader, CardBody } from '../components/Card';
import { ErrorMessage } from '../components/Alert';
import { useAnalytics } from '../hooks/useDiagnostics';

function AnalyticsSkeleton() {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {Array.from({ length: 4 }).map((_, i) => (
        <Card key={i}>
          <CardHeader title={['Overview', 'Status', 'Checks', 'DTCs'][i] || 'Section'} />
          <CardBody>
            <div className="space-y-3">
              <div className="h-4 w-full animate-pulse rounded bg-surface-container-high" />
              <div className="h-4 w-5/6 animate-pulse rounded bg-surface-container-high" />
              <div className="h-4 w-4/6 animate-pulse rounded bg-surface-container-high" />
            </div>
          </CardBody>
        </Card>
      ))}
    </div>
  );
}

export function AnalyticsPage() {
  const { loadAnalytics, ...apiState } = useAnalytics();

  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  const data = apiState.data;

  return (
    <div className="mx-auto max-w-5xl">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-on-surface">Diagnostic Analytics</h1>
          <p className="mt-1 text-on-surface-variant">
            Overview of diagnostic outcomes and trends across all sessions.
          </p>
        </div>

        {apiState.error && (
          <ErrorMessage message={apiState.error} onRetry={loadAnalytics} />
        )}

        {apiState.loading && <AnalyticsSkeleton />}

        {!apiState.loading && !apiState.error && data && (
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader title="Overview" />
              <CardBody>
                <div className="grid grid-cols-2 gap-4">
                  <Stat label="Total Sessions" value={data.total_sessions} />
                  <Stat label="Total Results" value={data.total_results} />
                </div>
              </CardBody>
            </Card>

            <Card>
              <CardHeader title="Hypothesis Status Distribution" />
              <CardBody>
                {data.hypothesis_status_distribution &&
                Object.keys(data.hypothesis_status_distribution).length > 0 ? (
                  <div className="space-y-2">
                    {Object.entries(data.hypothesis_status_distribution).map(([status, count]) => (
                      <div key={status} className="flex items-center justify-between">
                        <span className="text-sm font-medium text-on-surface-variant capitalize">{status}</span>
                        <span className="text-sm font-semibold text-on-surface">{count}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-on-surface-variant">No data available.</p>
                )}
              </CardBody>
            </Card>

            <Card>
              <CardHeader title="Check Status Distribution" />
              <CardBody>
                {data.check_status_distribution &&
                Object.keys(data.check_status_distribution).length > 0 ? (
                  <div className="space-y-2">
                    {Object.entries(data.check_status_distribution).map(([status, count]) => (
                      <div key={status} className="flex items-center justify-between">
                        <span className="text-sm font-medium text-on-surface-variant capitalize">{status}</span>
                        <span className="text-sm font-semibold text-on-surface">{count}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-on-surface-variant">No data available.</p>
                )}
              </CardBody>
            </Card>

            <Card>
              <CardHeader title="Common DTCs" />
              <CardBody>
                {data.common_dtcs && data.common_dtcs.length > 0 ? (
                  <div className="space-y-2">
                    {data.common_dtcs.map((item) => (
                      <div key={item.code} className="flex items-center justify-between">
                        <span className="font-mono text-sm font-medium text-on-surface-variant">{item.code}</span>
                        <span className="text-sm font-semibold text-on-surface">{item.count}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-on-surface-variant">No DTC data available.</p>
                )}
              </CardBody>
            </Card>

            <Card className="lg:col-span-2">
              <CardHeader title="Confirmed Faults" />
              <CardBody>
                {data.confirmed_faults && data.confirmed_faults.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-left text-sm">
                      <thead>
                        <tr className="border-b border-outline-variant">
                          <th className="pb-2 pr-4 font-semibold text-on-surface-variant">Fault Description</th>
                          <th className="pb-2 text-right font-semibold text-on-surface-variant">Occurrences</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.confirmed_faults.map((item) => (
                          <tr key={item.fault_description} className="border-b border-outline-variant last:border-0">
                            <td className="py-2 pr-4 text-on-surface">{item.fault_description}</td>
                            <td className="py-2 text-right font-mono text-on-surface-variant">{item.count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-sm text-on-surface-variant">No confirmed faults recorded yet.</p>
                )}
              </CardBody>
            </Card>
          </div>
        )}
      </div>
    );
  }

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md bg-surface-container-low p-4">
      <p className="text-2xl font-bold text-on-surface">{value}</p>
      <p className="text-sm text-on-surface-variant">{label}</p>
    </div>
  );
}
