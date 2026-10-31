import { describe, it, expect, vi } from 'vitest';
import { TreeMapApiClient } from '../src/trees';
import { SupabaseClient } from '@supabase/supabase-js';

describe('TreeMapApiClient', () => {
  it('instantiates successfully and formats search queries', async () => {
    const mockRpc = vi.fn().mockResolvedValue({
      data: [
        {
          id: '123e4567-e89b-12d3-a456-426614174000',
          source: 'city_register',
          source_id: 'TREE-1',
          licence: 'dl-de/by-2-0',
          status: 'verified',
          genus: 'Acer',
          species: 'pseudoplatanus',
          longitude: 13.4,
          latitude: 52.5,
        },
      ],
      error: null,
    });

    const mockSupabase = {
      rpc: mockRpc,
    } as unknown as SupabaseClient;

    const client = new TreeMapApiClient(mockSupabase);
    const trees = await client.searchTreesNear({
      latitude: 52.5,
      longitude: 13.4,
      radius_m: 50,
    });

    expect(mockRpc).toHaveBeenCalledWith('trees_near', {
      lat: 52.5,
      lon: 13.4,
      radius_m: 50,
    });
    expect(trees).toHaveLength(1);
    expect(trees[0]?.genus).toBe('Acer');
  });
});
