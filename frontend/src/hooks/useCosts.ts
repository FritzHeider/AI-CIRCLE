// useCosts — poll session cost summary
import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';
import type { SessionCostSummary } from '../types';

interface UseCostsReturn {
  summary: SessionCostSummary | null;
  isLoading: boolean;
  refetch: () => void;
}

export function useCosts(sessionId: string, pollMs = 10_000): UseCostsReturn {
  const [summary, setSummary] = useState<SessionCostSummary | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [tick, setTick] = useState(0);

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    if (!sessionId) return;
    setIsLoading(true);
    api.costs
      .summary(sessionId)
      .then(setSummary)
      .catch(console.error)
      .finally(() => setIsLoading(false));
  }, [sessionId, tick]);

  // Auto-poll
  useEffect(() => {
    if (!sessionId || pollMs <= 0) return;
    const id = setInterval(refetch, pollMs);
    return () => clearInterval(id);
  }, [sessionId, pollMs, refetch]);

  return { summary, isLoading, refetch };
}
