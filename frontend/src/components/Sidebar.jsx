import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Package,
  Truck,
  ShoppingCart,
  Receipt,
  Boxes,
  Tag,
  TrendingUp,
  Bell,
  Lightbulb,
  Sparkles,
  Settings,
  LogOut,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import useUnreadAlerts from "../hooks/useUnreadAlerts";

// label, icon and the URL it opens
const navItems = [
  { label: "Dashboard", icon: LayoutDashboard, to: "/dashboard" },
  { label: "Products", icon: Package, to: "/products" },
  { label: "Suppliers", icon: Truck, to: "/suppliers" },
  { label: "Purchases", icon: ShoppingCart, to: "/purchases" },
  { label: "Sales", icon: Receipt, to: "/sales" },
  { label: "Inventory", icon: Boxes, to: "/inventory" },
  { label: "Pricing", icon: Tag, to: "/price-analysis" },
  { label: "Forecast", icon: TrendingUp, to: "/forecast" },
  { label: "Alerts", icon: Bell, to: "/alerts" },
  { label: "Recommendations", icon: Lightbulb, to: "/recommendations" },
  { label: "AI Advisor", icon: Sparkles, to: "/advisor" },
  { label: "Settings", icon: Settings, to: "/settings" },
];

export default function Sidebar() {
  const { shop, logout } = useAuth();
  const unread = useUnreadAlerts();   // red pill on the Alerts item

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

      {/* Navigation (NavLink adds the active style by itself) */}
      <nav className="mt-2 flex-1 space-y-1 overflow-y-auto px-3">
        {navItems.map(({ label, icon: Icon, to }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex w-full items-center gap-3 rounded-control px-3 py-2.5 text-left text-[14px] transition-colors ${
                isActive
                  ? "bg-white/10 font-medium text-white"
                  : "text-white/75 hover:bg-white/10 hover:text-white"
              }`
            }
          >
            <Icon size={17} />
            <span className="flex-1">{label}</span>
            {to === "/alerts" && unread > 0 && (
              <span className="rounded-full bg-accent px-1.5 py-0.5 text-[11px] font-semibold leading-none text-white" aria-label={`${unread} unread alerts`}>
                {unread > 99 ? "99+" : unread}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Shop information + logout */}
      <div className="flex items-center justify-between gap-2 border-t border-white/10 px-5 py-4">
        <div className="min-w-0">
          <p className="text-[12px] text-white/50">Signed in as</p>
          <p className="truncate text-[13px] font-medium text-white/90">
            {shop?.shopName || "Your Shop"}
          </p>
        </div>

        <button
          onClick={logout}
          title="Log out"
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control text-white/70 transition-colors hover:bg-white/10 hover:text-white"
        >
          <LogOut size={16} />
        </button>
      </div>
    </aside>
  );
}
