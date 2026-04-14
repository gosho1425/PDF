import { AppShell } from '@/components/layout/AppShell';
import { PaperDetailContent } from './PaperDetailContent';

export default function PaperDetailPage({ params }: { params: { id: string } }) {
  return (
    <AppShell>
      <PaperDetailContent paperId={params.id} />
    </AppShell>
  );
}
