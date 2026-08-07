export const WEBSITE_GRAPH_GROUPS = [
  { id: 'core', label: 'Core', color: '#1f77b4' },
  { id: 'profile', label: 'Profile', color: '#ff7f0e' },
  { id: 'projects', label: 'Projects', color: '#2ca02c' },
  { id: 'spaces', label: 'Spaces', color: '#d62728' },
  { id: 'experiments', label: 'Experiments', color: '#9467bd' },
] as const;

export type WebsiteGraphGroupId = (typeof WEBSITE_GRAPH_GROUPS)[number]['id'];

export const WEBSITE_GRAPH_GROUP_COLORS: Record<WebsiteGraphGroupId, string> =
  Object.fromEntries(
    WEBSITE_GRAPH_GROUPS.map(({ id, color }) => [id, color]),
  ) as Record<WebsiteGraphGroupId, string>;
