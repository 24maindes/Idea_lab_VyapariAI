export default function Card({ children, className = '' }) {
  return (
    <div className={`rounded-[10px] border border-[#E7E9E4] bg-card shadow-[0_1px_2px_rgba(15,76,92,0.06)] ${className}`}>
      {children}
    </div>
  )
}
