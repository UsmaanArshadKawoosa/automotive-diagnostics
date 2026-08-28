import { NavLink, useLocation } from 'react-router-dom';
import { NAV_ITEMS, isNavActive } from './navItems';
import { cn } from '../utils/cn';

export function AppRail() {
  const { pathname } = useLocation();

  return (
    <aside className="hidden w-60 shrink-0 border-r border-outline-variant bg-surface-container-lowest md:flex md:flex-col">
      <nav className="flex flex-1 flex-col gap-1 p-3" aria-label="Primary">
        {NAV_ITEMS.map((item) => {
          const active = isNavActive(item, pathname);
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={cn(
                'group flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors',
                active
                  ? 'bg-primary-container/20 text-primary-fixed-dim'
                  : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface'
              )}
            >
              <span
                className={cn(
                  'material-symbols-outlined text-[22px]',
                  active ? 'text-primary' : 'text-on-surface-variant'
                )}
              >
                {item.icon}
              </span>
              <span>{item.label}</span>
              {active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-primary" aria-hidden="true" />}
            </NavLink>
          );
        })}
      </nav>

      <div className="border-t border-outline-variant p-4">
        <p className="font-label-caps text-[10px] uppercase text-on-surface-variant/70">
          AutoSage Diagnostic
        </p>
        <p className="mt-1 text-xs text-on-surface-variant">Precision-first AI workspace</p>
      </div>
    </aside>
  );
}
