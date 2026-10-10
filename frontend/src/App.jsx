import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";

import Login from "./pages/Login";
import Signup from "./pages/Signup";
import ShopSetup from "./pages/ShopSetup";
import Products from "./pages/Products";
import Suppliers from "./pages/Suppliers";
import PurchaseEntry from "./pages/PurchaseEntry";
import Inventory from "./pages/Inventory";
import Dashboard from "./pages/Dashboard";
import PriceAnalysis from "./pages/PriceAnalysis";
import Sales from "./pages/Sales";
import Alerts from "./pages/Alerts";
import Forecast from "./pages/Forecast";
import Recommendations from "./pages/Recommendations";
import Advisor from "./pages/Advisor";
import Settings from "./pages/Settings";
import AdvisorWidget from "./components/advisor/AdvisorWidget";

import Sidebar from "./components/Sidebar";
import RequireAuth from "./components/RequireAuth";

import { AppDataProvider } from "./context/AppDataContext";
import { AuthProvider } from "./context/AuthContext";
import { ToastProvider } from "./components/ui/Toast";

// Logged-in layout: ONE common sidebar + the page content (same layout as before)
function MainLayout() {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-bg">
      <Sidebar />
      <main className="flex-1 overflow-y-auto px-8 py-7">
        <Outlet />
      </main>
      <AdvisorWidget />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
        <AppDataProvider>
          <Routes>
            {/* public */}
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />

            {/* logged in, shop not needed yet */}
            <Route element={<RequireAuth needShop={false} />}>
              <Route path="/shop-setup" element={<ShopSetup />} />
            </Route>

            {/* logged in AND shop exists */}
            <Route element={<RequireAuth />}>
              <Route element={<MainLayout />}>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/products" element={<Products />} />
                <Route path="/suppliers" element={<Suppliers />} />
                <Route path="/purchases" element={<PurchaseEntry />} />
                <Route path="/sales" element={<Sales />} />
                <Route path="/inventory" element={<Inventory />} />
                <Route path="/price-analysis" element={<PriceAnalysis />} />
                <Route path="/forecast" element={<Forecast />} />
                <Route path="/alerts" element={<Alerts />} />
                <Route path="/recommendations" element={<Recommendations />} />
                <Route path="/advisor" element={<Advisor />} />
                <Route path="/settings" element={<Settings />} />
              </Route>
            </Route>

            {/* unknown address -> dashboard (the guard sends logged-out users to /login) */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </AppDataProvider>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
