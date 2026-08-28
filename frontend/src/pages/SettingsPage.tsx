import { Card, CardBody } from '../components/Card';
import { useOnlineStatus } from '../hooks/useOnlineStatus';

export function SettingsPage() {
  const isOnline = useOnlineStatus();

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-8">
        <h1 className="font-headline-lg text-2xl font-bold text-on-surface sm:text-3xl">Settings</h1>
        <p className="mt-1 text-on-surface-variant">
          Workspace preferences and connection status.
        </p>
      </div>

      <div className="space-y-4">
        <Card>
          <CardBody className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-on-surface">Connection</p>
                <p className="text-sm text-on-surface-variant">
                  Live diagnosis requires a backend connection.
                </p>
              </div>
              <span
                className={[
                  'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ring-1 ring-inset',
                  isOnline
                    ? 'bg-secondary-container/20 text-secondary ring-secondary-container/40'
                    : 'bg-error-container/25 text-on-error-container ring-error-container/40',
                ].join(' ')}
              >
                <span className={['h-1.5 w-1.5 rounded-full', isOnline ? 'bg-secondary' : 'bg-error'].join(' ')} />
                {isOnline ? 'Connected' : 'Offline'}
              </span>
            </div>

            <div className="flex items-center justify-between border-t border-outline-variant pt-4">
              <div>
                <p className="font-medium text-on-surface">Offline cache</p>
                <p className="text-sm text-on-surface-variant">
                  Previously loaded results are available without a connection.
                </p>
              </div>
              <span className="text-sm font-medium text-on-surface-variant">Enabled</span>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <p className="font-medium text-on-surface">About</p>
            <p className="mt-1 text-sm text-on-surface-variant">
              AutoSage is an AI-powered automotive diagnostic workspace. Describe symptoms to receive
              structured, safety-first diagnostic assessments with likely causes, recommended checks,
              and repair guidance.
            </p>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
