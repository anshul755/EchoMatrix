import { useState, useEffect } from 'react';
import { fetchEvents, fetchTimeSeries } from '../services/api';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  ReferenceLine,
} from 'recharts';
import { BarChart3, Sparkles, Calendar, Filter, Activity } from 'lucide-react';
import PageHeader from '../components/ui/PageHeader';
import { Card, CardHeader } from '../components/ui/Card';
import { EmptyState, ErrorState, LoadingState } from '../components/ui/StatePanel';

const TREND_COLORS = ['#5ad1c6', '#e8a15b', '#77b8ff', '#74d58c', '#f07d7d'];

export default function TimeSeriesPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [granularity, setGranularity] = useState('day');
  const [query, setQuery] = useState('');
  const [groupBy, setGroupBy] = useState('');
  const [events, setEvents] = useState([]);
  const [selectedEventId, setSelectedEventId] = useState('');

  useEffect(() => {
    fetchEvents()
      .then((result) => setEvents(result?.events || []))
      .catch(() => setEvents([]));
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchTimeSeries(query, granularity, groupBy, selectedEventId)
      .then(setData)
      .catch(() => {
        setData(null);
        setError('Time-series service unavailable. Please ensure the backend is running.');
      })
      .finally(() => setLoading(false));
  }, [query, granularity, groupBy, selectedEventId]);

  const series = data?.grouped?.length ? mergeGroupedSeries(data.grouped) : data?.data ?? [];
  const totalPosts = data?.total_posts ?? 0;
  const peakBucket = series.length
    ? series.reduce((best, bucket) => ((bucket.count || 0) > (best.count || 0) ? bucket : best), series[0])
    : null;
  const nonZeroBuckets = series.filter((bucket) => (bucket.count || 0) > 0).length;
  const sparse = series.length > 0 && nonZeroBuckets / series.length < 0.35;
  const eventOverlay = buildEventOverlay(data, events, selectedEventId);

  return (
    <div>
      <PageHeader
        eyebrow="Narrative Momentum"
        title="Time-Series Trends"
        description="Follow volume over time, switch resolution, and use the summary panel to understand what the chart is actually saying."
      />

      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 12, marginBottom: 18, flexWrap: 'wrap' }}>
          <div className="topbar-search" style={{ maxWidth: 420 }}>
            <BarChart3 size={16} />
            <input
              type="text"
              placeholder="Filter by topic, claim, or keyword..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <div className="topbar-search" style={{ maxWidth: 220 }}>
            <Filter size={16} />
            <select
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value)}
              className="trend-select"
            >
              <option value="">All posts</option>
              <option value="platform">By platform</option>
              <option value="author">By author</option>
              <option value="hashtag">By hashtag</option>
              <option value="topic">By topic</option>
            </select>
          </div>
          <div className="topbar-search" style={{ maxWidth: 280 }}>
            <Sparkles size={16} />
            <select
              value={selectedEventId}
              onChange={(e) => setSelectedEventId(e.target.value)}
              className="trend-select"
            >
              <option value="">No event overlay</option>
              {events.map((event) => (
                <option key={event.id} value={event.id}>
                  {event.title}
                </option>
              ))}
            </select>
          </div>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {['day', 'week', 'hour'].map((g) => (
              <button
                key={g}
                className={`btn ${granularity === g ? 'btn-primary' : 'btn-ghost'}`}
                onClick={() => setGranularity(g)}
                style={{ padding: '8px 16px', fontSize: 13 }}
                type="button"
              >
                <Calendar size={14} />
                {g.charAt(0).toUpperCase() + g.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div className="trend-stat-grid">
          <TrendStat label="Posts in view" value={formatCompact(totalPosts)} />
          <TrendStat label="Peak bucket" value={peakBucket ? peakBucket.date : '—'} />
          <TrendStat label="Signal shape" value={data?.trend_shape || (sparse ? 'Sparse' : 'Sustained')} />
        </div>
      </div>

      {loading ? (
        <LoadingState label="Loading time-series data..." />
      ) : error ? (
        <ErrorState icon={<Activity size={18} />} message={error} />
      ) : series.length > 0 ? (
        <div className="grid-2 trend-layout">
          <Card className="trend-chart-card">
            <CardHeader
              title="Post Volume Over Time"
              subtitle={
                groupBy
                  ? `Grouped by ${groupBy}${data?.query ? ` • filtered by "${data.query}"` : ''}`
                  : data?.query
                    ? `Filtered by "${data.query}"`
                    : 'All posts'
              }
              action={<Activity size={16} style={{ color: 'var(--accent)' }} />}
            />
            <ResponsiveContainer width="100%" height={360}>
              {data?.grouped?.length ? (
                <LineChart data={series}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(90,209,198,0.08)" />
                  <XAxis dataKey="date" stroke="var(--text-tertiary)" fontSize={12} tickLine={false} />
                  <YAxis stroke="var(--text-tertiary)" fontSize={12} tickLine={false} />
                  <Tooltip contentStyle={tooltipStyle()} />
                  {Object.keys(series[0] || {})
                    .filter((key) => key !== 'date' && key !== 'count')
                    .map((key, index) => (
                      <Line
                        key={key}
                        type="monotone"
                        dataKey={key}
                        stroke={TREND_COLORS[index % TREND_COLORS.length]}
                        strokeWidth={2}
                        dot={false}
                      />
                    ))}
                </LineChart>
              ) : (
                <AreaChart data={series}>
                  <defs>
                    <linearGradient id="trendAreaGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#5ad1c6" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="#5ad1c6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(90,209,198,0.08)" />
                  <XAxis dataKey="date" stroke="var(--text-tertiary)" fontSize={12} tickLine={false} />
                  <YAxis stroke="var(--text-tertiary)" fontSize={12} tickLine={false} />
                  <Tooltip contentStyle={tooltipStyle()} />
                  {eventOverlay ? (
                    <ReferenceLine
                      x={eventOverlay.date}
                      stroke="#e8a15b"
                      strokeDasharray="4 4"
                      label={{
                        value: eventOverlay.label,
                        position: 'top',
                        fill: '#e8a15b',
                        fontSize: 11,
                      }}
                    />
                  ) : null}
                  <Area
                    type="monotone"
                    dataKey="count"
                    stroke="#5ad1c6"
                    strokeWidth={2}
                    fill="url(#trendAreaGrad)"
                  />
                </AreaChart>
              )}
            </ResponsiveContainer>
          </Card>

          <Card>
            <CardHeader
              title="Narrative Readout"
              subtitle={data?.date_range || 'Observed range'}
            />

            {data?.summary ? (
              <div className="ai-summary" style={{ marginTop: 0 }}>
                <div className="ai-summary-label">
                  <Sparkles size={12} /> GenAI Summary
                </div>
                <div className="ai-summary-text">{data.summary}</div>
              </div>
            ) : (
              <EmptyState
                icon={<Sparkles size={32} />}
                title="No summary available"
                description="A plain-language summary will appear here when the backend returns one."
              />
            )}

            <div className="trend-fact-list">
              <NarrativeFact label="Date range" value={data?.date_range || '—'} />
              <NarrativeFact label="Trend shape" value={data?.trend_shape || '—'} />
              <NarrativeFact
                label="Peak activity"
                value={peakBucket ? `${peakBucket.count || 0} posts on ${peakBucket.date}` : '—'}
              />
              <NarrativeFact
                label="Event overlay"
                value={eventOverlay ? `${eventOverlay.label} at ${eventOverlay.date}` : 'No event selected'}
              />
              {data?.event_comparison ? (
                <NarrativeFact
                  label="Before / after"
                  value={`${data.event_comparison.before_total} -> ${data.event_comparison.after_total} (${formatDelta(data.event_comparison.delta, data.event_comparison.change_ratio)})`}
                />
              ) : null}
            </div>
          </Card>
        </div>
      ) : (
        <Card>
          <EmptyState
            icon={<BarChart3 size={48} />}
            title={data?.message ? 'No trend data available' : 'No time-series data'}
            description={
              data?.message ||
              'This view will populate once the dataset contains dated posts that match the current filters.'
            }
          />
        </Card>
      )}
    </div>
  );
}

function mergeGroupedSeries(grouped) {
  const map = new Map();
  grouped.slice(0, 5).forEach((series) => {
    series.buckets.forEach((bucket) => {
      const current = map.get(bucket.date) || { date: bucket.date };
      current[series.group] = bucket.count;
      current.count = (current.count || 0) + bucket.count;
      map.set(bucket.date, current);
    });
  });
  return Array.from(map.values());
}

function buildEventOverlay(data, events, selectedEventId) {
  if (selectedEventId) {
    const selected = (data?.events || events || []).find((event) => event.id === selectedEventId);
    if (selected) {
      return { date: selected.date, label: selected.title };
    }
  }
  if (data?.events?.length) return data.events[0];
  if (!data?.data?.length) return null;
  const peak = data.data.reduce((best, bucket) => (bucket.count > best.count ? bucket : best), data.data[0]);
  if (!peak || peak.count <= 0) return null;
  return { date: peak.date, label: 'Peak activity' };
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

function TrendStat({ label, value }) {
  return (
    <div className="trend-stat">
      <div className="trend-stat-label">{label}</div>
      <div className="trend-stat-value">{value}</div>
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

function formatDelta(delta, ratio) {
  const sign = delta > 0 ? '+' : '';
  if (ratio == null) return `${sign}${delta}`;
  return `${sign}${delta} (${(ratio * 100).toFixed(1)}%)`;
}
