import { defineCollection } from 'astro:content';
import { z } from 'astro/zod';
import { glob } from 'astro/loaders';

const sharedFields = {
  title: z.string(),
  description: z.string(),
  publishedAt: z.coerce.date(),
  updatedAt: z.coerce.date().optional(),
  featured: z.boolean().default(false),
  draft: z.boolean().default(false),
  tags: z.array(z.string()).default([]),
};

const projects = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/projects' }),
  schema: z.object({
    ...sharedFields,
    status: z.enum(['idea', 'prototype', 'active', 'complete', 'archived']),
    technologies: z.array(z.string()).default([]),
    repositoryUrl: z.url().optional(),
    demoUrl: z.url().optional(),
    accent: z.string().optional(),
  }),
});

const music = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/music' }),
  schema: z.object({
    ...sharedFields,
    instrument: z.enum(['clarinet', 'piano']),
    composer: z.string(),
    work: z.string(),
    role: z.string().optional(),
    venue: z.string().optional(),
    mediaUrl: z.url().optional(),
  }),
});

const chess = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/chess' }),
  schema: z.object({
    ...sharedFields,
    playedAt: z.coerce.date().optional(),
    color: z.enum(['white', 'black']).optional(),
    result: z.enum(['win', 'draw', 'loss', 'study']).default('study'),
    opponent: z.string().optional(),
    opening: z.string().optional(),
    pgn: z.string().optional(),
  }),
});

const pickleball = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/pickleball' }),
  schema: z.object({
    ...sharedFields,
    kind: z.enum(['match', 'training', 'strategy', 'experiment']),
    playedAt: z.coerce.date().optional(),
    rating: z.number().optional(),
  }),
});

const notes = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/notes' }),
  schema: z.object({
    ...sharedFields,
    category: z.enum([
      'code',
      'clarinet',
      'piano',
      'chess',
      'pickleball',
      'general',
    ]),
  }),
});

export const collections = { projects, music, chess, pickleball, notes };
