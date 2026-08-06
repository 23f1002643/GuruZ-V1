import { useState, useEffect } from 'react';
import { useListJobs, useCancelJob, getListJobsQueryKey, JobStatus } from '@workspace/api-client-react';
import { useQueryClient } from '@tanstack/react-query';
import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { StatusBadge } from '@/components/ui/status-badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { Link } from 'wouter';
import { formatDate } from '@/lib/utils';
import { Search, X } from 'lucide-react';
import { motion } from 'framer-motion';

export default function JobsPage() {
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: jobs, isLoading, refetch } = useListJobs({
    status: statusFilter === 'all' ? undefined : (statusFilter as JobStatus),
  });

  const cancelJobMutation = useCancelJob();

  // Auto-refresh when any job is processing
  useEffect(() => {
    const hasProcessingJobs = jobs?.some(
      (job) => job.status === 'processing' || job.status === 'pending'
    );

    if (hasProcessingJobs) {
      const interval = setInterval(() => {
        refetch();
      }, 3000);
      return () => clearInterval(interval);
    }
    return undefined;
  }, [jobs, refetch]);

  const filteredJobs = jobs?.filter((job) =>
    job.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
    job.job_id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCancelJob = async (jobId: string, filename: string) => {
    try {
      await cancelJobMutation.mutateAsync({ jobId });
      toast({
        title: 'Job cancelled',
        description: `${filename} has been cancelled.`,
      });
      queryClient.invalidateQueries({ queryKey: getListJobsQueryKey() });
    } catch (error) {
      toast({
        title: 'Failed to cancel job',
        description: error instanceof Error ? error.message : 'An error occurred',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="flex-1 overflow-auto">
      <PageHeader
        title="Processing Jobs"
        description="Monitor document processing pipeline and job status"
      />
      
      <div className="p-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          {/* Filters */}
          <Card data-testid="card-filters">
            <CardContent className="pt-6">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search by filename or job ID..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9"
                    data-testid="input-search-jobs"
                  />
                </div>
                
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-full md:w-48" data-testid="select-status-filter">
                    <SelectValue placeholder="All statuses" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All statuses</SelectItem>
                    <SelectItem value="pending">Pending</SelectItem>
                    <SelectItem value="processing">Processing</SelectItem>
                    <SelectItem value="completed">Completed</SelectItem>
                    <SelectItem value="failed">Failed</SelectItem>
                    <SelectItem value="cancelled">Cancelled</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Jobs List */}
          <Card data-testid="card-jobs-list">
            <CardContent className="pt-6">
              {isLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <Skeleton key={i} className="h-20 w-full" />
                  ))}
                </div>
              ) : filteredJobs && filteredJobs.length > 0 ? (
                <div className="space-y-3">
                  {filteredJobs.map((job, index) => (
                    <motion.div
                      key={job.job_id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      data-testid={`row-job-${job.job_id}`}
                    >
                      <div className="flex items-center justify-between p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors">
                        <Link
                          href={`/jobs/${job.job_id}`}
                          className="flex-1 min-w-0"
                          data-testid={`link-job-${job.job_id}`}
                        >
                          <div className="flex items-center gap-3 mb-2">
                            <span className="font-medium truncate">{job.filename}</span>
                            <StatusBadge status={job.status} />
                          </div>
                          
                          <div className="flex items-center gap-4 text-xs text-muted-foreground font-mono">
                            <span>{job.job_id.slice(0, 8)}</span>
                            <span>{formatDate(job.created_at)}</span>
                            {job.current_stage && <span>{job.current_stage}</span>}
                          </div>

                          {/* Progress Bar */}
                          {(job.status === 'processing' || job.status === 'pending') && (
                            <div className="mt-3">
                              <div className="flex items-center justify-between text-xs mb-1">
                                <span className="text-muted-foreground">Progress</span>
                                <span className="font-mono font-medium">{job.overall_progress}%</span>
                              </div>
                              <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-primary transition-all duration-500"
                                  style={{ width: `${job.overall_progress}%` }}
                                />
                              </div>
                            </div>
                          )}

                          {job.error && (
                            <div className="mt-2 text-xs text-destructive">
                              Error: {job.error}
                            </div>
                          )}
                        </Link>

                        <div className="ml-4 flex items-center gap-2">
                          {(job.status === 'processing' || job.status === 'pending') && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleCancelJob(job.job_id, job.filename)}
                              disabled={cancelJobMutation.isPending}
                              data-testid={`button-cancel-${job.job_id}`}
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  {searchQuery || statusFilter !== 'all'
                    ? 'No jobs match your filters.'
                    : 'No jobs yet. Upload a document to get started.'}
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
