import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 70000,
});

export async function fetchStats() {
  const { data } = await api.get('/stats');
  return data;
}

export async function fetchDashboardOverview(forceRefresh = false) {
  const { data } = await api.get('/dashboard/overview', {
    params: { force_refresh: forceRefresh },
  });
  return data;
}

export async function searchPosts(query, limit = 20) {
  const { data } = await api.get('/search', { params: { q: query, limit } });
  return data;
}

export async function fetchTimeSeries(query = '', granularity = 'day', groupBy = '', eventId = '') {
  const params = { q: query, granularity };
  if (groupBy) params.group_by = groupBy;
  if (eventId) params.event_id = eventId;
  const { data } = await api.get('/timeseries', { params });
  return data;
}

export async function fetchEvents() {
  const { data } = await api.get('/events');
  return data;
}

export async function fetchTopics(nClusters = 8) {
  const { data } = await api.get('/topics', { params: { n_clusters: nClusters } });
  return data;
}

export async function fetchProjectorExport(nClusters = 8, maxPoints = 2000) {
  const { data } = await api.get('/topics/projector', {
    params: { n_clusters: nClusters, max_points: maxPoints },
  });
  return data;
}

export async function fetchNetwork(
  query = '',
  minDegree = 1,
  graphType = 'account',
  scoring = 'pagerank',
  removeTopNode = false,
) {
  const { data } = await api.get('/network', {
    params: {
      q: query,
      min_degree: minDegree,
      graph_type: graphType,
      scoring,
      remove_top_node: removeTopNode,
    },
  });
  return data;
}

export default api;
