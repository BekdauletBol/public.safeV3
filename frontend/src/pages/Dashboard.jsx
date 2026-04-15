import { useEffect, useState } from 'react'
import { Plus, Users, Camera, Activity, AlertTriangle } from 'lucide-react'
import { getCameras, deleteCamera } from '../services/api'
import { useCameraStore } from '../store'
import CameraCard from '../components/camera/CameraCard'
import AddCameraModal from '../components/camera/AddCameraModal'
import toast from 'react-hot-toast'

const mono = { fontFamily: "'JetBrains Mono', monospace" }

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div style={{
      ...mono,
      background: 'rgba(255,255,255,0.02)',
      border: '1px solid rgba(255,255,255,0.06)',
      borderRadius: '3px',
      padding: '16px 18px',
      display: 'flex',
      alignItems: 'center',
      gap: 14,
    }}>
      <div style={{
        width: 34, height: 34, borderRadius: '3px', flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: `${color}09`, border: `1px solid ${color}22`,
      }}>
        <Icon size={14} style={{ color }} />
      </div>
      <div>
        <div style={{ fontSize: 24, fontWeight: 300, color: '#fff', lineHeight: 1, letterSpacing: '-0.02em' }}>{value}</div>
        <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)', marginTop: 5, letterSpacing: '0.1em' }}>{label}</div>
      </div>
    </div>
  )
}

function getGridCols(count) {
  if (count === 1) return 'grid-cols-1'
  if (count === 2) return 'grid-cols-2'
  if (count <= 4) return 'grid-cols-2 xl:grid-cols-2'
  if (count <= 6) return 'grid-cols-2 xl:grid-cols-3'
  return 'grid-cols-2 xl:grid-cols-4'
}

export default function Dashboard() {
  const { cameras, setCameras, addCamera, removeCamera, liveCounts } = useCameraStore()
  const [showAdd, setShowAdd] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getCameras()
      .then(({ data }) => setCameras(data))
      .catch(() => toast.error('Failed to load cameras'))
      .finally(() => setLoading(false))
  }, [])

  const handleDelete = async (id) => {
    if (!confirm('Remove this camera?')) return
    try {
      await deleteCamera(id)
      removeCamera(id)
      toast.success('Camera removed')
    } catch {
      toast.error('Failed to remove camera')
    }
  }

  const handleAdded = (camera) => addCamera(camera)

  const totalPeople = Object.values(liveCounts).reduce((a, b) => a + b, 0)
  const activeCams = cameras.filter((c) => c.is_active).length
  const connectedCams = cameras.filter((c) => c.is_connected).length

  return (
    <div
      className="p-6 flex flex-col gap-6 min-h-full"
      style={{
        ...mono,
        backgroundImage: `
          linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px)
        `,
        backgroundSize: '40px 40px',
      }}
    >
      <div className="flex items-start justify-between">
        <div>
          <h1 style={{ fontWeight: 300, fontSize: 22, color: '#fff', letterSpacing: '-0.01em' }}>
            surveillance dashboard<span style={{ color: '#00d4ff' }}>.</span>
          </h1>
          <p style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)', marginTop: 6, letterSpacing: '0.1em' }}>
            real-time monitoring · {cameras.length} camera{cameras.length !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          style={{
            ...mono, fontSize: 11, cursor: 'pointer',
            background: 'transparent', border: '1px solid rgba(0,212,255,0.35)',
            borderRadius: '3px', color: '#00d4ff', padding: '8px 14px',
            display: 'flex', alignItems: 'center', gap: 6,
            letterSpacing: '0.04em', transition: 'all 0.15s',
          }}
          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(0,212,255,0.07)'; e.currentTarget.style.borderColor = 'rgba(0,212,255,0.6)' }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'rgba(0,212,255,0.35)' }}
        >
          <Plus size={12} /> add camera
        </button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard icon={Users} label="people right now" value={totalPeople} color="#00d4ff" />
        <StatCard icon={Camera} label="total cameras" value={cameras.length} color="#00ff9d" />
        <StatCard icon={Activity} label="active streams" value={activeCams} color="#ffb830" />
        <StatCard icon={AlertTriangle} label="disconnected" value={cameras.length - connectedCams} color="#ff3d6b" />
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="w-5 h-5 rounded-full border mx-auto mb-4"
              style={{ borderColor: 'rgba(0,212,255,0.2)', borderTopColor: '#00d4ff', animation: 'spin 1s linear infinite' }} />
            <p style={{ fontSize: 10, color: 'rgba(255,255,255,0.2)', letterSpacing: '0.1em' }}>loading cameras...</p>
          </div>
        </div>
      ) : cameras.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Camera size={32} style={{ color: 'rgba(255,255,255,0.08)', margin: '0 auto 16px' }} />
            <h3 style={{ fontSize: 13, fontWeight: 300, color: 'rgba(255,255,255,0.3)', marginBottom: 6 }}>no cameras configured</h3>
            <p style={{ fontSize: 10, color: 'rgba(255,255,255,0.15)', marginBottom: 20, letterSpacing: '0.06em' }}>
              add your first camera to start monitoring
            </p>
            <button
              onClick={() => setShowAdd(true)}
              style={{
                ...mono, fontSize: 11, cursor: 'pointer',
                background: 'transparent', border: '1px solid rgba(0,212,255,0.35)',
                borderRadius: '3px', color: '#00d4ff', padding: '8px 14px',
                letterSpacing: '0.04em',
              }}
            >
              → add camera
            </button>
          </div>
        </div>
      ) : (
        <div className={`grid gap-4 ${getGridCols(cameras.length)}`}>
          {cameras.map((cam) => (
            <CameraCard
              key={cam.id}
              camera={cam}
              count={liveCounts[cam.id] ?? cam.current_count ?? 0}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {showAdd && (
        <AddCameraModal onClose={() => setShowAdd(false)} onAdded={handleAdded} />
      )}
    </div>
  )
}