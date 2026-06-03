import React, { useState, useEffect, useRef } from 'react';
import LiveFeed from './components/LiveFeed';
import ThreatMeter from './components/ThreatMeter';
import NodeMap from './components/NodeMap';
import AlertFeed from './components/AlertFeed';
import ZoneEditor from './components/ZoneEditor';
import { Settings, Shield, Activity, Map as MapIcon, Bell } from 'lucide-react';

const App: React.FC = () => {
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [maxThreat, setMaxThreat] = useState(0);
  const [activeTab, setActiveTab] = useState('live');

  return (
    <div className="min-h-screen bg-[#FAF9F6] text-[#1C1B1A] font-['Inter']">
      {/* Navigation */}
      <nav className="border-b border-gray-200 bg-white px-6 py-4 flex items-center justify-between sticky top-0 z-50 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="bg-[#FF6600] p-1.5 rounded-md shadow-sm">
            <Shield size={20} className="text-white" />
          </div>
          <h1 className="text-lg font-bold tracking-tight text-[#1C1B1A]">public.safe <span className="text-gray-400 font-normal">v3.0</span></h1>
        </div>
        <div className="flex gap-8 text-sm font-medium text-gray-500">
          <button onClick={() => setActiveTab('live')} className={`hover:text-[#FF6600] transition-colors pb-1 border-b-2 ${activeTab === 'live' ? 'text-[#FF6600] border-[#FF6600]' : 'border-transparent'}`}>Live Feed</button>
          <button onClick={() => setActiveTab('analytics')} className={`hover:text-[#FF6600] transition-colors pb-1 border-b-2 ${activeTab === 'analytics' ? 'text-[#FF6600] border-[#FF6600]' : 'border-transparent'}`}>Analytics</button>
          <button onClick={() => setActiveTab('map')} className={`hover:text-[#FF6600] transition-colors pb-1 border-b-2 ${activeTab === 'map' ? 'text-[#FF6600] border-[#FF6600]' : 'border-transparent'}`}>City Map</button>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-green-50 px-3 py-1 rounded-full border border-green-100">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-xs font-semibold text-green-700">Network Active</span>
          </div>
          <Settings size={18} className="text-gray-400 cursor-pointer hover:text-gray-600" />
        </div>
      </nav>

      <main className="max-w-[1600px] mx-auto p-6">
        {activeTab === 'live' && (
          <div className="grid grid-cols-12 gap-6">
            {/* Left Column: Feeds & Map */}
            <div className="col-span-8 space-y-6">
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-100 flex justify-between items-center bg-[#FAFAFA]">
                  <div className="flex items-center gap-2">
                    <Activity size={16} className="text-[#FF6600]" />
                    <h2 className="font-semibold text-sm uppercase tracking-wider text-gray-600">Real-time Node Surveillance</h2>
                  </div>
                  <span className="text-xs font-mono text-gray-400">{activeNode || 'SELECT A NODE'}</span>
                </div>
                <div className="aspect-video bg-[#1C1B1A] relative">
                   <LiveFeed node_id={activeNode} onThreatUpdate={setMaxThreat} />
                </div>
              </div>
              
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm h-[400px] overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2 bg-[#FAFAFA]">
                  <MapIcon size={16} className="text-[#FF6600]" />
                  <h2 className="font-semibold text-sm uppercase tracking-wider text-gray-600">City Mesh Topology</h2>
                </div>
                <NodeMap onNodeSelect={setActiveNode} />
              </div>
            </div>

            {/* Right Column: Alerts & Scoring */}
            <div className="col-span-4 space-y-6">
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
                 <ThreatMeter score={maxThreat} />
              </div>

              <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden flex flex-col h-[600px]">
                <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between bg-[#FAFAFA]">
                  <div className="flex items-center gap-2">
                    <Bell size={16} className="text-red-500" />
                    <h2 className="font-semibold text-sm uppercase tracking-wider text-gray-600">Alert Propagation Log</h2>
                  </div>
                  <span className="bg-red-50 text-red-600 text-[10px] font-bold px-1.5 py-0.5 rounded">LIVE</span>
                </div>
                <AlertFeed />
              </div>
            </div>
          </div>
        )}

        {activeTab === 'analytics' && (
          <div className="grid grid-cols-12 gap-6">
            <div className="col-span-6">
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 h-[400px]">
                 <h2 className="font-semibold text-sm uppercase tracking-wider text-gray-600 mb-4">Global Threat Level</h2>
                 <ThreatMeter score={maxThreat} />
              </div>
            </div>
            <div className="col-span-6">
              <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 h-[400px] flex items-center justify-center">
                 <p className="text-gray-400">Detailed analytics visualization coming soon...</p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'map' && (
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm h-[800px] overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2 bg-[#FAFAFA]">
              <MapIcon size={16} className="text-[#FF6600]" />
              <h2 className="font-semibold text-sm uppercase tracking-wider text-gray-600">Full City Mesh Topology</h2>
            </div>
            <NodeMap onNodeSelect={setActiveNode} />
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
