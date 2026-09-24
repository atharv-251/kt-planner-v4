import React, { useState, useEffect } from 'react';
import { Network, Sparkles, ChevronRight, ChevronDown, Clock, Tag, ArrowRight } from 'lucide-react';
import ReactFlow, { Background, Controls, MiniMap } from 'reactflow';
import 'reactflow/dist/style.css';
import { api } from '../../api/client';

interface Page5Props {
  transition: any;
  onNext: () => void;
  onRefresh: () => void;
}

export const Page5_KnowledgeHierarchy: React.FC<Page5Props> = ({ transition, onNext, onRefresh }) => {
  const [hierarchy, setHierarchy] = useState<any[]>([]);
  const [flatNodes, setFlatNodes] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [viewMode, setViewMode] = useState<'tree' | 'graph'>('tree');
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const loadData = async () => {
    if (!transition) return;
    setLoading(true);
    try {
      const tree = await api.getHierarchy(transition.id, 'nested');
      const flat = await api.getHierarchy(transition.id, 'flat');
      setHierarchy(tree);
      setFlatNodes(flat);

      // Expand top levels by default
      const exp: Record<string, boolean> = {};
      tree.forEach((n) => {
        exp[n.id] = true;
        n.children?.forEach((c: any) => { exp[c.id] = true; });
      });
      setExpanded(exp);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [transition]);

  const handleGenerate = async () => {
    if (!transition) return;
    setGenerating(true);
    try {
      await api.generateHierarchy(transition.id);
      await loadData();
      onRefresh();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setGenerating(false);
    }
  };

  const toggleExpand = (id: string) => {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  // Convert hierarchy to React Flow nodes and edges
  const flowNodes: any[] = [];
  const flowEdges: any[] = [];

  const traverseGraph = (nodes: any[], depth = 0, yOffset = { val: 50 }, parentId: string | null = null) => {
    nodes.forEach((node) => {
      const currentY = yOffset.val;
      yOffset.val += 80;

      const typeColors: Record<string, string> = {
        application: '#1E3A8A',
        domain: '#4338CA',
        capability: '#0284C7',
        process: '#0D9488',
        topic: '#D97706',
        subtopic: '#475569',
      };

      flowNodes.push({
        id: node.id,
        data: {
          label: (
            <div className="text-[11px] font-semibold text-left">
              <span className="text-[9px] uppercase tracking-wider block opacity-75">{node.node_type}</span>
              <span className="truncate block max-w-[150px]">{node.name}</span>
            </div>
          )
        },
        position: { x: depth * 220 + 40, y: currentY },
        style: {
          background: typeColors[node.node_type] || '#334155',
          color: '#ffffff',
          borderRadius: 8,
          border: '1px solid rgba(255,255,255,0.2)',
          padding: '6px 10px',
          width: 170,
        },
      });

      if (parentId) {
        flowEdges.push({
          id: `e-${parentId}-${node.id}`,
          source: parentId,
          target: node.id,
          animated: node.node_type === 'subtopic',
          style: { stroke: '#94A3B8' },
        });
      }

      if (node.children && node.children.length > 0) {
        traverseGraph(node.children, depth + 1, yOffset, node.id);
      }
    });
  };

  if (viewMode === 'graph' && hierarchy.length > 0) {
    traverseGraph(hierarchy);
  }

  // Recursive Tree Node Renderer
  const renderTreeNode = (node: any, level = 0) => {
    const hasChildren = node.children && node.children.length > 0;
    const isExp = expanded[node.id];

    const badges: Record<string, string> = {
      application: 'bg-blue-100 text-blue-800 border-blue-200',
      domain: 'bg-indigo-100 text-indigo-800 border-indigo-200',
      capability: 'bg-sky-100 text-sky-800 border-sky-200',
      process: 'bg-teal-100 text-teal-800 border-teal-200',
      topic: 'bg-amber-100 text-amber-800 border-amber-200',
      subtopic: 'bg-slate-100 text-slate-800 border-slate-200',
    };

    return (
      <div key={node.id} className="text-xs">
        <div
          className={`flex items-center justify-between py-2 px-3 hover:bg-slate-50 border-b border-slate-100 ${
            node.node_type === 'subtopic' ? 'bg-slate-50/40' : ''
          }`}
          style={{ paddingLeft: `${Math.max(level * 24, 12)}px` }}
        >
          <div className="flex items-center space-x-2">
            {hasChildren ? (
              <button onClick={() => toggleExpand(node.id)} className="p-0.5 text-slate-400 hover:text-slate-600">
                {isExp ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
              </button>
            ) : (
              <div className="w-4" />
            )}
            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase border ${badges[node.node_type] || 'bg-slate-100'}`}>
              {node.node_type}
            </span>
            <span className="font-semibold text-slate-800">{node.name}</span>
          </div>

          <div className="flex items-center space-x-4 text-slate-500">
            {node.estimated_hours > 0 && (
              <div className="flex items-center space-x-1 font-medium text-slate-700 bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
                <Clock className="h-3 w-3 text-sky-600" />
                <span>{node.estimated_hours}h</span>
              </div>
            )}
            <div className="flex items-center space-x-1 capitalize text-[11px]">
              <Tag className="h-3 w-3 text-slate-400" />
              <span>{node.category}</span>
            </div>
            <span className="text-[11px] text-slate-400 uppercase tracking-wider font-semibold">
              {node.recommended_method}
            </span>
          </div>
        </div>

        {hasChildren && isExp && (
          <div>
            {node.children.map((c: any) => renderTreeNode(c, level + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-sky-100 rounded-lg text-sky-700">
              <Network className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Stage 5: 6-Tier Knowledge Hierarchy</h2>
              <p className="text-sm text-slate-500">Application → Domain → Capability → Process → Topic → Subtopic</p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <div className="flex bg-slate-100 p-1 rounded-lg text-xs font-semibold text-slate-600">
              <button
                onClick={() => setViewMode('tree')}
                className={`px-3 py-1 rounded-md transition ${viewMode === 'tree' ? 'bg-white text-slate-900 shadow-sm' : ''}`}
              >
                Tree View
              </button>
              <button
                onClick={() => setViewMode('graph')}
                className={`px-3 py-1 rounded-md transition ${viewMode === 'graph' ? 'bg-white text-slate-900 shadow-sm' : ''}`}
              >
                Graph View
              </button>
            </div>

            <button
              onClick={handleGenerate}
              disabled={generating}
              className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow"
            >
              <Sparkles className="h-3.5 w-3.5" />
              <span>{generating ? 'Agent Synthesizing...' : 'Generate Hierarchy'}</span>
            </button>

            <button
              onClick={onNext}
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow"
            >
              <span>Proceed to KT Levels</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {viewMode === 'tree' ? (
          <div className="border border-slate-200 rounded-xl overflow-hidden mt-4">
            <div className="bg-slate-100 px-4 py-2.5 font-bold text-slate-700 text-xs flex justify-between">
              <span>Hierarchy Node</span>
              <span>Metadata & Effort Hours</span>
            </div>
            {hierarchy.length > 0 ? (
              <div className="divide-y divide-slate-100">
                {hierarchy.map((n) => renderTreeNode(n, 0))}
              </div>
            ) : (
              <div className="text-center py-12 text-slate-400 text-xs">
                No hierarchy generated yet. Click "Generate Hierarchy" to decompose application scope.
              </div>
            )}
          </div>
        ) : (
          <div className="h-[550px] w-full border border-slate-200 rounded-xl overflow-hidden mt-4 bg-slate-50">
            {flowNodes.length > 0 ? (
              <ReactFlow nodes={flowNodes} edges={flowEdges} fitView>
                <Background />
                <Controls />
                <MiniMap />
              </ReactFlow>
            ) : (
              <div className="text-center py-24 text-slate-400 text-xs">
                Graph requires generated nodes. Click "Generate Hierarchy".
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

