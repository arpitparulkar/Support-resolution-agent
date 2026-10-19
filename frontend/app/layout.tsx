import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'ResolveAI | Intelligent Support',
  description: 'A thoughtful support workspace for orders, refunds, and customer care.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
