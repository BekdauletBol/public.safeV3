import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, BarChart3, FileText, Camera, LogOut, Wifi, WifiOff
} from 'lucide-react'
import { useAuthStore, useCameraStore } from '../../store'
import { useClock } from '../../hooks/useClock'

import myLogo from '../../../src/public.safe.png'

const NAV = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
  { to: '/reports', icon: FileText, label: 'Reports' },
  { to: '/cameras', icon: Camera, label: 'Cameras' },
]

export default function Layout({ children }) {
  const { logout } = useAuthStore()
  const { cameras, wsConnected } = useCameraStore()
  const time = useClock()

  const activeCams = cameras.filter((c) => c.is_active).length

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--bg-primary)' }}>
      {/* Sidebar */}
      <aside
        className="w-56 flex flex-col shrink-0 border-r"
        style={{ background: 'var(--bg-secondary)', borderColor: 'var(--border)' }}
      >
        {/* Logo Section */}
        <div className="px-5 py-5 border-b" style={{ borderColor: 'var(--border)' }}>
          <div className="flex items-center gap-2.5">
            {/* Контейнер для вашего фото */}
            <div className="w-8 h-8 rounded-lg flex items-center justify-center overflow-hidden shrink-0">
              <img
                src={myLogo}
                alt="Logo"
                className="w-full h-full object-contain"
              />
            </div>
            <div>
              <div className="font-display font-bold text-sm" style={{ color: 'var(--text-primary)' }}>
                public.safe
              </div>
              <div className="font-mono text-xs" style={{ color: 'var(--accent-cyan)' }}>V3</div>
            </div>
          </div>
        </div>

        {/* Live status bar */}
        <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--border)' }}>
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--text-secondary)' }}>
              {wsConnected
                ? <><Wifi size={11} style={{ color: 'var(--accent-green)' }} /> Live</>
                : <><WifiOff size={11} style={{ color: 'var(--accent-red)' }} /> Offline</>}
            </div>
            <div className="font-mono text-xs" style={{ color: 'var(--text-muted)' }}>
              {time.toLocaleTimeString()}
            </div>
          </div>
          <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
            {activeCams} / {cameras.length} cameras active
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 flex flex-col gap-1">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 ${isActive
                  ? 'font-medium'
                  : 'hover:bg-white/5'
                }`
              }
              style={({ isActive }) => ({
                background: isActive ? 'rgba(0,212,255,0.1)' : undefined,
                color: isActive ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                borderLeft: isActive ? '2px solid var(--accent-cyan)' : '2px solid transparent',
              })}
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-3 py-4 border-t" style={{ borderColor: 'var(--border)' }}>
          <button
            onClick={logout}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm transition-all duration-150 hover:bg-white/5"
            style={{ color: 'var(--text-secondary)' }}
          >
            <LogOut size={16} />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
}