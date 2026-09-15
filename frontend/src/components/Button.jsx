export default function Button({
  children,
  onClick,
  type = "button",
  variant = "primary",
  icon: Icon,
  className = "",
  fullWidth = false,
}) {
  const base =
    "inline-flex items-center justify-center gap-1.5 rounded-control text-[14px] font-medium transition-colors px-4 py-2.5 disabled:opacity-50";
  const variants = {
    primary: "bg-primary text-white hover:bg-[#0c3e4a]",
    accent: "bg-accent text-white hover:bg-[#d96745]",
    secondary: "bg-white border border-ink/15 text-ink hover:bg-ink/5",
    ghost: "text-secondary hover:text-primary",
  };

  return (
    <button
      type={type}
      onClick={onClick}
      className={`${base} ${variants[variant]} ${fullWidth ? "w-full" : ""} ${className}`}
    >
      {Icon && <Icon size={16} />}
      {children}
    </button>
  );
}
