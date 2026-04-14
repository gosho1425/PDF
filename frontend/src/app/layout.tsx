import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'PaperLens – Scientific Paper Extraction',
  description: 'Extract structured scientific data from research papers using AI',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-surface-secondary min-h-screen`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
