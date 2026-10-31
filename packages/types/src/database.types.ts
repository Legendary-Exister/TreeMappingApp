export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[];

export type Database = {
  graphql_public: {
    Tables: {
      [_ in never]: never;
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      graphql: {
        Args: { extensions?: Json; operationName?: string; query?: string; variables?: Json };
        Returns: Json;
      };
    };
    Enums: {
      [_ in never]: never;
    };
    CompositeTypes: {
      [_ in never]: never;
    };
  };
  public: {
    Tables: {
      care_events: {
        Row: {
          created_at: string;
          event_type: Database['public']['Enums']['care_event_type'];
          id: string;
          litres: number | null;
          notes: string | null;
          tree_id: string;
          user_id: string | null;
        };
        ComputedFields: never;
        Insert: {
          created_at?: string;
          event_type: Database['public']['Enums']['care_event_type'];
          id?: string;
          litres?: number | null;
          notes?: string | null;
          tree_id: string;
          user_id?: string | null;
        };
        Update: {
          created_at?: string;
          event_type?: Database['public']['Enums']['care_event_type'];
          id?: string;
          litres?: number | null;
          notes?: string | null;
          tree_id?: string;
          user_id?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: 'care_events_tree_id_fkey';
            columns: ['tree_id'];
            isOneToOne: false;
            referencedRelation: 'trees';
            referencedColumns: ['id'];
          },
        ];
      };
      observations: {
        Row: {
          author: string | null;
          author_id: string | null;
          created_at: string;
          health: Database['public']['Enums']['tree_health'];
          id: string;
          notes: string | null;
          observed_at: string;
          surroundings: string | null;
          tree_id: string;
        };
        ComputedFields: never;
        Insert: {
          author?: string | null;
          author_id?: string | null;
          created_at?: string;
          health: Database['public']['Enums']['tree_health'];
          id?: string;
          notes?: string | null;
          observed_at?: string;
          surroundings?: string | null;
          tree_id: string;
        };
        Update: {
          author?: string | null;
          author_id?: string | null;
          created_at?: string;
          health?: Database['public']['Enums']['tree_health'];
          id?: string;
          notes?: string | null;
          observed_at?: string;
          surroundings?: string | null;
          tree_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: 'observations_tree_id_fkey';
            columns: ['tree_id'];
            isOneToOne: false;
            referencedRelation: 'trees';
            referencedColumns: ['id'];
          },
        ];
      };
      photos: {
        Row: {
          author: string | null;
          author_id: string | null;
          created_at: string;
          id: string;
          observation_id: string | null;
          photo_url: string;
          tag: Database['public']['Enums']['photo_tag'];
          tree_id: string;
          verified: boolean;
        };
        ComputedFields: never;
        Insert: {
          author?: string | null;
          author_id?: string | null;
          created_at?: string;
          id?: string;
          observation_id?: string | null;
          photo_url: string;
          tag?: Database['public']['Enums']['photo_tag'];
          tree_id: string;
          verified?: boolean;
        };
        Update: {
          author?: string | null;
          author_id?: string | null;
          created_at?: string;
          id?: string;
          observation_id?: string | null;
          photo_url?: string;
          tag?: Database['public']['Enums']['photo_tag'];
          tree_id?: string;
          verified?: boolean;
        };
        Relationships: [
          {
            foreignKeyName: 'photos_observation_id_fkey';
            columns: ['observation_id'];
            isOneToOne: false;
            referencedRelation: 'observations';
            referencedColumns: ['id'];
          },
          {
            foreignKeyName: 'photos_tree_id_fkey';
            columns: ['tree_id'];
            isOneToOne: false;
            referencedRelation: 'trees';
            referencedColumns: ['id'];
          },
        ];
      };
      profiles: {
        Row: {
          created_at: string;
          id: string;
          role: Database['public']['Enums']['user_role'];
          updated_at: string;
          username: string | null;
        };
        ComputedFields: never;
        Insert: {
          created_at?: string;
          id: string;
          role?: Database['public']['Enums']['user_role'];
          updated_at?: string;
          username?: string | null;
        };
        Update: {
          created_at?: string;
          id?: string;
          role?: Database['public']['Enums']['user_role'];
          updated_at?: string;
          username?: string | null;
        };
        Relationships: [];
      };
      trees: {
        Row: {
          circumference_m: number | null;
          created_at: string;
          crown_diameter_m: number | null;
          genus: string | null;
          geom: unknown;
          height_m: number | null;
          id: string;
          leaf_cycle: Database['public']['Enums']['leaf_cycle'] | null;
          licence: string;
          planted_year: number | null;
          raw_attributes: Json | null;
          source: Database['public']['Enums']['tree_source'];
          source_id: string;
          species: string | null;
          status: Database['public']['Enums']['tree_status'];
          updated_at: string;
        };
        ComputedFields: never;
        Insert: {
          circumference_m?: number | null;
          created_at?: string;
          crown_diameter_m?: number | null;
          genus?: string | null;
          geom: unknown;
          height_m?: number | null;
          id?: string;
          leaf_cycle?: Database['public']['Enums']['leaf_cycle'] | null;
          licence: string;
          planted_year?: number | null;
          raw_attributes?: Json | null;
          source: Database['public']['Enums']['tree_source'];
          source_id: string;
          species?: string | null;
          status?: Database['public']['Enums']['tree_status'];
          updated_at?: string;
        };
        Update: {
          circumference_m?: number | null;
          created_at?: string;
          crown_diameter_m?: number | null;
          genus?: string | null;
          geom?: unknown;
          height_m?: number | null;
          id?: string;
          leaf_cycle?: Database['public']['Enums']['leaf_cycle'] | null;
          licence?: string;
          planted_year?: number | null;
          raw_attributes?: Json | null;
          source?: Database['public']['Enums']['tree_source'];
          source_id?: string;
          species?: string | null;
          status?: Database['public']['Enums']['tree_status'];
          updated_at?: string;
        };
        Relationships: [];
      };
      verifications: {
        Row: {
          created_at: string;
          id: string;
          notes: string | null;
          reviewer_id: string | null;
          tree_id: string;
          verdict: Database['public']['Enums']['verification_verdict'];
        };
        ComputedFields: never;
        Insert: {
          created_at?: string;
          id?: string;
          notes?: string | null;
          reviewer_id?: string | null;
          tree_id: string;
          verdict: Database['public']['Enums']['verification_verdict'];
        };
        Update: {
          created_at?: string;
          id?: string;
          notes?: string | null;
          reviewer_id?: string | null;
          tree_id?: string;
          verdict?: Database['public']['Enums']['verification_verdict'];
        };
        Relationships: [
          {
            foreignKeyName: 'verifications_tree_id_fkey';
            columns: ['tree_id'];
            isOneToOne: false;
            referencedRelation: 'trees';
            referencedColumns: ['id'];
          },
        ];
      };
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      is_reviewer: { Args: Record<PropertyKey, never>; Returns: boolean };
      submit_tree_with_observation: {
        Args: { observation_data: Json; photo_urls: string[]; tree_data: Json };
        Returns: Json;
      };
      trees_near: {
        Args: { lat: number; lon: number; radius_m?: number };
        Returns: {
          circumference_m: number;
          crown_diameter_m: number;
          distance_m: number;
          genus: string;
          height_m: number;
          id: string;
          latitude: number;
          leaf_cycle: Database['public']['Enums']['leaf_cycle'];
          licence: string;
          longitude: number;
          planted_year: number;
          source: Database['public']['Enums']['tree_source'];
          source_id: string;
          species: string;
          status: Database['public']['Enums']['tree_status'];
        }[];
      };
    };
    Enums: {
      care_event_type: 'watered' | 'mulched' | 'pruned' | 'reported_damage';
      leaf_cycle: 'deciduous' | 'evergreen' | 'semi_evergreen' | 'unknown';
      photo_tag: 'whole' | 'bark' | 'leaf' | 'crown';
      tree_health: 'good' | 'fair' | 'poor' | 'dead';
      tree_source: 'city_register' | 'osm' | 'citizen';
      tree_status: 'unverified' | 'verified' | 'disputed' | 'removed';
      user_role: 'citizen' | 'reviewer' | 'admin';
      verification_verdict: 'approved' | 'rejected' | 'correction_needed';
    };
    CompositeTypes: {
      [_ in never]: never;
    };
  };
};

type DatabaseWithoutInternals = Omit<Database, '__InternalSupabase'>;

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, 'public'>];

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema['Tables'] & DefaultSchema['Views'])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Tables'] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Views'])
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends { schema: keyof DatabaseWithoutInternals }
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Tables'] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Views'])[TableName] extends {
      Row: infer R;
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema['Tables'] & DefaultSchema['Views'])
    ? (DefaultSchema['Tables'] & DefaultSchema['Views'])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R;
      }
      ? R
      : never
    : never;

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    keyof DefaultSchema['Tables'] | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Tables']
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends { schema: keyof DatabaseWithoutInternals }
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Tables'][TableName] extends {
      Insert: infer I;
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema['Tables']
    ? DefaultSchema['Tables'][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I;
      }
      ? I
      : never
    : never;

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    keyof DefaultSchema['Tables'] | { schema: keyof DatabaseWithoutInternals },
  TableName extends (DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Tables']
    : never) = never,
> = DefaultSchemaTableNameOrOptions extends { schema: keyof DatabaseWithoutInternals }
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions['schema']]['Tables'][TableName] extends {
      Update: infer U;
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema['Tables']
    ? DefaultSchema['Tables'][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U;
      }
      ? U
      : never
    : never;

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    keyof DefaultSchema['Enums'] | { schema: keyof DatabaseWithoutInternals },
  EnumName extends (DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions['schema']]['Enums']
    : never) = never,
> = DefaultSchemaEnumNameOrOptions extends { schema: keyof DatabaseWithoutInternals }
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions['schema']]['Enums'][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema['Enums']
    ? DefaultSchema['Enums'][DefaultSchemaEnumNameOrOptions]
    : never;

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    keyof DefaultSchema['CompositeTypes'] | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends (PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions['schema']]['CompositeTypes']
    : never) = never,
> = PublicCompositeTypeNameOrOptions extends { schema: keyof DatabaseWithoutInternals }
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions['schema']]['CompositeTypes'][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema['CompositeTypes']
    ? DefaultSchema['CompositeTypes'][PublicCompositeTypeNameOrOptions]
    : never;

export const Constants = {
  graphql_public: {
    Enums: {},
  },
  public: {
    Enums: {
      care_event_type: ['watered', 'mulched', 'pruned', 'reported_damage'],
      leaf_cycle: ['deciduous', 'evergreen', 'semi_evergreen', 'unknown'],
      photo_tag: ['whole', 'bark', 'leaf', 'crown'],
      tree_health: ['good', 'fair', 'poor', 'dead'],
      tree_source: ['city_register', 'osm', 'citizen'],
      tree_status: ['unverified', 'verified', 'disputed', 'removed'],
      user_role: ['citizen', 'reviewer', 'admin'],
      verification_verdict: ['approved', 'rejected', 'correction_needed'],
    },
  },
} as const;
