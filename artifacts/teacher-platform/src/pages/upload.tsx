import { useState, useCallback, useRef } from 'react';
import { useListJobs, getListJobsQueryKey } from '@workspace/api-client-react';
import { useQueryClient } from '@tanstack/react-query';
import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/ui/status-badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { Upload, FileText, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDate } from '@/lib/utils';
import { Link } from 'wouter';
import { motion } from 'framer-motion';

const ACCEPTED_TYPES = '.pdf,.docx,.pptx,.txt';

interface AssessmentConfig {
  mcq_count: number;
  include_mcq: boolean;
  include_short_answer: boolean;
  include_long_answer: boolean;
  include_numerical: boolean;
  include_case_study: boolean;
  include_hots: boolean;
  include_diagram: boolean;
  include_answer_key: boolean;
}

const DEFAULT_CONFIG: AssessmentConfig = {
  mcq_count: 6,
  include_mcq: true,
  include_short_answer: true,
  include_long_answer: true,
  include_numerical: true,
  include_case_study: false,
  include_hots: false,
  include_diagram: false,
  include_answer_key: true,
};

function AssessmentConfigPanel({
  config,
  onChange,
}: {
  config: AssessmentConfig;
  onChange: (config: AssessmentConfig) => void;
}) {
  const toggle = (key: keyof AssessmentConfig) => {
    onChange({ ...config, [key]: !config[key] });
  };

  const checkboxes: { key: keyof AssessmentConfig; label: string }[] = [
    { key: 'include_mcq', label: 'MCQ' },
    { key: 'include_short_answer', label: 'Short Answer' },
    { key: 'include_long_answer', label: 'Long Answer' },
    { key: 'include_numerical', label: 'Numericals' },
    { key: 'include_case_study', label: 'Case Study' },
    { key: 'include_hots', label: 'HOTS' },
    { key: 'include_diagram', label: 'Diagram Questions' },
    { key: 'include_answer_key', label: 'Answer Key' },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Label htmlFor="mcq-count" className="text-sm font-medium">
          MCQ Count
        </Label>
        <div className="w-24">
          <Input
            id="mcq-count"
            type="number"
            min={0}
            max={50}
            value={config.mcq_count}
            onChange={(e) =>
              onChange({
                ...config,
                mcq_count: Math.max(0, parseInt(e.target.value || '0', 10)),
              })
            }
            className="text-right"
            data-testid="input-mcq-count"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 pt-2 border-t border-border">
        {checkboxes.map(({ key, label }) => (
          <label
            key={key}
            className="flex items-center gap-2 text-sm cursor-pointer select-none"
            data-testid={`checkbox-${key}`}
          >
            <Checkbox
              checked={config[key] as boolean}
              onCheckedChange={() => toggle(key)}
            />
            <span className="text-muted-foreground">{label}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [assessmentConfig, setAssessmentConfig] = useState<AssessmentConfig>(DEFAULT_CONFIG);
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
      formData.append('assessment_config', JSON.stringify(assessmentConfig));

      // const response = await fetch('/api/upload', {
      //   method: 'POST',
      //   body: formData,
      // });
      const API_BASE =
        import.meta.env.DEV
          ? ""
          : (import.meta.env.VITE_API_URL || "https://guruz-backend.onrender.com");
    
      const response = await fetch(`${API_BASE}/api/upload`, {
        method: "POST",
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

{/* Assessment Configuration */}
              <div className="rounded-lg border border-border p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-sm">Assessment Configuration</div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      Select the question types to generate
                    </div>
                  </div>
                </div>
                <AssessmentConfigPanel
                  config={assessmentConfig}
                  onChange={setAssessmentConfig}
                />
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
