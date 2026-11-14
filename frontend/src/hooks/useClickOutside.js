import { useEffect } from 'react'

// ref ke bahar click hone par handler chalta hai (dropdown band karne ke liye)
export default function useClickOutside(ref, handler) {
  useEffect(() => {
    const listener = (event) => {
      if (ref.current && !ref.current.contains(event.target)) handler()
    }
    document.addEventListener('mousedown', listener)
    return () => document.removeEventListener('mousedown', listener)
  }, [ref, handler])
}