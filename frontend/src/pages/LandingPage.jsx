import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Search,
  BarChart3,
  Layers3,
  Network,
  Database,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import Aurora from '../components/visuals/Aurora';
import BorderGlow from '../components/visuals/BorderGlow';
import { fetchStats } from '../services/api';

const pillars = [
  {
    icon: <Search size={18} />,
    title: 'Semantic Search',
    text: 'Investigate narratives by meaning instead of relying on exact keyword overlap.',
    to: '/search',
  },
  {
    icon: <BarChart3 size={18} />,
    title: 'Time-Series Trends',
    text: 'See when discussion spikes, how activity changes, and what the trend means in plain language.',
    to: '/trends',
  },
  {
    icon: <Layers3 size={18} />,
    title: 'Topic Clustering',
    text: 'Group posts into themes, inspect representative examples, and export embeddings for interactive exploration.',
    to: '/topics',
  },
  {
    icon: <Network size={18} />,
    title: 'Network Analysis',
    text: 'Map shared actors, URLs, hashtags, and topic relationships with influence and community scoring.',
    to: '/network',
  },
  {
    icon: <Database size={18} />,
    title: 'Dataset-Aware',
    text: 'Built around the actual Reddit-style JSONL corpus, including malformed-row handling and robust fallbacks.',
    to: '/dashboard',
  },
  {
    icon: <ShieldCheck size={18} />,
    title: 'Stress-Tested',
    text: 'Handles empty queries, short input, sparse trends, disconnected graphs, and extreme cluster settings.',
    to: '/dashboard',
  },
];

const navLinks = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/search', label: 'Search' },
  { to: '/trends', label: 'Trends' },
  { to: '/topics', label: 'Topics' },
  { to: '/network', label: 'Network' },
];

export default function LandingPage() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetchStats().then(setStats).catch(() => setStats(null));
  }, []);

  return (
    <div className="landing-page">
      <section className="landing-hero">
        <div className="landing-aurora-layer" aria-hidden="true">
          <Aurora
            colorStops={['#7cff67', '#a9f4ae', '#25a10c']}
            blend={0.7}
            amplitude={1.0}
            speed={1.2}
          />
        </div>
        <div className="landing-topbar">
          <div className="landing-wordmark">
            <span className="landing-wordmark-text">EchoMatrix</span>
            <span className="landing-wordmark-subtitle">Investigative Narrative Dashboard</span>
          </div>
          <div className="landing-nav">
            {navLinks.map((item) => (
              <BorderGlow
                key={item.to}
                className="landing-nav-shell"
                edgeSensitivity={34}
                glowColor="118 52 76"
                backgroundColor="#163c1c"
                borderRadius={16}
                glowRadius={20}
                glowIntensity={0.85}
                coneSpread={22}
                animated={false}
                colors={['#8fd46d', '#7cff67', '#46c08f']}
                fillOpacity={0.2}
              >
                <Link to={item.to} className="landing-nav-link">
                  {item.label}
                </Link>
              </BorderGlow>
            ))}
          </div>
        </div>

        <div className="landing-hero-content">
          <div className="landing-hero-copy">
            <div className="landing-badge">
              <Sparkles size={14} />
              Built for investigative storytelling
            </div>
            <h1>Trace how narratives move through communities, topics, and networks.</h1>
            <p>
              EchoMatrix turns the posts in `backend/data/data.jsonl` into a research-ready workspace for semantic search, trend analysis, topic discovery, and graph-based investigation.
            </p>
            <div className="landing-actions">
              <BorderGlow
                className="landing-cta-shell landing-cta-primary-shell"
                edgeSensitivity={30}
                glowColor="106 88 74"
                backgroundColor="#08120d"
                borderRadius={18}
                glowRadius={26}
                glowIntensity={1}
                coneSpread={23}
                animated={false}
                colors={['#7cff67', '#bdf58f', '#2ec866']}
                fillOpacity={0.42}
              >
                <Link to="/dashboard" className="landing-border-link landing-border-link-primary">
                  <span>Enter Dashboard</span>
                  <ArrowRight size={14} />
                </Link>
              </BorderGlow>
              <BorderGlow
                className="landing-cta-shell landing-cta-secondary-shell"
                edgeSensitivity={32}
                glowColor="160 44 82"
                backgroundColor="#07110d"
                borderRadius={18}
                glowRadius={24}
                glowIntensity={0.92}
                coneSpread={24}
                animated={false}
                colors={['#85f7d3', '#3ec9d7', '#8fd46d']}
                fillOpacity={0.28}
              >
                <Link to="/about" className="landing-border-link landing-border-link-secondary">
                  <span>Open About</span>
                </Link>
              </BorderGlow>
            </div>
          </div>

          <div className="landing-preview-card">
            <div className="landing-preview-header">
              <div>
                <div className="landing-preview-title">Live Corpus Snapshot</div>
                <div className="landing-preview-subtitle">Current project dataset</div>
              </div>
              <span className="landing-preview-chip">Research Mode</span>
            </div>

            <div className="landing-preview-grid">
              <div className="landing-preview-stat">
                <div className="landing-preview-label">Posts</div>
                <div className="landing-preview-value">{formatNumber(stats?.total_posts)}</div>
              </div>
              <div className="landing-preview-stat">
                <div className="landing-preview-label">Authors</div>
                <div className="landing-preview-value">{formatNumber(stats?.total_authors)}</div>
              </div>
              <div className="landing-preview-stat landing-preview-span">
                <div className="landing-preview-label">Date Range</div>
                <div className="landing-preview-value-small">
                  {stats?.date_range?.start && stats?.date_range?.end
                    ? `${stats.date_range.start} — ${stats.date_range.end}`
                    : 'Loading live range'}
                </div>
              </div>
            </div>

            <div className="landing-preview-list">
              {(stats?.platforms || []).slice(0, 4).map((platform) => (
                <div key={platform.name} className="landing-preview-row">
                  <span>{platform.name}</span>
                  <strong>{formatNumber(platform.count)}</strong>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="landing-about">
        <div className="landing-section-heading">
          <div className="landing-section-kicker">About EchoMatrix</div>
          <h2>An investigative dashboard shaped around the actual project, not generic admin widgets.</h2>
          <p>
            The platform is designed to make social narrative analysis legible: search by meaning, read time-series summaries, inspect topic clusters, and understand which actors or communities are structurally influential.
          </p>
        </div>

        <div className="landing-pillars-grid">
          {pillars.map((pillar) => (
            <Link key={pillar.title} to={pillar.to} className="landing-pillar-card">
              <div className="landing-pillar-icon">{pillar.icon}</div>
              <div className="landing-pillar-title">{pillar.title}</div>
              <div className="landing-pillar-text">{pillar.text}</div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}

function formatNumber(value) {
  return new Intl.NumberFormat().format(value || 0);
}
