'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { syncApi } from '@/lib/api';
import { RefreshCw, Check, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

export function SyncStatusWidget() {
  const queryClient = useQueryClient();
  const [showSuccess, setShowSuccess] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['sync-status'],
    queryFn: syncApi.getStatus,
    refetchInterval: 60000, // Refresh every minute
  });

  const syncMutation = useMutation({
    mutationFn: syncApi.triggerSync,
    onSuccess: () => {
      setShowSuccess(true);
      // Keep showing success message longer since sync happens in background
      setTimeout(() => {
        setShowSuccess(false);
        // Refresh status after delay to show updated data
        queryClient.invalidateQueries({ queryKey: ['sync-status'] });
      }, 5000);
    },
  });

  const handleSync = () => {
    syncMutation.mutate();
  };

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <RefreshCw className="w-4 h-4 animate-spin" />
        <span>Checking sync status...</span>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const isRecent = data.hours_since_sync !== null && data.hours_since_sync < 24;
  const formatLastSync = () => {
    if (!data.last_sync) return 'Never synced';

    const syncDate = new Date(data.last_sync);
    const now = new Date();
    const diffMs = now.getTime() - syncDate.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

    if (diffHours < 1) {
      return 'Just now';
    }
    if (diffHours < 24) {
      return `${diffHours}h ago`;
    }
    return syncDate.toLocaleDateString();
  };

  return (
    <div className="flex items-center gap-3">
      <div
        className={cn(
          'flex items-center gap-2 text-sm px-3 py-1.5 rounded-full',
          isRecent
            ? 'bg-green-50 text-green-700'
            : 'bg-amber-50 text-amber-700'
        )}
      >
        {isRecent ? (
          <Check className="w-4 h-4" />
        ) : (
          <AlertCircle className="w-4 h-4" />
        )}
        <span>
          {isRecent ? 'Data synced' : 'Sync needed'}: {formatLastSync()}
        </span>
      </div>

      <button
        onClick={handleSync}
        disabled={syncMutation.isPending}
        className={cn(
          'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
          'bg-gray-900 text-white hover:bg-gray-800',
          'disabled:opacity-50 disabled:cursor-not-allowed'
        )}
        title="Manually trigger data sync from Garmin and Hevy"
      >
        <RefreshCw className={cn('w-4 h-4', syncMutation.isPending && 'animate-spin')} />
        {syncMutation.isPending ? 'Syncing...' : 'Sync Now'}
      </button>

      {showSuccess && (
        <div className="text-sm text-green-600 font-medium">
          Sync triggered! Data will update in 1-2 minutes.
        </div>
      )}

      {syncMutation.isError && (
        <div className="text-sm text-red-600">
          Sync failed. Please try again.
        </div>
      )}
    </div>
  );
}
