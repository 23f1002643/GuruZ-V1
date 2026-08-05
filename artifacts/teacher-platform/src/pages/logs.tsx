import { useState } from 'react';
import { useGetLogs } from '@workspace/api-client-react';
import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { RefreshCw, Search } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

const LEVEL_COLORS: Record<string, string> = {
  debug: 'text-gray-400',
  info: 'text-blue-400',
  warning: 'text-yellow-400',
  error: 'text-red-400',
  critical: 'text-red-500',
};

const LEVEL_BG: Record<string, string> = {
  debug: 'bg-gray-500/10 border-gray-500/20',
  info: 'bg-blue-500/10 border-blue-500/20',
  warning: 'bg-yellow-500/10 border-yellow-500/20',
  error: 'bg-red-500/10 border-red-500/20',
  critical: 'bg-red-600/10 border-red-600/20',
};

export default function LogsPage() {
  const [levelFilter, setLevelFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  const { data: logs, isLoading, refetch, isFetching } = useGetLogs({
    limit: 200,
    level: levelFilter === 'all' ? undefined : levelFilter,
  });

  const filtered = logs?.filter((log) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      log.message?.toLowerCase().includes(q) ||
      log.job_id?.toLowerCase().includes(q) ||
      log.stage?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="flex-1 overflow-auto">
      <PageHeader
        title="System Logs"
        description="Real-time pipeline and system event log"
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            data-testid="button-refresh-logs"
          >
            <RefreshCw className={cn('h-4 w-4 mr-2', isFetching && 'animate-spin')} />
            Refresh
          </Button>
        }
      />

      <div className="p-8 space-y-4">
        {/* Filters */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <Card data-testid="card-log-filters">
            <CardContent className="pt-4 pb-4">
              <div className="flex flex-col md:flex-row gap-3">
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search messages, job IDs, stages..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 font-mono text-sm"
                    data-testid="input-search-logs"
                  />
                </div>
                <Select value={levelFilter} onValueChange={setLevelFilter}>
                  <SelectTrigger className="w-full md:w-40" data-testid="select-level-filter">
                    <SelectValue placeholder="All levels" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All levels</SelectItem>
                    <SelectItem value="debug">Debug</SelectItem>
                    <SelectItem value="info">Info</SelectItem>
                    <SelectItem value="warning">Warning</SelectItem>
                    <SelectItem value="error">Error</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Log Entries */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card data-testid="card-log-entries">
            <CardContent className="pt-4">
              {isLoading ? (
                <div className="space-y-2">
                  {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
                    <Skeleton key={i} className="h-10 w-full" />
                  ))}
                </div>
              ) : filtered && filtered.length > 0 ? (
                <div className="space-y-1 font-mono text-xs">
                  {filtered.map((log, i) => (
                    <div
                      key={i}
                      className={cn(
                        'flex items-start gap-3 p-2.5 rounded border',
                        LEVEL_BG[log.level] || LEVEL_BG.info
                      )}
                      data-testid={`log-entry-${i}`}
                    >
                      {/* Timestamp */}
                      <span className="text-muted-foreground flex-shrink-0 w-[155px] truncate">
                        {log.timestamp
                          ? new Date(log.timestamp).toLocaleTimeString('en-US', {
                              hour12: false,
                              hour: '2-digit',
                              minute: '2-digit',
                              second: '2-digit',
                            })
                          : '—'}
                      </span>

                      {/* Level badge */}
                      <span
                        className={cn(
                          'flex-shrink-0 uppercase font-bold w-12',
                          LEVEL_COLORS[log.level] || LEVEL_COLORS.info
                        )}
                      >
                        {log.level?.slice(0, 4)}
                      </span>

                      {/* Job ID */}
                      {log.job_id && (
                        <span className="text-muted-foreground flex-shrink-0 w-[70px] truncate">
                          {log.job_id.slice(0, 8)}
                        </span>
                      )}

                      {/* Stage */}
                      {log.stage && (
                        <span className="text-primary flex-shrink-0">
                          [{log.stage}]
                        </span>
                      )}

                      {/* Message */}
                      <span className="flex-1 break-all">{log.message}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-16 text-muted-foreground">
                  {searchQuery || levelFilter !== 'all'
                    ? 'No logs match your filters.'
                    : 'No logs yet. Start processing a document to see activity.'}
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
