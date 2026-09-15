export default function InputField({
  label,
  icon: Icon,
  type = "text",
  value,
  onChange,
  placeholder,
  error,
  rightElement,
  name,
}) {
  return (
    <div className="w-full">
      {label && (
        <label className="mb-1.5 block text-[13px] font-medium text-ink/80">
          {label}
        </label>
      )}
      <div
        className={`flex items-center gap-2 rounded-control border bg-white px-3 py-2.5 transition-colors focus-within:border-secondary ${
          error ? "border-accent" : "border-ink/15"
        }`}
      >
        {Icon && <Icon size={16} className="shrink-0 text-ink/40" />}
        <input
          name={name}
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className="w-full bg-transparent text-[14px] text-ink placeholder:text-ink/35 focus:outline-none"
        />
        {rightElement}
      </div>
      {error && <p className="mt-1 text-[12px] text-accent">{error}</p>}
    </div>
  );
}
