import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { searchPosts } from '../services/api';
import { Search, AlertCircle, Languages, MessageSquareText, Sparkles } from 'lucide-react';
import PageHeader from '../components/ui/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../components/ui/StatePanel';
import SearchInput from '../components/search/SearchInput';
import SuggestedQueries from '../components/search/SuggestedQueries';
import { SearchResultDetail, SearchResults } from '../components/search/SearchResults';

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const urlQuery = searchParams.get('q') || '';
  const [query, setQuery] = useState(urlQuery);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedResult, setSelectedResult] = useState(null);
  const debounceRef = useRef(null);

  useEffect(() => {
    const onlyWhitespaceDiffers = query.trim() === urlQuery;
    if (urlQuery !== query && !onlyWhitespaceDiffers) {
      setQuery(urlQuery);
    }
    if (urlQuery) doSearch(urlQuery);
    if (!urlQuery) {
      setResults(null);
      setSelectedResult(null);
    }
  }, [urlQuery]);

  const doSearch = async (q) => {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await searchPosts(q);
      setResults(data);
    } catch (err) {
      setError('Search service unavailable. Please ensure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed === urlQuery) return;

    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (!trimmed) {
      debounceRef.current = setTimeout(() => setSearchParams({}), 250);
      return;
    }

    if (trimmed.length >= 2) {
      debounceRef.current = setTimeout(() => {
        setSearchParams({ q: trimmed });
      }, 350);
    }

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, urlQuery, setSearchParams]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      setSearchParams({ q: query.trim() });
    }
  };

  const helperTone = (() => {
    const trimmed = query.trim();
    if (!trimmed) {
      return {
        icon: <Search size={16} />,
        text: 'Use natural language. The search ranks posts by semantic similarity rather than exact keywords.',
      };
    }
    if (trimmed.length < 2) {
      return {
        icon: <MessageSquareText size={16} />,
        text: 'Short queries are allowed in the input, but the backend will ask for at least 2 characters before searching.',
      };
    }
    if (/[^\u0000-\u007f]/.test(trimmed)) {
      return {
        icon: <Languages size={16} />,
        text: 'Non-English queries are supported. Results depend on the embedding model and available dataset coverage.',
      };
    }
    return {
      icon: <Search size={16} />,
      text: 'Results update automatically after a short pause, or press Search to run immediately.',
    };
  })();

  return (
    <div>
      <PageHeader
        eyebrow="Investigative Retrieval"
        title="Semantic Search"
        description="Search by meaning, inspect ranked evidence, and pivot into follow-up questions without losing context."
      />

      <div className="card" style={{ marginBottom: 20 }}>
        <SearchInput
          query={query}
          onChange={setQuery}
          onSubmit={handleSubmit}
          busy={loading}
        />
        <div className="search-helper-row">
          <span className="search-helper-icon">{helperTone.icon}</span>
          <span>{helperTone.text}</span>
        </div>
      </div>

      {loading && (
        <LoadingState label="Searching across embeddings..." />
      )}

      {error && (
        <ErrorState icon={<AlertCircle size={18} />} message={error} />
      )}

      {results && !loading && (
        <div>
          {results.retrieval_method ? (
            <div className="card" style={{ marginBottom: 20, padding: 16 }}>
              <div className="card-title" style={{ marginBottom: 6 }}>Retrieval Method</div>
              <div className="card-subtitle">{results.retrieval_method}</div>
            </div>
          ) : null}

          {results.message && (
            <div className="ai-summary" style={{ marginTop: 0, marginBottom: 20 }}>
              <div className="ai-summary-label">
                <Sparkles size={12} /> Search Info
              </div>
              <div className="ai-summary-text">{results.message}</div>
            </div>
          )}

          <SuggestedQueries queries={results.related_queries} onPick={(rq) => setSearchParams({ q: rq })} />

          {results.results?.length > 0 ? (
            <SearchResults results={results.results} onSelect={setSelectedResult} />
          ) : (
            !results.message && (
              <EmptyState
                icon={<Search size={40} />}
                title="No results found"
                description="Try a different query, broaden the wording, or click one of the suggested follow-up angles."
              />
            )
          )}
        </div>
      )}

      {!results && !loading && !error && (
        <EmptyState
          icon={<Search size={48} />}
          title="Start searching"
          description="Enter a query to investigate narratives, communities, or actors. The interface will surface ranked evidence, metadata, and follow-up paths."
        />
      )}

      <SearchResultDetail result={selectedResult} onClose={() => setSelectedResult(null)} />
    </div>
  );
}
