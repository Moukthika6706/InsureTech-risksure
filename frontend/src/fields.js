// Helpers for config-driven form fields (validation, API conversion, display).
import { inrWords, isMoneyField } from './format'

// Mirrors the backend's checks (engine/rating.py) so most mistakes are caught
// before submitting; the server still validates everything.
export function validateField(field, value) {
  if (value === '' || value == null) return 'Required'
  if (field.type === 'int' || field.type === 'float') {
    const n = Number(value)
    if (Number.isNaN(n)) return 'Must be a number'
    if (field.type === 'int' && !Number.isInteger(n)) return 'Must be a whole number'
    if (field.min != null && n < field.min) return `Must be at least ${field.min.toLocaleString('en-IN')}`
    if (field.max != null && n > field.max) return `Must be at most ${field.max.toLocaleString('en-IN')}`
  }
  return null
}

// Convert the form's string state back to the field's type for the API.
export function toApiValue(field, value) {
  if (field.type === 'int') return parseInt(value, 10)
  if (field.type === 'float') return parseFloat(value)
  return value
}

// Text shown for a value on the review page.
export function displayValue(field, value) {
  if (field.type === 'bool') return value ? 'Yes' : 'No'
  if (field.type === 'select') return field.options.find((o) => String(o.value) === String(value))?.label ?? value
  if (isMoneyField(field)) return inrWords(value)
  return Number(value).toLocaleString('en-IN')
}
