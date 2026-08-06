/**
 * Routes that should render the seasonal shower.
 *
 * Add or remove normalized site paths here. Use `/` for the home page and
 * omit trailing slashes for other pages, for example `/shower`.
 */
export const SEASONAL_SHOWER_PAGES = ['/shower'] as const;

function normalizePath(pathname: string) {
  const withoutQueryOrHash = pathname.split(/[?#]/, 1)[0] || '/';
  const normalized = withoutQueryOrHash.replace(/\/+$/, '');
  return normalized || '/';
}

export function shouldShowSeasonalShower(pathname: string) {
  const basePath = normalizePath(import.meta.env.BASE_URL || '/');
  let routePath = normalizePath(pathname);

  if (basePath !== '/' && (routePath === basePath || routePath.startsWith(`${basePath}/`))) {
    routePath = normalizePath(routePath.slice(basePath.length));
  }

  return SEASONAL_SHOWER_PAGES.some((page) => page === routePath);
}
