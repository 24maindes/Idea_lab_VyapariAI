import { useState } from "react";

import Login from "./pages/Login";
import Signup from "./pages/Signup";
import ShopSetup from "./pages/ShopSetup";
import Products from "./pages/Products";

import Suppliers from "./pages/Suppliers";
import PurchaseEntry from "./pages/PurchaseEntry";
import Inventory from "./pages/Inventory";

import Dashboard from "./pages/Dashboard";
import PriceAnalysis from "./pages/PriceAnalysis";

import Sidebar from "./components/Sidebar";

import { AppDataProvider } from "./context/AppDataContext";

const mainScreens = [
  "dashboard",
  "products",
  "suppliers",
  "purchases",
  "inventory",
  "priceAnalysis",
];

export default function App() {
  const [screen, setScreen] = useState("login");
  const [shop, setShop] = useState(null);

  const renderPage = () => {
    switch (screen) {
      case "dashboard":
        return <Dashboard />;

      case "products":
        return <Products shop={shop} />;

      case "suppliers":
        return <Suppliers />;

      case "purchases":
        return <PurchaseEntry />;

      case "inventory":
        return <Inventory />;

      case "priceAnalysis":
        return <PriceAnalysis />;

      default:
        return <Dashboard />;
    }
  };

  return (
    <AppDataProvider>
      {/* LOGIN */}
      {screen === "login" && (
        <Login
          onLogin={() => setScreen("dashboard")}
          onGoToSignup={() => setScreen("signup")}
        />
      )}

      {/* SIGNUP */}
      {screen === "signup" && (
        <Signup
          onSignup={() => setScreen("shopSetup")}
          onGoToLogin={() => setScreen("login")}
        />
      )}

      {/* SHOP SETUP */}
      {screen === "shopSetup" && (
        <ShopSetup
          onComplete={(data) => {
            setShop(data);
            localStorage.setItem("vyapariShop", JSON.stringify(data));
            setScreen("dashboard");
          }}
        />
      )}

      {/* MAIN APPLICATION */}
      {mainScreens.includes(screen) && (
        <div className="flex h-screen w-full overflow-hidden bg-bg">
          {/* ONE COMMON SIDEBAR */}
          <Sidebar
            shopName={shop?.shopName}
            currentScreen={screen}
            onNavigate={setScreen}
          />

          {/* PAGE CONTENT */}
          <main className="flex-1 overflow-y-auto px-8 py-7">
            {renderPage()}
          </main>
        </div>
      )}
    </AppDataProvider>
  );
}