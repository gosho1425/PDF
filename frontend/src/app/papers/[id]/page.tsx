import { AppShell } from '@/components/layout/AppShell';
import { PaperDetailContent } from './PaperDetailContent';

// Next.js 15: params is now a Promise — must be awaited in async page components.
export default async function PaperDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <AppShell>
      <PaperDetailContent paperId={id} />
    </AppShell>
  );
}
