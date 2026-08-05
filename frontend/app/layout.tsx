import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'FP&A Copilot',
  description: 'Financial Planning & Analysis with AI',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-white text-gray-900">
        {children}
      </body>
    </html>
  );
}
