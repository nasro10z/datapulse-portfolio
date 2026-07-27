import { render } from '@testing-library/react'
import { LangProvider } from '../i18n'

/** Rend un composant enveloppé du provider de langue (défaut : fr). */
export function renderWithLang(ui, options) {
  return render(<LangProvider>{ui}</LangProvider>, options)
}
