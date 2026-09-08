import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight } from "@phosphor-icons/react";
import AppHeader from "@/components/AppHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenantSlug, setTenantSlug] = useState("");
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    const res = await login(email, password, tenantSlug.trim() || null);
    setBusy(false);
    if (!res.ok) return toast.error(res.error);
    toast.success("Welcome back");
    navigate(res.user.role === "platform_superadmin" ? "/platform" : "/school");
  };

  return (
    <div className="min-h-screen bg-[var(--paper)]" data-testid="login-page">
      <AppHeader variant="marketing" />
      <div className="max-w-[1400px] mx-auto px-6 lg:px-10 py-16 lg:py-24 grid grid-cols-1 lg:grid-cols-12 gap-12">
        <div className="lg:col-span-5">
          <div className="overline mb-6">Sign in</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter leading-tight">
            Back to your console.
          </h1>
          <p className="mt-4 text-[var(--tinted-grey-500)] max-w-md">
            Platform super admins land on the platform console. School users land on their school console — their
            data is invisible to every other tenant on this platform.
          </p>
        </div>

        <motion.form
          data-testid="login-form"
          onSubmit={onSubmit}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="lg:col-span-6 lg:col-start-7 bg-white border border-[var(--tinted-grey-200)] p-8 lg:p-10"
        >
          <div className="space-y-5">
            <div>
              <Label htmlFor="email" className="overline">Email</Label>
              <Input
                id="email"
                data-testid="login-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                className="mt-2 h-12 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0 text-lg"
                placeholder="you@school.example"
              />
            </div>
            <div>
              <Label htmlFor="password" className="overline">Password</Label>
              <Input
                id="password"
                data-testid="login-password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                className="mt-2 h-12 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0 text-lg"
              />
            </div>
            <div>
              <Label htmlFor="tenant" className="overline">School slug <span className="normal-case tracking-normal text-[var(--tinted-grey-400)]">(optional)</span></Label>
              <Input
                id="tenant"
                data-testid="login-tenant-slug"
                value={tenantSlug}
                onChange={(e) => setTenantSlug(e.target.value)}
                placeholder="e.g. riverside"
                className="mt-2 h-12 rounded-none border-x-0 border-t-0 border-b border-[var(--tinted-grey-300)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0"
              />
            </div>
          </div>

          <Button
            data-testid="login-submit"
            type="submit"
            disabled={busy}
            className="mt-8 h-12 w-full rounded-none bg-[var(--ink)] hover:bg-[var(--klein)] text-white transition-colors"
          >
            {busy ? "Signing in…" : (<>Sign in <ArrowRight size={18} className="ml-2" /></>)}
          </Button>
          <div className="mt-6 flex items-center justify-between text-sm">
            <span className="text-[var(--tinted-grey-500)]">New school?</span>
            <Link to="/register" className="klein-underline text-[var(--klein)] font-semibold" data-testid="login-link-register">Register →</Link>
          </div>
        </motion.form>
      </div>
    </div>
  );
}
