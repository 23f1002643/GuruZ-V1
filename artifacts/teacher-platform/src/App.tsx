import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import { ThemeProvider } from '@/components/theme-provider';
import { Sidebar } from '@/components/layout/sidebar';
import NotFound from '@/pages/not-found';
import Dashboard from '@/pages/dashboard';
import UploadPage from '@/pages/upload';
import JobsPage from '@/pages/jobs';
import JobDetailPage from '@/pages/job-detail';
import PackagesPage from '@/pages/packages';
import PackageDetailPage from '@/pages/package-detail';
import LogsPage from '@/pages/logs';
import SettingsPage from '@/pages/settings';
import { Route, Switch, Router as WouterRouter } from 'wouter';
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5_000,
    },
  },
});

function AppLayout() {
  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      <Sidebar />
      <main className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <Switch>
          <Route path="/" component={Dashboard} />
          <Route path="/upload" component={UploadPage} />
          <Route path="/jobs" component={JobsPage} />
          <Route path="/jobs/:id" component={JobDetailPage} />
          <Route path="/packages" component={PackagesPage} />
          <Route path="/packages/:id" component={PackageDetailPage} />
          <Route path="/logs" component={LogsPage} />
          <Route path="/settings" component={SettingsPage} />
          <Route component={NotFound} />
        </Switch>
      </main>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="dark">
        <TooltipProvider>
          <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, '')}>
            <AppLayout />
          </WouterRouter>
          <Toaster />
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
