import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { LangProvider } from './i18n'
import AppLayout from './layout/AppLayout'
import SiteHealth from './pages/SiteHealth'
import Forecast from './pages/Forecast'
import Anomalies from './pages/Anomalies'
import Maintenance from './pages/Maintenance'
import Reminders from './pages/Reminders'

export default function App() {
  return (
    <LangProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<SiteHealth />} />
            <Route path="/forecast" element={<Forecast />} />
            <Route path="/anomalies" element={<Anomalies />} />
            <Route path="/maintenance" element={<Maintenance />} />
            <Route path="/reminders" element={<Reminders />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </LangProvider>
  )
}
