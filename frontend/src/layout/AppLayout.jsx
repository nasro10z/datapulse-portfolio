import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import Logo from '../components/Logo'
import { api } from '../api/client'
import useApi from '../hooks/useApi'
import useTheme from '../hooks/useTheme'
import { useLang, LANGS } from '../i18n'
import { SITES, findSite } from '../sites'
import GlobalView from '../pages/GlobalView'

const footerControl = {
  display: 'flex', alignItems: 'center', gap: 9, width: '100%',
  padding: '10px 11px', border: '1px solid var(--border)', borderRadius: 12,
  background: 'var(--surface)', color: 'var(--text)', textAlign: 'left', cursor: 'pointer',
}

const SunIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
  </svg>
)
const MoonIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z" />
  </svg>
)
const GlobeIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3a15 15 0 010 18M12 3a15 15 0 000 18" />
  </svg>
)

const NAV = [
  { to: '/', key: 'siteHealth', icon: <path d="M22 12h-4l-3 9L9 3l-3 9H2" /> },
  { to: '/forecast', key: 'forecast', icon: <path d="M3 17l6-6 4 4 8-8M21 7v6h-6" /> },
  { to: '/anomalies', key: 'anomalies', icon: <><circle cx="12" cy="12" r="9" /><path d="M12 8v4M12 16h.01" /></> },
  { to: '/maintenance', key: 'maintenance', icon: <path d="M14.7 6.3a4.5 4.5 0 106.4 6.4l-3.1-3.1 3.1-3.1a4.5 4.5 0 00-6.4-.2zM8 16l-5 5M9.3 17.7a4.5 4.5 0 10-6.4-6.4" /> },
  { to: '/reminders', key: 'reminders', icon: <path d="M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 01-3.4 0" /> },
]

const TITLES = Object.fromEntries(NAV.map((n) => [n.to, n]))

export default function AppLayout() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const currentNav = TITLES[pathname] ?? NAV[0]
  const { isLight, toggle: toggleTheme } = useTheme()
  const { lang, setLang, t } = useLang()
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && setMenuOpen(false)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const reminders = useApi(api.remindersCount, [pathname])
  const reminderCount = reminders.data?.count ?? 0

  // vue : 'global' (agrégat multi-sites) ou l'id d'un site (personnalisé)
  const [view, setView] = useState('global')
  const [siteMenuOpen, setSiteMenuOpen] = useState(false)
  const isGlobal = view === 'global'
  const site = isGlobal ? null : findSite(view) ?? SITES[0]

  const enterSite = (id) => { setView(id); setSiteMenuOpen(false); setMenuOpen(false); navigate('/') }
  const goGlobal = () => { setView('global'); setSiteMenuOpen(false); setMenuOpen(false) }

  return (
    <div className="flex h-screen" style={{ background: 'var(--bg)' }}>
      {/* ---- Backdrop du tiroir de navigation ---- */}
      <div className={`app-backdrop ${menuOpen ? 'open' : ''}`} onClick={() => setMenuOpen(false)} aria-hidden="true" />

      {/* ---- Sidebar (tiroir, masqué par défaut) ---- */}
      <aside
        className="app-sidebar flex flex-col"
        style={{
          width: 232, flex: 'none',
          borderRight: '1px solid var(--border)', background: 'var(--bg-elevated)',
          padding: '18px 14px',
          transform: menuOpen ? 'translateX(0)' : 'translateX(-100%)',
        }}
      >
        <div style={{ padding: '4px 8px 18px' }}>
          <Logo />
        </div>

        {/* Navigation par site — masquée en vue globale */}
        {!isGlobal && (
          <>
            <div className="num" style={{ fontSize: 9.5, letterSpacing: 'var(--tracking-caps)', color: 'var(--text-muted)', padding: '8px 10px 6px', textTransform: 'uppercase' }}>
              {t('nav.section')}
            </div>
            <nav className="flex flex-col gap-1" aria-label={t('nav.section')}>
              {NAV.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  onClick={() => setMenuOpen(false)}
                  className="flex items-center gap-3"
                  style={({ isActive }) => ({
                    padding: '10px 11px', borderRadius: 10,
                    border: `1px solid ${isActive ? 'var(--border)' : 'transparent'}`,
                    background: isActive ? 'var(--accent-soft)' : 'transparent',
                    color: isActive ? 'var(--text)' : 'var(--text-muted)',
                    transition: 'background var(--transition-fast), color var(--transition-fast)',
                  })}
                >
                  {({ isActive }) => (
                    <>
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={isActive ? 'var(--accent)' : 'currentColor'} strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" style={{ flex: 'none' }} aria-hidden="true">
                        {item.icon}
                      </svg>
                      <span style={{ lineHeight: 1.3 }}>
                        <span className="block" style={{ fontSize: 12.5, fontWeight: 500 }}>{t(`nav.${item.key}`)}</span>
                        <span className="num block" style={{ fontSize: 9.5, color: 'var(--text-muted)' }}>{t(`nav.${item.key}Sub`)}</span>
                      </span>
                      {item.to === '/reminders' && reminderCount > 0 && (
                        <span className="num" aria-label={t('layout.remindersActive', { n: reminderCount })}
                          style={{ marginLeft: 'auto', flex: 'none', minWidth: 18, height: 18, padding: '0 5px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 700, borderRadius: 'var(--radius-pill)', background: 'var(--status-watch)', color: 'var(--text-inverse)' }}>
                          {reminderCount}
                        </span>
                      )}
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
              style={{ position: 'absolute', bottom: '100%', left: 0, right: 0, marginBottom: 6, background: 'var(--bg-elevated)', border: '1px solid var(--border-strong)', borderRadius: 12, padding: 6, boxShadow: '0 12px 40px -8px rgba(0,0,0,.5)', zIndex: 20 }}>
              <button type="button" role="option" aria-selected={isGlobal} onClick={goGlobal}
                className="flex items-center gap-2 w-full"
                style={{ padding: '9px 10px', borderRadius: 8, border: 'none', textAlign: 'left', background: isGlobal ? 'var(--accent-soft)' : 'transparent', color: 'var(--text)', cursor: 'pointer' }}>
                <span style={{ display: 'flex', flex: 'none', color: 'var(--accent)' }}><GlobeIcon /></span>
                <span style={{ lineHeight: 1.25, flex: 1 }}>
                  <span className="block" style={{ fontSize: 12, fontWeight: 500 }}>{t('global.option')}</span>
                  <span className="num block" style={{ fontSize: 9.5, color: 'var(--text-muted)' }}>{t('global.sub', { n: SITES.length })}</span>
                </span>
              </button>
              <div style={{ height: 1, background: 'var(--hairline)', margin: '5px 6px' }} aria-hidden="true" />
              {SITES.map((s) => (
                <button key={s.id} type="button" role="option" aria-selected={view === s.id}
                  onClick={() => enterSite(s.id)}
                  className="flex items-center gap-2 w-full"
                  style={{ padding: '9px 10px', borderRadius: 8, border: 'none', textAlign: 'left', background: view === s.id ? 'var(--accent-soft)' : 'transparent', color: 'var(--text)', cursor: 'pointer' }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', flex: 'none', background: s.connected ? 'var(--status-healthy)' : 'var(--text-muted)' }} aria-hidden="true" />
                  <span style={{ lineHeight: 1.25, flex: 1, minWidth: 0 }}>
                    <span className="block" style={{ fontSize: 12, fontWeight: 500 }}>{s.name}</span>
                    <span className="num block" style={{ fontSize: 9.5, color: 'var(--text-muted)' }}>{s.operator} · {t('common.units', { n: s.assets })}</span>
                  </span>
                  {!s.connected && (
                    <span className="num" style={{ fontSize: 8.5, color: 'var(--text-muted)', border: '1px solid var(--border)', borderRadius: 'var(--radius-pill)', padding: '1px 6px', flex: 'none' }}>{t('layout.demo')}</span>
                  )}
                </button>
              ))}
            </div>
          )}

          <button type="button" onClick={() => setSiteMenuOpen((v) => !v)} style={footerControl}
            aria-haspopup="listbox" aria-expanded={siteMenuOpen}
            aria-label={isGlobal ? t('global.title') : t('layout.siteActive', { name: site.name })}>
            <span style={{ display: 'flex', flex: 'none', color: isGlobal ? 'var(--accent)' : (site.connected ? 'var(--status-healthy)' : 'var(--text-muted)') }}>
              {isGlobal ? <GlobeIcon /> : <span style={{ width: 9, height: 9, borderRadius: '50%', background: 'currentColor', display: 'inline-block' }} aria-hidden="true" />}
            </span>
            <span style={{ lineHeight: 1.25, flex: 1, minWidth: 0 }}>
              <span className="block" style={{ fontSize: 12, fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{isGlobal ? t('global.title') : site.name}</span>
              <span className="num block" style={{ fontSize: 9.5, color: 'var(--text-muted)', letterSpacing: 'var(--tracking-wide)' }}>{isGlobal ? t('global.sub', { n: SITES.length }) : `${site.operator} · ${t('common.units', { n: site.assets })}`}</span>
            </span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flex: 'none', color: 'var(--text-muted)', transform: siteMenuOpen ? 'rotate(180deg)' : 'none', transition: 'transform var(--transition-fast)' }} aria-hidden="true">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </button>
        </div>
      </aside>

      {/* ---- Main ---- */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3" style={{ height: 66, flex: 'none', padding: '0 16px', borderBottom: '1px solid var(--border)' }}>
          <button className="app-menu-btn" onClick={() => setMenuOpen((v) => !v)}
            aria-label={menuOpen ? t('layout.closeMenu') : t('layout.openMenu')} aria-expanded={menuOpen}
            style={{ width: 38, height: 38, flex: 'none', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', background: 'transparent', color: 'var(--text)', cursor: 'pointer' }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="M3 6h18M3 12h18M3 18h18" />
            </svg>
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
              <span style={{ display: 'flex', color: 'var(--accent)' }}>{isLight ? <MoonIcon /> : <SunIcon />}</span>
              <span className="num hide-sm" style={{ fontSize: 11, fontWeight: 600, letterSpacing: 'var(--tracking-wide)' }}>{isLight ? t('layout.light') : t('layout.dark')}</span>
            </button>
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
