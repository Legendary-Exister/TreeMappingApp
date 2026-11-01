'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import maplibregl, {
  Map as MapLibreMap,
  NavigationControl,
  GeolocateControl,
  type MapMouseEvent,
  type MapGeoJSONFeature,
} from 'maplibre-gl';
import { Protocol } from 'pmtiles';
import { useSearchParams, useRouter } from 'next/navigation';
import { TreeFilters } from './TreeFilters';
import { TreeSidePanel } from './TreeSidePanel';
import { Tree } from '@treemap/types';

const DEFAULT_STYLE =
  process.env.NEXT_PUBLIC_MAP_STYLE_URL || 'https://tiles.openfreemap.org/styles/liberty';
const CITY_NAME = process.env.NEXT_PUBLIC_CITY_NAME || 'Berlin';
const CITY_LON = parseFloat(process.env.NEXT_PUBLIC_MAP_LON || '13.4050');
const CITY_LAT = parseFloat(process.env.NEXT_PUBLIC_MAP_LAT || '52.5200');
const CITY_ZOOM = parseFloat(process.env.NEXT_PUBLIC_MAP_ZOOM || '13');

/**
 * URL of the PMTiles archive served from object storage.
 * Must support HTTP range requests and include the CORS header
 *   Access-Control-Allow-Origin: *
 * Wrap in the pmtiles:// protocol so MapLibre uses the PMTiles JS library.
 */
const TREE_TILES_URL = process.env.NEXT_PUBLIC_TREE_TILES_URL
  ? process.env.NEXT_PUBLIC_TREE_TILES_URL.replace(/^https?:\/\//, 'pmtiles://')
  : null;

// ---------------------------------------------------------------------------
// Leaf cycle → colour mapping (matches DB enum)
// ---------------------------------------------------------------------------
const LEAF_CYCLE_COLOURS: Record<'deciduous' | 'evergreen' | 'semi_evergreen' | 'unknown', string> = {
  deciduous: '#16a34a',      // green-600
  evergreen: '#0d9488',     // teal-600
  semi_evergreen: '#0891b2', // cyan-600
  unknown: '#9ca3af',       // gray-400
};

export default function Map() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const searchParams = useSearchParams();
  const router = useRouter();

  // Filter state
  const [searchQuery, setSearchQuery] = useState(searchParams.get('q') || '');
  const [healthFilter, setHealthFilter] = useState(searchParams.get('health') || 'all');
  const [verifiedOnly, setVerifiedOnly] = useState(searchParams.get('verified') === 'true');
  const [selectedTree, setSelectedTree] = useState<Tree | null>(null);

  // Map position from URL or defaults
  const initialCenter: [number, number] = [
    parseFloat(searchParams.get('lon') || String(CITY_LON)),
    parseFloat(searchParams.get('lat') || String(CITY_LAT)),
  ];
  const initialZoom = parseFloat(searchParams.get('zoom') || String(CITY_ZOOM));

  // Update URL when filters or map position change
  const updateUrl = useCallback((updates: { q?: string; health?: string; verified?: boolean; lon?: number; lat?: number; zoom?: number }) => {
    const params = new URLSearchParams(searchParams.toString());
    if (updates.q !== undefined) {
      if (updates.q) params.set('q', updates.q);
      else params.delete('q');
    }
    if (updates.health !== undefined) {
      if (updates.health !== 'all') params.set('health', updates.health);
      else params.delete('health');
    }
    if (updates.verified !== undefined) {
      if (updates.verified) params.set('verified', 'true');
      else params.delete('verified');
    }
    if (updates.lon !== undefined && updates.lat !== undefined) {
      params.set('lon', updates.lon.toFixed(4));
      params.set('lat', updates.lat.toFixed(4));
    }
    if (updates.zoom !== undefined) {
      params.set('zoom', updates.zoom.toFixed(1));
    }
    router.replace(`/?${params.toString()}`, { scroll: false });
  }, [searchParams, router]);

  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;

    // -------------------------------------------------------------------------
    // Register the PMTiles protocol ONCE per page so MapLibre can resolve
    // pmtiles:// URLs without any remote tile server.
    // -------------------------------------------------------------------------
    const pmtilesProtocol = new Protocol();
    maplibregl.addProtocol('pmtiles', pmtilesProtocol.tile);

    const map = new MapLibreMap({
      container: mapContainer.current,
      style: DEFAULT_STYLE,
      center: initialCenter,
      zoom: initialZoom,
      attributionControl: {
        customAttribution:
          '© OpenStreetMap contributors | MapLibre GL | OpenFreeMap',
      },
    });

    map.addControl(new NavigationControl({ showCompass: true }), 'top-right');
    map.addControl(
      new GeolocateControl({
        positionOptions: { enableHighAccuracy: true },
        trackUserLocation: true,
      }),
      'top-right',
    );

    // -------------------------------------------------------------------------
    // Add tree layer once the base style has loaded
    // -------------------------------------------------------------------------
    if (TREE_TILES_URL) {
      map.on('load', () => {
        // Source — PMTiles archive (served via range requests)
        map.addSource('trees', {
          type: 'vector',
          url: TREE_TILES_URL,
          attribution: 'Trees: ODbL © OpenStreetMap contributors / OGDL',
        });

        // ── Cluster circles (zoom < 14) ────────────────────────────────────
        map.addLayer({
          id: 'tree-clusters',
          type: 'circle',
          source: 'trees',
          'source-layer': 'trees',
          maxzoom: 14,
          filter: ['has', 'point_count'],
          paint: {
            'circle-color': [
              'step',
              ['get', 'point_count'],
              '#bbf7d0', // < 10
              10, '#4ade80', // 10–49
              50, '#16a34a', // 50–499
              500, '#15803d', // 500+
            ],
            'circle-radius': [
              'step',
              ['get', 'point_count'],
              12,
              10, 18,
              50, 24,
              500, 32,
            ],
            'circle-stroke-width': 1.5,
            'circle-stroke-color': '#fff',
            'circle-opacity': 0.85,
          },
        });

        // ── Cluster labels ─────────────────────────────────────────────────
        map.addLayer({
          id: 'tree-cluster-count',
          type: 'symbol',
          source: 'trees',
          'source-layer': 'trees',
          maxzoom: 14,
          filter: ['has', 'point_count'],
          layout: {
            'text-field': '{point_count_abbreviated}',
            'text-font': ['Noto Sans Regular'],
            'text-size': 11,
          },
          paint: { 'text-color': '#14532d' },
        });

        // ── Individual tree circles (zoom ≥ 14) ────────────────────────────
        map.addLayer({
          id: 'tree-points',
          type: 'circle',
          source: 'trees',
          'source-layer': 'trees',
          minzoom: 14,
          filter: ['!', ['has', 'point_count']],
          paint: {
            'circle-color': [
              'match',
              ['get', 'leaf_cycle'],
              'deciduous',      LEAF_CYCLE_COLOURS.deciduous,
              'evergreen',     LEAF_CYCLE_COLOURS.evergreen,
              'semi_evergreen', LEAF_CYCLE_COLOURS.semi_evergreen,
              'unknown',       LEAF_CYCLE_COLOURS.unknown,
              '#6b7280', // fallback gray-500
            ],
            'circle-radius': [
              'interpolate', ['linear'], ['zoom'],
              14, 4,
              18, 9,
            ],
            'circle-stroke-width': 1,
            'circle-stroke-color': '#fff',
            'circle-opacity': 0.9,
          },
        });

        // ── Hover cursor ───────────────────────────────────────────────────
        map.on('mouseenter', 'tree-points', () => {
          map.getCanvas().style.cursor = 'pointer';
        });
        map.on('mouseleave', 'tree-points', () => {
          map.getCanvas().style.cursor = '';
        });

        // ── Click to open side panel ────────────────────────────────────────
        map.on('click', 'tree-points', (e: MapMouseEvent & { features?: MapGeoJSONFeature[] }) => {
          const feature = e.features?.[0];
          if (!feature) return;
          const tree = feature.properties as Tree;
          setSelectedTree(tree);
        });

        // ── Update URL on map move (debounced) ────────────────────────────────
        let moveTimeout: NodeJS.Timeout;
        map.on('moveend', () => {
          clearTimeout(moveTimeout);
          moveTimeout = setTimeout(() => {
            const center = map.getCenter();
            const zoom = map.getZoom();
            updateUrl({ lon: center.lng, lat: center.lat, zoom });
          }, 500);
        });
      });
    }

    mapRef.current = map;

    return () => {
      maplibregl.removeProtocol('pmtiles');
      map.remove();
      mapRef.current = null;
    };
  }, []);

  const handleSearchChange = (q: string) => {
    setSearchQuery(q);
    updateUrl({ q });
  };

  const handleHealthChange = (h: string) => {
    setHealthFilter(h);
    updateUrl({ health: h });
  };

  const handleVerifiedToggle = () => {
    const newValue = !verifiedOnly;
    setVerifiedOnly(newValue);
    updateUrl({ verified: newValue });
  };

  const handleClosePanel = () => setSelectedTree(null);

  // Keyboard navigation handler
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!mapRef.current) return;
    const map = mapRef.current;

    switch (e.key) {
      case 'ArrowUp':
        map.panBy([0, -100]);
        e.preventDefault();
        break;
      case 'ArrowDown':
        map.panBy([0, 100]);
        e.preventDefault();
        break;
      case 'ArrowLeft':
        map.panBy([-100, 0]);
        e.preventDefault();
        break;
      case 'ArrowRight':
        map.panBy([100, 0]);
        e.preventDefault();
        break;
      case '+':
      case '=':
        map.zoomIn();
        e.preventDefault();
        break;
      case '-':
      case '_':
        map.zoomOut();
        e.preventDefault();
        break;
      case 'Escape':
        setSelectedTree(null);
        e.preventDefault();
        break;
    }
  }, []);

  return (
    <div className="relative w-full h-full">
      <div
        ref={mapContainer}
        className="w-full h-full"
        role="application"
        aria-label="Interactive tree map. Use arrow keys to pan, plus and minus to zoom, Escape to close panel."
        tabIndex={0}
        onKeyDown={handleKeyDown}
      />

      {/* Filters */}
      <TreeFilters
        searchQuery={searchQuery}
        onSearchChange={handleSearchChange}
        healthFilter={healthFilter}
        onHealthChange={handleHealthChange}
        verifiedOnly={verifiedOnly}
        onVerifiedToggle={handleVerifiedToggle}
      />

      {/* City Center Badge */}
      <div className="absolute top-4 left-4 right-4 sm:right-auto sm:w-auto z-10 bg-white/95 backdrop-blur-md px-4 py-2.5 rounded-xl shadow-md border border-gray-100 flex items-center gap-3 sm:mt-16">
        <div className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse" aria-hidden="true" />
        <div>
          <h1 className="text-sm font-bold text-gray-900 leading-tight">TreeMap</h1>
          <p className="text-xs text-gray-500 font-medium">
            Centred on {CITY_NAME} ({CITY_LAT.toFixed(4)}, {CITY_LON.toFixed(4)})
          </p>
        </div>
      </div>

      {/* Legend */}
      {TREE_TILES_URL && (
        <div className="absolute bottom-8 left-4 z-10 bg-white/95 backdrop-blur-md px-3 py-2 rounded-xl shadow-md border border-gray-100 text-xs text-gray-700 space-y-1" role="legend" aria-label="Tree leaf cycle legend">
          <p className="font-semibold text-gray-800 mb-1">Leaf cycle</p>
          <ul className="space-y-1" role="list">
            {Object.entries(LEAF_CYCLE_COLOURS).map(([cycle, colour]) => (
              <li key={cycle} className="flex items-center gap-2">
                <span
                  className="inline-block w-3 h-3 rounded-full border border-white/60"
                  style={{ backgroundColor: colour }}
                  aria-hidden="true"
                />
                <span className="capitalize">{cycle.replace('_', ' ')}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Tree Side Panel */}
      {selectedTree && (
        <TreeSidePanel tree={selectedTree} onClose={handleClosePanel} />
      )}
    </div>
  );
}
