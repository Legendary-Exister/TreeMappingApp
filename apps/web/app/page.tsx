'use client';

import dynamic from 'next/dynamic';

const MapWithNoSSR = dynamic(() => import('../components/Map'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-screen flex flex-col items-center justify-center bg-gray-50">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-emerald-600 mb-4" />
      <p className="text-gray-600 font-medium">Loading MapLibre GL Tree Map...</p>
    </div>
  ),
});

export default function HomePage() {
  return (
    <main className="w-full h-screen relative">
      <MapWithNoSSR />
    </main>
  );
}
