import { SupabaseClient } from '@supabase/supabase-js';
import {
  Tree,
  TreeSchema,
  CreateTreeInput,
  CreateTreeInputSchema,
  TreesNearQuery,
  TreesNearQuerySchema,
} from '@treemap/types';

export class TreeMapApiClient {
  constructor(private readonly supabase: SupabaseClient) {}

  /**
   * Fetch a single tree by UUID, including observations and verified photos.
   */
  async getTree(id: string): Promise<Tree | null> {
    const { data, error } = await this.supabase
      .from('trees')
      .select('*, observations(*), photos(*)')
      .eq('id', id)
      .single();

    if (error) {
      if (error.code === 'PGRST116') return null; // not found
      throw new Error(`Failed to fetch tree: ${error.message}`);
    }

    return TreeSchema.parse(data);
  }

  /**
   * Query existing trees within a radius in metres around a coordinate.
   * Calls the PostGIS RPC function `trees_near`.
   */
  async searchTreesNear(query: TreesNearQuery): Promise<Tree[]> {
    const validated = TreesNearQuerySchema.parse(query);

    const { data, error } = await this.supabase.rpc('trees_near', {
      lon: validated.longitude,
      lat: validated.latitude,
      radius_m: validated.radius_m,
    });

    if (error) {
      throw new Error(`Failed to search nearby trees: ${error.message}`);
    }

    return (data || []).map((row: unknown) => TreeSchema.parse(row));
  }

  /**
   * Submit a new citizen tree report with observation and photos in a single atomic flow.
   */
  async submitCitizenTree(input: CreateTreeInput): Promise<{ treeId: string }> {
    const validated = CreateTreeInputSchema.parse(input);

    const { data, error } = await this.supabase.rpc('submit_tree_with_observation', {
      tree_data: {
        latitude: validated.latitude,
        longitude: validated.longitude,
        genus: validated.genus ?? null,
        species: validated.species ?? null,
        circumference_m: validated.circumference_m ?? null,
        height_m: validated.height_m ?? null,
        crown_diameter_m: validated.crown_diameter_m ?? null,
      },
      observation_data: {
        health: validated.health,
        surroundings: validated.surroundings ?? null,
        notes: validated.notes ?? null,
      },
      photo_urls: validated.photo_urls,
    });

    if (error) {
      throw new Error(`Tree submission failed: ${error.message}`);
    }

    return { treeId: data.id };
  }
}
