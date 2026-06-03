import React from 'react';

interface NodeMapProps {
  onNodeSelect: (id: string) => void;
}

const NodeMap: React.FC<NodeMapProps> = ({ onNodeSelect }) => {
  return (
    <div className="w-full h-full bg-[#f0f2f5] relative flex items-center justify-center">
      {/* Placeholder for Leaflet/Actual Map */}
      <div className="text-gray-400 text-xs font-medium uppercase tracking-widest text-center">
        City Grid Topology Visualization<br/>
        <span className="text-[10px] font-normal lowercase opacity-50">Interactive Map Layer (Leaflet)</span>
      </div>
      
      {/* Mock Node Pins */}
      <button 
        onClick={() => onNodeSelect('node_01')}
        className="absolute top-1/4 left-1/3 w-4 h-4 bg-[#ff6600] rounded-full border-2 border-white shadow-md animate-pulse cursor-pointer"
      ></button>
      <button 
        onClick={() => onNodeSelect('node_02')}
        className="absolute top-1/2 right-1/4 w-4 h-4 bg-green-500 rounded-full border-2 border-white shadow-md cursor-pointer"
      ></button>
    </div>
  );
};

export default NodeMap;
