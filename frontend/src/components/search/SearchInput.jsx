import { Search, Sparkles } from 'lucide-react';

export default function SearchInput({
  query,
  onChange,
  onSubmit,
  busy = false,
}) {
  return (
    <form
      onSubmit={onSubmit}
      style={{
        display: 'flex',
        gap: 12,
        marginBottom: 24,
        flexWrap: 'wrap',
      }}
    >
      <div className="topbar-search search-input-shell" style={{ flex: 1, minWidth: 260 }}>
        <Search size={16} />
        <input
          type="text"
          placeholder="Search narratives, campaigns, slogans, or actors..."
          value={query}
          onChange={(event) => onChange(event.target.value)}
        />
      </div>
      <button type="submit" className="btn btn-primary" disabled={busy}>
        <Sparkles size={16} />
        {busy ? 'Searching...' : 'Search'}
      </button>
    </form>
  );
}
