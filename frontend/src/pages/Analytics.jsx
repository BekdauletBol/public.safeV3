import { useEffect, useState, useRef } from 'react'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend
} from 'recharts'
import { Download, TrendingUp, Clock, BarChart2 } from 'lucide-react'
import { getCameras, getCameraHourly, getCameraDaily, getCameraPeaks } from '../services/api'
import { format, parseISO } from 'date-fns'
import toast from 'react-hot-toast'

const mono = { fontFamily: "'JetBrains Mono', monospace" }

const card = {
  background: 'rgba(255,255,255,0.02)',
  border: '1px solid rgba(255,255,255,0.06)',
  borderRadius: '3px',
  padding: '20px',
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ ...mono, ...card, fontSize: 10, padding: '10px 14px' }}>
      <p style={{ color: 'rgba(255,255,255,0.3)', marginBottom: 6, letterSpacing: '0.06em' }}>{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color, letterSpacing: '0.04em' }}>
          {p.name}: <span style={{ fontWeight: 500 }}>{p.value}</span>
        </p>
      ))}
    </div>
  )
}

const selectStyle = {
  ...mono, fontSize: 11, cursor: 'pointer',
  background: 'rgba(255,255,255,0.03)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: '3px', color: 'rgba(255,255,255,0.7)',
  padding: '7px 10px', outline: 'none',
  letterSpacing: '0.04em',
}

const ghostBtn = {
  ...mono, fontSize: 11, cursor: 'pointer',
  background: 'transparent',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: '3px', color: 'rgba(255,255,255,0.3)',
  padding: '7px 10px', display: 'flex', alignItems: 'center', gap: 5,
  letterSpacing: '0.04em',
}

function exportCSV(data, filename) {
  if (!data.length) return
  const keys = Object.keys(data[0])
  const csv = [keys.join(','), ...data.map((row) => keys.map((k) => row[k]).join(','))].join('\n')
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }))
  a.download = filename
  a.click()
}

export default function Analytics() {
  const [cameras, setCameras] = useState([])
  const [selected, setSelected] = useState(null)
  const [hourlyData, setHourlyData] = useState([])
  const [dailyData, setDailyData] = useState([])
  const [peaks, setPeaks] = useState([])
  const [hours, setHours] = useState(24)
  const [loading, setLoading] = useState(false)
  const chartRef = useRef(null)

  useEffect(() => {
    getCameras().then(({ data }) => {
      setCameras(data)
      if (data.length) setSelected(data[0].id)
    })
  }, [])

  useEffect(() => {
    if (!selected) return
    setLoading(true)
    Promise.all([
      getCameraHourly(selected, hours),
      getCameraDaily(selected, 7),
      getCameraPeaks(selected),
    ])
      .then(([h, d, p]) => {
        setHourlyData((h.data.hourly || []).map((r) => ({
          time: r.hour ? format(parseISO(r.hour), 'HH:mm') : '',
          avg: r.avg, max: r.max, total: r.total,
        })))
        setDailyData((d.data.daily || []).map((r) => ({ date: r.date, total: r.total, avg: r.avg })))
        setPeaks((p.data.distribution || []).map((r) => ({ hour: `${r.hour}h`, avg: r.avg })))
      })
      .catch(() => toast.error('Failed to load analytics'))
      .finally(() => setLoading(false))
  }, [selected, hours])

  const exportPNG = () => {
    if (!chartRef.current) return
    import('html2canvas').then(({ default: html2canvas }) => {
      html2canvas(chartRef.current).then((canvas) => {
        const a = document.createElement('a')
        a.href = canvas.toDataURL('image/png')
        a.download = `analytics_camera${selected}.png`
        a.click()
      })
    })
  }

  return (
    <div
      className="p-6 flex flex-col gap-6"
      style={{
        ...mono,
        backgroundImage: `
          linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px)
        `,
        backgroundSize: '40px 40px',
      }}
    >
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 style={{ fontWeight: 300, fontSize: 22, color: '#fff', letterSpacing: '-0.01em' }}>
            analytics<span style={{ color: '#00d4ff' }}>.</span>
          </h1>
          <p style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)', marginTop: 6, letterSpacing: '0.1em' }}>
            traffic patterns & trends
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <select style={selectStyle} value={selected || ''} onChange={(e) => setSelected(Number(e.target.value))}>
            {cameras.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <select style={selectStyle} value={hours} onChange={(e) => setHours(Number(e.target.value))}>
            <option value={6}>last 6h</option>
            <option value={24}>last 24h</option>
            <option value={48}>last 48h</option>
            <option value={168}>last 7 days</option>
          </select>
          <button style={ghostBtn} onClick={() => exportCSV(hourlyData, `hourly_cam${selected}.csv`)}>
            <Download size={11} /> csv
          </button>
          <button style={ghostBtn} onClick={exportPNG}>
            <Download size={11} /> png
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center py-24">
          <div className="w-5 h-5 rounded-full border"
            style={{ borderColor: 'rgba(0,212,255,0.2)', borderTopColor: '#00d4ff', animation: 'spin 1s linear infinite' }} />
        </div>
      ) : (
        <div ref={chartRef} className="flex flex-col gap-5">
          <div style={card}>
            <div className="flex items-center gap-2 mb-5">
              <TrendingUp size={12} style={{ color: '#00d4ff' }} />
              <span style={{ fontSize: 10, letterSpacing: '0.1em', color: 'rgba(255,255,255,0.35)' }}>hourly traffic</span>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={hourlyData} margin={{ left: -10, right: 10 }}>
                <defs>
                  <linearGradient id="gAvg" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00d4ff" stopOpacity={0.12} />
                    <stop offset="95%" stopColor="#00d4ff" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gMax" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00ff9d" stopOpacity={0.08} />
                    <stop offset="95%" stopColor="#00ff9d" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                <XAxis dataKey="time" tick={{ fill: 'rgba(255,255,255,0.2)', fontSize: 9, fontFamily: 'JetBrains Mono' }} tickLine={false} />
                <YAxis tick={{ fill: 'rgba(255,255,255,0.2)', fontSize: 9, fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: 10, color: 'rgba(255,255,255,0.25)', fontFamily: 'JetBrains Mono' }} />
                <Area type="monotone" dataKey="avg" name="avg count" stroke="#00d4ff" fill="url(#gAvg)" strokeWidth={1.5} dot={false} />
                <Area type="monotone" dataKey="max" name="peak count" stroke="#00ff9d" fill="url(#gMax)" strokeWidth={1} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div style={card}>
              <div className="flex items-center gap-2 mb-5">
                <BarChart2 size={12} style={{ color: '#ffb830' }} />
                <span style={{ fontSize: 10, letterSpacing: '0.1em', color: 'rgba(255,255,255,0.35)' }}>daily totals (7 days)</span>
              </div>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={dailyData} margin={{ left: -10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                  <XAxis dataKey="date" tick={{ fill: 'rgba(255,255,255,0.2)', fontSize: 9, fontFamily: 'JetBrains Mono' }} tickLine={false} />
                  <YAxis tick={{ fill: 'rgba(255,255,255,0.2)', fontSize: 9, fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="total" name="total" fill="#ffb830" radius={[2, 2, 0, 0]} opacity={0.75} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div style={card}>
              <div className="flex items-center gap-2 mb-5">
                <Clock size={12} style={{ color: '#ff3d6b' }} />
                <span style={{ fontSize: 10, letterSpacing: '0.1em', color: 'rgba(255,255,255,0.35)' }}>peak hour distribution</span>
              </div>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={peaks.slice(0, 12)} margin={{ left: -10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                  <XAxis dataKey="hour" tick={{ fill: 'rgba(255,255,255,0.2)', fontSize: 9, fontFamily: 'JetBrains Mono' }} tickLine={false} />
                  <YAxis tick={{ fill: 'rgba(255,255,255,0.2)', fontSize: 9, fontFamily: 'JetBrains Mono' }} tickLine={false} axisLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="avg" name="avg people" fill="#ff3d6b" radius={[2, 2, 0, 0]} opacity={0.75} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}