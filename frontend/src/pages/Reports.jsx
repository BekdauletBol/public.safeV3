import { useEffect, useState, useCallback } from 'react'
import { FileText, Download, RefreshCw, Clock, CheckCircle, AlertCircle, Loader } from 'lucide-react'
import { getReports, generateReport } from '../services/api'
import { format, parseISO } from 'date-fns'
import toast from 'react-hot-toast'

const mono = { fontFamily: "'JetBrains Mono', monospace" }

// Helper for status colors
const STATUS_THEMES = {
  ready: { color: '#00ff9d', icon: CheckCircle },
  failed: { color: '#ff3d6b', icon: AlertCircle },
  pending: { color: '#ffb830', icon: Loader }
}

const StatusIcon = ({ status }) => {
  const theme = STATUS_THEMES[status] || STATUS_THEMES.pending
  const Icon = theme.icon
  return <Icon size={11} className={status !== 'ready' && status !== 'failed' ? "animate-spin" : ""} style={{ color: theme.color }} />
}

export default function Reports() {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)

  const fetchReports = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await getReports()
      setReports(Array.isArray(data) ? data : [])
    } catch (err) {
      toast.error('Failed to load reports')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchReports() }, [fetchReports])

  const handleGenerate = async () => {
    if (generating) return
    setGenerating(true)
    try {
      await generateReport()
      toast.success('Report generation started')
      fetchReports()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Report generation failed')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div
      className="p-6 flex flex-col gap-6 min-h-screen"
      style={{
        ...mono,
        backgroundColor: '#0a0a0a', // Ensuring dark background for the grid
        backgroundImage: `
          linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px)
        `,
        backgroundSize: '40px 40px',
      }}
    >
      {/* Header Section */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 style={{ fontWeight: 300, fontSize: 22, color: '#fff', letterSpacing: '-0.01em' }}>
            reports<span style={{ color: '#00d4ff' }}>.</span>
          </h1>
          <p style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)', marginTop: 6, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            auto-generated every sunday at 23:59 · pdf & csv
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={fetchReports}
            className="hover:opacity-80 transition-all"
            style={{
              ...mono, fontSize: 11, cursor: 'pointer',
              background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: '3px', color: 'rgba(255,255,255,0.5)', padding: '7px 12px',
              display: 'flex', alignItems: 'center', gap: 6, letterSpacing: '0.04em',
            }}
          >
            <RefreshCw size={11} className={loading ? "animate-spin" : ""} /> refresh
          </button>

          <button
            onClick={handleGenerate}
            disabled={generating}
            style={{
              ...mono, fontSize: 11, cursor: generating ? 'not-allowed' : 'pointer',
              opacity: generating ? 0.6 : 1,
              background: 'transparent', border: '1px solid rgba(0,212,255,0.35)',
              borderRadius: '3px', color: '#00d4ff', padding: '7px 12px',
              display: 'flex', alignItems: 'center', gap: 6,
              letterSpacing: '0.04em', transition: 'all 0.2s',
            }}
          >
            {generating ? <Loader size={11} className="animate-spin" /> : <FileText size={11} />}
            {generating ? 'generating...' : 'generate now'}
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      {loading && reports.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-32 gap-3">
          <Loader size={20} className="animate-spin" style={{ color: '#00d4ff' }} />
          <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.2)' }}>ACCESSING ARCHIVES...</span>
        </div>
      ) : reports.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-32 gap-5 border border-dashed border-white/5 rounded-lg">
          <FileText size={32} style={{ color: 'rgba(255,255,255,0.05)' }} />
          <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.25)', letterSpacing: '0.08em' }}>NO REPORTS FOUND</p>
          <button
            onClick={handleGenerate}
            className="hover:bg-cyan-500/10 transition-colors"
            style={{
              ...mono, fontSize: 11, cursor: 'pointer',
              background: 'transparent', border: '1px solid rgba(0,212,255,0.35)',
              borderRadius: '3px', color: '#00d4ff', padding: '8px 16px',
              letterSpacing: '0.04em',
            }}
          >
            → initialize first sequence
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {reports.map((r) => (
            <div
              key={r.id}
              className="hover:bg-white/[0.04] transition-colors group"
              style={{
                background: 'rgba(255,255,255,0.02)',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: '3px',
                padding: '16px',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                gap: 16, flexWrap: 'wrap',
              }}
            >
              <div className="flex items-center gap-4">
                <div style={{
                  width: 36, height: 36, borderRadius: '3px', flexShrink: 0,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: 'rgba(0,212,255,0.05)', border: '1px solid rgba(0,212,255,0.12)',
                }}>
                  <FileText size={14} style={{ color: '#00d4ff' }} />
                </div>
                <div>
                  <div style={{ fontSize: 13, color: '#fff', letterSpacing: '0.01em' }}>{r.title}</div>
                  <div className="flex flex-col gap-1 mt-1">
                    <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', display: 'flex', alignItems: 'center', gap: 5 }}>
                      <Clock size={9} />
                      {r.period_start ? format(parseISO(r.period_start), 'MMM d') : 'n/a'}
                      {' – '}
                      {r.period_end ? format(parseISO(r.period_end), 'MMM d, yyyy') : 'n/a'}
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-6">
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, color: 'rgba(255,255,255,0.4)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                  <StatusIcon status={r.status} />
                  {r.status}
                </div>

                {r.status === 'ready' && r.download_url && (
                  <a
                    href={r.download_url}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      ...mono, fontSize: 10, textDecoration: 'none',
                      background: 'rgba(0,212,255,0.05)', border: '1px solid rgba(0,212,255,0.3)',
                      borderRadius: '2px', color: '#00d4ff', padding: '6px 12px',
                      display: 'flex', alignItems: 'center', gap: 6,
                      letterSpacing: '0.05em', transition: 'all 0.2s'
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,212,255,0.15)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'rgba(0,212,255,0.05)'}
                  >
                    <Download size={10} /> PDF
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}