import { useState, useCallback, useRef } from 'react';
import { useListJobs, getListJobsQueryKey } from '@workspace/api-client-react';
import { useQueryClient } from '@tanstack/react-query';
import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { StatusBadge } from '@/components/ui/status-badge';
import { useToast } from '@/hooks/use-toast';
import { Upload, FileText, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDate } from '@/lib/utils';
import { Link } from 'wouter';
import { motion } from 'framer-motion';

const ACCEPTED_TYPES = '.pdf,.docx,.pptx,.txt';
const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'es', label: 'Spanish' },
  { value: 'fr', label: 'French' },
  { value: 'de', label: 'German' },
  { value: 'zh', label: 'Chinese' },
  { value: 'hi', label: 'Hindi' },
];

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [language, setLanguage] = useState<string>('en');
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: activeJobs } = useListJobs({
    status: 'processing',
  });

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      const ext = '.' + droppedFile.name.split('.').pop()?.toLowerCase();
      if (ACCEPTED_TYPES.includes(ext)) {
        setFile(droppedFile);
      } else {
        toast({
          title: 'Invalid file type',
          description: 'Please upload a PDF, DOCX, PPTX, or TXT file.',
          variant: 'destructive',
        });
      }
    }
  }, [toast]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      if (language) {
        formData.append('language', language);
      }

      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const result = await response.json();
      
      toast({
        title: 'Upload successful',
        description: `Job ${result.job_id.slice(0, 8)} created. Processing started.`,
      });

      setFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }

      queryClient.invalidateQueries({ queryKey: getListJobsQueryKey() });
    } catch (error) {
      toast({
        title: 'Upload failed',
        description: error instanceof Error ? error.message : 'An error occurred',
        variant: 'destructive',
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="flex-1 overflow-auto">
      <PageHeader
        title="Upload Document"
        description="Upload educational documents to transform into Teacher Knowledge Packages"
      />
      
      <div className="p-8 max-w-4xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-6"
        >
          <Card data-testid="card-upload">
            <CardHeader>
              <CardTitle>Document Upload</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Drag and Drop Zone */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={cn(
                  'border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors',
                  isDragging
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:border-primary/50 hover:bg-accent/50'
                )}
                data-testid="dropzone-upload"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={ACCEPTED_TYPES}
                  onChange={handleFileSelect}
                  className="hidden"
                  data-testid="input-file"
                />
                
                {file ? (
                  <div className="space-y-4">
                    <FileText className="h-12 w-12 mx-auto text-primary" />
                    <div>
                      <div className="font-medium text-lg">{file.name}</div>
                      <div className="text-sm text-muted-foreground mt-1">
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        setFile(null);
                        if (fileInputRef.current) {
                          fileInputRef.current.value = '';
                        }
                      }}
                      data-testid="button-remove-file"
                    >
                      <X className="h-4 w-4 mr-2" />
                      Remove
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <Upload className="h-12 w-12 mx-auto text-muted-foreground" />
                    <div>
                      <div className="font-medium text-lg">
                        Drop your file here or click to browse
                      </div>
                      <div className="text-sm text-muted-foreground mt-2">
                        Supports PDF, DOCX, PPTX, TXT
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Language Selector */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Language</label>
                <Select value={language} onValueChange={setLanguage}>
                  <SelectTrigger data-testid="select-language">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {LANGUAGES.map((lang) => (
                      <SelectItem key={lang.value} value={lang.value}>
                        {lang.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Upload Button */}
              <Button
                onClick={handleUpload}
                disabled={!file || isUploading}
                className="w-full"
                size="lg"
                data-testid="button-upload"
              >
                {isUploading ? 'Uploading...' : 'Start Processing'}
              </Button>
            </CardContent>
          </Card>

          {/* Active Jobs Queue */}
          {activeJobs && activeJobs.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <Card data-testid="card-active-jobs">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    Active Processing Queue
                    <span className="text-sm font-normal text-muted-foreground">
                      ({activeJobs.length})
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {activeJobs.map((job) => (
                      <Link
                        key={job.job_id}
                        href={`/jobs/${job.job_id}`}
                        data-testid={`link-active-job-${job.job_id}`}
                      >
                        <div className="flex items-center justify-between p-4 rounded-lg border border-border hover:bg-accent/50 transition-colors">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-3">
                              <span className="font-medium truncate">{job.filename}</span>
                              <StatusBadge status={job.status} />
                            </div>
                            <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground font-mono">
                              <span>{job.job_id.slice(0, 8)}</span>
                              {job.current_stage && <span>{job.current_stage}</span>}
                            </div>
                          </div>
                          <div className="ml-4">
                            <div className="text-right font-mono text-sm font-medium">
                              {job.overall_progress}%
                            </div>
                          </div>
                        </div>
                      </Link>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
