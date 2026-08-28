import { useOnlineStatus } from '../hooks/useOnlineStatus';

export function TopBar() {
  const isOnline = useOnlineStatus();

  return (
    <header className="sticky top-0 z-40 flex h-16 shrink-0 items-center justify-between border-b border-outline-variant bg-surface/90 px-4 backdrop-blur md:px-6">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-md bg-primary-container shadow-sm">
          <span className="material-symbols-outlined text-on-primary-container text-lg">precision_manufacturing</span>
        </div>
        <div className="flex flex-col leading-tight">
          <span className="font-headline-md text-base font-bold tracking-tight text-primary-fixed-dim">
            AutoSage
          </span>
          <div className="flex items-center gap-1.5">
            <span
              className={cnDot(isOnline ? 'bg-secondary' : 'bg-error')}
              aria-hidden="true"
            />
            <span className="font-label-caps text-[10px] uppercase text-on-surface-variant">
              {isOnline ? 'Connected' : 'Offline'}
            </span>
          </div>
        </div>
      </div>

      <button
        type="button"
        aria-label="Notifications"
        className="rounded-full p-2 text-on-surface-variant transition-colors hover:bg-surface-container-highest hover:text-primary active:scale-95"
      >
        <span className="material-symbols-outlined text-[22px]">notifications</span>
      </button>
    </header>
  );
}

function cnDot(color: string) {
  return `inline-block h-1.5 w-1.5 rounded-full ${color}`;
}
