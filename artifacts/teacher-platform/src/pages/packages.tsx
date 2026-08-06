import { useState } from 'react';
import {
  useListPackages,
  useDeletePackage,
  getListPackagesQueryKey,
} from '@workspace/api-client-react';
import { useQueryClient } from '@tanstack/react-query';
import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { Link } from 'wouter';
import { formatDate } from '@/lib/utils';
import { Search, Package, BookOpen, GraduationCap, Star, Trash2 } from 'lucide-react';
import { motion } from 'framer-motion';

export default function PackagesPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: packages, isLoading } = useListPackages({ limit: 200 });
  const deletePackageMutation = useDeletePackage();

  const handleDelete = async (e: React.MouseEvent, packageId: string, filename?: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm(`Delete package "${filename ?? packageId}"? This removes all related data.`)) return;
    try {
      await deletePackageMutation.mutateAsync({ packageId });
      toast({ title: 'Package deleted', description: `${filename} was removed.` });
      queryClient.invalidateQueries({ queryKey: getListPackagesQueryKey() });
    } catch (error) {
      toast({
        title: 'Failed to delete package',
        description: error instanceof Error ? error.message : 'An error occurred',
        variant: 'destructive',
      });
    }
  };

  const filtered = packages?.filter((pkg) => {
    const q = searchQuery.toLowerCase();
    return (
      pkg.filename?.toLowerCase().includes(q) ||
      pkg.subject?.toLowerCase().includes(q) ||
      pkg.topic?.toLowerCase().includes(q) ||
      pkg.grade?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="flex-1 overflow-auto">
      <PageHeader
        title="Knowledge Packages"
        description="Browse all generated Teacher Knowledge Packages"
      />

      <div className="p-8 space-y-6">
        {/* Search */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <Card data-testid="card-search">
            <CardContent className="pt-6">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by filename, subject, topic, or grade..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                  data-testid="input-search-packages"
                />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Packages Grid */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <Skeleton key={i} className="h-48 w-full" />
              ))}
            </div>
          ) : filtered && filtered.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filtered.map((pkg, index) => (
                <motion.div
                  key={pkg.package_id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.04 }}
                  data-testid={`card-package-${pkg.package_id}`}
                >
                  <Link href={`/packages/${pkg.package_id}`}>
                    <Card className="h-full hover:border-primary/50 hover:shadow-md transition-all cursor-pointer group">
                      <CardContent className="pt-5 space-y-4">
                        <div className="flex items-start gap-3">
                          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0 group-hover:bg-primary/20 transition-colors">
                            <Package className="h-5 w-5 text-primary" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-sm truncate">{pkg.filename}</div>
                            <div className="text-xs text-muted-foreground font-mono mt-0.5">
                              {pkg.package_id?.slice(0, 8)}
                            </div>
                          </div>
                        </div>

                        <div className="space-y-2">
                          <div className="flex items-center gap-2 text-sm">
                            <BookOpen className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                            <span className="font-medium truncate">{pkg.subject}</span>
                          </div>
                          {pkg.topic && (
                            <div className="text-xs text-muted-foreground truncate pl-5">
                              {pkg.topic}
                            </div>
                          )}
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <GraduationCap className="h-3.5 w-3.5" />
                            <span>{pkg.grade}</span>
                            {pkg.difficulty && (
                              <>
                                <span>·</span>
                                <span className="capitalize">{pkg.difficulty}</span>
                              </>
                            )}
                          </div>
                        </div>

<div className="flex items-center justify-between pt-1 border-t border-border">
                          <div className="text-xs text-muted-foreground">
                            {pkg.created_at ? formatDate(pkg.created_at) : '—'}
                          </div>
                          <div className="flex items-center gap-2">
                            {pkg.validation_score !== null && pkg.validation_score !== undefined && (
                              <div className="flex items-center gap-1 text-xs font-mono">
                                <Star className="h-3 w-3 text-yellow-500" />
                                <span>{(pkg.validation_score * 100).toFixed(0)}%</span>
                              </div>
                            )}
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6 text-muted-foreground hover:text-destructive"
                              onClick={(e) => handleDelete(e, pkg.package_id, pkg.filename)}
                              disabled={deletePackageMutation.isPending}
                              data-testid={`button-delete-package-${pkg.package_id}`}
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </Link>
                </motion.div>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="pt-6">
                <div className="text-center py-16 text-muted-foreground">
                  <Package className="h-12 w-12 mx-auto mb-4 opacity-30" />
                  <div className="font-medium mb-1">
                    {searchQuery ? 'No packages match your search.' : 'No packages yet.'}
                  </div>
                  <div className="text-sm">
                    {!searchQuery && (
                      <Link href="/upload" className="text-primary hover:underline">
                        Upload a document
                      </Link>
                    )}{' '}
                    {!searchQuery && 'to generate your first package.'}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </motion.div>
      </div>
    </div>
  );
}
