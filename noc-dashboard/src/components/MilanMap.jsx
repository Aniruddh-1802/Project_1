/**
 * MilanMap
 * ─────────────────────────────────────────────────────────────────────────
 * Renders the Milan 100×100 grid with hotspot/alert status overlaid.
 *
 * Performance strategy (RE4):
 *   Only polygons that appear in the API hotspot/alert response are rendered
 *   as coloured GeoJSON layers. The remaining 10,000 cells are NOT drawn as
 *   SVG paths, which would make the page unresponsive.
 *
 * Join key: properties.cellId (1-based) → grid_id
 *   NOT the top-level GeoJSON feature id, which is 0-based.
 */
import { useEffect, useRef, useMemo, useCallback } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import styles from './MilanMap.module.css';

// Milan bounding box centre
const MILAN_CENTER = [45.464, 9.19];
const DEFAULT_ZOOM = 12;

// Status → fill colour mapping (must be distinguishable without colour alone)
function statusColor(level) {
  switch ((level || '').toUpperCase()) {
    case 'HIGH':      return '#f85149';
    case 'ATTENTION': return '#d29922';
    default:          return '#3fb950';
  }
}

function statusOpacity(level) {
  switch ((level || '').toUpperCase()) {
    case 'HIGH':      return 0.65;
    case 'ATTENTION': return 0.50;
    default:          return 0.30;
  }
}

/**
 * Build a lookup: cellId (int) → status level, from the combined
 * hotspot + alert lists.
 */
function buildStatusMap(hotspots, alerts) {
  const map = {};
  const order = { HIGH: 3, ATTENTION: 2, NORMAL: 1 };
  const update = (id, level) => {
    const current = map[id];
    if (!current || (order[level] || 0) > (order[current] || 0)) {
      map[id] = level;
    }
  };
  (hotspots || []).forEach(h => update(h.grid_id, h.status || h.severity || 'ATTENTION'));
  (alerts || []).forEach(a => update(a.grid_id, a.alert_type === 'HIGH_ACTIVITY' ? 'HIGH' : 'ATTENTION'));
  return map;
}

// Sub-component: fly to a selected grid's approximate position
function FlyToGrid({ gridId, geojson }) {
  const map = useMap();
  useEffect(() => {
    if (!gridId || !geojson) return;
    const feature = geojson.features.find(
      f => f.properties?.cellId === Number(gridId)
    );
    if (!feature) return;
    const coords = feature.geometry?.coordinates?.[0];
    if (!coords || coords.length === 0) return;
    const lats = coords.map(c => c[1]);
    const lngs = coords.map(c => c[0]);
    const lat = (Math.min(...lats) + Math.max(...lats)) / 2;
    const lng = (Math.min(...lngs) + Math.max(...lngs)) / 2;
    map.flyTo([lat, lng], 15, { duration: 0.8 });
  }, [gridId, geojson, map]);
  return null;
}

export default function MilanMap({
  geojson,         // full FeatureCollection (fetched once, passed as prop)
  hotspots = [],
  alerts = [],
  selectedGridId,
  onGridClick,
}) {
  const statusMap = useMemo(
    () => buildStatusMap(hotspots, alerts),
    [hotspots, alerts]
  );

  // Only include features that are present in statusMap (performance)
  const filteredGeojson = useMemo(() => {
    if (!geojson) return null;
    const activeIds = new Set(Object.keys(statusMap).map(Number));
    return {
      ...geojson,
      features: geojson.features.filter(
        f => activeIds.has(f.properties?.cellId)
      ),
    };
  }, [geojson, statusMap]);

  const onEachFeature = useCallback(
    (feature, layer) => {
      const id = feature.properties?.cellId;
      const level = statusMap[id] || 'NORMAL';

      layer.setStyle({
        fillColor:   statusColor(level),
        fillOpacity: statusOpacity(level),
        color:       statusColor(level),
        weight:      level === 'HIGH' ? 2 : 1,
        opacity:     0.8,
      });

      layer.bindTooltip(
        `Grid ${id} · ${level}`,
        { sticky: true, className: styles.tooltip }
      );

      layer.on('click', () => {
        if (onGridClick) onGridClick(id);
      });

      if (id === Number(selectedGridId)) {
        layer.setStyle({ weight: 3, color: '#58a6ff', fillOpacity: 0.8 });
      }
    },
    [statusMap, selectedGridId, onGridClick]
  );

  // Key forces remount when data changes so GeoJSON re-renders correctly
  const geojsonKey = useMemo(
    () => `${hotspots.length}-${alerts.length}-${selectedGridId}`,
    [hotspots.length, alerts.length, selectedGridId]
  );

  return (
    <div className={styles.mapWrap}>
      <MapContainer
        center={MILAN_CENTER}
        zoom={DEFAULT_ZOOM}
        className={styles.map}
        scrollWheelZoom
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>'
          subdomains="abcd"
          maxZoom={19}
        />

        {filteredGeojson && filteredGeojson.features.length > 0 && (
          <GeoJSON
            key={geojsonKey}
            data={filteredGeojson}
            onEachFeature={onEachFeature}
          />
        )}

        {selectedGridId && geojson && (
          <FlyToGrid gridId={selectedGridId} geojson={geojson} />
        )}
      </MapContainer>

      <div className={styles.legend}>
        <span className={styles.legendItem} data-level="HIGH">      ■ High</span>
        <span className={styles.legendItem} data-level="ATTENTION"> ■ Attention</span>
        <span className={styles.legendItem} data-level="NORMAL">    ■ Normal</span>
      </div>
    </div>
  );
}
