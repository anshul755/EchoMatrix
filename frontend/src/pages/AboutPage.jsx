import { Database, Radar, ShieldCheck, Search, GitBranch, Layers } from 'lucide-react';
import PageHeader from '../components/ui/PageHeader';
import { Card, CardHeader } from '../components/ui/Card';
import Badge from '../components/ui/Badge';

const pillars = [
  {
    icon: <Radar size={18} />,
    title: 'Investigative Workflow',
    text: 'Move from broad signal detection into search, trends, topic clustering, and network analysis without leaving the shell.',
  },
  {
    icon: <Database size={18} />,
    title: 'Structured Evidence',
    text: 'Each module is designed to turn raw post streams into legible evidence: counts, summaries, clusters, timelines, and representative records.',
  },
  {
    icon: <ShieldCheck size={18} />,
    title: 'Interview-Friendly Architecture',
    text: 'The frontend keeps layout, routing, API access, and reusable UI primitives cleanly separated so the product is easy to explain and extend.',
  },
  {
    icon: <Search size={18} />,
    title: 'Backend-Aligned Search',
    text: 'Search, trends, topics, and network views now read the real FastAPI response shapes rather than simplified mock contracts.',
  },
  {
    icon: <GitBranch size={18} />,
    title: 'Graph and Cluster Views',
    text: 'Topic clustering and network analysis surface model notes, resilience checks, and relationship evidence directly in the interface.',
  },
  {
    icon: <Layers size={18} />,
    title: 'Dataset-Aware UX',
    text: 'The UI is tuned for the Reddit-style JSONL dataset in backend/data/data.jsonl, including empty states, sparse results, and derived metadata.',
  },
];

export default function AboutPage() {
  return (
    <div>
      <PageHeader
        eyebrow="Product Brief"
        title="About EchoMatrix"
        description="A premium investigative dashboard for exploring Reddit-derived narrative activity through semantic search, time-series analysis, topic clustering, and network mapping."
        actions={<Badge variant="success">Frontend + API Aligned</Badge>}
      />

      <div className="grid-3">
        {pillars.map((pillar) => (
          <Card key={pillar.title}>
            <CardHeader
              title={pillar.title}
              subtitle="Design principle"
              action={<span className="insight-chip">{pillar.icon}</span>}
            />
            <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>{pillar.text}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}
