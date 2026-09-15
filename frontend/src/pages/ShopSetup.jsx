import { useState } from "react";
import { Store, MapPin, ChevronDown } from "lucide-react";
import InputField from "../components/InputField";
import Button from "../components/Button";

const shopTypes = [
  "Grocery",
  "Kirana Store",
  "Medical Store",
  "Stationery",
  "Clothing",
  "Electronics",
  "Other",
];

export default function ShopSetup({ onComplete }) {
  const [shopName, setShopName] = useState("");
  const [shopType, setShopType] = useState("");
  const [location, setLocation] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!shopName.trim() || !shopType || !location.trim()) {
      setError("Please fill in all fields to continue.");
      return;
    }
    setError("");
    onComplete({ shopName, shopType, location });
  };

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-bg px-6 py-10">
      <div className="grid w-full max-w-3xl grid-cols-1 overflow-hidden rounded-card border border-ink/10 bg-white shadow-card md:grid-cols-2">
        {/* Form side */}
        <div className="px-8 py-9">
          <h1 className="text-[24px] font-semibold text-ink">Set up your shop</h1>
          <p className="mt-1 text-[14px] text-ink/60">
            Tell us a bit about your shop to get started
          </p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <InputField
              label="Shop Name"
              icon={Store}
              value={shopName}
              onChange={(e) => setShopName(e.target.value)}
              placeholder="Sharma General Store"
            />

            <div className="w-full">
              <label className="mb-1.5 block text-[13px] font-medium text-ink/80">
                Shop Type
              </label>
              <div className="relative flex items-center rounded-control border border-ink/15 bg-white px-3 py-2.5 focus-within:border-secondary">
                <select
                  value={shopType}
                  onChange={(e) => setShopType(e.target.value)}
                  className="w-full appearance-none bg-transparent text-[14px] text-ink focus:outline-none"
                >
                  <option value="" disabled>
                    Select shop type
                  </option>
                  {shopTypes.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
                <ChevronDown size={16} className="pointer-events-none text-ink/40" />
              </div>
            </div>

            <InputField
              label="Location"
              icon={MapPin}
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="Nagpur"
              error={error}
            />

            <Button type="submit" fullWidth className="mt-1">
              Continue
            </Button>
          </form>
        </div>

        {/* Illustration side */}
        <div className="hidden flex-col items-center justify-center gap-4 bg-gradient-to-br from-primary to-secondary p-8 text-center text-white md:flex">
          <div className="flex h-16 w-16 items-center justify-center rounded-card bg-white/15">
            <Store size={28} />
          </div>
          <p className="text-[15px] font-medium">
            Your shop, organized in one place
          </p>
          <p className="text-[13px] leading-relaxed text-white/70">
            Add your products next and start tracking stock right away.
          </p>
        </div>
      </div>
    </div>
  );
}
