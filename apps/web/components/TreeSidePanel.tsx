'use client';

import React from 'react';
import Link from 'next/link';
import { Tree } from '@treemap/types';
import { X, ExternalLink, ShieldCheck, TreePine, Ruler, Calendar, Award, HeartPulse } from 'lucide-react';

interface TreeSidePanelProps {
  tree: Tree & { observations?: Array<{ health: string }> };
  onClose: () => void;
}

export function TreeSidePanel({ tree, onClose }: TreeSidePanelProps) {
  const displayName = tree.genus && tree.species ? `${tree.genus} ${tree.species}` : 'Urban Tree';
  const latestObservation = tree.observations?.[0];
  const health = latestObservation?.health || 'unknown';

  return (
    <aside
      className="absolute bottom-0 left-0 right-0 sm:top-4 sm:bottom-4 sm:left-4 sm:right-auto sm:w-96 bg-white shadow-2xl rounded-t-2xl sm:rounded-2xl p-6 z-20 flex flex-col max-h-[80vh] sm:max-h-none overflow-y-auto border border-gray-100"
      aria-label="Tree Details Panel"
    >
      <div className="flex items-start justify-between border-b pb-4">
        <div>
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800 uppercase tracking-wide">
            {tree.status}
          </span>
          <h2 className="text-xl font-bold text-gray-900 mt-1 italic">{displayName}</h2>
          <p className="text-sm text-gray-500">ID: {tree.source_id}</p>
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 p-1 rounded-full hover:bg-gray-100 transition-colors"
          aria-label="Close tree details"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="mt-4 space-y-4 flex-1">
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="bg-gray-50 p-3 rounded-lg flex items-center gap-2">
            <Ruler className="w-4 h-4 text-emerald-600" />
            <div>
              <p className="text-xs text-gray-400">Circumference</p>
              <p className="font-semibold">
                {tree.circumference_m ? `${tree.circumference_m} m` : 'N/A'}
              </p>
            </div>
          </div>
          <div className="bg-gray-50 p-3 rounded-lg flex items-center gap-2">
            <TreePine className="w-4 h-4 text-emerald-600" />
            <div>
              <p className="text-xs text-gray-400">Height</p>
              <p className="font-semibold">{tree.height_m ? `${tree.height_m} m` : 'N/A'}</p>
            </div>
          </div>
          <div className="bg-gray-50 p-3 rounded-lg flex items-center gap-2">
            <Calendar className="w-4 h-4 text-emerald-600" />
            <div>
              <p className="text-xs text-gray-400">Planted Year</p>
              <p className="font-semibold">{tree.planted_year || 'Unknown'}</p>
            </div>
          </div>
          <div className="bg-gray-50 p-3 rounded-lg flex items-center gap-2">
            <HeartPulse className="w-4 h-4 text-emerald-600" />
            <div>
              <p className="text-xs text-gray-400">Health</p>
              <p className="font-semibold capitalize">{health}</p>
            </div>
          </div>
        </div>

        {tree.leaf_cycle && (
          <div className="bg-gray-50 p-3 rounded-lg flex items-center gap-2 text-sm">
            <Award className="w-4 h-4 text-emerald-600" />
            <div>
              <p className="text-xs text-gray-400">Leaf Cycle</p>
              <p className="font-semibold capitalize">{tree.leaf_cycle.replace('_', ' ')}</p>
            </div>
          </div>
        )}

        {/* Provenance & Licence */}
        <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-xs text-emerald-900 space-y-1">
          <p className="font-semibold flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4" /> Provenance & Licence
          </p>
          <p>
            Source: <span className="font-mono font-medium">{tree.source}</span>
          </p>
          <p>
            Licence: <span className="font-mono font-medium">{tree.licence}</span>
          </p>
        </div>
      </div>

      <div className="mt-6 pt-4 border-t">
        <Link
          href={`/tree/${tree.id}`}
          className="w-full flex items-center justify-center gap-2 bg-emerald-600 text-white font-medium py-2.5 px-4 rounded-xl hover:bg-emerald-700 transition-colors shadow-sm"
        >
          View Full Tree Profile <ExternalLink className="w-4 h-4" />
        </Link>
      </div>
    </aside>
  );
}
