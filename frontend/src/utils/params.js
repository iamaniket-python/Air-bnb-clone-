// Khali ('' / null / undefined) values hata deta hai, taaki API ko faltu params na jayein
export function cleanParams(obj) {
  return Object.fromEntries(Object.entries(obj).filter(([, v]) => v !== '' && v !== null && v !== undefined))
}