import { Search } from 'lucide-react'

export default function SearchInput({ value, onChange, placeholder = 'Search...' }) {
  return (
    <div className="relative w-full max-w-xs">
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#8A9599]" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-[8px] border border-[#D9DEDA] bg-white py-2 pl-9 pr-3 text-sm text-text
          placeholder:text-[#9AA5A8] focus:border-secondary focus:outline-none focus:ring-2 focus:ring-secondary/20"
      />
    </div>
  )
}
