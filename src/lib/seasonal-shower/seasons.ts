import { autumnShower } from './autumn';
import { springShower } from './spring';
import { summerShower } from './summer';
import type { Season, SeasonDefinition } from './types';
import { winterShower } from './winter';

export const VALID_SEASONS: Season[] = ['spring', 'summer', 'autumn', 'winter'];

export const SEASONAL_SHOWERS: Record<Season, SeasonDefinition> = {
  spring: springShower,
  summer: summerShower,
  autumn: autumnShower,
  winter: winterShower,
};
