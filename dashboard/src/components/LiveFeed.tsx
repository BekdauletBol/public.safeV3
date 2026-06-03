import React, { useEffect, useRef, useState } from 'react';

interface LiveFeedProps {
  node_id: string | null;
  onThreatUpdate: (score: number) => void;
}

const LiveFeed: React.FC<LiveFeedProps> = ({ node_id, onThreatUpdate }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);

  useEffect(() => {
    const socket = new WebSocket(`ws://${window.location.hostname}:8000/ws/dashboard`);
    
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'FRAME_UPDATE' && (!node_id || data.node_id === node_id)) {
        const img = new Image();
        img.onload = () => {
          const ctx = canvasRef.current?.getContext('2d');
          if (ctx && canvasRef.current) {
            canvasRef.current.width = img.width;
            canvasRef.current.height = img.height;
            ctx.drawImage(img, 0, 0);
          }
        };
        img.src = `data:image/jpeg;base64,${data.frame}`;
        onThreatUpdate(data.max_threat);
      }
    };

    setWs(socket);
    return () => socket.close();
  }, [node_id]);

  return (
    <div className="w-full h-full flex items-center justify-center bg-gray-900">
      {!node_id && (
        <div className="text-gray-500 text-sm font-medium animate-pulse">
          AWAITING NODE CONNECTION...
        </div>
      )}
      <canvas ref={canvasRef} className="max-w-full max-h-full" />
    </div>
  );
};

export default LiveFeed;
