import Logo from './Logo'

export default function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-slate-50">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 px-4 py-8 text-sm text-slate-500 sm:flex-row sm:px-6 lg:px-8">
        <Logo />
        <p>© {new Date().getFullYear()} StayNest. Developed By Aniket Shrivastava</p>
      </div>
    </footer>
  )
}