import React, { useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts';
import { useCosts } from '../../hooks/useCosts';
import { useAgents } from '../../hooks/useAgents';

interface CostDashboardProps {
  sessionId: string;
}

const CHART_COLORS = ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

const BudgetMeter: React.FC<{ pct: number; total: number; budget: number }> = ({
  pct, total, budget,
}) => {
  const color = pct > 0.9 ? '#ef4444' : pct > 0.7 ? '#f59e0b' : '#10b981';
  return (
    <div className="mb-4">
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>Session Budget</span>
        <span>
          ${total.toFixed(4)} / ${budget.toFixed(2)} ({(pct * 100).toFixed(1)}%)
        </span>
      </div>
      <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${Math.min(pct * 100, 100)}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
};

export const CostDashboard: React.FC<CostDashboardProps> = ({ sessionId }) => {
  const { summary, isLoading } = useCosts(sessionId, 15_000);
  const { agents } = useAgents();

  if (isLoading && !summary) {
    return (
      <div className="p-4 text-gray-400 text-sm text-center">Loading cost data…</div>
    );
  }

  if (!summary) {
    return (
      <div className="p-4 text-gray-400 text-sm text-center">No cost data yet.</div>
    );
  }

  const agentMap = Object.fromEntries(agents.map((a) => [a.id, a.name]));

  const chartData = summary.agents.map((a, i) => ({
    name: agentMap[a.agent_id] ?? a.agent_id.slice(0, 8),
    cost: parseFloat(a.cost_usd.toFixed(5)),
    tokens_in: a.tokens_in,
    tokens_out: a.tokens_out,
    color: CHART_COLORS[i % CHART_COLORS.length],
  }));

  return (
    <div className="p-4">
      <h2 className="text-base font-semibold text-gray-800 mb-3">Cost Dashboard</h2>

      <BudgetMeter
        pct={summary.budget_pct}
        total={summary.total_usd}
        budget={summary.budget_usd}
      />

      {chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(value: number) => [`$${value.toFixed(5)}`, 'Cost']}
              labelStyle={{ fontSize: 12 }}
            />
            <Bar dataKey="cost" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, i) => (
                <Cell key={i} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <p className="text-xs text-gray-400 text-center py-8">
          No agent costs recorded yet.
        </p>
      )}

      {/* Per-agent table */}
      {chartData.length > 0 && (
        <table className="w-full text-xs mt-4">
          <thead>
            <tr className="text-gray-400 border-b">
              <th className="text-left pb-1">Agent</th>
              <th className="text-right pb-1">In</th>
              <th className="text-right pb-1">Out</th>
              <th className="text-right pb-1">Cost</th>
            </tr>
          </thead>
          <tbody>
            {summary.agents.map((a) => (
              <tr key={a.agent_id} className="border-b border-gray-50">
                <td className="py-1 text-gray-700">{agentMap[a.agent_id] ?? a.agent_id.slice(0, 8)}</td>
                <td className="py-1 text-right text-gray-500">{a.tokens_in.toLocaleString()}</td>
                <td className="py-1 text-right text-gray-500">{a.tokens_out.toLocaleString()}</td>
                <td className="py-1 text-right text-indigo-600">${a.cost_usd.toFixed(5)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};
