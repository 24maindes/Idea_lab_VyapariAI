import { useState } from "react";
import { Mail, Lock, Eye, EyeOff, Store } from "lucide-react";
import InputField from "../components/InputField";
import Button from "../components/Button";
import loginShop from "../assets/login-shop.png";

// See extractErrorMessage in Signup.jsx — FastAPI's `detail` field is a
// string for our own errors but an array of {msg} objects for pydantic
// validation errors, which would otherwise render as "[object Object]".
function extractErrorMessage(data) {
  const detail = data?.detail;
  if (!detail) return "Login failed";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join(" ");
  }
  return "Login failed";
}

export default function Login({ onLogin, onGoToSignup }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError("Please enter both email and password.");
      return;
    }
    try {
      const res = await fetch("http://127.0.0.1:8000/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(extractErrorMessage(data));

      localStorage.setItem("vyapariToken", data.access_token);
      localStorage.setItem("vyapariUser", JSON.stringify(data.user));
      setError("");
      onLogin();
    } catch (err) {
      setError(err.message);
    }
  };

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
              onClick={onGoToSignup}
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
