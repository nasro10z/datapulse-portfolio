import { NavLink, Outlet, useLocation } from 'react-router-dom'
import Logo from '../components/Logo'
import { api } from '../api/client'
import useApi from '../hooks/useApi'

const NAV = [
  {
    to: '/',
    label: 'Site Health',
    sub: 'Vue d’ensemble',
    icon: (
      <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
    ),
  },
  {
    to: '/forecast',
    label: 'Forecast',
    sub: 'Prédiction des pannes',
    icon: (
      <path d="M3 17l6-6 4 4 8-8M21 7v6h-6" />
    ),
  },
  {
    to: '/anomalies',
    label: 'Anomalies',
    sub: 'Détection',
    icon: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 8v4M12 16h.01" />
      </>
    ),
  },
  {
    to: '/maintenance',
    label: 'Maintenance',
    sub: 'Préventive',
    icon: (
      <path d="M14.7 6.3a4.5 4.5 0 106.4 6.4l-3.1-3.1 3.1-3.1a4.5 4.5 0 00-6.4-.2zM8 16l-5 5M9.3 17.7a4.5 4.5 0 10-6.4-6.4" />
    ),
  },
  {
    to: '/reminders',
    label: 'Reminders',
    sub: 'Rappels actifs',
    icon: (
      <path d="M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 01-3.4 0" />
    ),
  },
]

const TITLES = Object.fromEntries(NAV.map((n) => [n.to, n]))

export default function AppLayout() {
  const { pathname } = useLocation()
  const current = TITLES[pathname] ?? NAV[0]
  // rechargé à chaque changement de page (couvre les acquittements/snooze depuis la page Reminders)
  const reminders = useApi(api.remindersCount, [pathname])
  const reminderCount = reminders.data?.count ?? 0

  return (
    <div className="flex h-screen" style={{ background: 'var(--bg)' }}>
      {/* ---- Sidebar ---- */}
      <aside
        className="flex flex-col"
        style={{
          width: 232,
          flex: 'none',
          borderRight: '1px solid var(--border)',
          background: 'var(--bg-elevated)',
          padding: '18px 14px',
        }}
      >
        <div style={{ padding: '4px 8px 18px' }}>
          <Logo />
        </div>

        <div
          className="num"
          style={{
            fontSize: 9.5,
            letterSpacing: 'var(--tracking-caps)',
            color: 'var(--text-muted)',
            padding: '8px 10px 6px',
          }}
        >
          SURVEILLANCE
        </div>

        <nav className="flex flex-col gap-1" aria-label="Navigation principale">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className="flex items-center gap-3"
              style={({ isActive }) => ({
                padding: '10px 11px',
                borderRadius: 10,
                border: `1px solid ${isActive ? 'var(--border)' : 'transparent'}`,
                background: isActive ? 'var(--accent-soft)' : 'transparent',
                color: isActive ? 'var(--text)' : 'var(--text-muted)',
                transition: 'background var(--transition-fast), color var(--transition-fast)',
              })}
            >
              {({ isActive }) => (
                <>
                  <svg
                    width="16" height="16" viewBox="0 0 24 24" fill="none"
                    stroke={isActive ? 'var(--accent)' : 'currentColor'}
                    strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"
                    style={{ flex: 'none' }} aria-hidden="true"
                  >
                    {item.icon}
                  </svg>
                  <span style={{ lineHeight: 1.3 }}>
                    <span className="block" style={{ fontSize: 12.5, fontWeight: 500 }}>
                      {item.label}
                    </span>
                    <span className="num block" style={{ fontSize: 9.5, color: 'var(--text-muted)' }}>
                      {item.sub}
                    </span>
                  </span>
                  {item.to === '/reminders' && reminderCount > 0 && (
                    <span
                      className="num"
                      aria-label={`${reminderCount} rappel${reminderCount > 1 ? 's' : ''} actif${reminderCount > 1 ? 's' : ''}`}
                      style={{
                        marginLeft: 'auto', flex: 'none',
                        minWidth: 18, height: 18, padding: '0 5px',
                        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 10, fontWeight: 700, borderRadius: 'var(--radius-pill)',
                        background: 'var(--status-watch)', color: 'var(--text-inverse)',
                      }}
                    >
                      {reminderCount}
                    </span>
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div
          className="num mt-auto"
          style={{ fontSize: 9.5, color: 'var(--text-muted)', padding: '10px', letterSpacing: 'var(--tracking-wide)' }}
        >
          MSC-10 · UC3
        </div>
      </aside>

      {/* ---- Main ---- */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header
          className="flex items-center gap-5"
          style={{
            height: 66,
            flex: 'none',
            padding: '0 28px',
            borderBottom: '1px solid var(--border)',
          }}
        >
          <div>
            <div style={{ fontSize: 18, fontWeight: 'var(--fw-semibold)', letterSpacing: 'var(--tracking-tight)' }}>
              {current.label}
            </div>
            <div
              className="num"
              style={{ fontSize: 10, letterSpacing: '0.1em', color: 'var(--text-muted)', marginTop: 2, textTransform: 'uppercase' }}
            >
              {current.sub} — data center MSC-10
            </div>
          </div>
        </header>

        <main className="min-w-0 flex-1 overflow-y-auto" style={{ padding: 28 }}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
