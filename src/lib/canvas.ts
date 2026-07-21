interface AnimationLoopOptions {
  draw: (time: number, delta: number) => void;
  drawStatic?: () => void;
  maxDeltaMs?: number;
}

export function resizeCanvasToDisplaySize(
  canvas: HTMLCanvasElement,
  maxPixelRatio = 2,
) {
  const pixelRatio = Math.min(window.devicePixelRatio || 1, maxPixelRatio);
  const width = Math.max(1, Math.floor(canvas.clientWidth * pixelRatio));
  const height = Math.max(1, Math.floor(canvas.clientHeight * pixelRatio));

  if (canvas.width === width && canvas.height === height) return false;

  canvas.width = width;
  canvas.height = height;
  return true;
}

/**
 * Starts an animation loop that pauses on hidden tabs and renders one static
 * frame for visitors who prefer reduced motion. Return value disposes all
 * listeners and animation frames.
 */
export function startAnimationLoop({
  draw,
  drawStatic,
  maxDeltaMs = 50,
}: AnimationLoopOptions) {
  const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
  let frameId = 0;
  let previousTime = performance.now();
  let disposed = false;

  const renderStatic = () =>
    (drawStatic ?? (() => draw(performance.now(), 0)))();

  const frame = (time: number) => {
    if (disposed || document.hidden || motionQuery.matches) return;
    const delta = Math.min(time - previousTime, maxDeltaMs);
    previousTime = time;
    draw(time, delta);
    frameId = requestAnimationFrame(frame);
  };

  const start = () => {
    cancelAnimationFrame(frameId);
    if (motionQuery.matches) {
      renderStatic();
      return;
    }
    previousTime = performance.now();
    frameId = requestAnimationFrame(frame);
  };

  const handleVisibility = () => {
    if (document.hidden) cancelAnimationFrame(frameId);
    else start();
  };

  motionQuery.addEventListener('change', start);
  document.addEventListener('visibilitychange', handleVisibility);
  start();

  return () => {
    disposed = true;
    cancelAnimationFrame(frameId);
    motionQuery.removeEventListener('change', start);
    document.removeEventListener('visibilitychange', handleVisibility);
  };
}
