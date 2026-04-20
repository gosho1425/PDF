'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BookOpen, ScanLine, Settings, FlaskConical, TrendingUp } from 'lucide-react';

const links = [
  { href: '/',             label: 'Dashboard',    icon: FlaskConical },
  { href: '/scan',         label: 'Scan',         icon: ScanLine },
  { href: '/papers',       label: 'Papers',       icon: BookOpen },
  { href: '/optimization', label: 'Optimization', icon: TrendingUp },
  { href: '/settings',     label: 'Settings',     icon: Settings },
];

export function Nav() {
  const path = usePathname();
  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
      <div className="container mx-auto max-w-7xl px-4">
        <div className="flex items-center h-14 gap-1">
          <span className="font-bold text-blue-700 mr-4 text-lg tracking-tight">
            🔬 PaperLens
          </span>
          {links.map(({ href, label, icon: Icon }) => {
            const active = href === '/' ? path === '/' : path.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  active
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            );
          })}
        </div>
      </div>
    </header>
  );
}
