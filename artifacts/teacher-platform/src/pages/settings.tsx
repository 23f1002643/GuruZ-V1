import { useGetSettings, useDetailedHealthCheck } from '@workspace/api-client-react';
import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { motion } from 'framer-motion';
import { Server, Brain, Database, Settings, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function SettingsPage() {
  const { data: settings, isLoading: settingsLoading } = useGetSettings();
  const { data: health, isLoading: healthLoading } = useDetailedHealthCheck();

  const isLoading = settingsLoading || healthLoading;

  const statusDot = (ok: boolean) => (
    <div
      className={cn(
        'h-2.5 w-2.5 rounded-full flex-shrink-0',
        ok ? 'bg-emerald-500' : 'bg-red-400'
      )}
    />
  );

  return (
    <div className="flex-1 overflow-auto">
      <PageHeader
        title="Settings"
        description="Current platform configuration and system status"
      />

      <div className="p-8 max-w-4xl space-y-6">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          {/* System Health */}
          <Card data-testid="card-system-health">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-4 w-4" />
                System Health
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-3/4" />
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center justify-between py-2 border-b border-border">
                    <div className="flex items-center gap-3">
                      {statusDot(health?.status === 'ok')}
                      <span className="text-sm font-medium">API Server</span>
                    </div>
                    <span className="text-xs font-mono text-muted-foreground capitalize">
                      {health?.status ?? 'unknown'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2 border-b border-border">
                    <div className="flex items-center gap-3">
                      {statusDot(health?.chromadb_status === 'ok')}
                      <span className="text-sm font-medium">ChromaDB</span>
                    </div>
                    <span className="text-xs font-mono text-muted-foreground">
                      {health?.chromadb_status ?? 'unknown'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2 border-b border-border">
                    <div className="flex items-center gap-3">
                      {statusDot(
                        health?.llm_status === 'gemini' || health?.llm_status === 'ollama'
                      )}
                      <span className="text-sm font-medium">LLM Provider</span>
                    </div>
                    <span className="text-xs font-mono text-muted-foreground">
                      {health?.llm_provider ?? settings?.llm_provider ?? '—'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between py-2">
                    <div className="flex items-center gap-3">
                      <div className="h-2.5 w-2.5 rounded-full bg-emerald-500 flex-shrink-0" />
                      <span className="text-sm font-medium">Uptime</span>
                    </div>
                    <span className="text-xs font-mono text-muted-foreground">
                      {health?.uptime_seconds != null
                        ? `${Math.round(health.uptime_seconds)}s`
                        : '—'}
                    </span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* LLM Configuration */}
          <Card className="mt-4" data-testid="card-llm-config">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Brain className="h-4 w-4" />
                LLM Configuration
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-6 w-full" />
                  <Skeleton className="h-6 w-full" />
                </div>
              ) : (
                <div className="space-y-3 text-sm">
                  <Row label="Provider" value={settings?.llm_provider} />
                  <Row label="Gemini Model" value={settings?.gemini_model} />
                  <Row label="Ollama Model" value={settings?.ollama_model} />
                  <Row label="Ollama URL" value={settings?.ollama_base_url} mono />
                </div>
              )}
            </CardContent>
          </Card>

          {/* RAG Configuration */}
          <Card className="mt-4" data-testid="card-rag-config">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-4 w-4" />
                RAG Configuration
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-6 w-full" />
                  <Skeleton className="h-6 w-full" />
                </div>
              ) : (
                <div className="space-y-3 text-sm">
                  <Row label="Chunk Size" value={settings?.chunk_size?.toString()} mono />
                  <Row label="Chunk Overlap" value={settings?.chunk_overlap?.toString()} mono />
                  <Row label="Max Retries" value={settings?.max_retry_attempts?.toString()} mono />
                </div>
              )}
            </CardContent>
          </Card>

          {/* Pipeline Configuration */}
          <Card className="mt-4" data-testid="card-pipeline-config">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-4 w-4" />
                Pipeline Configuration
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-6 w-full" />
              ) : (
                <div className="space-y-3 text-sm">
                  <Row label="Period Duration" value={`${settings?.period_duration_minutes ?? '—'} min`} />
                  <Row label="Default Language" value={settings?.default_language} />
                </div>
              )}
            </CardContent>
          </Card>

          {/* Jobs Summary */}
          {health && (
            <Card className="mt-4" data-testid="card-jobs-summary">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Server className="h-4 w-4" />
                  Jobs Summary
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 text-sm">
                  <Row label="Total Jobs" value={health.total_jobs?.toString()} mono />
                  <Row label="Active Jobs" value={health.active_jobs?.toString()} mono />
                </div>
              </CardContent>
            </Card>
          )}
        </motion.div>

        <p className="text-xs text-muted-foreground pb-4">
          Settings are read-only in this view. To change them, set environment variables and restart the server.
        </p>
      </div>
    </div>
  );
}

function Row({
  label,
  value,
  mono = false,
}: {
  label: string;
  value?: string | null;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-border last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className={cn('font-medium', mono && 'font-mono text-xs')}>{value ?? '—'}</span>
    </div>
  );
}
