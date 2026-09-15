export default function PageHeader({ title, subtitle, action }) {
  return (
    <div className="flex flex-col gap-3 border-b border-[#E4E6E1] pb-5 mb-6 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-[24px] font-semibold leading-tight text-primary">{title}</h1>
        {subtitle && <p className="mt-1 text-[13px] text-[#5B6B70]">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}
