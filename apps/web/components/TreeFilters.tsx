'use client';

import React from 'react';
import { Search, Filter, ShieldCheck } from 'lucide-react';

interface TreeFiltersProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  healthFilter: string;
  onHealthChange: (h: string) => void;
  verifiedOnly: boolean;
  onVerifiedToggle: () => void;
}

export function TreeFilters({
  searchQuery,
  onSearchChange,
  healthFilter,
  onHealthChange,
  verifiedOnly,
  onVerifiedToggle,
}: TreeFiltersProps) {
  return (
    <div className="absolute top-4 left-4 right-4 sm:right-auto sm:w-auto z-10 flex flex-col sm:flex-row gap-2">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" aria-hidden="true" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search species or genus (e.g. Quercus)..."
          className="w-full pl-9 pr-4 py-2.5 bg-white/95 backdrop-blur shadow-md rounded-xl text-sm border border-gray-200 focus:outline-none focus:ring-2 focus:ring-emerald-500 text-gray-900"
          aria-label="Search tree species or genus"
          id="tree-search"
        />
      </div>

      <div className="relative">
        <select
          value={healthFilter}
          onChange={(e) => onHealthChange(e.target.value)}
          className="appearance-none bg-white/95 backdrop-blur shadow-md rounded-xl text-sm border border-gray-200 py-2.5 pl-3 pr-8 focus:outline-none focus:ring-2 focus:ring-emerald-500 font-medium text-gray-700"
          aria-label="Filter trees by health status"
          id="health-filter"
        >
          <option value="all">All Health</option>
          <option value="good">Good</option>
          <option value="fair">Fair</option>
          <option value="poor">Poor</option>
          <option value="dead">Dead</option>
        </select>
        <Filter className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none" />
      </div>

      <button
        onClick={onVerifiedToggle}
        className={`flex items-center gap-2 px-4 py-2.5 bg-white/95 backdrop-blur shadow-md rounded-xl text-sm border transition-colors ${
          verifiedOnly
            ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
            : 'border-gray-200 text-gray-700 hover:border-emerald-300'
        }`}
        aria-pressed={verifiedOnly}
        aria-label={`${verifiedOnly ? 'Showing only verified trees. Click to show all trees.' : 'Click to show only verified trees.'}`}
        id="verified-toggle"
      >
        <ShieldCheck className="w-4 h-4" />
        <span className="font-medium">Verified</span>
      </button>
    </div>
  );
}
