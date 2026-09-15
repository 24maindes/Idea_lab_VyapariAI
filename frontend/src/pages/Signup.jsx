import { useState } from "react";
import { User, Mail, Lock, Eye, EyeOff, Store } from "lucide-react";
import InputField from "../components/InputField";
import Button from "../components/Button";

// FastAPI sends `detail` as a plain string for our own HTTPExceptions
// (e.g. "An account with this email already exists."), but as an ARRAY of
// {loc, msg, type} objects for automatic pydantic validation errors
// (e.g. password too short). Without this, the array case renders as
// "[object Object]" in the UI.
function extractErrorMessage(data) {
  const detail = data?.detail;
  if (!detail) return "Signup failed";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => d.msg || JSON.stringify(d))
      .join(" ");
  }
  return "Signup failed";
}

export default function Signup({ onSignup, onGoToLogin }) {
  const [form, setForm] = useState({
    fullName: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [errors, setErrors] = useState({});

  const update = (key) => (e) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    const newErrors = {};
    if (!form.fullName.trim()) newErrors.fullName = "Full name is required.";
    if (!form.email.trim()) newErrors.email = "Email is required.";
    if (!form.password.trim()) newErrors.password = "Password is required.";
    if (form.password !== form.confirmPassword)
      newErrors.confirmPassword = "Passwords do not match.";

    setErrors(newErrors);
    if (Object.keys(newErrors).length > 0) return;

    try {
      const res = await fetch("http://127.0.0.1:8000/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fullName: form.fullName,
          email: form.email,
          password: form.password,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(extractErrorMessage(data));

      localStorage.setItem("vyapariToken", data.access_token);
      localStorage.setItem("vyapariUser", JSON.stringify(data.user));
      onSignup();
    } catch (err) {
      setErrors({ email: err.message });
    }
  };

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-bg px-6 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-7 flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-control bg-primary">
            <Store size={18} className="text-white" />
          </div>
          <span className="text-[18px] font-semibold text-ink">VyapariAI</span>
        </div>

        <h1 className="text-[24px] font-semibold text-ink">Create your account</h1>
        <p className="mt-1 text-[14px] text-ink/60">
          Start managing your shop smarter
        </p>

        <form onSubmit={handleSubmit} className="mt-7 space-y-4">
          <InputField
            label="Full Name"
            icon={User}
            value={form.fullName}
            onChange={update("fullName")}
            placeholder="Ramesh Sharma"
            error={errors.fullName}
          />
          <InputField
            label="Email Address"
            icon={Mail}
            value={form.email}
            onChange={update("email")}
            placeholder="you@shop.com"
            error={errors.email}
          />
          <InputField
            label="Password"
            icon={Lock}
            type={showPassword ? "text" : "password"}
            value={form.password}
            onChange={update("password")}
            placeholder="Create a password"
            error={errors.password}
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
          <InputField
            label="Confirm Password"
            icon={Lock}
            type={showConfirm ? "text" : "password"}
            value={form.confirmPassword}
            onChange={update("confirmPassword")}
            placeholder="Re-enter your password"
            error={errors.confirmPassword}
            rightElement={
              <button
                type="button"
                onClick={() => setShowConfirm((s) => !s)}
                className="text-ink/40 hover:text-ink/70"
              >
                {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            }
          />

          <Button type="submit" fullWidth className="mt-1">
            Sign Up
          </Button>
        </form>

        <p className="mt-5 text-center text-[13px] text-ink/60">
          Already have an account?{" "}
          <button
            onClick={onGoToLogin}
            className="font-medium text-secondary hover:text-primary"
          >
            Login
          </button>
        </p>
      </div>
    </div>
  );
}
