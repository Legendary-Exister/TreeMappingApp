import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'TreeMap - Citizen Science Tree Map',
  description: 'Map, monitor and protect urban city trees using open map tech.',
  openGraph: {
    title: 'TreeMap - Urban Forest Explorer',
    description: 'Explore municipal tree registers and OpenStreetMap trees with MapLibre GL.',
    type: 'website',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="h-screen w-screen m-0 p-0 antialiased overflow-hidden">{children}</body>
    </html>
  );
}
