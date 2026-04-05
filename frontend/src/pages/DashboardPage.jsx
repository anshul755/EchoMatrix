import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchDashboardOverview } from '../services/api';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  PieChart,
  Pie,
} from 'recharts';
import {
  ArrowRight,
  Activity,
  Globe2,
  Network,
  Layers3,
  CalendarDays,
  Search,
  ShieldAlert,
  TrendingUp,
  Clock3,
  GitBranch,
  Users,
} from 'lucide-react';
import { Card, CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import { EmptyState, ErrorState, LoadingState } from '../components/ui/StatePanel';

const BAR_COLORS = ['#4fa08f', '#b7eb34', '#6aa8ff', '#f0ad61', '#7edfd2', '#8ecf6c'];
const DASHBOARD_CACHE_KEY = 'echomatrix-dashboard-cache-v1';

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [platformTimeline, setPlatformTimeline] = useState(null);
  const [topics, setTopics] = useState(null);
  const [network, setNetwork] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const cached = readDashboardCache();
    if (cached) {
      hydrateDashboardState(cached, {
        setStats,
        setTimeline,
        setPlatformTimeline,
        setTopics,
        setNetwork,
      });
      setLoading(false);
    }

    setLoading(true);
    setError(null);
    fetchDashboardOverview()
      .then((payload) => {
        const next = {
          stats: payload?.stats ?? cached?.stats ?? null,
          timeseries: payload?.timeseries ?? cached?.timeseries ?? null,
          platformTimeseries: payload?.platformTimeseries ?? cached?.platformTimeseries ?? null,
          topics: payload?.topics ?? cached?.topics ?? null,
          network: payload?.network ?? cached?.network ?? null,
        };

        hydrateDashboardState(next, {
          setStats,
          setTimeline,
          setPlatformTimeline,
          setTopics,
          setNetwork,
        });

        if (next.stats || next.timeseries || next.platformTimeseries || next.topics || next.network) {
          writeDashboardCache(next);
        }

        if (payload?.cache?.stale && !cached) {
          setError('Dashboard is using a stale cached backend snapshot while live refresh recovers.');
        } else {
          setError(null);
        }
      })
      .catch(() => {
        if (!cached) {
          setError('Dashboard overview is unavailable right now. Please ensure the backend is running.');
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const platformBreakdown = useMemo(() => {
    const platforms = stats?.platforms || [];
    const total = platforms.reduce((sum, item) => sum + (item.count || 0), 0) || 1;
    return platforms.slice(0, 4).map((item, index) => ({
      ...item,
      share: Math.round(((item.count || 0) / total) * 100),
      fill: BAR_COLORS[index % BAR_COLORS.length],
    }));
  }, [stats]);

  const recentSignals = useMemo(() => {
    return (topics?.clusters || []).slice(0, 5).map((cluster) => ({
      id: cluster.id,
      title: cluster.label,
      count: cluster.count,
      summary: cluster.summary,
      keywords: cluster.keywords?.slice(0, 2) || [],
    }));
  }, [topics]);

  const peakWeek = useMemo(() => {
    if (!timeline.length) return null;
    return timeline.reduce((best, bucket) => ((bucket.count || 0) > (best.count || 0) ? bucket : best), timeline[0]);
  }, [timeline]);

  const mergedPlatformSeries = useMemo(() => {
    if (!platformTimeline?.grouped?.length) return [];
    return mergeGroupedSeries(platformTimeline.grouped);
  }, [platformTimeline]);

  const authorLeaders = useMemo(() => {
    return (stats?.top_authors || []).slice(0, 6).map((author, index) => ({
      name: author.name,
      count: author.count || 0,
      fill: BAR_COLORS[index % BAR_COLORS.length],
    }));
  }, [stats]);

  const weeklyAverage = useMemo(() => {
    if (!timeline.length) return 0;
    const total = timeline.reduce((sum, bucket) => sum + (bucket.count || 0), 0);
    return Math.round(total / timeline.length);
  }, [timeline]);

  const latestDelta = useMemo(() => {
    if (timeline.length < 2) return null;
    const current = timeline[timeline.length - 1]?.count || 0;
    const previous = timeline[timeline.length - 2]?.count || 0;
    const delta = current - previous;
    const ratio = previous > 0 ? delta / previous : null;
    return { delta, ratio, current, previous };
  }, [timeline]);

  const activeWeeks = useMemo(() => timeline.filter((bucket) => (bucket.count || 0) > 0).length, [timeline]);

  const topCommunity = stats?.platforms?.[0];
  const topTopic = topics?.clusters?.[0];

  if (loading) {
    return <LoadingState label="Building investigative overview..." />;
  }

  if (error) {
    return <ErrorState message={error} icon={<ShieldAlert size={18} />} />;
  }

  if (!stats) {
    return (
      <EmptyState
        icon={<Activity size={42} />}
        title="No overview data"
        description="The dashboard overview will appear once the backend data endpoints are available."
      />
    );
  }

  return (
    <div className="overview-shell">
      <div className="overview-heading-row">
        <div>
          <div className="overview-kicker">EchoMatrix Workspace</div>
          <h1 className="overview-title">Narrative Dashboard</h1>
          <p className="overview-subtitle">
            Read the corpus at a glance, compare community activity, and jump into the tools that explain where a narrative is gaining shape.
          </p>
        </div>

        <div className="overview-toolbar">
          <div className="overview-toolbar-pill">
            <CalendarDays size={14} />
            {stats?.date_range?.start} - {stats?.date_range?.end}
          </div>
          <Link to="/search">
            <Button variant="primary" type="button">
              Open Search
              <ArrowRight size={14} />
            </Button>
          </Link>
        </div>
      </div>

      {error ? <div className="overview-banner">{error}</div> : null}

      <div className="overview-grid">
        <div className="overview-main-column">
          <div className="overview-kpi-row">
            <Card className="overview-update-card">
              <div className="overview-update-badge">
                <span className="overview-status-dot" />
                Live dataset
              </div>
              <div className="overview-update-date">{stats?.date_range?.end}</div>
              <div className="overview-update-copy">
                {peakWeek
                  ? `Narrative activity peaked at ${formatNumber(peakWeek.count)} posts in the week ending ${peakWeek.date}.`
                  : 'Dataset overview is active and ready for investigation.'}
              </div>
              <Link to="/trends" className="overview-inline-link">
                See trend analysis
              </Link>
            </Card>

            <MetricCard
              title="Indexed Posts"
              value={formatNumber(stats?.total_posts)}
              detail={`${formatNumber(stats?.total_authors)} distinct authors`}
              accent="positive"
            />
            <MetricCard
              title="Network Nodes"
              value={formatNumber(network?.total_nodes)}
              detail={`${formatNumber(network?.communities)} detected communities`}
              accent="neutral"
            />
          </div>

          <div className="overview-content-grid">
            <Card className="overview-transaction-card">
              <CardHeader
                title="Recent Narrative Signals"
                subtitle="Leading clusters worth investigating first"
              />
              {recentSignals.length ? (
                <div className="signal-list">
                  {recentSignals.map((signal) => (
                    <div key={signal.id} className="signal-row">
                      <div className="signal-icon-wrap">
                        <Layers3 size={16} />
                      </div>
                      <div className="signal-main">
                        <div className="signal-title">{signal.title}</div>
                        <div className="signal-meta">{signal.summary}</div>
                        <div className="signal-tags">
                          {signal.keywords.map((keyword) => (
                            <span key={keyword} className="signal-tag">{keyword}</span>
                          ))}
                        </div>
                      </div>
                      <div className="signal-count">{signal.count} posts</div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  icon={<Layers3 size={34} />}
                  title="No topic signals"
                  description="Topic clustering output will appear here once the backend is available."
                />
              )}
            </Card>

            <Card className="overview-chart-card">
              <CardHeader
                title="Weekly Activity"
                subtitle="Recent weekly volume across the corpus"
                action={<Badge variant="success">Trend view</Badge>}
              />
              {timeline.length ? (
                <>
                  <div className="overview-revenue-value">
                    {formatNumber(stats?.total_posts)}
                    <span className="overview-revenue-note">
                      <TrendingUp size={13} />
                      {peakWeek ? `${formatNumber(peakWeek.count)} at peak week` : 'Active corpus'}
                    </span>
                  </div>
                  <div style={{ width: '100%', height: 232 }}>
                    <ResponsiveContainer>
                      <BarChart data={timeline.slice(-10)} barGap={8}>
                        <XAxis dataKey="date" tick={{ fill: '#92a3aa', fontSize: 11 }} tickLine={false} axisLine={false} />
                        <YAxis tick={{ fill: '#92a3aa', fontSize: 11 }} tickLine={false} axisLine={false} width={34} />
                        <Tooltip contentStyle={tooltipStyle()} />
                        <Bar dataKey="count" radius={[8, 8, 0, 0]}>
                          {timeline.slice(-10).map((_, index) => (
                            <Cell key={index} fill={index % 2 === 0 ? '#4fa08f' : '#b7eb34'} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </>
              ) : (
                <EmptyState
                  icon={<CalendarDays size={34} />}
                  title="No trend data"
                  description="Weekly activity will appear once the time-series endpoint returns data."
                />
              )}
            </Card>
          </div>

          <div className="overview-bottom-grid">
            <Card>
              <CardHeader
                title="Community Spread"
                subtitle="Largest communities in the dataset"
                action={<Globe2 size={16} style={{ color: 'var(--accent)' }} />}
              />
              {stats?.platforms?.length ? (
                <div className="overview-report-wrap">
                  <div style={{ width: '100%', height: 210 }}>
                    <ResponsiveContainer>
                      <BarChart data={stats.platforms.slice(0, 6)} layout="vertical" margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                        <XAxis type="number" tick={{ fill: '#92a3aa', fontSize: 11 }} tickLine={false} axisLine={false} />
                        <YAxis type="category" dataKey="name" tick={{ fill: '#edf3f4', fontSize: 11 }} tickLine={false} axisLine={false} width={92} />
                        <Tooltip contentStyle={tooltipStyle()} />
                        <Bar dataKey="count" radius={[0, 8, 8, 0]}>
                          {stats.platforms.slice(0, 6).map((_, index) => (
                            <Cell key={index} fill={BAR_COLORS[index % BAR_COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              ) : (
                <EmptyState
                  icon={<Globe2 size={34} />}
                  title="No community breakdown"
                  description="Community distribution will appear once stats are available."
                />
              )}
            </Card>

            <Card>
              <CardHeader
                title="Topic Snapshot"
                subtitle="Largest active cluster right now"
                action={<Badge variant="warning">{topics?.actual_clusters || 0} clusters</Badge>}
              />
              {topTopic ? (
                <div className="overview-topic-panel">
                  <div className="overview-topic-title">{topTopic.label}</div>
                  <div className="overview-topic-copy">{topTopic.summary}</div>
                  <div className="overview-topic-meta">
                    <span>{topTopic.count} posts</span>
                    <span>{Math.round((topTopic.metadata?.share_of_posts || 0) * 100)}% of corpus</span>
                    <span>{topTopic.metadata?.top_platforms?.[0] || 'Mixed communities'}</span>
                  </div>
                  <Link to="/topics" className="overview-inline-link">
                    Open topic clustering
                  </Link>
                </div>
              ) : (
                <EmptyState
                  icon={<Layers3 size={34} />}
                  title="No topic snapshot"
                  description="The topic clustering panel will appear once the backend returns clusters."
                />
              )}
            </Card>
          </div>

        </div>

        <div className="overview-side-column">
          <Card className="overview-ring-card">
            <CardHeader title="Community Composition" subtitle="Top communities in the current dataset" />
            {platformBreakdown.length ? (
              <>
                <div style={{ width: '100%', height: 220 }}>
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie
                        data={platformBreakdown}
                        dataKey="count"
                        innerRadius={58}
                        outerRadius={90}
                        paddingAngle={3}
                        stroke="none"
                      >
                        {platformBreakdown.map((entry) => (
                          <Cell key={entry.name} fill={entry.fill} />
                        ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="overview-ring-center">
                  <div className="overview-ring-center-label">Total Posts</div>
                  <div className="overview-ring-center-value">{compactK(stats?.total_posts)}</div>
                </div>
                <div className="overview-ring-legend">
                  {platformBreakdown.map((item) => (
                    <div key={item.name} className="overview-ring-legend-item">
                      <span className="overview-dot" style={{ background: item.fill }} />
                      <span>{item.share}%</span>
                      <span className="overview-ring-name">{item.name.replace('r/', '')}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <EmptyState
                icon={<Globe2 size={34} />}
                title="No composition data"
                description="Top communities will appear here once stats load."
              />
            )}
          </Card>

          <Card>
            <CardHeader title="Network Health" subtitle="Structural readout of the account graph" />
            <div className="overview-side-facts">
              <SideFact label="Graph type" value={network?.meta?.graph_type || 'account'} />
              <SideFact label="Nodes / edges" value={`${formatNumber(network?.total_nodes)} / ${formatNumber(network?.total_edges)}`} />
              <SideFact label="Communities" value={formatNumber(network?.communities)} />
              <SideFact label="State" value={network?.meta?.disconnected_graph ? 'Disconnected' : 'Connected'} />
            </div>
            {network?.meta?.message ? (
              <div className="ai-summary" style={{ marginTop: 16 }}>
                <div className="ai-summary-label">
                  <Network size={12} /> Graph Note
                </div>
                <div className="ai-summary-text">{network.meta.message}</div>
              </div>
            ) : null}
            <Link to="/network" className="overview-side-button">
              Explore network map
            </Link>
          </Card>

          <Card>
            <CardHeader
              title="Investigation Brief"
              subtitle="Fast context before you open a deeper tool"
            />
            <div className="overview-brief-list">
              <div className="overview-brief-item">
                <div className="overview-brief-label">Peak week</div>
                <div className="overview-brief-value">
                  {peakWeek ? `${formatNumber(peakWeek.count)} posts on ${peakWeek.date}` : 'No peak detected yet'}
                </div>
              </div>
              <div className="overview-brief-item">
                <div className="overview-brief-label">Most active community</div>
                <div className="overview-brief-value">
                  {topCommunity ? `${topCommunity.name} with ${formatNumber(topCommunity.count)} posts` : 'No community summary yet'}
                </div>
              </div>
              <div className="overview-brief-item">
                <div className="overview-brief-label">Leading cluster</div>
                <div className="overview-brief-value">
                  {topTopic ? `${topTopic.label} across ${formatNumber(topTopic.count)} posts` : 'No topic cluster available'}
                </div>
              </div>
            </div>
            <div className="overview-brief-note">
              Start with search if you have a claim, use trends if timing matters, and move to network when the question is about spread or coordination.
            </div>
            <div className="overview-brief-actions">
              <MiniAction to="/search" icon={<Search size={14} />} label="Open search" />
              <MiniAction to="/topics" icon={<Layers3 size={14} />} label="Inspect topics" />
            </div>
          </Card>

        </div>
      </div>

      <div className="overview-insights-grid overview-insights-grid-full">
        <Card className="overview-insight-card">
          <CardHeader
            title="Top Authors"
            subtitle="Most active accounts in the current corpus"
            action={<Users size={16} style={{ color: 'var(--accent)' }} />}
          />
          {authorLeaders.length ? (
            <div style={{ width: '100%', height: 250 }}>
              <ResponsiveContainer>
                <BarChart data={authorLeaders} layout="vertical" margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
                  <XAxis type="number" tick={{ fill: '#92a3aa', fontSize: 11 }} tickLine={false} axisLine={false} />
                  <YAxis type="category" dataKey="name" tick={{ fill: '#edf3f4', fontSize: 11 }} tickLine={false} axisLine={false} width={118} />
                  <Tooltip contentStyle={tooltipStyle()} />
                  <Bar dataKey="count" radius={[0, 8, 8, 0]}>
                    {authorLeaders.map((entry) => (
                      <Cell key={entry.name} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState
              icon={<Users size={34} />}
              title="No author ranking"
              description="Top author activity will appear here once author stats are available."
            />
          )}
        </Card>

        <Card className="overview-insight-card">
          <CardHeader
            title="Platform Momentum"
            subtitle="How leading communities rise and cool over time"
            action={<GitBranch size={16} style={{ color: 'var(--accent)' }} />}
          />
          {mergedPlatformSeries.length ? (
            <div style={{ width: '100%', height: 250 }}>
              <ResponsiveContainer>
                <LineChart data={mergedPlatformSeries}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(90,209,198,0.08)" />
                  <XAxis dataKey="date" tick={{ fill: '#92a3aa', fontSize: 11 }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fill: '#92a3aa', fontSize: 11 }} tickLine={false} axisLine={false} width={34} />
                  <Tooltip contentStyle={tooltipStyle()} />
                  {Object.keys(mergedPlatformSeries[0] || {})
                    .filter((key) => key !== 'date' && key !== 'count')
                    .slice(0, 4)
                    .map((key, index) => (
                      <Line
                        key={key}
                        type="monotone"
                        dataKey={key}
                        stroke={BAR_COLORS[index % BAR_COLORS.length]}
                        strokeWidth={2}
                        dot={false}
                      />
                    ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState
              icon={<GitBranch size={34} />}
              title="No platform trend split"
              description="Grouped weekly community activity will appear here once the API returns grouped series."
            />
          )}
        </Card>

        <Card className="overview-insight-card">
          <CardHeader
            title="Dataset Rhythm"
            subtitle="Cadence, pace, and latest movement"
            action={<Clock3 size={16} style={{ color: 'var(--accent)' }} />}
          />
          {timeline.length ? (
            <>
              <div className="overview-rhythm-grid">
                <div className="overview-rhythm-stat">
                  <div className="overview-rhythm-label">Active Weeks</div>
                  <div className="overview-rhythm-value">{formatNumber(activeWeeks)}</div>
                </div>
                <div className="overview-rhythm-stat">
                  <div className="overview-rhythm-label">Average / Week</div>
                  <div className="overview-rhythm-value">{formatNumber(weeklyAverage)}</div>
                </div>
                <div className="overview-rhythm-stat overview-rhythm-span">
                  <div className="overview-rhythm-label">Latest Change</div>
                  <div className="overview-rhythm-value-small">
                    {latestDelta
                      ? `${latestDelta.delta >= 0 ? '+' : ''}${formatNumber(latestDelta.delta)} vs prior week${latestDelta.ratio != null ? ` (${(latestDelta.ratio * 100).toFixed(1)}%)` : ''}`
                      : 'Not enough weekly buckets yet'}
                  </div>
                </div>
              </div>
              <div style={{ width: '100%', height: 168, marginTop: 18 }}>
                <ResponsiveContainer>
                  <AreaChart data={timeline.slice(-12)}>
                    <defs>
                      <linearGradient id="overviewRhythmArea" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#5ad1c6" stopOpacity={0.35} />
                        <stop offset="100%" stopColor="#5ad1c6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(90,209,198,0.08)" />
                    <XAxis dataKey="date" tick={{ fill: '#92a3aa', fontSize: 11 }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fill: '#92a3aa', fontSize: 11 }} tickLine={false} axisLine={false} width={34} />
                    <Tooltip contentStyle={tooltipStyle()} />
                    <Area type="monotone" dataKey="count" stroke="#5ad1c6" strokeWidth={2} fill="url(#overviewRhythmArea)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </>
          ) : (
            <EmptyState
              icon={<Clock3 size={34} />}
              title="No rhythm view"
              description="Cadence stats will appear once timeline buckets are available."
            />
          )}
        </Card>

        <Card className="overview-cta-card overview-insight-card">
          <div className="overview-cta-pattern" />
          <div className="overview-cta-title">Turn signals into evidence.</div>
          <div className="overview-cta-copy">
            Use search to inspect claims, open trends to verify timing, and pivot into topics or network structure when you need context behind the spike.
          </div>
          <div className="overview-cta-row">
            <MiniAction to="/search" icon={<Search size={14} />} label="Search evidence" />
            <MiniAction to="/trends" icon={<CalendarDays size={14} />} label="Open trends" />
          </div>
        </Card>
      </div>
    </div>
  );
}

function MetricCard({ title, value, detail, accent = 'neutral' }) {
  return (
    <Card className="overview-metric-card">
      <div className="overview-metric-title">{title}</div>
      <div className="overview-metric-value">{value}</div>
      <div className={`overview-metric-detail overview-metric-detail-${accent}`}>{detail}</div>
    </Card>
  );
}

function SideFact({ label, value }) {
  return (
    <div className="overview-side-fact">
      <div className="overview-side-fact-label">{label}</div>
      <div className="overview-side-fact-value">{value}</div>
    </div>
  );
}

function MiniAction({ to, icon, label }) {
  return (
    <Link to={to} className="overview-mini-action">
      {icon}
      {label}
    </Link>
  );
}

function formatNumber(value) {
  return new Intl.NumberFormat().format(value || 0);
}

function compactK(value) {
  const number = value || 0;
  if (number >= 1000) {
    return `${Math.round(number / 1000)}K`;
  }
  return String(number);
}

function mergeGroupedSeries(grouped) {
  const map = new Map();
  grouped.slice(0, 4).forEach((series) => {
    series.buckets.forEach((bucket) => {
      const current = map.get(bucket.date) || { date: bucket.date };
      current[series.group] = bucket.count;
      current.count = (current.count || 0) + bucket.count;
      map.set(bucket.date, current);
    });
  });
  return Array.from(map.values());
}

function tooltipStyle() {
  return {
    backgroundColor: 'rgba(11, 20, 18, 0.96)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-primary)',
    fontSize: 13,
    boxShadow: '0 18px 44px rgba(0, 0, 0, 0.32)',
    padding: '10px 12px',
  };
}

function readDashboardCache() {
  try {
    const raw = window.localStorage.getItem(DASHBOARD_CACHE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function writeDashboardCache(payload) {
  try {
    window.localStorage.setItem(DASHBOARD_CACHE_KEY, JSON.stringify(payload));
  } catch {
  }
}

function hydrateDashboardState(payload, setters) {
  setters.setStats(payload?.stats ?? null);
  setters.setTimeline(payload?.timeseries?.data || []);
  setters.setPlatformTimeline(payload?.platformTimeseries ?? null);
  setters.setTopics(payload?.topics ?? null);
  setters.setNetwork(payload?.network ?? null);
}
