export function prefersReducedMotion() {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );
}

export function subscribeToMotionPreference(
  callback: (reduced: boolean) => void,
) {
  const query = window.matchMedia('(prefers-reduced-motion: reduce)');
  const listener = (event: MediaQueryListEvent) => callback(event.matches);
  query.addEventListener('change', listener);
  callback(query.matches);
  return () => query.removeEventListener('change', listener);
}
