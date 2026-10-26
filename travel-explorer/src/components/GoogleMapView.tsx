import { useEffect } from 'react';
import { AdvancedMarker, Map, useMap } from '@vis.gl/react-google-maps';
import { CATEGORY_BY_ID } from '../categories';
import type { MapViewProps } from '../types';

// DEMO_MAP_ID is Google's development Map ID; set your own for production styling.
const MAP_ID = import.meta.env.VITE_GOOGLE_MAP_ID || 'DEMO_MAP_ID';

export function GoogleMapView({
  initialCenter,
  flyTo,
  places,
  selectedId,
  userLocation,
  onSelect,
  onCenterChange,
}: MapViewProps) {
  const map = useMap();

  useEffect(() => {
    if (!map || !flyTo) return;
    map.panTo(flyTo.center);
    if (flyTo.zoom) map.setZoom(flyTo.zoom);
  }, [map, flyTo]);

  return (
    <Map
      mapId={MAP_ID}
      defaultCenter={initialCenter}
      defaultZoom={14}
      gestureHandling="greedy"
      clickableIcons={false}
      streetViewControl={false}
      mapTypeControl={false}
      onIdle={(e) => {
        const c = e.map.getCenter();
        if (c) onCenterChange(c.toJSON());
      }}
      style={{ width: '100%', height: '100%' }}
    >
      {userLocation && (
        <AdvancedMarker position={userLocation} zIndex={1}>
          <div className="me-dot" />
        </AdvancedMarker>
      )}
      {places.map((p) => {
        const cat = CATEGORY_BY_ID[p.category];
        const selected = p.id === selectedId;
        return (
          <AdvancedMarker
            key={p.id}
            position={p.location}
            title={p.name}
            zIndex={selected ? 1000 : 10}
            onClick={() => onSelect(p.id)}
          >
            <div className={selected ? 'pin pin--selected' : 'pin'} style={{ background: cat.color }}>
              {cat.emoji}
            </div>
          </AdvancedMarker>
        );
      })}
    </Map>
  );
}
