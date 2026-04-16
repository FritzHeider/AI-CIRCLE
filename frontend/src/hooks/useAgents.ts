// useAgents — fetches and caches the agent list
import { useState, useEffect } from 'react';
import { api } from '../lib/api';
import type { Agent } from '../types';

interface UseAgentsReturn {
  agents: Agent[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useAgents(): UseAgentsReturn {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    setIsLoading(true);
    api.agents
      .list()
      .then(setAgents)
      .catch((e) => setError(e.message))
      .finally(() => setIsLoading(false));
  }, [tick]);

  return {
    agents,
    isLoading,
    error,
    refetch: () => setTick((t) => t + 1),
  };
}
