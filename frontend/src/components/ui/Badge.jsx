const STYLES = {
  'In Stock': 'bg-[#E4EFE7] text-[#3C6B4B]',
  'Low Stock': 'bg-[#FBEAE3] text-[#B9522E]',
  'Out of Stock': 'bg-[#F1E1E1] text-[#9A3B3B]',
  neutral: 'bg-[#EAEEF0] text-[#4B5B61]',
}

export default function Badge({ children, tone = 'neutral' }) {
  const style = STYLES[tone] ?? STYLES.neutral
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${style}`}>
      {children}
    </span>
  )
}
