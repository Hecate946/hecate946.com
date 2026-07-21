export type AnalyticsEventName =
  | 'season_changed'
  | 'command_palette_opened'
  | 'recording_played'
  | 'project_opened'
  | 'chess_puzzle_attempted'
  | 'lab_experiment_opened';

export type AnalyticsPayload = Record<string, string | number | boolean | null>;

/**
 * Provider-neutral analytics hook.
 *
 * Keep UI components calling this function instead of importing Plausible,
 * Google Analytics, or another provider directly. That makes the provider
 * replaceable and keeps tracking decisions centralized.
 */
export function trackEvent(
  name: AnalyticsEventName,
  payload: AnalyticsPayload = {},
) {
  if (import.meta.env.DEV) {
    console.info('[analytics]', name, payload);
    return;
  }

  window.dispatchEvent(
    new CustomEvent('portfolio:analytics', {
      detail: { name, payload },
    }),
  );
}
