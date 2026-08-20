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
              <div className="h-4 w-full animate-pulse rounded bg-slate-200" />
              <div className="h-4 w-5/6 animate-pulse rounded bg-slate-200" />
              <div className="h-4 w-4/6 animate-pulse rounded bg-slate-200" />
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
          <h1 className="text-2xl font-bold text-slate-900">Diagnostic Analytics</h1>
          <p className="mt-1 text-slate-600">
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
                        <span className="text-sm font-medium text-slate-700 capitalize">{status}</span>
                        <span className="text-sm font-semibold text-slate-900">{count}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">No data available.</p>
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
                        <span className="text-sm font-medium text-slate-700 capitalize">{status}</span>
                        <span className="text-sm font-semibold text-slate-900">{count}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">No data available.</p>
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
                        <span className="font-mono text-sm font-medium text-slate-700">{item.code}</span>
                        <span className="text-sm font-semibold text-slate-900">{item.count}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">No DTC data available.</p>
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
                        <tr className="border-b border-slate-200">
                          <th className="pb-2 pr-4 font-semibold text-slate-600">Fault Description</th>
                          <th className="pb-2 text-right font-semibold text-slate-600">Occurrences</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.confirmed_faults.map((item) => (
                          <tr key={item.fault_description} className="border-b border-slate-50 last:border-0">
                            <td className="py-2 pr-4 text-slate-900">{item.fault_description}</td>
                            <td className="py-2 text-right font-mono text-slate-600">{item.count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">No confirmed faults recorded yet.</p>
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
    <div className="rounded-md bg-slate-50 p-4">
      <p className="text-2xl font-bold text-slate-900">{value}</p>
      <p className="text-sm text-slate-500">{label}</p>
    </div>
  );
}
