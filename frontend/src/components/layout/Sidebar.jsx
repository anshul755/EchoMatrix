import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Search,
  BarChart3,
  Layers,
  Network,
  Info,
} from 'lucide-react';

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/search', icon: Search, label: 'Search' },
  { to: '/trends', icon: BarChart3, label: 'Trends' },
  { to: '/topics', icon: Layers, label: 'Topics' },
  { to: '/network', icon: Network, label: 'Network' },
  { to: '/about', icon: Info, label: 'About' },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <NavLink to="/" className="sidebar-logo">
        <div>
          <h1>EchoMatrix</h1>
          <div className="sidebar-tagline">Investigative console</div>
        </div>
      </NavLink>

      <nav className="sidebar-nav">
        <div className="nav-section-title">Workspace</div>
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `nav-item${isActive ? ' active' : ''}`
            }
            end={to === '/dashboard'}
          >
            <Icon size={18} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-footer-label">Dataset</div>
        <div className="sidebar-footer-value">Reddit JSONL Corpus</div>
        <div className="sidebar-footer-meta">Narratives indexed for search, trends, topics, and network analysis.</div>
      </div>
    </aside>
  );
}
