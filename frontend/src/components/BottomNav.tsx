import { NavLink, useLocation } from 'react-router-dom';
import { NAV_ITEMS, isNavActive } from './navItems';
import { cn } from '../utils/cn';

export function BottomNav() {
  const { pathname } = useLocation();

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-40 flex h-16 items-center justify-around border-t border-outline-variant bg-surface-container pb-[env(safe-area-inset-bottom,0px)] md:hidden"
      aria-label="Primary"
    >
      {NAV_ITEMS.map((item) => {
        const active = isNavActive(item, pathname);
        return (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={cn(
              'flex flex-1 flex-col items-center justify-center gap-1 py-1 text-[10px] font-medium uppercase tracking-wider transition-colors',
              active ? 'text-primary-fixed-dim' : 'text-on-surface-variant'
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
            {item.label}
          </NavLink>
        );
      })}
    </nav>
  );
}
