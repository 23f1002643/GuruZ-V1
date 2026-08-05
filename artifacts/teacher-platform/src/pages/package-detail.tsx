import { useState } from 'react';
import { useParams, Link } from 'wouter';
import { useGetPackage } from '@workspace/api-client-react';
import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { formatDate } from '@/lib/utils';
import { ArrowLeft, BookOpen, Target, Brain, CheckSquare, AlertTriangle, ShieldCheck } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

export default function PackageDetailPage() {
  const params = useParams();
  const packageId = params.id as string;
  const [activeTab, setActiveTab] = useState('overview');

  const { data: pkg, isLoading } = useGetPackage(packageId, {
    query: { enabled: !!packageId },
  });

  if (isLoading) {
    return (
      <div className="flex-1 overflow-auto">
        <PageHeader title="Package Details" />
        <div className="p-8 space-y-4">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-80 w-full" />
        </div>
      </div>
    );
  }

  if (!pkg) {
    return (
      <div className="flex-1 overflow-auto">
        <PageHeader title="Package Not Found" />
        <div className="p-8">
          <Card>
            <CardContent className="pt-6 text-center py-16">
              <p className="text-muted-foreground mb-4">Package not found.</p>
              <Link href="/packages">
                <Button>Back to Packages</Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const scoreColor = pkg.validation_report?.overall_score
    ? pkg.validation_report.overall_score >= 0.8
      ? 'text-emerald-400'
      : pkg.validation_report.overall_score >= 0.6
      ? 'text-yellow-400'
      : 'text-red-400'
    : 'text-muted-foreground';

  return (
    <div className="flex-1 overflow-auto">
      <PageHeader
        title="Package Details"
        actions={
          <Link href="/packages">
            <Button variant="outline" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Packages
            </Button>
          </Link>
        }
      />

      <div className="p-8 space-y-6">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          {/* Header Card */}
          <Card data-testid="card-package-overview">
            <CardContent className="pt-6">
              <div className="flex items-start justify-between flex-wrap gap-4">
                <div>
                  <h2 className="text-2xl font-display font-bold">{pkg.filename}</h2>
                  <div className="text-sm text-muted-foreground font-mono mt-1">
                    {pkg.package_id}
                  </div>
                  <div className="flex items-center gap-4 mt-3 text-sm">
                    <span className="font-medium">{pkg.metadata?.subject}</span>
                    <span className="text-muted-foreground">·</span>
                    <span className="text-muted-foreground">{pkg.metadata?.topic}</span>
                    <span className="text-muted-foreground">·</span>
                    <span className="text-muted-foreground">{pkg.metadata?.grade}</span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-muted-foreground mb-1">Validation Score</div>
                  <div className={cn('text-4xl font-display font-bold', scoreColor)}>
                    {pkg.validation_report?.overall_score
                      ? `${(pkg.validation_report.overall_score * 100).toFixed(0)}%`
                      : '—'}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t border-border">
                <div>
                  <div className="text-xs text-muted-foreground mb-1">Concepts</div>
                  <div className="text-xl font-display font-bold">{pkg.concepts?.length ?? 0}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground mb-1">Lessons</div>
                  <div className="text-xl font-display font-bold">{pkg.lessons?.length ?? 0}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground mb-1">Questions</div>
                  <div className="text-xl font-display font-bold">
                    {pkg.assessments?.total_questions ?? 0}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground mb-1">Created</div>
                  <div className="text-sm font-mono">
                    {pkg.created_at ? formatDate(pkg.created_at) : '—'}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-6">
                <a
                  href={`/api/packages/${packageId}/download/lesson_plan`}
                  target="_blank"
                  rel="noreferrer"
                >
                  <Button size="sm" className="w-full">
                    Download Lesson Plan
                  </Button>
                </a>
                <a
                  href={`/api/packages/${packageId}/download/teacher_guide`}
                  target="_blank"
                  rel="noreferrer"
                >
                  <Button size="sm" className="w-full">
                    Download Teacher Guide
                  </Button>
                </a>
                <a
                  href={`/api/packages/${packageId}/download/assessment_book`}
                  target="_blank"
                  rel="noreferrer"
                >
                  <Button size="sm" className="w-full">
                    Download Assessment Book
                  </Button>
                </a>
              </div>
            </CardContent>
          </Card>

          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-6">
            <TabsList className="grid w-full grid-cols-6">
              <TabsTrigger value="overview" data-testid="tab-overview">Overview</TabsTrigger>
              <TabsTrigger value="lessons" data-testid="tab-lessons">Lessons</TabsTrigger>
              <TabsTrigger value="activities" data-testid="tab-activities">Activities</TabsTrigger>
              <TabsTrigger value="assessments" data-testid="tab-assessments">Assessments</TabsTrigger>
              <TabsTrigger value="misconceptions" data-testid="tab-misconceptions">Misconceptions</TabsTrigger>
              <TabsTrigger value="validation" data-testid="tab-validation">Validation</TabsTrigger>
            </TabsList>

            {/* Overview Tab */}
            <TabsContent value="overview" className="mt-4 space-y-4">
              {/* Learning Objectives */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Target className="h-4 w-4" />
                    Learning Objectives
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {(pkg.learning_objectives ?? []).map((obj, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm">
                        <span className="text-primary font-mono text-xs mt-0.5 flex-shrink-0">
                          {String(i + 1).padStart(2, '0')}
                        </span>
                        {obj}
                      </li>
                    ))}
                    {!pkg.learning_objectives?.length && (
                      <li className="text-muted-foreground text-sm">No objectives listed.</li>
                    )}
                  </ul>
                </CardContent>
              </Card>

              {/* Concepts */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Brain className="h-4 w-4" />
                    Key Concepts ({pkg.concepts?.length ?? 0})
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {(pkg.concepts ?? []).map((concept, i) => (
                      <div key={i} className="p-3 rounded-lg border border-border">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-sm">{concept.name}</span>
                          <span className="text-xs font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                            {concept.importance}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground">{concept.description}</p>
                      </div>
                    ))}
                    {!pkg.concepts?.length && (
                      <div className="text-muted-foreground text-sm">No concepts extracted.</div>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Prerequisites */}
              {pkg.prerequisites && pkg.prerequisites.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <BookOpen className="h-4 w-4" />
                      Prerequisites
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {pkg.prerequisites.map((p, i) => (
                        <span
                          key={i}
                          className="text-xs font-mono bg-muted px-2.5 py-1 rounded-md border border-border"
                        >
                          {p}
                        </span>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* Lessons Tab */}
            <TabsContent value="lessons" className="mt-4 space-y-4">
              {(pkg.lessons ?? []).length === 0 ? (
                <Card>
                  <CardContent className="pt-6 text-center text-muted-foreground py-12">
                    No lessons generated.
                  </CardContent>
                </Card>
              ) : (
                (pkg.lessons ?? []).map((lesson, i) => (
                  <Card key={i} data-testid={`card-lesson-${i}`}>
                    <CardHeader>
                      <CardTitle className="text-base">
                        Period {lesson.period_number}: {lesson.title}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex items-center gap-4 text-xs text-muted-foreground font-mono">
                        <span>{lesson.duration_minutes} min</span>
                        {lesson.prior_knowledge_check && (
                          <span className="text-primary">Prior knowledge check included</span>
                        )}
                      </div>
                      {lesson.objectives && (
                        <div>
                          <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">
                            Objectives
                          </div>
                          <ul className="space-y-1">
                            {lesson.objectives.map((obj, j) => (
                              <li key={j} className="text-sm flex items-start gap-2">
                                <span className="text-primary mt-0.5">·</span> {obj}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {lesson.entry_ticket && (
                        <div className="p-3 bg-muted/50 rounded-lg text-sm">
                          <div className="font-medium text-xs uppercase tracking-wide text-muted-foreground mb-1">
                            Entry Ticket
                          </div>
                          {lesson.entry_ticket}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))
              )}
            </TabsContent>

            {/* Activities Tab */}
            <TabsContent value="activities" className="mt-4 space-y-4">
              {(pkg.activities ?? []).length === 0 ? (
                <Card>
                  <CardContent className="pt-6 text-center text-muted-foreground py-12">
                    No activities generated.
                  </CardContent>
                </Card>
              ) : (
                (pkg.activities ?? []).map((activity, i) => (
                  <Card key={i} data-testid={`card-activity-${i}`}>
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-3">
                        {activity.title}
                        <span className="text-xs font-mono text-muted-foreground bg-muted px-2 py-0.5 rounded capitalize">
                          {activity.activity_type}
                        </span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <p className="text-sm text-muted-foreground">{activity.description}</p>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground font-mono">
                        <span>{activity.duration_minutes} min</span>
                        {activity.materials && (
                          <span>Materials: {activity.materials.join(', ')}</span>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </TabsContent>

            {/* Assessments Tab */}
            <TabsContent value="assessments" className="mt-4 space-y-4">
              {!pkg.assessments ? (
                <Card>
                  <CardContent className="pt-6 text-center text-muted-foreground py-12">
                    No assessments generated.
                  </CardContent>
                </Card>
              ) : (
                <>
                  {/* MCQs */}
                  {(pkg.assessments.mcqs ?? []).length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-base">
                          <CheckSquare className="h-4 w-4" />
                          Multiple Choice ({pkg.assessments.mcqs.length})
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-4">
                          {pkg.assessments.mcqs.map((mcq, i) => (
                            <div key={i} className="p-4 border border-border rounded-lg">
                              <div className="font-medium text-sm mb-3">
                                Q{i + 1}. {mcq.question}
                              </div>
                              <div className="grid grid-cols-2 gap-2">
                                {mcq.options.map((opt, j) => (
                                  <div
                                    key={j}
                                    className={cn(
                                      'text-xs p-2 rounded border',
                                      j === mcq.correct_option
                                        ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400'
                                        : 'border-border text-muted-foreground'
                                    )}
                                  >
                                    {String.fromCharCode(65 + j)}. {opt}
                                  </div>
                                ))}
                              </div>
                              <div className="text-xs text-muted-foreground mt-2 italic">
                                {mcq.explanation}
                              </div>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Short Answers */}
                  {(pkg.assessments.short_answers ?? []).length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">
                          Short Answer ({pkg.assessments.short_answers.length})
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        {pkg.assessments.short_answers.map((q, i) => (
                          <div key={i} className="p-3 border border-border rounded-lg">
                            <div className="font-medium text-sm mb-1">Q{i + 1}. {q.question}</div>
                            <div className="text-xs text-muted-foreground">
                              {q.expected_answer_outline}
                            </div>
                          </div>
                        ))}
                      </CardContent>
                    </Card>
                  )}
                </>
              )}
            </TabsContent>

            {/* Misconceptions Tab */}
            <TabsContent value="misconceptions" className="mt-4 space-y-4">
              {(pkg.misconceptions ?? []).length === 0 ? (
                <Card>
                  <CardContent className="pt-6 text-center text-muted-foreground py-12">
                    No misconceptions identified.
                  </CardContent>
                </Card>
              ) : (
                (pkg.misconceptions ?? []).map((m, i) => (
                  <Card key={i} data-testid={`card-misconception-${i}`}>
                    <CardContent className="pt-5">
                      <div className="flex items-start gap-3">
                        <AlertTriangle
                          className={cn(
                            'h-5 w-5 mt-0.5 flex-shrink-0',
                            m.severity === 'high'
                              ? 'text-red-400'
                              : m.severity === 'medium'
                              ? 'text-yellow-400'
                              : 'text-blue-400'
                          )}
                        />
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="font-medium text-sm">{m.description}</span>
                            <span
                              className={cn(
                                'text-xs font-mono px-2 py-0.5 rounded uppercase',
                                m.severity === 'high'
                                  ? 'bg-red-500/10 text-red-400'
                                  : m.severity === 'medium'
                                  ? 'bg-yellow-500/10 text-yellow-400'
                                  : 'bg-blue-500/10 text-blue-400'
                              )}
                            >
                              {m.severity}
                            </span>
                          </div>
                          {m.correct_understanding && (
                            <div className="text-sm text-muted-foreground mb-2">
                              <strong>Correct:</strong> {m.correct_understanding}
                            </div>
                          )}
                          {m.remedial_actions && m.remedial_actions.length > 0 && (
                            <div>
                              <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">
                                Remedial Actions
                              </div>
                              <ul className="space-y-1">
                                {m.remedial_actions.map((a, j) => (
                                  <li key={j} className="text-xs text-muted-foreground flex gap-2">
                                    <span className="text-primary">·</span> {a}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </TabsContent>

            {/* Validation Tab */}
            <TabsContent value="validation" className="mt-4 space-y-4">
              {!pkg.validation_report ? (
                <Card>
                  <CardContent className="pt-6 text-center text-muted-foreground py-12">
                    No validation report available.
                  </CardContent>
                </Card>
              ) : (
                <>
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <ShieldCheck className="h-4 w-4" />
                        Validation Summary
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                          <div className="text-xs text-muted-foreground mb-1">Overall Score</div>
                          <div className={cn('text-2xl font-display font-bold', scoreColor)}>
                            {(pkg.validation_report.overall_score * 100).toFixed(0)}%
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground mb-1">Hallucination Risk</div>
                          <div className="text-2xl font-display font-bold">
                            {(pkg.validation_report.hallucination_score * 100).toFixed(0)}%
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground mb-1">Completeness</div>
                          <div className="text-2xl font-display font-bold">
                            {(pkg.validation_report.completeness_score * 100).toFixed(0)}%
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground mb-1">Valid</div>
                          <div className={cn(
                            'text-2xl font-display font-bold',
                            pkg.validation_report.is_valid ? 'text-emerald-400' : 'text-red-400'
                          )}>
                            {pkg.validation_report.is_valid ? 'Yes' : 'No'}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  {pkg.validation_report.issues && pkg.validation_report.issues.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">Issues ({pkg.validation_report.issues.length})</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        {pkg.validation_report.issues.map((issue, i) => (
                          <div key={i} className="flex items-start gap-2 p-3 border border-border rounded-lg">
                            <span className={cn(
                              'text-xs font-mono px-2 py-0.5 rounded uppercase flex-shrink-0',
                              issue.severity === 'error'
                                ? 'bg-red-500/10 text-red-400'
                                : issue.severity === 'warning'
                                ? 'bg-yellow-500/10 text-yellow-400'
                                : 'bg-blue-500/10 text-blue-400'
                            )}>
                              {issue.severity}
                            </span>
                            <div className="flex-1">
                              <div className="text-sm font-medium">{issue.message}</div>
                              {issue.field && (
                                <div className="text-xs text-muted-foreground font-mono mt-0.5">
                                  Field: {issue.field}
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </CardContent>
                    </Card>
                  )}
                </>
              )}
            </TabsContent>
          </Tabs>
        </motion.div>
      </div>
    </div>
  );
}
