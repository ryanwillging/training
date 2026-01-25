'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { Menu, X, Dumbbell } from 'lucide-react';
import { cn } from '@/lib/utils';

const PAGES = [
  { path: '/dashboard', name: 'Dashboard' },
  { path: '/explore', name: 'Explore' },
  { path: '/goals', name: 'Goals' },
  { path: '/plan-adjustments', name: 'Plan Adjustments' },
  { path: '/upcoming', name: 'Upcoming' },
];

export function Navigation() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <nav className="bg-surface border-b border-outline-variant sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand */}
          <Link
            href="/dashboard"
            className="flex items-center gap-2 text-primary hover:text-primary-dark transition-colors"
          >
            <Dumbbell className="w-6 h-6" />
            <span className="text-xl font-medium">Training</span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden sm:flex items-center gap-1">
            {PAGES.map((page) => (
              <Link
                key={page.path}
                href={page.path}
                className={cn(
                  'px-3 py-2 text-sm font-medium rounded-full transition-colors',
                  pathname === page.path
                    ? 'bg-primary/10 text-primary'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                )}
              >
                {page.name}
              </Link>
            ))}
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="sm:hidden p-2 rounded-full hover:bg-gray-100 transition-colors"
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? (
              <X className="w-6 h-6" />
            ) : (
              <Menu className="w-6 h-6" />
            )}
          </button>
        </div>
      </div>

      {/* Mobile Navigation */}
      {mobileMenuOpen && (
        <div className="sm:hidden border-t border-outline-variant bg-surface">
          <div className="px-4 py-2 space-y-1">
            {PAGES.map((page) => (
              <Link
                key={page.path}
                href={page.path}
                onClick={() => setMobileMenuOpen(false)}
                className={cn(
                  'block px-4 py-3 text-sm font-medium rounded-lg transition-colors',
                  pathname === page.path
                    ? 'bg-primary/10 text-primary'
                    : 'text-gray-600 hover:bg-gray-100'
                )}
              >
                {page.name}
              </Link>
            ))}
          </div>
        </div>
      )}
    </nav>
  );
}
