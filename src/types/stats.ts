export type StatsWindowKey = '7' | '30' | '90';

export interface SectionStat {
  name: string;
  views: number;
}

export interface WindowStats {
  visitors: number;
  pageviews: number;
  averageSessionSeconds: number;
  returningPercent: number;
  topSections: SectionStat[];
}

export interface StatsSnapshot {
  generatedAt: string;
  isSample: boolean;
  windows: Record<StatsWindowKey, WindowStats>;
  lifetime: {
    visitors: number;
    pageviews: number;
  };
  performance: {
    lighthousePerformance: number;
    lighthouseAccessibility: number;
    javascriptKb: number;
    imageKb: number;
  };
  events: Array<{
    name: string;
    count: number;
  }>;
}
