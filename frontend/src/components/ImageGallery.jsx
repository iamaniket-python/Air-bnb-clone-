import { useEffect, useState } from 'react'
import { FiChevronLeft, FiChevronRight, FiGrid, FiImage, FiX } from 'react-icons/fi'
import { mediaUrl } from '../utils/media'

// Primary image pehle, phir display_order
function sortImages(images = []) {
  return [...images]
    .sort((a, b) => Number(b.is_primary) - Number(a.is_primary) || (a.display_order ?? 0) - (b.display_order ?? 0))
    .map((img) => ({ url: mediaUrl(img), caption: img.caption }))
    .filter((img) => img.url)
}

export default function ImageGallery({ images, title }) {
  const items = sortImages(images)
  const count = items.length
  const [index, setIndex] = useState(null)
  const open = index !== null

  // Lightbox: Esc / arrow keys, aur background scroll band
  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') setIndex(null)
      if (e.key === 'ArrowRight') setIndex((i) => (i + 1) % count)
      if (e.key === 'ArrowLeft') setIndex((i) => (i - 1 + count) % count)
    }
    document.addEventListener('keydown', onKey)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
    }
  }, [open, count])

  if (count === 0) {
    return (
      <div className="flex aspect-[16/7] items-center justify-center rounded-2xl bg-slate-100 text-slate-300">
        <FiImage className="h-12 w-12" />
      </div>
    )
  }

  const tile = (item, i, extra = '') => (
    <button
      key={item.url}
      type="button"
      onClick={() => setIndex(i)}
      className={`relative overflow-hidden bg-slate-100 ${extra}`}
      aria-label={`Open photo ${i + 1}`}
    >
      <img src={item.url} alt={item.caption || `${title} photo ${i + 1}`} className="h-full w-full object-cover transition hover:scale-105" />
    </button>
  )

  return (
    <>
      {/* Desktop: 1 bada + 4 chhote. Mobile: sirf pehli image */}
      <div className="relative overflow-hidden rounded-2xl">
        <div className="hidden aspect-[16/7] gap-2 md:grid md:grid-cols-4 md:grid-rows-2">
          {tile(items[0], 0, 'col-span-2 row-span-2')}
          {items.slice(1, 5).map((item, i) => tile(item, i + 1))}
        </div>
        <div className="aspect-[4/3] md:hidden">{tile(items[0], 0, 'h-full w-full')}</div>

        {count > 1 && (
          <button
            type="button"
            onClick={() => setIndex(0)}
            className="absolute bottom-3 right-3 inline-flex items-center gap-2 rounded-lg bg-white px-3 py-1.5 text-sm font-semibold shadow hover:bg-slate-50"
          >
            <FiGrid /> Show all {count} photos
          </button>
        )}
      </div>

      {open && (
        <div className="fixed inset-0 z-50 flex flex-col bg-black/90" role="dialog" aria-modal="true" aria-label="Photo gallery">
          <div className="flex items-center justify-between px-4 py-3 text-white">
            <span className="text-sm">{index + 1} / {count}</span>
            <button type="button" onClick={() => setIndex(null)} aria-label="Close gallery" className="rounded-full p-2 hover:bg-white/10">
              <FiX className="h-6 w-6" />
            </button>
          </div>

          <div className="relative flex flex-1 items-center justify-center px-12 pb-4">
            <button type="button" onClick={() => setIndex((i) => (i - 1 + count) % count)} aria-label="Previous photo" className="absolute left-2 rounded-full bg-white/10 p-3 text-white hover:bg-white/20">
              <FiChevronLeft className="h-6 w-6" />
            </button>
            <img src={items[index].url} alt={items[index].caption || title} className="max-h-full max-w-full rounded-lg object-contain" />
            <button type="button" onClick={() => setIndex((i) => (i + 1) % count)} aria-label="Next photo" className="absolute right-2 rounded-full bg-white/10 p-3 text-white hover:bg-white/20">
              <FiChevronRight className="h-6 w-6" />
            </button>
          </div>

          {items[index].caption && <p className="pb-4 text-center text-sm text-white/80">{items[index].caption}</p>}
        </div>
      )}
    </>
  )
}