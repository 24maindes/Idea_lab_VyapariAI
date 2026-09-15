import {
  LayoutDashboard,
  Package,
  Truck,
  ShoppingCart,
  Boxes,
  Tag,
  Settings,
} from "lucide-react";

const navItems = [
  { label: "Dashboard", icon: LayoutDashboard, screen: "dashboard" },
  { label: "Products", icon: Package, screen: "products" },
  { label: "Suppliers", icon: Truck, screen: "suppliers" },
  { label: "Purchases", icon: ShoppingCart, screen: "purchases" },
  { label: "Inventory", icon: Boxes, screen: "inventory" },
  { label: "Pricing", icon: Tag, screen: "priceAnalysis" },
  { label: "Settings", icon: Settings, screen: "settings" },
];

export default function Sidebar({ shopName, currentScreen, onNavigate }) {
  return (
    <aside className="flex h-screen w-[230px] shrink-0 flex-col bg-primary text-white">
      {/* Logo */}
      <div className="flex items-center gap-2 px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-control bg-white/10">
          <span className="text-[15px] font-bold text-accent">V</span>
        </div>

        <span className="text-[16px] font-semibold tracking-tight">
          VyapariAI
        </span>
      </div>

      {/* Navigation */}
      <nav className="mt-2 flex-1 space-y-1 px-3">
        {navItems.map(({ label, icon: Icon, screen }) => {
          const active = currentScreen === screen;

          return (
            <button
              key={label}
              onClick={() => {
                if (screen !== "settings") {
                  onNavigate(screen);
                }
              }}
              disabled={screen === "settings"}
              className={`flex w-full items-center gap-3 rounded-control px-3 py-2.5 text-left text-[14px] transition-colors ${
                active
                  ? "bg-white/10 font-medium text-white"
                  : screen === "settings"
                    ? "cursor-not-allowed text-white/45"
                    : "text-white/75 hover:bg-white/10 hover:text-white"
              }`}
              title={
                screen === "settings"
                  ? "Settings coming soon"
                  : undefined
              }
            >
              <Icon size={17} />
              {label}
            </button>
          );
        })}
      </nav>

      {/* Shop information */}
      <div className="border-t border-white/10 px-5 py-4">
        <p className="text-[12px] text-white/50">Signed in as</p>

        <p className="truncate text-[13px] font-medium text-white/90">
          {shopName || "Your Shop"}
        </p>
      </div>
    </aside>
  );
}