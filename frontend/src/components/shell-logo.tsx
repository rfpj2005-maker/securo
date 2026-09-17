interface ShellLogoProps {
  size?: number
  className?: string
}

/** The app's brand mark — a stylized compass, matching "Bússola". Single-color
 * (currentColor) so every call site can tint it (sidebar, auth panels, a huge
 * translucent watermark) without passing a second color. The bezel ring is
 * drawn as one evenodd path (true negative-space hole, not a background-color
 * hack) so it stays correct on any background — light, dark, or colored badge.
 * The needle keeps the classic two-tone compass look — a solid north half and
 * a dimmer south half — using fillOpacity instead of a second color. */
export function ShellLogo({ size = 24, className }: ShellLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Bezel ring */}
      <path
        fill="currentColor"
        fillRule="evenodd"
        clipRule="evenodd"
        d="M22.5,12 A10.5,10.5 0 1,0 1.5,12 A10.5,10.5 0 1,0 22.5,12 Z
           M20.5,12 A8.5,8.5 0 1,0 3.5,12 A8.5,8.5 0 1,0 20.5,12 Z"
      />
      {/* Needle — north half (solid) */}
      <path fill="currentColor" d="M12 5 L14.3 12 L9.7 12 Z" />
      {/* Needle — south half (dimmer) */}
      <path fill="currentColor" fillOpacity="0.38" d="M12 19 L14.3 12 L9.7 12 Z" />
      {/* Pivot */}
      <circle cx="12" cy="12" r="1.4" fill="currentColor" />
    </svg>
  )
}
