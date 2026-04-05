import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { fetchNetwork } from '../services/api';
import ForceGraph2D from 'react-force-graph-2d';
import {
  Network,
  Search,
  AlertTriangle,
  Filter,
  Radar,
  ShieldAlert,
} from 'lucide-react';
import PageHeader from '../components/ui/PageHeader';
import { Card, CardHeader } from '../components/ui/Card';
import { EmptyState, ErrorState, LoadingState } from '../components/ui/StatePanel';

export default function NetworkPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState('');
  const [graphType, setGraphType] = useState('account');
  const [scoring, setScoring] = useState('pagerank');
  const [removeTopNode, setRemoveTopNode] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const graphRef = useRef();

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchNetwork(query, 1, graphType, scoring, removeTopNode)
      .then((result) => {
        setData(result);
        setSelectedNode(null);
      })
      .catch(() => {
        setData(null);
        setError('Network service unavailable. Please ensure the backend is running.');
      })
      .finally(() => setLoading(false));
  }, [query, graphType, scoring, removeTopNode]);

  const graphData = useMemo(() => {
    if (!data?.nodes?.length) return { nodes: [], links: [] };
    return {
      nodes: data.nodes.map((node) => ({
        ...node,
        name: node.label || node.id,
        val: Math.max(5, (node.centrality || 0.1) * 220),
        color: communityColor(node.community),
      })),
      links: data.edges.map((edge) => ({
        ...edge,
        source: edge.source,
        target: edge.target,
        value: edge.weight || 1,
      })),
    };
  }, [data]);

  const paintNode = useCallback((node, ctx, globalScale) => {
    const radius = Math.sqrt(node.val || 5);
    const selected = selectedNode?.id === node.id;

    ctx.beginPath();
    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
    ctx.fillStyle = node.color || '#5ad1c6';
    ctx.fill();

    if (selected) {
      ctx.lineWidth = 2;
      ctx.strokeStyle = '#edf3f4';
      ctx.stroke();
    }

    if (globalScale > 1.3) {
      ctx.font = `${Math.max(3, 10 / globalScale)}px Manrope, sans-serif`;
      ctx.fillStyle = '#edf3f4';
      ctx.textAlign = 'center';
      ctx.fillText(node.name, node.x, node.y + radius + 4);
    }
  }, [selectedNode]);

  return (
    <div>
      <PageHeader
        eyebrow="Relationship Mapping"
        title="Network Analysis"
        description="Use an interactive force graph to inspect influence, bridge nodes, communities, and the impact of removing a high-influence node."
      />

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="network-filter-grid">
          <div className="topbar-search">
            <Search size={16} />
            <input
              type="text"
              placeholder="Filter by query, hashtag, URL, or keyword..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>

          <div className="topbar-search">
            <Filter size={16} />
            <select value={graphType} onChange={(e) => setGraphType(e.target.value)} className="trend-select">
              <option value="account">Accounts</option>
              <option value="hashtag">Hashtags</option>
              <option value="url">URLs</option>
              <option value="post">Posts</option>
              <option value="topic">Topics</option>
            </select>
          </div>

          <div className="topbar-search">
            <Radar size={16} />
            <select value={scoring} onChange={(e) => setScoring(e.target.value)} className="trend-select">
              <option value="pagerank">PageRank</option>
              <option value="betweenness">Betweenness</option>
            </select>
          </div>

          <label className="network-toggle">
            <input
              type="checkbox"
              checked={removeTopNode}
              onChange={(e) => setRemoveTopNode(e.target.checked)}
            />
            <span>Remove top node and re-evaluate</span>
          </label>
        </div>

        <div className="network-stat-grid">
          <NetworkStat label="Nodes" value={formatCompact(data?.total_nodes)} />
          <NetworkStat label="Edges" value={formatCompact(data?.total_edges)} />
          <NetworkStat label="Communities" value={formatCompact(data?.communities)} />
          <NetworkStat
            label="Graph condition"
            value={data?.meta?.disconnected_graph ? 'Disconnected' : 'Connected'}
          />
        </div>
      </div>

      {loading ? (
        <LoadingState label="Building network graph..." />
      ) : error ? (
        <ErrorState icon={<AlertTriangle size={18} />} message={error} />
      ) : graphData.nodes.length > 0 ? (
        <div className="grid-2 network-layout">
          <Card className="network-graph-card" style={{ padding: 0, overflow: 'hidden' }}>
            <div className="network-note-bar">
              <span>Recommended graph renderer: `react-force-graph-2d` for a React + FastAPI stack because it stays interactive, readable, and demo-friendly without extra infrastructure.</span>
            </div>
            <ForceGraph2D
              ref={graphRef}
              graphData={graphData}
              width={920}
              height={600}
              backgroundColor="transparent"
              nodeCanvasObject={paintNode}
              linkColor={() => 'rgba(90,209,198,0.16)'}
              linkWidth={(link) => Math.sqrt(link.value || 1)}
              cooldownTicks={120}
              onNodeClick={(node) => {
                setSelectedNode(node);
                if (graphRef.current) {
                  graphRef.current.centerAt(node.x, node.y, 500);
                  graphRef.current.zoom(2.6, 500);
                }
              }}
            />
          </Card>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <Card>
              <CardHeader title="Graph Readout" subtitle={data?.meta?.method || 'Graph analysis'} />
              <div className="trend-fact-list" style={{ marginTop: 0 }}>
                <NarrativeFact label="Primary score" value={data?.meta?.scoring || '—'} />
                <NarrativeFact label="Graph type" value={data?.meta?.graph_type || '—'} />
                <NarrativeFact
                  label="Components"
                  value={formatCompact(data?.meta?.total_components)}
                />
                <NarrativeFact
                  label="Largest component"
                  value={formatCompact(data?.meta?.largest_component_size)}
                />
              </div>

              {data?.meta?.relationship_strategy?.length ? (
                <div className="ai-summary" style={{ marginTop: 16 }}>
                  <div className="ai-summary-label">
                    <Radar size={12} /> Relationship Strategy
                  </div>
                  <div className="note-list">
                    {data.meta.relationship_strategy.map((item, index) => (
                      <div key={index} className="note-item">{item}</div>
                    ))}
                  </div>
                </div>
              ) : null}

              {data?.meta?.message ? (
                <div className="ai-summary" style={{ marginTop: 16 }}>
                  <div className="ai-summary-label">
                    <ShieldAlert size={12} /> Stability Note
                  </div>
                  <div className="ai-summary-text">{data.meta.message}</div>
                </div>
              ) : null}

              {data?.meta?.missing_relationships?.length ? (
                <div className="ai-summary" style={{ marginTop: 16 }}>
                  <div className="ai-summary-label">
                    <AlertTriangle size={12} /> Missing Relationship Types
                  </div>
                  <div className="note-list">
                    {data.meta.missing_relationships.map((item, index) => (
                      <div key={index} className="note-item">{item}</div>
                    ))}
                  </div>
                </div>
              ) : null}
            </Card>

            <Card>
              <CardHeader
                title={selectedNode ? 'Node Detail' : 'Select a Node'}
                subtitle={selectedNode ? 'Influence and community context' : 'Click a node in the graph to inspect it'}
              />
              {selectedNode ? (
                <div className="network-detail-list">
                  <NarrativeFact label="Label" value={selectedNode.label || selectedNode.id} />
                  <NarrativeFact label="Type" value={selectedNode.type} />
                  <NarrativeFact label="Community" value={String(selectedNode.community)} />
                  <NarrativeFact label="Component" value={String(selectedNode.component)} />
                  <NarrativeFact label="Degree" value={String(selectedNode.degree)} />
                  <NarrativeFact label="Primary score" value={(selectedNode.centrality || 0).toFixed(4)} />
                  <NarrativeFact label="PageRank" value={(selectedNode.pagerank || 0).toFixed(4)} />
                  <NarrativeFact label="Betweenness" value={(selectedNode.betweenness || 0).toFixed(4)} />
                </div>
              ) : (
                <EmptyState
                  icon={<Network size={34} />}
                  title="No node selected"
                  description="Select a node to inspect its centrality, community, and role in the graph."
                />
              )}
            </Card>

            {data?.resilience ? (
              <Card>
                <CardHeader title="Resilience Check" subtitle="Impact of removing the highest-influence node" />
                <div className="network-detail-list">
                  <NarrativeFact label="Removed node" value={data.resilience.removed_node || '—'} />
                  <NarrativeFact
                    label="Largest component"
                    value={`${data.resilience.original_largest_component} -> ${data.resilience.updated_largest_component}`}
                  />
                  <NarrativeFact
                    label="Component count"
                    value={`${data.resilience.original_components} -> ${data.resilience.updated_components}`}
                  />
                  <NarrativeFact
                    label="Material change"
                    value={data.resilience.changed ? 'Yes' : 'No'}
                  />
                </div>
              </Card>
            ) : null}
          </div>
        </div>
      ) : (
        <Card>
          <EmptyState
            icon={<Network size={48} />}
            title={data?.meta?.message ? 'No usable network' : 'No network data'}
            description="The graph will populate once the dataset and current filters produce a usable network."
          />
          {data?.meta?.message ? (
            <div className="ai-summary" style={{ marginTop: 16 }}>
              <div className="ai-summary-label">
                <AlertTriangle size={12} /> Backend Note
              </div>
              <div className="ai-summary-text">{data.meta.message}</div>
            </div>
          ) : null}
        </Card>
      )}
    </div>
  );
}

function NetworkStat({ label, value }) {
  return (
    <div className="topic-stat">
      <div className="topic-stat-label">{label}</div>
      <div className="topic-stat-value">{value}</div>
    </div>
  );
}

function NarrativeFact({ label, value }) {
  return (
    <div className="trend-fact">
      <div className="trend-fact-label">{label}</div>
      <div className="trend-fact-value">{value}</div>
    </div>
  );
}

function formatCompact(value) {
  return new Intl.NumberFormat().format(value || 0);
}

function communityColor(community) {
  const palette = [
    '#5ad1c6', '#e8a15b', '#77b8ff', '#74d58c', '#f07d7d',
    '#b7efe9', '#f5c58e', '#9ac7ff', '#9be2aa', '#f5aaaa',
  ];
  return palette[(community || 0) % palette.length];
}
