import { Outlet } from 'react-router-dom';
import { TopBar } from './TopBar';
import { AppRail } from './AppRail';
import { BottomNav } from './BottomNav';

export function Layout() {
  return (
    <div className="flex min-h-screen bg-background text-on-surface">
      <div className="fixed inset-0 tech-grid z-0" aria-hidden="true" />
      <AppRail />
      <div className="relative z-10 flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="flex-1 overflow-y-auto px-4 pb-24 pt-6 md:px-8 md:pb-10">
          <Outlet />
        </main>
        <BottomNav />
      </div>
    </div>
  );
}
