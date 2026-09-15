import { useState } from "react";
import { ChevronDown } from "lucide-react";
import Modal from "./Modal";
import InputField from "./InputField";
import Button from "./Button";
import { categories, units } from "../data/mockProducts";

export default function AddProductModal({ onClose, onAdd }) {
  const [form, setForm] = useState({
    name: "",
    category: "",
    unit: "",
    stock: "",
  });
  const [error, setError] = useState("");

  const update = (key) => (e) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleAdd = () => {
    if (!form.name.trim() || !form.category || !form.unit || form.stock === "") {
      setError("Please fill in all fields.");
      return;
    }
    onAdd({
      name: form.name.trim(),
      category: form.category,
      unit: form.unit,
      stock: Number(form.stock),
    });
  };

  return (
    <Modal title="Add Product" onClose={onClose}>
      <div className="space-y-4">
        <InputField
          label="Product Name"
          value={form.name}
          onChange={update("name")}
          placeholder="e.g. Toor Dal"
        />

        <Select
          label="Category"
          value={form.category}
          onChange={update("category")}
          options={categories}
        />

        <Select
          label="Unit"
          value={form.unit}
          onChange={update("unit")}
          options={units}
        />

        <InputField
          label="Initial Stock"
          type="number"
          value={form.stock}
          onChange={update("stock")}
          placeholder="e.g. 25"
        />

        {error && <p className="text-[12px] text-accent">{error}</p>}

        <div className="flex justify-end gap-2 pt-1">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="accent" onClick={handleAdd}>
            Add Product
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function Select({ label, value, onChange, options }) {
  return (
    <div className="w-full">
      <label className="mb-1.5 block text-[13px] font-medium text-ink/80">
        {label}
      </label>
      <div className="relative flex items-center rounded-control border border-ink/15 bg-white px-3 py-2.5 focus-within:border-secondary">
        <select
          value={value}
          onChange={onChange}
          className="w-full appearance-none bg-transparent text-[14px] text-ink focus:outline-none"
        >
          <option value="" disabled>
            Select {label.toLowerCase()}
          </option>
          {options.map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </select>
        <ChevronDown size={16} className="pointer-events-none text-ink/40" />
      </div>
    </div>
  );
}
