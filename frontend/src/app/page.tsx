import { AppShell } from '@/components/layout/AppShell';
import { DashboardPage } from './dashboard/DashboardPage';

export default function Home() {
  return (
    <AppShell>
      <DashboardPage />
    </AppShell>
  );
}
