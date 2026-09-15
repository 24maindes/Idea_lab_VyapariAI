const VARIANTS = {
  primary: 'bg-primary text-white hover:bg-[#0C3E4B] border-transparent',
  accent: 'bg-accent text-white hover:bg-[#D66647] border-transparent',
  secondary: 'bg-white text-text border-[#D9DEDA] hover:bg-[#F1F2EF]',
  ghost: 'bg-transparent text-secondary border-transparent hover:bg-[#EEF3F3]',
}

export default function Button({
  as = 'button',
  variant = 'primary',
  className = '',
  children,
  ...props
}) {
  const Comp = as
  return (
    <Comp
      className={`inline-flex items-center justify-center gap-2 rounded-[8px] border px-4 py-2 text-sm font-medium
        transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
      {...props}
    >
      {children}
    </Comp>
  )
}
