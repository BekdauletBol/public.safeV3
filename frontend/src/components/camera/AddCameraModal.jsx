import { useState } from 'react'
import { X, Camera, MapPin, Link, Info } from 'lucide-react'
import { createCamera } from '../../services/api'
import toast from 'react-hot-toast'

export default function AddCameraModal({ onClose, onAdded }) {
  const [form, setForm] = useState({
    name: '',
    stream_url: '',
    address: '',
    description: '',
    fps: 15,
  })
  const [loading, setLoading] = useState(false)

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.name || !form.stream_url || !form.address) {
      toast.error('Name, stream URL and address are required')
      return
    }
    setLoading(true)
    try {
      const { data } = await createCamera(form)
      toast.success(`Camera "${data.name}" added (ID: ${data.id})`)
      onAdded(data)
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add camera')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)' }}
      onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="card w-full max-w-lg animate-fade-in" style={{ background: 'var(--bg-card)' }}>
        <div className="flex items-center justify-between px-5 py-4 border-b" style={{ borderColor: 'var(--border)' }}>
          <div className="flex items-center gap-2">
            <Camera size={16} style={{ color: 'var(--accent-cyan)' }} />
            <span className="font-display font-semibold">Add Camera</span>
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-white/5 transition-colors">
            <X size={18} style={{ color: 'var(--text-muted)' }} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 flex flex-col gap-4">
          <div>
            <label className="label"><Camera size={11} className="inline mr-1" />Camera Name</label>
            <input className="input-field" placeholder="e.g. Main Entrance" value={form.name} onChange={set('name')} />
          </div>

          <div>
            <label className="label"><Link size={11} className="inline mr-1" />Stream URL</label>
            <input className="input-field font-mono text-xs" placeholder="rtsp://192.168.1.100:554/stream" value={form.stream_url} onChange={set('stream_url')} />
            <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
              Supports: rtsp://, http://, 0 (local webcam), IP:port
            </p>
          </div>

          <div>
            <label className="label"><MapPin size={11} className="inline mr-1" />Physical Address / Location</label>
            <input className="input-field" placeholder="e.g. Dzerjinskoe 2a, Kazakhstan" value={form.address} onChange={set('address')} />
          </div>

          <div>
            <label className="label"><Info size={11} className="inline mr-1" />Description (optional)</label>
            <textarea className="input-field resize-none" rows={2} placeholder="Additional notes about this camera" value={form.description} onChange={set('description')} />
          </div>

          <div>
            <label className="label">Target FPS (inference)</label>
            <input type="number" min={1} max={30} className="input-field" value={form.fps} onChange={set('fps')} />
          </div>

          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onClose} className="btn-ghost flex-1">Cancel</button>
            <button type="submit" disabled={loading} className="btn-primary flex-1">
              {loading ? 'Adding...' : 'Add Camera'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
