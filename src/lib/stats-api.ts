// Updated automatically by `npm run stats:deploy` after Wrangler publishes the
// production Worker. Keep this empty in source until the first successful
// workers.dev deployment rather than pointing at a hostname that may not exist.
export const PROD_STATS_API_BASE = 'https://hecate-stats.hecate946.workers.dev';
export const LOCAL_STATS_API_BASE = '/__local-stats';

// Kept as the production constant for server-rendered markup and backwards
// compatibility. Browser code should call resolveStatsApiBase() instead.
export const STATS_API_BASE = PROD_STATS_API_BASE;

function isLoopbackHostname(hostname: string) {
  const value = hostname.toLowerCase();
  return (
    value === 'localhost' ||
    value.endsWith('.localhost') ||
    value === '127.0.0.1' ||
    value === '0.0.0.0' ||
    value === '::1' ||
    value === '[::1]'
  );
}

/**
 * Local development never contacts the production analytics Worker.
 * `npm run dev` serves LOCAL_STATS_API_BASE from the Astro/Vite dev server.
 * Hosted HTTP and HTTPS builds both use the same deployed workers.dev URL.
 */
export function resolveStatsApiBase(
  productionBase = PROD_STATS_API_BASE,
): string {
  if (typeof window === 'undefined') return productionBase;

  if (import.meta.env.DEV || isLoopbackHostname(window.location.hostname)) {
    return LOCAL_STATS_API_BASE;
  }

  return productionBase.trim().replace(/\/$/, '');
}
