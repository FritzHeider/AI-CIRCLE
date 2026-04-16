import React, { useState, useCallback, useEffect } from 'react';
import ReactFlow, {
  Node, Edge, Controls, MiniMap, Background,
  addEdge, useNodesState, useEdgesState,
  Connection, BackgroundVariant,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { api } from '../../lib/api';
import { useAgents } from '../../hooks/useAgents';
import type { Workflow, WorkflowNode as WFNode, WorkflowEdge as WFEdge } from '../../types';

// ── Custom node ────────────────────────────────────────────────────────────

const AgentNode: React.FC<{ data: { label: string; color: string; type: string } }> = ({ data }) => (
  <div
    className="px-3 py-2 rounded-xl border-2 border-white shadow-md text-xs font-medium text-white min-w-24 text-center"
    style={{ backgroundColor: data.color }}
  >
    <div className="text-base mb-0.5">
      {data.type === 'trigger' ? '⚡' : data.type === 'output' ? '📤' : '🤖'}
    </div>
    {data.label}
  </div>
);

const nodeTypes = { agentNode: AgentNode };

// ── WorkflowBuilder ────────────────────────────────────────────────────────

export const WorkflowBuilder: React.FC = () => {
  const { agents } = useAgents();
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [activeWorkflow, setActiveWorkflow] = useState<Workflow | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [workflowName, setWorkflowName] = useState('New Workflow');
  const [trigger, setTrigger] = useState<'manual' | 'scheduled' | 'event'>('manual');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.workflows.list().then(setWorkflows).catch(console.error);
  }, []);

  const onConnect = useCallback(
    (connection: Connection) => setEdges((eds) => addEdge(connection, eds)),
    [setEdges],
  );

  // Drag an agent from the palette onto the canvas
  const onDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      const agentId = event.dataTransfer.getData('agent_id');
      const agentName = event.dataTransfer.getData('agent_name');
      const agentColor = event.dataTransfer.getData('agent_color');
      if (!agentId) return;

      const bounds = (event.currentTarget as HTMLElement).getBoundingClientRect();
      const position = {
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
      };

      const newNode: Node = {
        id: `node-${Date.now()}`,
        type: 'agentNode',
        position,
        data: { label: agentName, color: agentColor, type: 'agent', agent_id: agentId },
      };
      setNodes((nds) => [...nds, newNode]);
    },
    [setNodes],
  );

  const onDragOver = (event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const wfNodes: WFNode[] = nodes.map((n) => ({
        id: n.id,
        type: (n.data.type ?? 'agent') as WFNode['type'],
        agent_id: n.data.agent_id,
        label: n.data.label,
        config: {},
        position: n.position,
      }));
      const wfEdges: WFEdge[] = edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: (e.label as string) ?? '',
      }));
      const data = {
        name: workflowName,
        nodes: wfNodes,
        edges: wfEdges,
        trigger,
        trigger_config: {},
      };
      if (activeWorkflow) {
        const updated = await api.workflows.update(activeWorkflow.id, data);
        setActiveWorkflow(updated);
      } else {
        const created = await api.workflows.create(data);
        setActiveWorkflow(created);
        setWorkflows((wfs) => [created, ...wfs]);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const loadWorkflow = (wf: Workflow) => {
    setActiveWorkflow(wf);
    setWorkflowName(wf.name);
    setTrigger(wf.trigger);
    const rfNodes: Node[] = wf.nodes.map((n) => {
      const agent = agents.find((a) => a.id === n.agent_id);
      return {
        id: n.id,
        type: 'agentNode',
        position: n.position as { x: number; y: number },
        data: {
          label: n.label || agent?.name || n.id,
          color: agent?.avatar_color ?? '#6366f1',
          type: n.type,
          agent_id: n.agent_id,
        },
      };
    });
    const rfEdges: Edge[] = wf.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label,
    }));
    setNodes(rfNodes);
    setEdges(rfEdges);
  };

  const handleNew = () => {
    setActiveWorkflow(null);
    setWorkflowName('New Workflow');
    setTrigger('manual');
    setNodes([]);
    setEdges([]);
  };

  return (
    <div className="flex h-full">
      {/* Left: workflow list + agent palette */}
      <div className="w-56 bg-white border-r border-gray-200 flex flex-col overflow-hidden">
        <div className="p-3 border-b border-gray-100">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Workflows</span>
            <button onClick={handleNew} className="text-xs text-indigo-600">+ New</button>
          </div>
          <ul className="space-y-1 max-h-40 overflow-y-auto">
            {workflows.map((wf) => (
              <li key={wf.id}>
                <button
                  onClick={() => loadWorkflow(wf)}
                  className={`w-full text-left px-2 py-1 rounded text-xs truncate ${
                    activeWorkflow?.id === wf.id ? 'bg-indigo-50 text-indigo-700' : 'text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  {wf.name}
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="p-3 flex-1 overflow-y-auto">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Drag Agents
          </span>
          <ul className="mt-2 space-y-1">
            {agents
              .filter((a) => a.adapter_type !== 'human')
              .map((agent) => (
                <li
                  key={agent.id}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData('agent_id', agent.id);
                    e.dataTransfer.setData('agent_name', agent.name);
                    e.dataTransfer.setData('agent_color', agent.avatar_color);
                  }}
                  className="flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-grab hover:bg-gray-50 select-none"
                >
                  <span
                    className="w-5 h-5 rounded-full flex items-center justify-center text-white text-xs flex-shrink-0"
                    style={{ backgroundColor: agent.avatar_color }}
                  >
                    {agent.name[0]}
                  </span>
                  <span className="text-xs text-gray-700 truncate">{agent.name}</span>
                </li>
              ))}
          </ul>
        </div>
      </div>

      {/* Right: canvas */}
      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
        <div className="flex items-center gap-3 px-4 py-2 bg-white border-b border-gray-200">
          <input
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value)}
            className="text-sm font-medium border border-gray-300 rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-indigo-400 w-48"
          />
          <select
            value={trigger}
            onChange={(e) => setTrigger(e.target.value as typeof trigger)}
            className="text-xs border border-gray-300 rounded-lg px-2 py-1 focus:outline-none"
          >
            <option value="manual">Manual trigger</option>
            <option value="scheduled">Scheduled</option>
            <option value="event">On event</option>
          </select>
          <button
            onClick={handleSave}
            disabled={saving}
            className="ml-auto text-xs bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white px-4 py-1.5 rounded-lg"
          >
            {saving ? 'Saving…' : 'Save Workflow'}
          </button>
        </div>

        {/* ReactFlow canvas */}
        <div className="flex-1" onDrop={onDrop} onDragOver={onDragOver}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            fitView
          >
            <Background variant={BackgroundVariant.Dots} gap={16} color="#e5e7eb" />
            <Controls />
            <MiniMap zoomable pannable />
          </ReactFlow>
        </div>
      </div>
    </div>
  );
};
