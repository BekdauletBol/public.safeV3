import React from 'react';

interface ThreatMeterProps {
  score: number;
}

const ThreatMeter: React.FC<ThreatMeterProps> = ({ score }) => {
  const percentage = Math.round(score * 100);
  
  let color = 'text-green-500';
  let bgColor = 'bg-green-500';
  let label = 'SECURE';

  if (score >= 0.9) {
    color = 'text-red-600';
    bgColor = 'bg-red-600';
    label = 'CRITICAL';
  } else if (score >= 0.7) {
    color = 'text-orange-500';
    bgColor = 'bg-orange-500';
    label = 'DANGER';
  } else if (score >= 0.3) {
    color = 'text-yellow-500';
    bgColor = 'bg-yellow-500';
    label = 'WARNING';
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-end">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-widest text-gray-400 mb-1">Predictive Threat Score</h3>
          <p className={`text-4xl font-black ${color}`}>{percentage}%</p>
        </div>
        <div className={`px-3 py-1 rounded text-[10px] font-black tracking-tighter border ${color.replace('text', 'border')} ${color.replace('text', 'bg').replace('500', '50').replace('600', '50')}`}>
          {label}
        </div>
      </div>
      
      <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden">
        <div 
          className={`h-full transition-all duration-500 ${bgColor}`} 
          style={{ width: `${percentage}%` }}
        ></div>
      </div>
      
      <p className="text-[11px] text-gray-400 leading-tight">
        * Based on real-time pedestrian velocity vectors and Time-To-Collision (TTC) probabilistic assessment.
      </p>
    </div>
  );
};

export default ThreatMeter;
