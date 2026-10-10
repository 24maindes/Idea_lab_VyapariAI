import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Mail, Lock, Eye, EyeOff, Store } from "lucide-react";
import InputField from "../components/InputField";
import Button from "../components/Button";
import loginShop from "../assets/login-shop.png";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login, token, user } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  // "Session expired" message left by api/client.js when the server answered 401
  const [error, setError] = useState(() => {
    const m = sessionStorage.getItem("vyapariSessionMessage");
    sessionStorage.removeItem("vyapariSessionMessage");
    return m || "";
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError("Please enter both email and password.");
      return;
    }
    try {
      // AuthContext calls POST /api/auth/login, stores the token and loads the shop
      await login(email, password);
      setError("");
      navigate("/dashboard", { replace: true });   // no shop yet? the route guard sends the user to /shop-setup
    } catch (err) {
      setError(err.message);
    }
  };

  // already logged in -> no need to see the login page
  if (token && user) return <Navigate to="/dashboard" replace />;

  return (
    <div className="flex min-h-screen w-full bg-bg">
      {/* Left branding panel */}
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-gradient-to-br from-primary to-secondary px-12 py-10 text-white md:flex">
        <div>
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-control bg-white/15">
              <Store size={18} />
            </div>
            <span className="text-[20px] font-semibold tracking-tight">
              VyapariAI
            </span>
          </div>
          <p className="mt-6 max-w-sm text-[15px] font-medium text-white/90">
            AI-Powered Price &amp; Purchase Advisor for Local Shopkeepers
          </p>
          <p className="mt-3 max-w-sm text-[13px] leading-relaxed text-white/65">
            VyapariAI helps local shop owners make smarter purchasing and
            pricing decisions, so every order and every price is backed by
            real numbers, not guesswork.
          </p>
        </div>

        <div className="flex items-end justify-center">
          <img
            src={loginShop}
            alt="VyapariAI local shop illustration"
            className="w-full max-w-[520px] object-contain"
          />
        </div>

        <p className="text-center text-[12px] tracking-wide text-white/55">
          Smarter Decisions &nbsp;|&nbsp; Better Profits &nbsp;|&nbsp; Stronger Local Businesses
        </p>
      </div>

      {/* Right form panel */}
      <div className="flex w-full items-center justify-center px-6 py-10 md:w-1/2">
        <div className="w-full max-w-sm">
          <h1 className="text-[24px] font-semibold text-ink">Welcome back</h1>
          <p className="mt-1 text-[14px] text-ink/60">
            Login to continue to your store
          </p>

          <form onSubmit={handleSubmit} className="mt-7 space-y-4">
            <InputField
              label="Email or Username"
              icon={Mail}
              type="text"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@shop.com"
            />
            <InputField
              label="Password"
              icon={Lock}
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              error={error}
              rightElement={
                <button
                  type="button"
                  onClick={() => setShowPassword((s) => !s)}
                  className="text-ink/40 hover:text-ink/70"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              }
            />

            <div className="flex justify-end">
              <button
                type="button"
                className="text-[13px] font-medium text-secondary hover:text-primary"
              >
                Forgot password?
              </button>
            </div>

            <Button type="submit" fullWidth>
              Login
            </Button>
          </form>

          <div className="my-5 flex items-center gap-3">
            <div className="h-px flex-1 bg-ink/10" />
            <span className="text-[12px] text-ink/40">OR</span>
            <div className="h-px flex-1 bg-ink/10" />
          </div>

          <p className="text-center text-[13px] text-ink/60">
            Don&apos;t have an account?{" "}
            <button
              onClick={() => navigate("/signup")}
              className="font-medium text-secondary hover:text-primary"
            >
              Sign up
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
