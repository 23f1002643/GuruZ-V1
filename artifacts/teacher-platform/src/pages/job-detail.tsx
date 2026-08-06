import { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'wouter';
import { useGetJob, getGetJobQueryKey, Job } from '@workspace/api-client-react';
import { useQueryClient } from '@tanstack/react-query';
import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/ui/status-badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import { formatDate, formatDuration, formatFileSize } from '@/lib/utils';
import { ArrowLeft, CheckCircle2, Circle, XCircle, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

const STAGE_ICONS = {
  'Document Intelligence': '📄',
  'Educational Classification': '🎓',
  'Knowledge Extraction': '🧠',
  'Teaching Planner': '📋',
  'Lesson Generation': '📚',
  'Activity Generation': '🎯',
  'Assessment Generation': '✍️',
  'Misconception Detection': '⚠️',
  'Validation': '✅',
  'Publishing': '🚀',
};

export default function JobDetailPage() {
  const params = useParams();
  const jobId = params.id as string;
  const queryClient = useQueryClient();
  const eventSourceRef = useRef<EventSource | null>(null);
  
  const { data: job, isLoading } = useGetJob(jobId, {
    query: {
      enabled: !!jobId,
      queryKey: getGetJobQueryKey(jobId),
      refetchInterval: (query) => {
        // Stop refetching when job is in terminal state
        const jobData = (query as any)?.state?.data as Job | undefined;
        if (!jobData) return false;
        const terminalStates = ['completed', 'failed', 'cancelled'];
        return terminalStates.includes(jobData.status) ? false : 3000;
      },
    },
  });

  // SSE connection for real-time updates
  useEffect(() => {
    if (!jobId || !job) return;
    
    // Only connect SSE for active jobs
    if (job.status !== 'processing' && job.status !== 'pending') {
      return;
    }

    const eventSource = new EventSource(`/api/jobs/${jobId}/events`);
    eventSourceRef.current = eventSource;

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Update the job data in cache
        queryClient.setQueryData(getGetJobQueryKey(jobId), (oldData: Job | undefined) => {
          if (!oldData) return oldData;
          
          return {
            ...oldData,
            ...data,
          };
        });
      } catch (error) {
        console.error('Error parsing SSE event:', error);
      }
    };

    eventSource.onerror = () => {
      console.error('SSE connection error');
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [jobId, job?.status, queryClient]);

  if (isLoading) {
    return (
      <div className="flex-1 overflow-auto">
        <PageHeader title="Job Details" />
        <div className="p-8">
          <div className="space-y-6">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-96 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="flex-1 overflow-auto">
        <PageHeader title="Job Not Found" />
        <div className="p-8">
          <Card>
            <CardContent className="pt-6">
              <div className="text-center py-12">
                <p className="text-muted-foreground mb-4">Job not found.</p>
                <Link href="/jobs">
                  <Button>Back to Jobs</Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-auto">
      <PageHeader
        title="Job Details"
        actions={
          <Link href="/jobs" data-testid="link-back-to-jobs">
            <Button variant="outline" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Jobs
            </Button>
          </Link>
        }
      />
      
      <div className="p-8 max-w-5xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Job Overview */}
          <Card data-testid="card-job-overview">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="text-xl">{job.filename}</CardTitle>
                  <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground font-mono">
                    <span>ID: {job.job_id}</span>
                    <span>Created: {formatDate(job.created_at)}</span>
                  </div>
                </div>
                <StatusBadge status={job.status} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div>
                  <div className="text-sm text-muted-foreground mb-1">Progress</div>
                  <div className="text-2xl font-display font-bold">{job.overall_progress}%</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground mb-1">File Size</div>
                  <div className="text-2xl font-display font-bold">
                    {formatFileSize(job.file_size)}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground mb-1">File Type</div>
                  <div className="text-2xl font-display font-bold uppercase">
                    {job.file_type || '—'}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground mb-1">Processing Time</div>
                  <div className="text-2xl font-display font-bold">
                    {formatDuration(job.processing_time_seconds)}
                  </div>
                </div>
              </div>

              {job.error && (
                <div className="mt-4 p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
                  <div className="text-sm font-medium text-destructive mb-1">Error</div>
                  <div className="text-sm text-destructive/90">{job.error}</div>
                </div>
              )}

              {job.package_id && (
                <div className="mt-4">
                  <Link href={`/packages/${job.package_id}`} data-testid="link-view-package">
                    <Button>View Package</Button>
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Pipeline Visualizer */}
          <Card data-testid="card-pipeline">
            <CardHeader>
              <CardTitle>10-Stage AI Pipeline</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {job.stages.map((stage, index) => {
                  const isCompleted = stage.completed_at !== null;
                  const isProcessing = stage.started_at && !stage.completed_at;
                  const isPending = !stage.started_at;

                  return (
                    <motion.div
                      key={stage.stage_index}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="relative"
                      data-testid={`stage-${stage.stage_index}`}
                    >
                      <div
                        className={cn(
                          'flex items-start gap-4 p-4 rounded-lg border transition-colors',
                          isProcessing && 'bg-primary/5 border-primary/30',
                          isCompleted && 'bg-emerald-500/5 border-emerald-500/20',
                          isPending && 'bg-muted/50 border-border'
                        )}
                      >
                        {/* Stage Icon/Status */}
                        <div className="flex-shrink-0 mt-1">
                          {isCompleted && (
                            <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                          )}
                          {isProcessing && (
                            <Circle className="h-5 w-5 text-primary animate-pulse" />
                          )}
                          {isPending && (
                            <Clock className="h-5 w-5 text-muted-foreground" />
                          )}
                        </div>

                        {/* Stage Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-3 mb-1">
                            <span className="text-2xl">
                              {STAGE_ICONS[stage.stage as keyof typeof STAGE_ICONS] || '⚙️'}
                            </span>
                            <div>
                              <div className="font-medium">{stage.stage}</div>
                              <div className="text-xs text-muted-foreground font-mono">
                                Stage {stage.stage_index + 1} of {stage.total_stages}
                              </div>
                            </div>
                          </div>

                          {stage.message && (
                            <div className="text-sm text-muted-foreground mt-2">
                              {stage.message}
                            </div>
                          )}

                          {/* Progress Bar */}
                          {isProcessing && (
                            <div className="mt-3">
                              <div className="flex items-center justify-between text-xs mb-1">
                                <span className="text-muted-foreground">Progress</span>
                                <span className="font-mono font-medium">{stage.progress}%</span>
                              </div>
                              <Progress value={stage.progress} className="h-1.5" />
                            </div>
                          )}

                          {/* Timestamps */}
                          <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground font-mono">
                            {stage.started_at && (
                              <span>Started: {formatDate(stage.started_at)}</span>
                            )}
                            {stage.completed_at && (
                              <span>Completed: {formatDate(stage.completed_at)}</span>
                            )}
                          </div>
                        </div>

                        {/* Stage Progress Percentage */}
                        <div className="flex-shrink-0">
                          <div
                            className={cn(
                              'text-2xl font-display font-bold',
                              isCompleted && 'text-emerald-500',
                              isProcessing && 'text-primary',
                              isPending && 'text-muted-foreground'
                            )}
                          >
                            {stage.progress}%
                          </div>
                        </div>
                      </div>

                      {/* Connector Line */}
                      {index < job.stages.length - 1 && (
                        <div className="flex justify-center my-2">
                          <div
                            className={cn(
                              'w-0.5 h-4',
                              isCompleted ? 'bg-emerald-500/30' : 'bg-border'
                            )}
                          />
                        </div>
                      )}
                    </motion.div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
