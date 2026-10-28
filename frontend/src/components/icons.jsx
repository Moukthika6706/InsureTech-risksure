// Inline line icons (24px grid, stroke = currentColor). No icon library needed.
const PATHS = {
  car: 'M5 16.5h14M6.2 16.5l1.3-4.6A2 2 0 019.4 10.5h5.2a2 2 0 011.9 1.4l1.3 4.6M7 16.5v2M17 16.5v2M3.5 12.5h2M18.5 12.5h2M8 14h.01M16 14h.01',
  home: 'M3.5 11L12 4l8.5 7M5.5 9.5V19a1 1 0 001 1h3.5v-5.5h4V20h3.5a1 1 0 001-1V9.5',
  business: 'M4 20h16M5 20V9l7-4 7 4v11M9 20v-5h6v5M8.5 11h.01M12 11h.01M15.5 11h.01',
  shield: 'M12 3l7.5 3v5.6c0 4.9-3.2 8.6-7.5 9.9-4.3-1.3-7.5-5-7.5-9.9V6z',
  check: 'M5 12.5l4.5 4.5L19 7.5',
  arrow: 'M5 12h14M13 6l6 6-6 6',
  back: 'M19 12H5M11 6l-6 6 6 6',
  chart: 'M4 19h16M7 16V10M11 16V6M15 16v-4M19 16V8',
  sparkles: 'M12 4l1.6 4.4L18 10l-4.4 1.6L12 16l-1.6-4.4L6 10l4.4-1.6zM18.5 15.5l.7 1.8 1.8.7-1.8.7-.7 1.8-.7-1.8-1.8-.7 1.8-.7z',
  scale: 'M12 4v16M7 20h10M5 8h14M5 8l-2.5 6a3 3 0 005 0zM19 8l-2.5 6a3 3 0 005 0z',
  brain: 'M9 4.5a3 3 0 00-3 3 3 3 0 00-1.5 5.6A3 3 0 007.5 18H9m0-13.5V18m0-13.5a3 3 0 016 0V18m0-13.5a3 3 0 013 3 3 3 0 011.5 5.6A3 3 0 0116.5 18H15',
  list: 'M9 6h11M9 12h11M9 18h11M4.5 6h.01M4.5 12h.01M4.5 18h.01',
  clock: 'M12 7v5l3 2M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  inbox: 'M3.5 13h4.5l1.5 2.5h5L16 13h4.5M5.5 5h13l2 8v5a1 1 0 01-1 1h-15a1 1 0 01-1-1v-5z',
  doc: 'M7 3.5h7l4 4V20a.5.5 0 01-.5.5h-10A.5.5 0 017 20zM14 3.5V8h4M9.5 12h5M9.5 15.5h5',
  plus: 'M12 5v14M5 12h14',
}

export default function Icon({ name, className = 'h-5 w-5', strokeWidth = 1.7 }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={strokeWidth}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={PATHS[name] || PATHS.shield} />
    </svg>
  )
}
