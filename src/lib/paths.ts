export function withBase(path = '/') {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return `${base}${normalized}` || '/';
}

export function isCurrentPath(currentPath: string, targetPath: string) {
  const baseTarget = withBase(targetPath);
  if (targetPath === '/')
    return currentPath === baseTarget || currentPath === `${baseTarget}/`;
  return currentPath.startsWith(baseTarget);
}

export function pdfViewerHref(pdfPath: string) {
  const source = pdfPath.startsWith('/') ? withBase(pdfPath) : pdfPath;
  return `${withBase('/pdf/')}?src=${encodeURIComponent(source)}`;
}

