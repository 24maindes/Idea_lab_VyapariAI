import { X } from "lucide-react";

export default function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 px-4">
      <div className="w-full max-w-md rounded-card bg-white shadow-card">
        <div className="flex items-center justify-between border-b border-ink/10 px-5 py-4">
          <h3 className="text-[16px] font-semibold text-ink">{title}</h3>
          <button
            onClick={onClose}
            className="rounded-control p-1 text-ink/40 hover:bg-ink/5 hover:text-ink"
          >
            <X size={18} />
          </button>
        </div>
        <div className="px-5 py-5">{children}</div>
      </div>
    </div>
  );
}
