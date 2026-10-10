// src/components/RequireAuth.jsx
// Route guard.
//   not logged in          -> /login
//   logged in, no shop yet -> /shop-setup   (unless needShop={false}, used by the shop-setup page itself)
import { Loader2 } from "lucide-react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function RequireAuth({ needShop = true }) {
  const { token, user, shop, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-bg text-sm text-ink/60">
        <Loader2 className="mr-2 animate-spin" size={18} /> Loading...
      </div>
    );
  }
  if (!token || !user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (needShop && !shop) return <Navigate to="/shop-setup" replace />;
  return <Outlet />;
}
