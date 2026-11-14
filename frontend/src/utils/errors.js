// normalizeApiError ke result se form ke neeche dikhane layak ek text banata hai.
// Field-wise errors ho to wahi dikhata hai (jaise "check_in: ..."), warna general message.
export function errorText(normalized) {
  const fields = Object.values(normalized.fieldErrors ?? {})
  if (fields.length > 0) return [normalized.message, ...fields].filter(Boolean).join(' ')
  return normalized.message
}