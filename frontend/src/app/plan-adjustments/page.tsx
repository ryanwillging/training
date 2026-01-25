'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Button,
  Badge,
  LoadingState,
} from '@/components/ui';
import { planApi, type DailyReview, type Modification } from '@/lib/api';
import { PRIORITY_COLORS } from '@/lib/utils';
import {
  Bot,
  Check,
  X,
  ChevronDown,
  ChevronUp,
  MessageSquare,
  Clock,
  Sparkles,
} from 'lucide-react';

export function PlanAdjustmentsPage() {
  const [userContext, setUserContext] = useState('');
  const [expandedReview, setExpandedReview] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const { data: latestReview, isLoading } = useQuery({
    queryKey: ['latest-review'],
    queryFn: planApi.getLatestReview,
  });

  const { data: planStatus } = useQuery({
    queryKey: ['plan-status'],
    queryFn: planApi.getStatus,
  });

  // Run evaluation mutation
  const evaluateMutation = useMutation({
    mutationFn: (context?: string) => planApi.runEvaluation(context),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['latest-review'] });
      setUserContext('');
    },
  });

  // Action modification mutation
  const actionModMutation = useMutation({
    mutationFn: ({
      reviewId,
      modIndex,
      action,
    }: {
      reviewId: number;
      modIndex: number;
      action: 'approve' | 'reject';
    }) => planApi.actionModification(reviewId, modIndex, action),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['latest-review'] });
    },
  });

  // Action all pending mutation
  const actionAllMutation = useMutation({
    mutationFn: ({
      reviewId,
      action,
    }: {
      reviewId: number;
      action: 'approve' | 'reject';
    }) => planApi.actionReview(reviewId, action),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['latest-review'] });
    },
  });

  if (isLoading) {
    return <LoadingState message="Loading plan adjustments..." />;
  }

  const review = latestReview as DailyReview | undefined;
  const hasReview = review && review.id;
  const modifications = review?.proposed_adjustments || [];
  const pendingMods = modifications.filter((m) => m.status === 'pending');
  const actionedMods = modifications.filter((m) => m.status !== 'pending');

  const handleRunEvaluation = () => {
    evaluateMutation.mutate(userContext || undefined);
  };

  const handleActionMod = (
    reviewId: number,
    modIndex: number,
    action: 'approve' | 'reject'
  ) => {
    actionModMutation.mutate({ reviewId, modIndex, action });
  };

  const handleActionAll = (action: 'approve' | 'reject') => {
    if (review?.id) {
      actionAllMutation.mutate({ reviewId: review.id, action });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="md-headline-large text-2xl sm:text-3xl font-medium text-gray-900">
          Plan Adjustments
        </h1>
        <p className="text-gray-500 mt-1">
          AI-powered training plan evaluations and modifications
        </p>
      </div>

      {/* Latest Review Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-primary" />
            Latest Review
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!hasReview ? (
            <div className="text-sm text-gray-600">
              No evaluations yet. Run a new evaluation to see insights and recommendations.
            </div>
          ) : (
            <div className="space-y-3 text-sm text-gray-700">
              <div className="flex items-center gap-2 text-gray-500">
                <Clock className="w-4 h-4" />
                <span>Evaluation date: {new Date(review.date).toLocaleDateString()}</span>
              </div>
              <div>
                <p className="font-medium text-gray-800">Insights</p>
                <p>{review.insights || 'No insights available.'}</p>
              </div>
              <div>
                <p className="font-medium text-gray-800">Recommendations</p>
                <p>{review.recommendations || 'No recommendations available.'}</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Run Evaluation Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="w-5 h-5 text-primary" />
            Run AI Evaluation
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-600 mb-4">
            The AI will analyze your wellness data, recent workouts, and goal
            progress to suggest any needed adjustments to your training plan.
          </p>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Your Notes (optional)
              </label>
              <textarea
                value={userContext}
                onChange={(e) => setUserContext(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                rows={3}
                placeholder="Example: I've been feeling fatigued this week... or I'm feeling great and want to push harder..."
              />
            </div>
            <div className="flex gap-2">
              <Button
                onClick={handleRunEvaluation}
                disabled={evaluateMutation.isPending}
              >
                {evaluateMutation.isPending ? (
                  <>
                    <Sparkles className="w-4 h-4 animate-pulse" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Run Evaluation
                  </>
                )}
              </Button>
            </div>
            {evaluateMutation.isPending && (
              <p className="text-sm text-blue-600 bg-blue-50 px-3 py-2 rounded-lg">
                Analyzing your training data with AI... This may take 30-60 seconds.
              </p>
            )}
            {evaluateMutation.isError && (
              <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">
                Error running evaluation. Please try again.
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Pending Modifications Alert */}
      {pendingMods.length > 0 && (
        <Card className="bg-amber-50 border-amber-200">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="text-2xl">⚠️</div>
                <div>
                  <h3 className="font-medium text-amber-800">
                    {pendingMods.length} modification
                    {pendingMods.length > 1 ? 's' : ''} pending approval
                  </h3>
                  <p className="text-sm text-amber-700">
                    Review the AI suggestions below and approve or reject each one.
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={() => handleActionAll('approve')}
                  disabled={actionAllMutation.isPending}
                >
                  <Check className="w-4 h-4" />
                  Approve All
                </Button>
                <Button
                  size="sm"
                  variant="outlined"
                  onClick={() => handleActionAll('reject')}
                  disabled={actionAllMutation.isPending}
                >
                  <X className="w-4 h-4" />
                  Reject All
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Latest Review */}
      {hasReview ? (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Latest Evaluation</CardTitle>
              <p className="text-sm text-gray-500 mt-1">
                {new Date(review.date).toLocaleDateString('en-US', {
                  weekday: 'long',
                  month: 'long',
                  day: 'numeric',
                })}
              </p>
            </div>
            <Badge
              variant={
                pendingMods.length > 0
                  ? 'warning'
                  : review.approval_status === 'approved'
                  ? 'success'
                  : 'default'
              }
            >
              {pendingMods.length > 0
                ? `${pendingMods.length} Pending`
                : review.approval_status || 'No changes'}
            </Badge>
          </CardHeader>
          <CardContent>
            {/* Insights */}
            {review.insights && (
              <div className="mb-4">
                <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
                  <MessageSquare className="w-4 h-4" />
                  AI Insights
                </h4>
                <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg">
                  {review.insights}
                </p>
              </div>
            )}

            {/* Recommendations */}
            {review.recommendations && (
              <div className="mb-4">
                <h4 className="text-sm font-medium text-gray-700 mb-2">
                  Recommendations
                </h4>
                <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg">
                  {review.recommendations}
                </p>
              </div>
            )}

            {/* Modifications */}
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-3">
                Proposed Modifications ({modifications.length})
              </h4>
              {modifications.length === 0 ? (
                <div className="text-center py-6 bg-gray-50 rounded-lg">
                  <Check className="w-8 h-8 text-green-500 mx-auto mb-2" />
                  <p className="text-sm text-gray-600">
                    No modifications needed - you're on track!
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {modifications.map((mod, index) => (
                    <ModificationCard
                      key={index}
                      modification={mod}
                      index={index}
                      reviewId={review.id}
                      onAction={handleActionMod}
                      isActioning={actionModMutation.isPending}
                    />
                  ))}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="text-center py-12">
            <Bot className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No Evaluations Yet
            </h3>
            <p className="text-sm text-gray-500 mb-4">
              Run an AI evaluation to get personalized training recommendations.
            </p>
          </CardContent>
        </Card>
      )}

      {/* History Section */}
      {actionedMods.length > 0 && (
        <Card>
          <CardHeader>
            <button
              onClick={() =>
                setExpandedReview(expandedReview === 1 ? null : 1)
              }
              className="w-full flex items-center justify-between"
            >
              <CardTitle className="flex items-center gap-2">
                <Clock className="w-5 h-5 text-gray-400" />
                Modification History
              </CardTitle>
              {expandedReview === 1 ? (
                <ChevronUp className="w-5 h-5 text-gray-400" />
              ) : (
                <ChevronDown className="w-5 h-5 text-gray-400" />
              )}
            </button>
          </CardHeader>
          {expandedReview === 1 && (
            <CardContent>
              <div className="space-y-3">
                {actionedMods.map((mod, index) => (
                  <div
                    key={index}
                    className={`p-3 rounded-lg border ${
                      mod.status === 'approved'
                        ? 'bg-green-50 border-green-200'
                        : 'bg-red-50 border-red-200'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-sm">
                        {mod.type.replace('_', ' ').toUpperCase()}
                      </span>
                      <Badge
                        variant={mod.status === 'approved' ? 'success' : 'error'}
                        size="sm"
                      >
                        {mod.status}
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-600">{mod.description}</p>
                    {mod.actioned_at && (
                      <p className="text-xs text-gray-400 mt-2">
                        {new Date(mod.actioned_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          )}
        </Card>
      )}
    </div>
  );
}

export default function PlanAdjustmentsPageRoute() {
  return <PlanAdjustmentsPage />;
}

function ModificationCard({
  modification,
  index,
  reviewId,
  onAction,
  isActioning,
}: {
  modification: Modification;
  index: number;
  reviewId: number;
  onAction: (reviewId: number, index: number, action: 'approve' | 'reject') => void;
  isActioning: boolean;
}) {
  const isPending = modification.status === 'pending';
  const priorityStyle = PRIORITY_COLORS[modification.priority] || PRIORITY_COLORS.medium;

  return (
    <div
      className={`p-4 rounded-lg border ${
        isPending
          ? 'bg-white border-gray-200'
          : modification.status === 'approved'
          ? 'bg-green-50/50 border-green-200'
          : 'bg-red-50/50 border-red-200'
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="font-medium text-gray-900">
              {modification.type.replace('_', ' ').toUpperCase()}
            </span>
            <Badge
              size="sm"
              style={{ backgroundColor: priorityStyle.bg, color: priorityStyle.text }}
            >
              {modification.priority.toUpperCase()}
            </Badge>
            <span className="text-xs text-gray-500">Week {modification.week}</span>
            {!isPending && (
              <Badge
                size="sm"
                variant={modification.status === 'approved' ? 'success' : 'error'}
              >
                {modification.status}
              </Badge>
            )}
          </div>
          <p className="text-sm text-gray-700 mb-2">{modification.description}</p>
          {modification.reason && (
            <p className="text-sm text-gray-500 italic">{modification.reason}</p>
          )}
        </div>
        {isPending && (
          <div className="flex gap-2">
            <button
              onClick={() => onAction(reviewId, index, 'approve')}
              disabled={isActioning}
              className="w-8 h-8 rounded-full bg-green-100 text-green-700 hover:bg-green-200 flex items-center justify-center transition-colors disabled:opacity-50"
              title="Approve"
            >
              <Check className="w-4 h-4" />
            </button>
            <button
              onClick={() => onAction(reviewId, index, 'reject')}
              disabled={isActioning}
              className="w-8 h-8 rounded-full bg-red-100 text-red-700 hover:bg-red-200 flex items-center justify-center transition-colors disabled:opacity-50"
              title="Reject"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
