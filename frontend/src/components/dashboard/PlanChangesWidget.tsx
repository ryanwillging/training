'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardContent, Badge, LoadingState } from '@/components/ui';
import { planApi } from '@/lib/api';
import { ChevronRight } from 'lucide-react';

export function PlanChangesWidget() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['latest-review'],
    queryFn: planApi.getLatestReview,
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Plan Changes</CardTitle>
        </CardHeader>
        <CardContent>
          <LoadingState message="Loading..." />
        </CardContent>
      </Card>
    );
  }

  const review = data;
  const hasReview = review && review.id;

  // Count pending modifications
  const pendingCount = hasReview
    ? (review.proposed_adjustments || []).filter(
        (adj) => adj.status === 'pending'
      ).length
    : 0;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Plan Changes</CardTitle>
        {pendingCount > 0 && (
          <Badge variant="warning">{pendingCount} pending</Badge>
        )}
      </CardHeader>
      <CardContent>
        {!hasReview ? (
          <div className="text-center py-4">
            <div className="text-3xl mb-2">✅</div>
            <p className="text-sm text-gray-500">No evaluations yet</p>
          </div>
        ) : pendingCount === 0 ? (
          <div className="text-center py-4">
            <div className="text-3xl mb-2">✅</div>
            <p className="text-sm text-gray-500">All changes reviewed</p>
            <p className="text-xs text-gray-400 mt-1">
              Last evaluation: {new Date(review.date).toLocaleDateString()}
            </p>
          </div>
        ) : (
          <div>
            <p className="text-sm text-amber-700 mb-3">
              {pendingCount} modification{pendingCount > 1 ? 's' : ''} awaiting your review
            </p>
            <Link
              href="/plan-adjustments"
              className="flex items-center justify-between p-3 rounded-lg bg-amber-50 hover:bg-amber-100 transition-colors"
            >
              <span className="text-sm font-medium text-amber-800">
                Review modifications
              </span>
              <ChevronRight className="w-5 h-5 text-amber-600" />
            </Link>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
