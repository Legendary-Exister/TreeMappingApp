import { describe, it, expect } from 'vitest';
import { TreeSchema, CreateTreeInputSchema } from '../src';

describe('TreeSchema', () => {
  it('validates a valid tree model', () => {
    const validTree = {
      id: '123e4567-e89b-12d3-a456-426614174000',
      source: 'city_register',
      source_id: 'TREE-101',
      licence: 'CC-BY-4.0',
      status: 'verified',
      genus: 'Quercus',
      species: 'robur',
      leaf_cycle: 'deciduous',
      circumference_m: 2.1,
      height_m: 18.5,
      crown_diameter_m: 12.0,
      planted_year: 1985,
      longitude: 13.405,
      latitude: 52.52,
    };

    const result = TreeSchema.safeParse(validTree);
    expect(result.success).toBe(true);
  });

  it('rejects impossible circumference or height values', () => {
    const impossibleTree = {
      id: '123e4567-e89b-12d3-a456-426614174000',
      source: 'osm',
      source_id: 'node/123456',
      licence: 'ODbL',
      status: 'unverified',
      circumference_m: 55, // > 43 m impossible
      longitude: 13.405,
      latitude: 52.52,
    };

    const result = TreeSchema.safeParse(impossibleTree);
    expect(result.success).toBe(false);
  });

  it('validates citizen contribution input schema', () => {
    const input = {
      latitude: 52.52,
      longitude: 13.405,
      genus: 'Tilia',
      species: 'cordata',
      health: 'good',
      photo_urls: ['https://example.com/tree1.jpg'],
    };

    const result = CreateTreeInputSchema.safeParse(input);
    expect(result.success).toBe(true);
  });
});
