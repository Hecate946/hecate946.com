export const seasons = ['spring', 'summer', 'autumn', 'winter'] as const;
export type Season = (typeof seasons)[number];
export type SeasonPreference = Season | 'auto';

export function getSeasonForMonth(monthIndex: number): Season {
  if (monthIndex >= 2 && monthIndex <= 4) return 'spring';
  if (monthIndex >= 5 && monthIndex <= 7) return 'summer';
  if (monthIndex >= 8 && monthIndex <= 10) return 'autumn';
  return 'winter';
}
