import React from 'react';

const AlertFeed: React.FC = () => {
  // Mock alerts for initial UI, will be populated via WebSocket in App.tsx later
  const alerts = [
    { id: 1, time: '14:20:05', node: 'node_01', type: 'PREDICTED', score: 0.75, ttc: '1.8s' },
    { id: 2, time: '14:19:58', node: 'node_04', type: 'CURRENT', score: 0.92, ttc: '0.0s' },
    { id: 3, time: '14:18:12', node: 'node_01', type: 'MAP_ACTIVATE', score: 0.20, ttc: 'N/A' },
  ];

  return (
    <div className="flex-1 overflow-y-auto">
      {alerts.map((alert) => (
        <div key={alert.id} className="p-4 border-b border-gray-50 hover:bg-gray-50 transition-colors">
          <div className="flex justify-between items-start mb-2">
            <span className="text-[10px] font-mono text-gray-400">{alert.time}</span>
            <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
              alert.type === 'CURRENT' ? 'bg-red-100 text-red-700' : 
              alert.type === 'PREDICTED' ? 'bg-yellow-100 text-yellow-700' : 'bg-blue-100 text-blue-700'
            }`}>
              {alert.type}
            </span>
          </div>
          <div className="flex justify-between items-center">
             <div>
               <p className="text-xs font-bold text-gray-700">{alert.node}</p>
               <p className="text-[10px] text-gray-400">Threat Propagated to neighbors</p>
             </div>
             <div className="text-right">
                <p className="text-xs font-black text-gray-800">{Math.round(alert.score * 100)}%</p>
                <p className="text-[9px] text-gray-400">TTC: {alert.ttc}</p>
             </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default AlertFeed;
