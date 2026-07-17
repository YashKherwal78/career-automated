import { useCallback, useEffect, useState } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  applyNodeChanges,
  applyEdgeChanges,
  Node,
  Edge,
  NodeChange,
  EdgeChange,
  Handle,
  Position,
  MarkerType,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

// Custom Node for the Pipeline stages
const PipelineNode = ({ data }: { data: any }) => {
  const isAvailable = data.available !== false

  return (
    <div className="bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl w-64 text-zinc-300 font-sans text-xs overflow-hidden group hover:border-zinc-500 transition-colors cursor-pointer">
      <div className={`px-3 py-2 border-b font-semibold flex justify-between items-center ${isAvailable ? 'bg-zinc-800 border-zinc-700' : 'bg-red-950/40 border-red-900/50 text-red-400'}`}>
        <span>{data.label}</span>
        {isAvailable && (
          <div className="flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
          </div>
        )}
      </div>
      
      <div className="p-3 space-y-2">
        {!isAvailable ? (
          <div className="text-red-400 py-3 text-center opacity-80 border border-dashed border-red-900 rounded bg-red-950/20 font-mono">
            Telemetry Unavailable
          </div>
        ) : (
          <>
            <div className="flex justify-between items-center">
              <span className="text-zinc-500">Input</span>
              <span className="font-mono font-medium">{data.input?.toLocaleString() || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-500">Output</span>
              <span className="font-mono font-medium text-emerald-400">{data.output?.toLocaleString() || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-zinc-500">Latency</span>
              <span className="font-mono">{data.latency ? `${data.latency}ms` : 'N/A'}</span>
            </div>
          </>
        )}
      </div>
      
      {/* Invisible overlay for click capturing */}
      <div className="absolute inset-0 z-10 flex items-center justify-center opacity-0 group-hover:opacity-100 bg-black/40 backdrop-blur-[1px] transition-opacity">
        <span className="bg-zinc-800 text-zinc-200 px-3 py-1 rounded font-medium border border-zinc-600 shadow-lg">Drilldown</span>
      </div>

      <Handle type="target" position={Position.Top} className="w-2 h-2 bg-zinc-500 border-none" />
      <Handle type="source" position={Position.Bottom} className="w-2 h-2 bg-zinc-500 border-none" />
    </div>
  )
}

const LeakageEdge = ({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data }: any) => {
  const conversion = data?.conversion;
  const lost = data?.lost;
  
  const midX = sourceX + (targetX - sourceX) * 0.5;
  const midY = sourceY + (targetY - sourceY) * 0.5;

  return (
    <>
      <path
        id={id}
        className="react-flow__edge-path stroke-2 stroke-zinc-600"
        d={`M ${sourceX},${sourceY} L ${sourceX},${midY} L ${targetX},${midY} L ${targetX},${targetY}`}
        markerEnd="url(#arrow)"
      />
      {conversion !== undefined && (
        <foreignObject
          width={120}
          height={40}
          x={midX - 60}
          y={midY - 20}
          className="bg-transparent"
        >
          <div className="flex flex-col items-center justify-center h-full bg-zinc-950 border border-zinc-800 rounded px-2 py-1 text-[10px] font-mono shadow-md">
            <span className={conversion < 50 ? 'text-red-400' : 'text-emerald-400'}>{conversion}% Conv</span>
            {lost > 0 && <span className="text-zinc-500">{lost.toLocaleString()} Lost</span>}
          </div>
        </foreignObject>
      )}
    </>
  );
};


const nodeTypes = {
  pipelineNode: PipelineNode,
}

const edgeTypes = {
  leakageEdge: LeakageEdge,
}

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");

export function PipelineNetworkMap() {
  const [nodes, setNodes] = useState<Node[]>([])
  const [edges, setEdges] = useState<Edge[]>([])
  
  useEffect(() => {
    fetch(`${API_BASE}/analytics/topology`)
      .then(res => res.json())
      .then(data => {
        if (!data || !data.core_nodes) return;
        
        const c = data.core_nodes;
        
        const createEdge = (source: string, target: string, outVal: number, inVal: number) => {
          let conversion, lost;
          if (outVal !== undefined && inVal !== undefined && outVal > 0) {
            conversion = Math.min(100, Math.round((inVal / outVal) * 100));
            lost = Math.max(0, outVal - inVal);
          }
          return {
            id: `e-${source}-${target}`,
            source,
            target,
            type: 'leakageEdge',
            data: { conversion, lost }
          };
        };

        const initialNodes: Node[] = [
          { id: 'universe', type: 'pipelineNode', position: { x: 500, y: 50 }, data: c.universe },
          
          // Discovery
          { id: 'homepage', type: 'pipelineNode', position: { x: 50, y: 250 }, data: c.homepage },
          { id: 'search', type: 'pipelineNode', position: { x: 350, y: 250 }, data: c.search },
          { id: 'sitemap', type: 'pipelineNode', position: { x: 650, y: 250 }, data: c.sitemap },
          { id: 'redirects', type: 'pipelineNode', position: { x: 950, y: 250 }, data: c.redirects },
          
          { id: 'merge', type: 'pipelineNode', position: { x: 500, y: 450 }, data: c.merge },
          { id: 'dedup', type: 'pipelineNode', position: { x: 500, y: 650 }, data: c.dedup },
          { id: 'ats', type: 'pipelineNode', position: { x: 500, y: 850 }, data: c.ats },
          
          // Unknown Branch
          { id: 'unknown', type: 'pipelineNode', position: { x: 1000, y: 850 }, data: c.unknown },
        ];
        
        let yBaseATS = 1100;
        let xStart = 50;
        const atsNodes: Node[] = [];
        const atsEdges: Edge[] = [];
        
        const atsList = Object.entries(data.ats_branches);
        atsList.forEach(([key, value], i) => {
            const v: any = value;
            const xPos = xStart + (i * 300);
            
            // ATS Head (Candidates)
            atsNodes.push({ id: `ats_head_${key}`, type: 'pipelineNode', position: { x: xPos, y: yBaseATS }, data: { label: `${v.label} Candidates`, ...v.candidates } });
            // ATS Verified
            atsNodes.push({ id: `ats_ver_${key}`, type: 'pipelineNode', position: { x: xPos, y: yBaseATS + 200 }, data: { label: `${v.label} Verified`, ...v.verified } });
            // ATS Jobs
            atsNodes.push({ id: `ats_job_${key}`, type: 'pipelineNode', position: { x: xPos, y: yBaseATS + 400 }, data: { label: `${v.label} Jobs`, ...v.jobs } });
            
            atsEdges.push(createEdge('ats', `ats_head_${key}`, c.ats.output, v.candidates.input));
            atsEdges.push(createEdge(`ats_head_${key}`, `ats_ver_${key}`, v.candidates.output, v.verified.input));
            atsEdges.push(createEdge(`ats_ver_${key}`, `ats_job_${key}`, v.verified.output, v.jobs.input));
        });
        
        // Job Pipeline
        const j = data.job_nodes;
        const jobY = yBaseATS + 650;
        
        const jobNodes: Node[] = [
            { id: 'crawler', type: 'pipelineNode', position: { x: 500, y: jobY }, data: j.crawler },
            { id: 'parser', type: 'pipelineNode', position: { x: 500, y: jobY + 200 }, data: j.parser },
            { id: 'normalizer', type: 'pipelineNode', position: { x: 500, y: jobY + 400 }, data: j.normalizer },
            { id: 'enrichment', type: 'pipelineNode', position: { x: 500, y: jobY + 600 }, data: j.enrichment },
            { id: 'ranking', type: 'pipelineNode', position: { x: 500, y: jobY + 800 }, data: j.ranking },
            { id: 'visible', type: 'pipelineNode', position: { x: 500, y: jobY + 1000 }, data: j.visible },
        ];
        
        setNodes([...initialNodes, ...atsNodes, ...jobNodes]);
        
        const initialEdges: Edge[] = [
            createEdge('universe', 'homepage', c.universe.output, c.homepage.input),
            createEdge('universe', 'search', c.universe.output, c.search.input),
            createEdge('universe', 'sitemap', c.universe.output, c.sitemap.input),
            createEdge('universe', 'redirects', c.universe.output, c.redirects.input),
            
            createEdge('homepage', 'merge', c.homepage.output, c.merge.input),
            createEdge('search', 'merge', c.search.output, c.merge.input),
            createEdge('sitemap', 'merge', c.sitemap.output, c.merge.input),
            createEdge('redirects', 'merge', c.redirects.output, c.merge.input),
            
            createEdge('merge', 'dedup', c.merge.output, c.dedup.input),
            createEdge('dedup', 'ats', c.dedup.output, c.ats.input),
            
            createEdge('ats', 'unknown', c.ats.output, c.unknown.input),
        ];
        
        const jobEdges: Edge[] = [
            createEdge('crawler', 'parser', j.crawler.output, j.parser.input),
            createEdge('parser', 'normalizer', j.parser.output, j.normalizer.input),
            createEdge('normalizer', 'enrichment', j.normalizer.output, j.enrichment.input),
            createEdge('enrichment', 'ranking', j.enrichment.output, j.ranking.input),
            createEdge('ranking', 'visible', j.ranking.output, j.visible.input),
        ];
        
        // Merge ATS jobs into crawler
        atsList.forEach(([key, value]) => {
            jobEdges.push(createEdge(`ats_job_${key}`, 'crawler', (value as any).jobs.output, j.crawler.input));
        });

        setEdges([...initialEdges, ...atsEdges, ...jobEdges]);
      })
  }, [])

  const onNodesChange = useCallback((changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds)), [])
  const onEdgesChange = useCallback((changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)), [])

  return (
    <div className="h-full w-full bg-zinc-950 rounded-xl overflow-hidden border border-zinc-800 font-sans">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        className="bg-zinc-950"
      >
        <Background color="#27272a" gap={24} size={2} />
        <Controls className="bg-zinc-900 fill-zinc-400 border-zinc-800" />
      </ReactFlow>
    </div>
  )
}
