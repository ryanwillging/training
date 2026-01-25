'use client';

import { useQuery } from '@tanstack/react-query';
import { syncApi } from '@/lib/api';
import { RefreshCw, Check, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

export function SyncStatusWidget() {
  const { data, isLoading } = useQuery({
    queryKey: ['sync-status'],
    queryFn: syncApi.getStatus,
    refetchInterval: 60000, // Refresh every minute
  });

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
  );
}
