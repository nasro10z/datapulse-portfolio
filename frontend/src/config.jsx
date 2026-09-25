import { createContext, useContext, useEffect, useState } from 'react'
import { api } from './api/client'

/**
 * Configuration de l'instance, lue une fois au démarrage (`GET /api/config`).
 *
 * Une même application sert deux contextes : un poste de développement (écriture
 * libre) et la démonstration publique (plannings figés, instantané recalé).
 * L'interface doit le savoir pour présenter un formulaire désactivé plutôt qu'un
 * échec à la soumission.
 *
 * Lue **au niveau de l'application**, pas page par page : la même information
 * servira le bandeau de démonstration, et une page rendue isolément (dans un test,
 * par exemple) n'a ainsi aucun appel réseau à simuler — elle reçoit la valeur par
 * défaut ci-dessous, qui n'interdit rien.
 */
const DEFAULT = { data_source: null, anomalies_source: null, pm_read_only: false }

const ConfigContext = createContext(DEFAULT)

export function ConfigProvider({ children }) {
  const [config, setConfig] = useState(DEFAULT)

  useEffect(() => {
    let cancelled = false
    api.config()
      .then((c) => { if (!cancelled) setConfig({ ...DEFAULT, ...c }) })
      // Une configuration injoignable ne doit pas empêcher l'application de
      // fonctionner : on reste sur la valeur par défaut, la plus permissive.
      .catch(() => {})
    return () => { cancelled = true }
  }, [])

  return <ConfigContext.Provider value={config}>{children}</ConfigContext.Provider>
}

export const useConfig = () => useContext(ConfigContext)
