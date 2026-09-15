export default function StatCard({ icon: Icon, label, value, tint = 'secondary' }) {
  const tintMap = {
    secondary: 'bg-secondary/10 text-secondary',
    accent: 'bg-accent/10 text-accent',
    primary: 'bg-primary/10 text-primary',
  }

  return (
    <div className="bg-card border border-black/5 rounded-card shadow-sm p-4 flex items-center gap-3">
      <div className={`w-10 h-10 rounded-[8px] flex items-center justify-center ${tintMap[tint]}`}>
        <Icon size={18} strokeWidth={2} />
      </div>
      <div>
        <p className="text-[12px] text-ink/60">{label}</p>
        <p className="text-[18px] font-semibold text-ink leading-tight">{value}</p>
      </div>
    </div>
  )
}
