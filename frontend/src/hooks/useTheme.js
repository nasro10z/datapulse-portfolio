import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'datapulse-theme'

function initialTheme() {
  const attr = document.documentElement.getAttribute('data-theme')
  if (attr === 'light' || attr === 'dark') return attr
  try {
    return localStorage.getItem(STORAGE_KEY) === 'dark' ? 'dark' : 'light'
  } catch {
    return 'light'
  }
}

/**
 * Thème clair/sombre. Le design system bascule via `[data-theme="light"]` sur
 * <html> (dark = défaut). L'attribut est posé avant le rendu par le script inline
 * de index.html (anti-flash) ; ce hook applique tout changement et le persiste.
 * L'effet de bord (DOM + localStorage) vit dans un effet, pas dans l'updater
 * d'état — indispensable sous StrictMode, qui double-invoque les updaters.
 */
export default function useTheme() {
  const [theme, setTheme] = useState(initialTheme)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    try {
      localStorage.setItem(STORAGE_KEY, theme)
    } catch {
      // stockage indisponible : le thème reste appliqué pour la session
    }
  }, [theme])

  const toggle = useCallback(() => setTheme((p) => (p === 'dark' ? 'light' : 'dark')), [])

  return { theme, toggle, isLight: theme === 'light' }
}
