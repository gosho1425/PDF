import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Nav } from '@/components/layout/Nav';
import { Toaster } from '@/components/ui/Toaster';
import BackendBanner from '@/components/ui/BackendBanner';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'PaperLens — Research Paper Extraction',
  description: 'Local AI-powered research paper extraction tool',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen flex flex-col">
          <Nav />
          <BackendBanner />
          <main className="flex-1 container mx-auto max-w-7xl px-4 py-8">
            {children}
          </main>
          <footer className="text-center text-xs text-gray-400 py-4 border-t border-gray-100">
            PaperLens v2 — local research tool · API at{' '}
            <a href="http://localhost:8000/api/docs" target="_blank" className="underline">
              localhost:8000/api/docs
            </a>
          </footer>
        </div>
        <Toaster />
      </body>
    </html>
  );
}
