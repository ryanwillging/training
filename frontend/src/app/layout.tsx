import type { Metadata, Viewport } from 'next';
import { Providers } from './providers';
import { Navigation } from '@/components/ui/Navigation';
import './globals.css';

export const metadata: Metadata = {
  title: 'Training Dashboard',
  description: 'AI-powered training optimization system',
};

export const viewport: Viewport = {
  themeColor: '#1976d2',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen bg-background">
        <Providers>
          <div className="min-h-screen flex flex-col">
            <Navigation />
            <main className="flex-1 py-4 sm:py-6">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                {children}
              </div>
            </main>
            <footer className="py-4 border-t border-outline-variant">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <p className="text-xs text-center text-gray-500">
                  Training Optimization System
                </p>
              </div>
            </footer>
          </div>
        </Providers>
      </body>
    </html>
  );
}
