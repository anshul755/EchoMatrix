import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import Input from '../ui/Input';
import Badge from '../ui/Badge';

export default function TopBar() {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  const handleSearch = (e) => {
    e.preventDefault();
    if (query.trim()) {
      navigate(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  };

  return (
    <header className="topbar">
      <form className="topbar-search-wrap" onSubmit={handleSearch}>
        <Input
          className="topbar-search"
          icon={<Search size={16} />}
          type="text"
          placeholder="Search narratives, topics, authors..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </form>

      <div className="topbar-actions">
        <Badge className="topbar-status">Live workspace</Badge>
      </div>
    </header>
  );
}
