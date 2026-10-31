import React from 'react';
import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowLeft, ShieldCheck, TreePine, Calendar, Ruler, Award, HeartPulse } from 'lucide-react';
import { TreeMapApiClient, createTreeMapSupabaseClient } from '@treemap/api-client';
import { Tree } from '@treemap/types';
import { notFound } from 'next/navigation';

interface Props {
  params: Promise<{ id: string }>;
}

async function getTree(id: string): Promise<Tree | null> {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseKey) {
    console.error('Missing Supabase environment variables');
    return null;
  }

  const client = new TreeMapApiClient(createTreeMapSupabaseClient({ supabaseUrl, supabaseKey }));
  return client.getTree(id);
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const tree = await getTree(id);

  const displayName = tree?.genus && tree?.species
    ? `${tree.genus} ${tree.species}`
    : 'Urban Tree';

  return {
    title: `${displayName} - TreeMap`,
    description: `Urban forestry register and citizen science observations for tree #${id.slice(0, 8)}`,
    openGraph: {
      title: `${displayName} - TreeMap`,
      description: `View measurements, species verification and health status.`,
    },
  };
}

export default async function TreeDetailPage({ params }: Props) {
  const { id } = await params;
  const tree = await getTree(id);

  if (!tree) {
    notFound();
  }

  const displayName = tree.genus && tree.species ? `${tree.genus} ${tree.species}` : 'Urban Tree';
  const latestObservation = (tree as any).observations?.[0];
  const health = latestObservation?.health || 'unknown';

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-8 flex flex-col items-center">
      <div className="w-full max-w-2xl bg-white rounded-2xl shadow-sm border border-gray-100 p-6 sm:p-8">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm text-emerald-600 hover:text-emerald-700 font-medium mb-6"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Map
        </Link>

        <div className="border-b pb-6">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 uppercase">
              {tree.status}
            </span>
            <span className="text-xs text-gray-400">ID: {tree.source_id}</span>
          </div>
          <h1 className="text-3xl font-extrabold text-gray-900 mt-2 italic">{displayName}</h1>
          <p className="text-gray-500 font-medium">UUID: {tree.id}</p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 my-6">
          <div className="bg-gray-50 p-4 rounded-xl text-center">
            <Ruler className="w-5 h-5 text-emerald-600 mx-auto mb-1" />
            <p className="text-xs text-gray-400">Circumference</p>
            <p className="font-bold text-gray-900 mt-0.5">
              {tree.circumference_m ? `${tree.circumference_m} m` : 'N/A'}
            </p>
          </div>
          <div className="bg-gray-50 p-4 rounded-xl text-center">
            <TreePine className="w-5 h-5 text-emerald-600 mx-auto mb-1" />
            <p className="text-xs text-gray-400">Height</p>
            <p className="font-bold text-gray-900 mt-0.5">
              {tree.height_m ? `${tree.height_m} m` : 'N/A'}
            </p>
          </div>
          <div className="bg-gray-50 p-4 rounded-xl text-center">
            <Calendar className="w-5 h-5 text-emerald-600 mx-auto mb-1" />
            <p className="text-xs text-gray-400">Planted</p>
            <p className="font-bold text-gray-900 mt-0.5">
              {tree.planted_year || 'Unknown'}
            </p>
          </div>
          <div className="bg-gray-50 p-4 rounded-xl text-center">
            <HeartPulse className="w-5 h-5 text-emerald-600 mx-auto mb-1" />
            <p className="text-xs text-gray-400">Health</p>
            <p className="font-bold text-emerald-600 mt-0.5 capitalize">
              {health}
            </p>
          </div>
        </div>

        <div className="bg-emerald-50 rounded-xl p-4 border border-emerald-100 text-sm text-emerald-950">
          <h3 className="font-semibold flex items-center gap-2 mb-1">
            <ShieldCheck className="w-4 h-4 text-emerald-700" /> Provenance & Licence
          </h3>
          <p className="text-xs text-emerald-800">
            Source: <span className="font-mono">{tree.source}</span> | Licence:{' '}
            <span className="font-mono">{tree.licence}</span>
          </p>
        </div>

        {tree.leaf_cycle && (
          <div className="mt-4 bg-gray-50 rounded-xl p-4 border border-gray-100 text-sm text-gray-700">
            <h3 className="font-semibold flex items-center gap-2 mb-1">
              <Award className="w-4 h-4 text-emerald-600" /> Leaf Cycle
            </h3>
            <p className="text-xs text-gray-600 capitalize">{tree.leaf_cycle.replace('_', ' ')}</p>
          </div>
        )}
      </div>
    </div>
  );
}
