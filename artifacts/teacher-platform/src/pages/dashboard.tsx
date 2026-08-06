import { useGetPackageStats, useListJobs, useDetailedHealthCheck } from '@workspace/api-client-react';
import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { StatusBadge } from '@/components/ui/status-badge';
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip';
import { Link } from 'wouter';
import { formatDate, formatDuration } from '@/lib/utils';
import { Package, ListChecks, BookOpen, Clock, Server, Database, Brain, Upload, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

const GRADIENT_CLASSES = [
  'from-indigo-500 to-purple-600',
  'from-emerald-500 to-teal-600',
  'from-amber-500 to-orange-600',
  'from-rose-500 to-pink-600',
];

function StatCard({
  icon: Icon,
  label,
  value,
  loading,
  testId,
  sub,
  gradient,
  index,
}: {
  icon: React.ElementType;
  label: string;
  value?: string | number | null;
  loading?: boolean;
  testId?: string;
  sub?: string;
  gradient?: string;
  index?: number;
}) {
  return (
    <Card
      data-testid={testId}
      className="relative overflow-hidden border-transparent"
    >
      <div
        className={cn(
          'absolute inset-0 bg-gradient-to-br opacity-90',
          gradient || GRADIENT_CLASSES[(index ?? 0) % GRADIENT_CLASSES.length]
        )}
      />
      <div className="absolute inset-0 bg-black/20" />
      <CardContent className="relative pt-6 pb-5 text-white">
        <div className="flex items-center justify-between mb-3">
          <div className="h-10 w-10 rounded-xl bg-white/20 backdrop-blur flex items-center justify-center">
            <Icon className="h-5 w-5 text-white" />
          </div>
        </div>
        {loading ? (
          <Skeleton className="h-8 w-24 bg-white/20" />
        ) : (
          <div className="text-3xl font-display font-bold drop-shadow">{value ?? '—'}</div>
        )}
        <div className="text-white/90 text-sm mt-1 font-medium">{label}</div>
        {sub && <div className="text-white/70 text-xs mt-0.5">{sub}</div>}
      </CardContent>
    </Card>
  );
}

export default function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useGetPackageStats();
  const { data: recentJobs, isLoading: jobsLoading } = useListJobs({ limit: 5 });
  const { data: health } = useDetailedHealthCheck();
  const jobs = Array.isArray(recentJobs) ? recentJobs : [];

  const isLlmOk =
    health?.llm_status === 'nvidia' || health?.llm_status === 'groq';

  return (
    <div className="flex-1 overflow-auto">
      <PageHeader
        title="Dashboard"
        description="Real-time overview of the AI processing pipeline and knowledge packages"
        actions={
          <Link href="/upload">
            <Button size="sm" data-testid="button-dashboard-upload">
              <Upload className="h-4 w-4 mr-2" />
              Upload
            </Button>
          </Link>
        }
      />

      <div className="p-8 space-y-8">
        {/* Stats Grid */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
        >
          <StatCard
            icon={Package}
            label="Total Packages"
            value={stats?.total_packages}
            loading={statsLoading}
            testId="card-stat-packages"
            index={0}
          />
          <StatCard
            icon={ListChecks}
            label="Total Jobs"
            value={stats?.total_jobs}
            loading={statsLoading}
            testId="card-stat-jobs"
            sub={stats ? `${stats.completed_jobs} completed · ${stats.failed_jobs} failed` : undefined}
            index={1}
          />
          <StatCard
            icon={Clock}
            label="Avg. Processing Time"
            value={
              stats?.avg_processing_time_seconds != null
                ? formatDuration(stats.avg_processing_time_seconds)
                : '—'
            }
            loading={statsLoading}
            testId="card-stat-avg-time"
            index={2}
          />
          <StatCard
            icon={BookOpen}
            label="Subjects"
            value={stats?.subjects?.length}
            loading={statsLoading}
            testId="card-stat-subjects"
            sub={stats?.subjects?.slice(0, 3).join(', ')}
            index={3}
          />
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Jobs */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="lg:col-span-2"
          >
            <Card data-testid="card-recent-jobs">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Recent Jobs</CardTitle>
                  <Link href="/jobs">
                    <Button variant="ghost" size="sm" className="text-xs">
                      View All
                    </Button>
                  </Link>
                </div>
              </CardHeader>
              <CardContent>
                {jobsLoading ? (
                  <div className="space-y-3">
                    {[1, 2, 3].map((i) => (
                      <Skeleton key={i} className="h-14 w-full" />
                    ))}
                  </div>
                ) : jobs.length > 0 ? (
                  <div className="space-y-2">
                    {jobs.map((job) => (
                      <Link
                        key={job.job_id}
                        href={`/jobs/${job.job_id}`}
                        data-testid={`link-recent-job-${job.job_id}`}
                      >
                        <div className="flex items-center justify-between p-3 rounded-lg border border-border hover:bg-accent/50 transition-colors">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium truncate">{job.filename}</span>
                              <StatusBadge status={job.status} />
                            </div>
                            <div className="text-xs text-muted-foreground font-mono mt-0.5">
                              {job.job_id.slice(0, 8)} · {formatDate(job.created_at)}
                            </div>
                          </div>
                          <div className="ml-3 text-right flex-shrink-0">
                            <div className="text-sm font-mono font-medium">
                              {job.overall_progress}%
                            </div>
                          </div>
                        </div>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-10 text-muted-foreground">
                    <p className="mb-3">No jobs yet.</p>
                    <Link href="/upload">
                      <Button size="sm" variant="outline">Upload a document</Button>
                    </Link>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>

          {/* System Status */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
          >
            <Card data-testid="card-system-status">
              <CardHeader>
                <CardTitle>System Status</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {[
                    {
                      icon: Server,
                      label: 'API Server',
                      tooltip: 'Checks whether the backend API is reachable and responding.',
                      ok: health?.status === 'ok',
                      value: health?.status ?? 'checking…',
                    },
                    {
                      icon: Database,
                      label: 'ChromaDB',
                      tooltip: 'Verifies the embedded vector store and connection health.',
                      ok: health?.chromadb_status === 'ok',
                      value: health?.chromadb_status ?? 'checking…',
                    },
                    {
                      icon: Brain,
                      label: 'LLM',
                      tooltip: 'Reports the active LLM provider and whether an AI model is reachable.',
                      ok: isLlmOk,
                      value:
                        health?.llm_status || health?.llm_provider || 'checking…',
                      sub:
                        health?.llm_status && health?.llm_provider &&
                        health.llm_status !== health.llm_provider
                          ? `configured=${health.llm_provider}`
                          : undefined,
                    },
                  ].map(({ icon: Icon, label, ok, value, tooltip, sub }) => (
                    <div
                      key={label}
                      className="flex items-center justify-between py-2 border-b border-border last:border-0"
                    >
                      <div className="flex items-center gap-2">
                        <div
                          className={cn(
                            'h-2 w-2 rounded-full',
                            ok ? 'bg-emerald-500' : 'bg-red-400'
                          )}
                        />
                        <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button
                              type="button"
                              className="inline-flex items-center gap-1 text-sm text-left"
                            >
                              <span>{label}</span>
                              <Info className="h-3 w-3 text-muted-foreground" />
                            </button>
                          </TooltipTrigger>
                          <TooltipContent>{tooltip}</TooltipContent>
                        </Tooltip>
                      </div>
                      <div className="text-right">
                        <div className="text-xs font-mono text-muted-foreground capitalize">
                          {value}
                        </div>
                        {sub && (
                          <div className="text-xxs text-muted-foreground/80 mt-0.5">
                            {sub}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {health && (
                    <div className="pt-2 text-xs text-muted-foreground font-mono">
                      Uptime: {Math.round(health.uptime_seconds ?? 0)}s
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Recent Subjects */}
            {stats?.subjects && stats.subjects.length > 0 && (
              <Card className="mt-4" data-testid="card-subjects">
                <CardHeader>
                  <CardTitle className="text-sm">Subjects Processed</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {stats.subjects.map((s) => (
                      <span
                        key={s}
                        className="text-xs font-mono bg-muted px-2 py-1 rounded border border-border"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  );
}
