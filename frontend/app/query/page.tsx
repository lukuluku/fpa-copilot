import { Suspense } from 'react';
import { QueryClient } from './QueryClient';

interface PageProps {
  searchParams: Promise<{ session?: string; file?: string }>;
}

export default async function QueryPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const sessionId = params.session || `session-${Date.now()}`;
  const fileName = params.file || 'data.csv';

  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center text-gray-500">Loading...</div>}>
      <QueryClient sessionId={sessionId} fileName={fileName} />
    </Suspense>
  );
}
