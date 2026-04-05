import { useState, useEffect, useRef } from 'react';
import { fetchProjectorExport, fetchTopics } from '../services/api';
import { Download, ExternalLink, Layers, Sparkles, SlidersHorizontal, AlertTriangle } from 'lucide-react';
import PageHeader from '../components/ui/PageHeader';
import { ErrorState, LoadingState } from '../components/ui/StatePanel';

function percent(value) {
  return `${Math.round((value || 0) * 100)}%`;
}

function compactNumber(value) {
  return new Intl.NumberFormat().format(value || 0);
}

export default function TopicsPage() {
  const [data, setData] = useState(null);
  const [projector, setProjector] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [nClusters, setNClusters] = useState(8);
  const canvasRef = useRef(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchTopics(nClusters)
      .then(setData)
      .catch(() => {
        setData(null);
        setError('Topic clustering is unavailable right now. Please ensure the backend is running.');
      })
      .finally(() => setLoading(false));
  }, [nClusters]);

  useEffect(() => {
    fetchProjectorExport(nClusters)
      .then(setProjector)
      .catch(() => setProjector(null));
  }, [nClusters]);

  useEffect(() => {
    if (!data?.embeddings_2d?.length || !canvasRef.current) return;
    const ctx = canvasRef.current.getContext('2d');
    const w = canvasRef.current.width;
    const h = canvasRef.current.height;
    ctx.clearRect(0, 0, w, h);

    const colors = [
      '#7c5cfc', '#34d399', '#f87171', '#fbbf24', '#60a5fa',
      '#f472b6', '#a78bfa', '#fb923c', '#4ade80', '#e879f9',
      '#38bdf8', '#facc15', '#c084fc', '#22d3ee', '#ef4444',
    ];

    const pts = data.embeddings_2d;
    const xs = pts.map(p => p.x);
    const ys = pts.map(p => p.y);
    const xMin = Math.min(...xs), xMax = Math.max(...xs);
    const yMin = Math.min(...ys), yMax = Math.max(...ys);
    const pad = 40;

    pts.forEach((p) => {
      const x = pad + ((p.x - xMin) / (xMax - xMin || 1)) * (w - 2 * pad);
      const y = pad + ((p.y - yMin) / (yMax - yMin || 1)) * (h - 2 * pad);
      const color = colors[p.cluster % colors.length];
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fillStyle = color + '99';
      ctx.fill();
    });
  }, [data]);

  return (
    <div>
      <PageHeader
        eyebrow="Topic Mapping"
        title="Topic Clustering"
        description="Adjust the cluster count, inspect representative posts, and jump into the embedding view to understand how themes separate."
      />

      <div className="card" style={{ marginBottom: 20 }}>
        <div className="topic-control-row">
          <div className="topic-control-head">
            <SlidersHorizontal size={16} style={{ color: 'var(--accent)' }} />
            <label style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              Clusters: <strong style={{ color: 'var(--text-primary)' }}>{nClusters}</strong>
            </label>
          </div>
          <input
            type="range"
            min={1}
            max={30}
            value={nClusters}
            onChange={(e) => setNClusters(Number(e.target.value))}
            style={{ flex: 1, maxWidth: 320, accentColor: 'var(--accent)' }}
          />
        </div>

        <div className="topic-stat-grid">
          <div className="topic-stat">
            <div className="topic-stat-label">Requested</div>
            <div className="topic-stat-value">{compactNumber(nClusters)}</div>
          </div>
          <div className="topic-stat">
            <div className="topic-stat-label">Actual</div>
            <div className="topic-stat-value">{compactNumber(data?.actual_clusters ?? nClusters)}</div>
          </div>
          <div className="topic-stat">
            <div className="topic-stat-label">Posts Clustered</div>
            <div className="topic-stat-value">{compactNumber(data?.clustered_posts)}</div>
          </div>
        </div>
      </div>

      {data?.message ? (
        <div
          style={{
            marginBottom: 20,
            padding: '12px 14px',
            borderRadius: 'var(--radius-md)',
            background: 'rgba(124, 92, 252, 0.10)',
            border: '1px solid rgba(124, 92, 252, 0.24)',
            color: 'var(--text-secondary)',
            fontSize: 13,
          }}
        >
          {data.message}
        </div>
      ) : null}

      {data?.parameter_notes?.length ? (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-title" style={{ marginBottom: 10 }}>Clustering Notes</div>
          <div className="note-list">
            {data.parameter_notes.map((note, index) => (
              <div key={index} className="note-item">{note}</div>
            ))}
          </div>
        </div>
      ) : null}

      {loading ? (
        <LoadingState label={`Clustering ${nClusters} topics...`} />
      ) : error ? (
        <ErrorState icon={<AlertTriangle size={18} />} message={error} />
      ) : (
        <div className="grid-2">
          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">Embedding Visualization</div>
                <div className="card-subtitle">
                  {data?.clustering_method || 'Semantic clustering overview'}
                </div>
              </div>
            </div>
            {data?.embeddings_2d?.length ? (
              <>
                <canvas
                  ref={canvasRef}
                  width={600}
                  height={400}
                  style={{
                    width: '100%',
                    height: 400,
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(0,0,0,0.2)',
                  }}
                />
                {projector ? (
                  <div
                    style={{
                      marginTop: 16,
                      padding: '14px',
                      borderRadius: 'var(--radius-md)',
                      background: 'rgba(255,255,255,0.03)',
                      border: '1px solid var(--border)',
                    }}
                  >
                    <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>
                      {projector.recommendation?.option}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10 }}>
                      {projector.recommendation?.reason}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10 }}>
                      Exporting {compactNumber(projector.exported_points)} of {compactNumber(projector.total_posts)} posts.
                    </div>
                    {projector.message ? (
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10 }}>
                        {projector.message}
                      </div>
                    ) : null}
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      <a
                        href={projector.files?.projector_url}
                        target="_blank"
                        rel="noreferrer"
                        className="btn btn-primary"
                      >
                        <ExternalLink size={14} />
                        Open Projector
                      </a>
                      <a href={projector.files?.vectors_tsv_url} className="btn btn-ghost">
                        <Download size={14} />
                        Vectors TSV
                      </a>
                      <a href={projector.files?.metadata_tsv_url} className="btn btn-ghost">
                        <Download size={14} />
                        Metadata TSV
                      </a>
                    </div>
                  </div>
                ) : null}
              </>
            ) : (
              <div className="empty-state">
                <Layers size={40} />
                <h3>No embedding data</h3>
                <p>Embedding visualization will appear once data is processed.</p>
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">Cluster Summary</div>
                <div className="card-subtitle">
                  {compactNumber(data?.actual_clusters ?? nClusters)} clusters
                </div>
              </div>
            </div>
            {data?.clusters?.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {data.clusters.map((c, i) => (
                  <div
                    key={i}
                    style={{
                      padding: '14px',
                      borderRadius: 'var(--radius-md)',
                      background: 'var(--accent-subtle)',
                      border: '1px solid var(--border)',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'flex-start',
                        gap: 12,
                      }}
                    >
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600, fontSize: 14 }}>
                          {c.label || `Cluster ${i + 1}`}
                        </div>
                        {c.keywords?.length ? (
                          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
                          {c.keywords.join(', ')}
                          </div>
                        ) : null}
                        {c.summary ? (
                          <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 8 }}>
                            {c.summary}
                          </div>
                        ) : null}
                      </div>
                      <span className="badge badge-accent">{c.count} posts</span>
                    </div>

                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
                        gap: 8,
                        marginTop: 12,
                      }}
                    >
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                        Share: <span style={{ color: 'var(--text-primary)' }}>{percent(c.metadata?.share_of_posts)}</span>
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                        Cohesion: <span style={{ color: 'var(--text-primary)' }}>{percent(c.metadata?.cohesion_score)}</span>
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                        Avg Length: <span style={{ color: 'var(--text-primary)' }}>{compactNumber(c.metadata?.average_post_length)}</span>
                      </div>
                    </div>

                    {c.metadata?.top_platforms?.length ? (
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 8 }}>
                        Top platforms: {c.metadata.top_platforms.join(', ')}
                      </div>
                    ) : null}

                    {c.representative_posts?.length ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12 }}>
                        {c.representative_posts.map((post, index) => (
                          <div
                            key={`${c.id}-${index}`}
                            className="topic-post-card"
                          >
                            <div style={{ fontSize: 13, lineHeight: 1.45 }}>{post.text}</div>
                            <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 6 }}>
                              {[post.author, post.platform, post.date].filter(Boolean).join(' • ')}
                              {post.score != null ? ` • centrality ${percent(post.score)}` : ''}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <Sparkles size={40} />
                <h3>No clusters</h3>
                <p>Cluster data will populate once the dataset is loaded.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
