import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { LayoutDashboard, HeartPulse, TrendingUp, TriangleAlert, CalendarDays, Globe, Sun, Moon, ChevronsUpDown, Menu, Circle } from 'lucide-react'
import Logo from '../components/Logo'
import NotificationBell from '../components/NotificationBell'
import useTheme from '../hooks/useTheme'
import { useLang, LANGS } from '../i18n'
import { SITES, findSite } from '../sites'
import GlobalView from '../pages/GlobalView'

const NAV = [
  { to: '/', key: 'overview', Icon: LayoutDashboard },
  { to: '/health', key: 'siteHealth', Icon: HeartPulse },
  { to: '/forecast', key: 'forecast', Icon: TrendingUp },
  { to: '/anomalies', key: 'anomalies', Icon: TriangleAlert },
  { to: '/maintenance', key: 'maintenance', Icon: CalendarDays },
]
const TITLES = Object.fromEntries(NAV.map((n) => [n.to, n]))

// contrôle bas de sidebar (sélecteur de site) — sur fond sombre
const siteBtnStyle = {
  display: 'flex', alignItems: 'center', gap: 9, width: '100%',
  padding: '10px 11px', border: '1px solid var(--sidebar-border)', borderRadius: 12,
  background: 'var(--sidebar-surface)', color: 'var(--sidebar-text)', textAlign: 'left', cursor: 'pointer',
}

export default function AppLayout() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const currentNav = TITLES[pathname] ?? NAV[0]
  const { isLight, toggle: toggleTheme } = useTheme()
  const { lang, setLang, t } = useLang()
  const [menuOpen, setMenuOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(max-width: 768px)').matches,
  )
  const [clock, setClock] = useState(() => new Date().toTimeString().slice(0, 5))

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 768px)')
    const onChange = () => setIsMobile(mq.matches)
    mq.addEventListener('change', onChange)
    const onKey = (e) => e.key === 'Escape' && setMenuOpen(false)
    window.addEventListener('keydown', onKey)
    const clockId = setInterval(() => setClock(new Date().toTimeString().slice(0, 5)), 30000)
    return () => { mq.removeEventListener('change', onChange); window.removeEventListener('keydown', onKey); clearInterval(clockId) }
  }, [])

  const [view, setView] = useState('global')
  const [siteMenuOpen, setSiteMenuOpen] = useState(false)
  const isGlobal = view === 'global'
  const site = isGlobal ? null : findSite(view) ?? SITES[0]

  const enterSite = (id) => { setView(id); setSiteMenuOpen(false); setMenuOpen(false); navigate('/') }
  const goGlobal = () => { setView('global'); setSiteMenuOpen(false); setMenuOpen(false) }

  const sidebarTransform = isMobile ? (menuOpen ? 'translateX(0)' : 'translateX(-100%)') : undefined

  return (
    <div className="flex flex-row h-screen" style={{ background: 'var(--bg)' }}>
      {isMobile && <div className={`app-backdrop ${menuOpen ? 'open' : ''}`} onClick={() => setMenuOpen(false)} aria-hidden="true" />}

      {/* ---- Sidebar (persistante desktop, tiroir mobile) ---- */}
      <aside
        className="app-sidebar flex flex-col"
        style={{
          width: 236, flex: 'none',
          background: 'var(--sidebar-bg)', color: 'var(--sidebar-text)',
          borderRight: '1px solid var(--sidebar-border)',
          padding: '18px 14px',
          transform: sidebarTransform,
        }}
      >
        <div style={{ padding: '4px 8px 20px' }}>
          <Logo mutedColor="var(--sidebar-muted)" boxBg="var(--sidebar-surface)" boxBorder="var(--sidebar-border)" />
        </div>

        {!isGlobal && (
          <>
            <div className="num" style={{ fontSize: 9.5, letterSpacing: 'var(--tracking-caps)', color: 'var(--sidebar-muted)', padding: '8px 10px 8px', textTransform: 'uppercase' }}>
              {t('nav.section')}
            </div>
            <nav className="flex flex-col gap-1" aria-label={t('nav.section')}>
              {NAV.map(({ to, key, Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  onClick={() => setMenuOpen(false)}
                  className="flex items-center gap-3"
                  style={({ isActive }) => ({
                    padding: '10px 12px', borderRadius: 10,
                    background: isActive ? 'var(--sidebar-active)' : 'transparent',
                    color: isActive ? 'var(--sidebar-active-text)' : 'var(--sidebar-muted)',
                    transition: 'background var(--transition-fast), color var(--transition-fast)',
                  })}
                >
                  {({ isActive }) => (
                    <>
                      <Icon size={18} strokeWidth={1.9} style={{ flex: 'none', color: isActive ? 'var(--chart-healthy)' : 'currentColor' }} aria-hidden="true" />
                      <span style={{ fontSize: 13, fontWeight: 500 }}>{t(`nav.${key}`)}</span>
                    </>
                  )}
                </NavLink>
              ))}
            </nav>
          </>
        )}

        <div className="mt-auto relative" style={{ paddingTop: 12 }}>
          {siteMenuOpen && (
            <div role="listbox" aria-label={t('layout.chooseSite')}
              style={{ position: 'absolute', bottom: '100%', left: 0, right: 0, marginBottom: 6, background: 'var(--sidebar-surface)', border: '1px solid var(--sidebar-border)', borderRadius: 12, padding: 6, boxShadow: '0 12px 40px -8px rgba(0,0,0,.6)', zIndex: 20 }}>
              <button type="button" role="option" aria-selected={isGlobal} onClick={goGlobal}
                className="flex items-center gap-2 w-full"
                style={{ padding: '9px 10px', borderRadius: 8, border: 'none', textAlign: 'left', background: isGlobal ? 'var(--sidebar-active)' : 'transparent', color: 'var(--sidebar-text)', cursor: 'pointer' }}>
                <Globe size={15} style={{ flex: 'none', color: 'var(--chart-healthy)' }} aria-hidden="true" />
                <span style={{ lineHeight: 1.25, flex: 1 }}>
                  <span className="block" style={{ fontSize: 12, fontWeight: 500 }}>{t('global.option')}</span>
                  <span className="num block" style={{ fontSize: 9.5, color: 'var(--sidebar-muted)' }}>{t('global.sub', { n: SITES.length })}</span>
                </span>
              </button>
              <div style={{ height: 1, background: 'var(--sidebar-border)', margin: '5px 6px' }} aria-hidden="true" />
              {SITES.map((s) => (
                <button key={s.id} type="button" role="option" aria-selected={view === s.id}
                  onClick={() => enterSite(s.id)}
                  className="flex items-center gap-2 w-full"
                  style={{ padding: '9px 10px', borderRadius: 8, border: 'none', textAlign: 'left', background: view === s.id ? 'var(--sidebar-active)' : 'transparent', color: 'var(--sidebar-text)', cursor: 'pointer' }}>
                  <Circle size={9} fill={s.connected ? 'var(--chart-healthy)' : 'var(--sidebar-muted)'} strokeWidth={0} style={{ flex: 'none' }} aria-hidden="true" />
                  <span style={{ lineHeight: 1.25, flex: 1, minWidth: 0 }}>
                    <span className="block" style={{ fontSize: 12, fontWeight: 500 }}>{s.name}</span>
                    <span className="num block" style={{ fontSize: 9.5, color: 'var(--sidebar-muted)' }}>{s.operator} · {t('common.units', { n: s.assets })}</span>
                  </span>
                  {!s.connected && <span className="num" style={{ fontSize: 8.5, color: 'var(--sidebar-muted)', border: '1px solid var(--sidebar-border)', borderRadius: 'var(--radius-pill)', padding: '1px 6px', flex: 'none' }}>{t('layout.demo')}</span>}
                </button>
              ))}
            </div>
          )}

          <button type="button" onClick={() => setSiteMenuOpen((v) => !v)} style={siteBtnStyle}
            aria-haspopup="listbox" aria-expanded={siteMenuOpen}
            aria-label={isGlobal ? t('global.title') : t('layout.siteActive', { name: site.name })}>
            {isGlobal ? <Globe size={16} style={{ flex: 'none', color: 'var(--chart-healthy)' }} aria-hidden="true" />
              : <Circle size={10} fill={site.connected ? 'var(--chart-healthy)' : 'var(--sidebar-muted)'} strokeWidth={0} style={{ flex: 'none' }} aria-hidden="true" />}
            <span style={{ lineHeight: 1.25, flex: 1, minWidth: 0 }}>
              <span className="block" style={{ fontSize: 12, fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{isGlobal ? t('global.title') : site.name}</span>
              <span className="num block" style={{ fontSize: 9.5, color: 'var(--sidebar-muted)' }}>{isGlobal ? t('global.sub', { n: SITES.length }) : `${site.operator} · ${t('common.units', { n: site.assets })}`}</span>
            </span>
            <ChevronsUpDown size={14} style={{ flex: 'none', color: 'var(--sidebar-muted)' }} aria-hidden="true" />
          </button>
        </div>
      </aside>

      {/* ---- Main ---- */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3" style={{ height: 66, flex: 'none', padding: '0 20px', borderBottom: '1px solid var(--border)', background: 'var(--bg-elevated)' }}>
          <button className="app-menu-btn" onClick={() => setMenuOpen((v) => !v)}
            aria-label={menuOpen ? t('layout.closeMenu') : t('layout.openMenu')} aria-expanded={menuOpen}
            style={{ width: 38, height: 38, flex: 'none', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', background: 'transparent', color: 'var(--text)', cursor: 'pointer' }}>
            <Menu size={18} aria-hidden="true" />
          </button>
          <div className="min-w-0">
            <h1 style={{ fontSize: 18, fontWeight: 'var(--fw-semibold)', letterSpacing: 'var(--tracking-tight)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {isGlobal ? t('global.title') : t(`nav.${currentNav.key}`)}
            </h1>
            <div className="num" style={{ fontSize: 10, letterSpacing: '0.1em', color: 'var(--text-muted)', marginTop: 2, textTransform: 'uppercase', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {isGlobal ? t('global.sub', { n: SITES.length }) : `${t(`nav.${currentNav.key}Sub`)} — ${site.name}`}
            </div>
          </div>

          <div className="flex items-center gap-2" style={{ marginLeft: 'auto', flex: 'none' }}>
            <NotificationBell />

            <div className="num flex" role="group" aria-label={t('layout.changeLanguage')}
              style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
              {LANGS.map((l) => (
                <button key={l} type="button" onClick={() => setLang(l)} aria-pressed={lang === l}
                  style={{ fontSize: 11, fontWeight: 700, letterSpacing: 'var(--tracking-wide)', padding: '0 10px', height: 36, border: 'none', cursor: 'pointer', background: lang === l ? 'var(--accent-soft)' : 'transparent', color: lang === l ? 'var(--accent-hover)' : 'var(--text-muted)' }}>
                  {l.toUpperCase()}
                </button>
              ))}
            </div>

            <button type="button" onClick={toggleTheme} className="flex items-center"
              style={{ flex: 'none', gap: 8, height: 38, padding: '0 12px', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', background: 'transparent', color: 'var(--text)', cursor: 'pointer' }}
              aria-label={isLight ? t('layout.toDark') : t('layout.toLight')} aria-pressed={isLight} title={isLight ? t('layout.toDark') : t('layout.toLight')}>
              {isLight ? <Moon size={16} style={{ color: 'var(--accent)' }} /> : <Sun size={16} style={{ color: 'var(--accent)' }} />}
              <span className="num hide-sm" style={{ fontSize: 11, fontWeight: 600, letterSpacing: 'var(--tracking-wide)' }}>{isLight ? t('layout.light') : t('layout.dark')}</span>
            </button>

            <span className="num hide-sm flex items-center gap-1.5" style={{ fontSize: 10.5, color: 'var(--text-muted)', letterSpacing: 'var(--tracking-wide)', paddingLeft: 4 }}>
              <Circle size={7} fill="var(--chart-healthy)" strokeWidth={0} aria-hidden="true" />
              {t('layout.synced')} · {clock}
            </span>
          </div>
        </header>

        <main className="app-main min-w-0 flex-1 overflow-y-auto">
          {isGlobal ? (
            <GlobalView onSelectSite={enterSite} />
          ) : site.connected ? (
            <Outlet />
          ) : (
            <div className="flex flex-col items-center justify-center gap-3" style={{ minHeight: '60%', textAlign: 'center', padding: 24 }}>
              <div style={{ fontSize: 15, fontWeight: 600 }}>{t('layout.siteComingTitle', { name: site.name })}</div>
              <p style={{ fontSize: 12.5, color: 'var(--text-muted)', maxWidth: 440, lineHeight: 1.55 }}>
                {t('layout.siteComingBody', { operator: site.operator, assets: site.assets })}
              </p>
              <button type="button" onClick={goGlobal} className="num"
                style={{ fontSize: 12, fontWeight: 600, padding: '8px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--accent)', background: 'var(--accent-soft)', color: 'var(--accent-hover)', cursor: 'pointer' }}>
                ‹ {t('global.backToGlobal')}
              </button>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
