import { ExternalLink, ChevronRight } from 'lucide-react';

function scoreLabel(score) {
  return `${(score * 100).toFixed(1)}% relevance`;
}

function renderSnippet(text) {
  const value = text || '';
  const parts = value.split(/(\*\*.*?\*\*)/g).filter(Boolean);
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    return <span key={index}>{part}</span>;
  });
}

export function SearchResults({ results = [], onSelect }) {
  if (!results.length) return null;

  return (
    <div className="search-results-list">
      {results.map((result, index) => (
        <button
          key={`${result.url || result.author || 'result'}-${index}`}
          className="search-result-card"
          onClick={() => onSelect(result)}
          type="button"
        >
          <div className="search-result-rank">{String(index + 1).padStart(2, '0')}</div>
          <div className="search-result-main">
            <div className="search-result-title-row">
              <div className="search-result-title">
                {renderSnippet(result.snippet || result.text || 'Untitled result')}
              </div>
              <span className="badge badge-accent">{scoreLabel(result.score || 0)}</span>
            </div>
            <div className="search-result-meta">
              {result.author ? <span>@{result.author}</span> : null}
              {result.platform ? <span>{result.platform}</span> : null}
              {result.date ? <span>{result.date}</span> : null}
              {result.metadata?.subreddit ? <span>r/{result.metadata.subreddit}</span> : null}
              {result.metadata?.domain ? <span>{result.metadata.domain}</span> : null}
            </div>
            <div className="search-result-preview">{result.text}</div>
          </div>
          <ChevronRight size={16} className="search-result-chevron" />
        </button>
      ))}
    </div>
  );
}

export function SearchResultDetail({ result, onClose }) {
  if (!result) return null;

  return (
    <div className="search-detail-overlay" onClick={onClose} role="presentation">
      <div className="search-detail-panel" onClick={(event) => event.stopPropagation()} role="dialog" aria-modal="true">
        <div className="card-header" style={{ marginBottom: 18 }}>
          <div>
            <div className="card-title">Result Detail</div>
            <div className="card-subtitle">Open the source or inspect the full metadata</div>
          </div>
          <button className="btn btn-ghost" type="button" onClick={onClose}>
            Close
          </button>
        </div>

        <div className="search-detail-score">{scoreLabel(result.score || 0)}</div>
        <div className="search-detail-snippet">{renderSnippet(result.snippet || result.text)}</div>
        <div className="search-detail-text">{result.text}</div>

        <div className="search-detail-meta">
          {result.author ? <div><strong>Author</strong><span>@{result.author}</span></div> : null}
          {result.platform ? <div><strong>Platform</strong><span>{result.platform}</span></div> : null}
          {result.date ? <div><strong>Date</strong><span>{result.date}</span></div> : null}
          {result.metadata?.post_id ? <div><strong>Post ID</strong><span>{result.metadata.post_id}</span></div> : null}
          {result.metadata?.subreddit ? <div><strong>Subreddit</strong><span>r/{result.metadata.subreddit}</span></div> : null}
          {result.metadata?.domain ? <div><strong>Domain</strong><span>{result.metadata.domain}</span></div> : null}
          {result.metadata?.media_type ? <div><strong>Media Type</strong><span>{result.metadata.media_type}</span></div> : null}
          {result.metadata?.comment_count != null ? <div><strong>Comments</strong><span>{result.metadata.comment_count}</span></div> : null}
          {result.metadata?.score_value != null ? <div><strong>Score</strong><span>{result.metadata.score_value}</span></div> : null}
          {result.hashtags?.length ? <div><strong>Hashtags</strong><span>{result.hashtags.join(', ')}</span></div> : null}
        </div>

        {result.url ? (
          <a href={result.url} target="_blank" rel="noreferrer" className="btn btn-primary">
            <ExternalLink size={14} />
            Open source
          </a>
        ) : null}
      </div>
    </div>
  );
}
