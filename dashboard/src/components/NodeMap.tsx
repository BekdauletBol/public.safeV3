import React from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default marker icons in react-leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

interface NodeMapProps {
  onNodeSelect: (id: string) => void;
}

const NodeMap: React.FC<NodeMapProps> = ({ onNodeSelect }) => {
  // Center on Almaty, Kazakhstan
  const position: [number, number] = [43.238949, 76.889709];

  // Custom icon for nodes
  const nodeIcon = (color: string) => L.divIcon({
    className: 'custom-icon',
    html: `<div style="background-color: ${color}; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8]
  });

  return (
    <div className="w-full h-full bg-[#FAFAFA] relative z-0">
      <MapContainer center={position} zoom={13} style={{ height: '100%', width: '100%', zIndex: 0 }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        {/* Mock Nodes */}
        <Marker position={[43.238949, 76.889709]} icon={nodeIcon('#FF6600')} eventHandlers={{ click: () => onNodeSelect('node_01') }}>
          <Popup>
            <div className="font-semibold text-[#1C1B1A]">node_01</div>
            <div className="text-xs text-red-500">Threat Detected</div>
          </Popup>
        </Marker>
        
        <Marker position={[43.248949, 76.899709]} icon={nodeIcon('#22c55e')} eventHandlers={{ click: () => onNodeSelect('node_02') }}>
          <Popup>
            <div className="font-semibold text-[#1C1B1A]">node_02</div>
            <div className="text-xs text-green-600">Secure</div>
          </Popup>
        </Marker>
      </MapContainer>
    </div>
  );
};

export default NodeMap;
