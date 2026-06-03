import React, { useState } from 'react';
import { MousePointer2, Save, Trash2 } from 'lucide-react';

interface ZoneEditorProps {
  node_id: string | null;
}

const ZoneEditor: React.FC<ZoneEditorProps> = ({ node_id }) => {
  const [points, setPoints] = useState<[number, number][]>([]);

  const handleSave = async () => {
    if (!node_id) return;
    await fetch(`http://${window.location.hostname}:8000/api/zones/${node_id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ node_id, polygon: points })
    });
    alert('Zone configuration saved.');
  };

  return (
    <div className="absolute bottom-6 right-6 flex flex-col gap-2">
      <div className="bg-white/90 backdrop-blur shadow-xl border border-gray-200 rounded-lg p-2 flex flex-col gap-2">
        <button 
          className="p-2 hover:bg-gray-100 rounded text-gray-600 transition-colors"
          title="Draw Polygon"
        >
          <MousePointer2 size={18} />
        </button>
        <button 
          onClick={() => setPoints([])}
          className="p-2 hover:bg-red-50 rounded text-red-500 transition-colors"
          title="Clear Points"
        >
          <Trash2 size={18} />
        </button>
        <div className="h-px bg-gray-200 mx-1"></div>
        <button 
          onClick={handleSave}
          className="p-2 hover:bg-[#ff6600] hover:text-white rounded text-[#ff6600] transition-colors"
          title="Save Zone"
        >
          <Save size={18} />
        </button>
      </div>
    </div>
  );
};

export default ZoneEditor;
