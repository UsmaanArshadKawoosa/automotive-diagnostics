import { Outlet } from 'react-router-dom';
import { MinimalHeader } from './MinimalHeader';

export function Layout() {
  return (
    <div className="min-h-screen bg-slate-50">
      <MinimalHeader />
      <main className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        <Outlet />
      </main>
    </div>
  );
}
