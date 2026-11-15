// Vercel request body limit 4.5 MB hai, isliye photos browser mein hi chhoti kar dete hain.
export const MAX_UPLOAD_BYTES = 4 * 1024 * 1024 // compress ke baad bhi itna se bada ho to reject
export const MAX_ORIGINAL_BYTES = 25 * 1024 * 1024 // browser memory bachane ke liye

// Image ko max 1600px aur JPEG 85% par laata hai. Faayda na ho to original wapas deta hai.
export async function compressImage(file, { maxSize = 1600, quality = 0.85 } = {}) {
  if (!file.type.startsWith('image/') || file.type === 'image/gif') return file

  let bitmap
  try {
    bitmap = await createImageBitmap(file)
  } catch {
    return file // decode nahi hua (jaise HEIC), original bhej do, backend validate karega
  }

  const scale = Math.min(1, maxSize / Math.max(bitmap.width, bitmap.height))
  const width = Math.round(bitmap.width * scale)
  const height = Math.round(bitmap.height * scale)

  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  canvas.getContext('2d').drawImage(bitmap, 0, 0, width, height)
  if (bitmap.close) bitmap.close()

  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality))
  if (!blob || blob.size >= file.size) return file

  return new File([blob], `${file.name.replace(/\.[^.]+$/, '')}.jpg`, { type: 'image/jpeg' })
}