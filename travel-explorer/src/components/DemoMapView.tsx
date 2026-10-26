import { useEffect, useMemo } from 'react';
import L from 'leaflet';
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { CATEGORY_BY_ID } from '../categories';
import type { CategoryId, FlyTo, LatLng, Level, MapViewProps } from '../types';

// Leaflet + OpenStreetMap map used in demo mode, so the app is usable without a Google key.

function pinIcon(category: CategoryId, selected: boolean, level?: Level) {
  const cat = CATEGORY_BY_ID[category];
  const badge = level ? `<span class="pin-lvl lvl--${level}">${level}</span>` : '';
  return L.divIcon({
    className: '',
    html: `<div class="pin${selected ? ' pin--selected' : ''}" style="background:${cat.color}">${cat.emoji}${badge}</div>`,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
  });
}

const meIcon = L.divIcon({ className: '', html: '<div class="me-dot"></div>', iconSize: [16, 16], iconAnchor: [8, 8] });

function MapBridge({ flyTo, onCenterChange }: { flyTo?: FlyTo; onCenterChange(c: LatLng): void }) {
  const map = useMap();
  useMapEvents({ moveend: () => onCenterChange(map.getCenter()) });
  useEffect(() => {
    if (flyTo) map.flyTo(flyTo.center, flyTo.zoom ?? map.getZoom());
  }, [map, flyTo]);
  return null;
}

export function DemoMapView({
  initialCenter,
  flyTo,
  places,
  selectedId,
  userLocation,
  onSelect,
  onCenterChange,
}: MapViewProps) {
  const icons = useMemo(() => new Map<string, L.DivIcon>(), []);
  const iconFor = (c: CategoryId, sel: boolean, level?: Level) => {
    const key = `${c}-${sel}-${level}`;
    if (!icons.has(key)) icons.set(key, pinIcon(c, sel, level));
    return icons.get(key)!;
  };

  return (
    <MapContainer center={initialCenter} zoom={14} style={{ width: '100%', height: '100%' }}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <MapBridge flyTo={flyTo} onCenterChange={onCenterChange} />
      {userLocation && <Marker position={userLocation} icon={meIcon} interactive={false} />}
      {places.map((p) => (
        <Marker
          key={p.id}
          position={p.location}
          icon={iconFor(p.category, p.id === selectedId, p.ranking?.level)}
          zIndexOffset={p.id === selectedId ? 1000 : 0}
          title={p.name}
          eventHandlers={{ click: () => onSelect(p.id) }}
        />
      ))}
    </MapContainer>
  );
}
