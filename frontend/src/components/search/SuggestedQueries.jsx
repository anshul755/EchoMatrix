export default function SuggestedQueries({ queries = [], onPick }) {
  if (!queries.length) return null;

  return (
    <div className="search-suggestions">
      <span className="search-suggestions-label">Follow-up angles</span>
      <div className="search-suggestions-list">
        {queries.map((query) => (
          <button
            key={query}
            className="badge badge-accent search-suggestion-chip"
            onClick={() => onPick(query)}
            type="button"
          >
            {query}
          </button>
        ))}
      </div>
    </div>
  );
}
