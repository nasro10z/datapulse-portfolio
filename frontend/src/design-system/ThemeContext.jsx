import { createContext, useContext, useEffect, useMemo, useState } from 'react'

const STORAGE_KEY = 'datapulse-theme'
const ThemeContext = createContext({ theme: 'dark', setTheme: () => {}, toggle: () => {} })

function initialTheme() {
  if (typeof window === 'undefined') return 'dark'
  const stored = window.localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark') return stored
  // Pas de préférence enregistrée : on suit l'OS, sombre par défaut.
  return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(initialTheme)

  useEffect(() => {
    const root = document.documentElement
    root.setAttribute('data-theme', theme)
    // Aligne les contrôles natifs (scrollbars, date pickers, selects)
    root.style.colorScheme = theme
    window.localStorage.setItem(STORAGE_KEY, theme)
  }, [theme])

  // Suit l'OS tant que l'utilisateur n'a pas choisi explicitement
  useEffect(() => {
    if (window.localStorage.getItem(STORAGE_KEY)) return
    const mq = window.matchMedia('(prefers-color-scheme: light)')
    const onChange = (e) => setTheme(e.matches ? 'light' : 'dark')
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  const value = useMemo(
    () => ({ theme, setTheme, toggle: () => setTheme((t) => (t === 'dark' ? 'light' : 'dark')) }),
    [theme],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export const useTheme = () => useContext(ThemeContext)
