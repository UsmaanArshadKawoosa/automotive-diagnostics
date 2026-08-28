export interface NavItem {
  to: string;
  label: string;
  icon: string;
  /** Path prefixes that should mark this item active. */
  match: string[];
}

export const NAV_ITEMS: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: 'dashboard', match: ['/dashboard'] },
  { to: '/', label: 'Diagnosis', icon: 'troubleshoot', match: ['/', '/diagnose'] },
  { to: '/history', label: 'History', icon: 'history', match: ['/history', '/sessions'] },
  { to: '/vehicles', label: 'Vehicles', icon: 'directions_car', match: ['/vehicles'] },
  { to: '/settings', label: 'Settings', icon: 'settings', match: ['/settings'] },
];

export function isNavActive(item: NavItem, pathname: string): boolean {
  return item.match.some((prefix) => pathname === prefix || pathname.startsWith(prefix + '/'));
}
