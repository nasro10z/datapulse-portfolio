import { useTheme } from '../design-system/ThemeContext'

export default function ThemeToggle() {
  const { theme, toggle } = useTheme()
  const isDark = theme === 'dark'

  return (
    <button
      onClick={toggle}
      title={isDark ? 'Passer en thème clair' : 'Passer en thème sombre'}
      aria-label={isDark ? 'Passer en thème clair' : 'Passer en thème sombre'}
      aria-pressed={isDark}
      className="flex items-center justify-center"
      style={{
        width: 34,
        height: 34,
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--border)',
        background: 'transparent',
        color: 'var(--text-muted)',
        cursor: 'pointer',
        transition: 'background var(--transition-fast), color var(--transition-fast)',
      }}
    >
      {isDark ? (
        // Lune → propose le thème clair
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z" />
        </svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <circle cx="12" cy="12" r="4.2" />
          <path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M19.1 4.9l-1.8 1.8M6.7 17.3l-1.8 1.8" />
        </svg>
      )}
    </button>
  )
}
