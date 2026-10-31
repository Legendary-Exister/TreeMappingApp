import { z } from 'zod';

export const TreeStatusSchema = z.enum(['unverified', 'verified', 'disputed', 'removed']);
export type TreeStatus = z.infer<typeof TreeStatusSchema>;

export const TreeSourceSchema = z.enum(['city_register', 'osm', 'citizen']);
export type TreeSource = z.infer<typeof TreeSourceSchema>;

export const LeafCycleSchema = z.enum(['deciduous', 'evergreen', 'semi_evergreen', 'unknown']);
export type LeafCycle = z.infer<typeof LeafCycleSchema>;

export const TreeHealthSchema = z.enum(['good', 'fair', 'poor', 'dead']);
export type TreeHealth = z.infer<typeof TreeHealthSchema>;

export const UserRoleSchema = z.enum(['citizen', 'reviewer', 'admin']);
export type UserRole = z.infer<typeof UserRoleSchema>;

export const PhotoTagSchema = z.enum(['whole', 'bark', 'leaf', 'crown']);
export type PhotoTag = z.infer<typeof PhotoTagSchema>;

export const TreeSchema = z.object({
  id: z.string().uuid(),
  source: TreeSourceSchema,
  source_id: z.string(),
  licence: z.string(),
  status: TreeStatusSchema,
  genus: z.string().nullable().optional(),
  species: z.string().nullable().optional(),
  leaf_cycle: LeafCycleSchema.nullable().optional(),
  circumference_m: z.number().positive().max(43).nullable().optional(), // 43m plausible world record
  height_m: z.number().positive().max(120).nullable().optional(), // 120m plausible world record
  crown_diameter_m: z.number().positive().max(60).nullable().optional(),
  planted_year: z.number().int().min(1500).max(new Date().getFullYear()).nullable().optional(),
  longitude: z.number().min(-180).max(180),
  latitude: z.number().min(-90).max(90),
  raw_attributes: z.record(z.unknown()).nullable().optional(),
  created_at: z.string().datetime().optional(),
  updated_at: z.string().datetime().optional(),
});
export type Tree = z.infer<typeof TreeSchema>;

export const ObservationSchema = z.object({
  id: z.string().uuid(),
  tree_id: z.string().uuid(),
  health: TreeHealthSchema,
  surroundings: z.string().nullable().optional(),
  notes: z.string().nullable().optional(),
  author: z.string().optional(),
  author_id: z.string().optional(),
  observed_at: z.string().datetime(),
});
export type Observation = z.infer<typeof ObservationSchema>;

export const PhotoSchema = z.object({
  id: z.string().uuid(),
  tree_id: z.string().uuid(),
  observation_id: z.string().uuid().nullable().optional(),
  photo_url: z.string().url(),
  tag: PhotoTagSchema,
  author: z.string().optional(),
  author_id: z.string().optional(),
  verified: z.boolean().default(false),
  created_at: z.string().datetime().optional(),
});
export type Photo = z.infer<typeof PhotoSchema>;

export const CreateTreeInputSchema = z.object({
  latitude: z.number().min(-90).max(90),
  longitude: z.number().min(-180).max(180),
  genus: z.string().trim().min(1).optional(),
  species: z.string().trim().min(1).optional(),
  circumference_m: z.number().positive().max(43).optional(),
  height_m: z.number().positive().max(120).optional(),
  crown_diameter_m: z.number().positive().max(60).optional(),
  health: TreeHealthSchema.default('good'),
  surroundings: z.string().optional(),
  notes: z.string().optional(),
  photo_urls: z.array(z.string().url()).min(1).max(4),
});
export type CreateTreeInput = z.infer<typeof CreateTreeInputSchema>;

export const TreesNearQuerySchema = z.object({
  latitude: z.number().min(-90).max(90),
  longitude: z.number().min(-180).max(180),
  radius_m: z.number().positive().max(5000).default(50),
});
export type TreesNearQuery = z.infer<typeof TreesNearQuerySchema>;
