import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Buildings } from "@phosphor-icons/react";
import AppHeader from "@/components/AppHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

const field =
  "mt-2 h-11 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";

export default function RegisterSchoolPage() {
  const { registerSchool } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    school_name: "",
    slug: "",
    contact_email: "",
    country: "",
    owner_full_name: "",
    owner_email: "",
    owner_password: "",
  });
  const [busy, setBusy] = useState(false);

  const upd = (k) => (e) => {
    const v = e.target.value;
    setForm((f) => ({ ...f, [k]: k === "slug" ? v.toLowerCase().replace(/[^a-z0-9-]/g, "") : v }));
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    const res = await registerSchool(form);
    setBusy(false);
    if (!res.ok) return toast.error(res.error);
    toast.success("School onboarded");
    navigate("/school");
  };

  return (
    <div className="min-h-screen bg-[var(--paper)]" data-testid="register-page">
      <AppHeader variant="marketing" />
      <div className="max-w-[1400px] mx-auto px-6 lg:px-10 py-12 lg:py-16 grid grid-cols-1 lg:grid-cols-12 gap-10">
        <div className="lg:col-span-4">
          <div className="overline mb-6">Onboard</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter leading-tight">
            Spin up your school's tenant.
          </h1>
          <p className="mt-4 text-[var(--tinted-grey-500)]">
            You'll become the owner (<span className="font-mono text-xs">school_owner</span>) — the highest role
            within your tenant. Nothing you create is visible to any other school on this platform.
          </p>
          <div className="mt-8 p-6 bg-white border border-[var(--tinted-grey-200)]">
            <Buildings size={22} weight="duotone" className="text-[var(--klein)]" />
            <div className="mt-3 font-heading font-bold">What gets created</div>
            <ul className="mt-3 space-y-1 text-sm text-[var(--tinted-grey-500)]">
              <li>· One tenant with a unique slug</li>
              <li>· One owner user with full school-admin permissions</li>
              <li>· Audit events for tenant creation and registration</li>
            </ul>
          </div>
        </div>

        <motion.form
          data-testid="register-form"
          onSubmit={onSubmit}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="lg:col-span-8 bg-white border border-[var(--tinted-grey-200)] p-8 lg:p-10"
        >
          <div className="overline mb-4">School</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <Label htmlFor="school_name" className="overline">School name</Label>
              <Input id="school_name" required minLength={2} value={form.school_name} onChange={upd("school_name")} className={field} data-testid="reg-school-name" />
            </div>
            <div>
              <Label htmlFor="slug" className="overline">Slug (url)</Label>
              <Input id="slug" required minLength={2} value={form.slug} onChange={upd("slug")} placeholder="riverside" className={`${field} font-mono`} data-testid="reg-slug" />
            </div>
            <div>
              <Label htmlFor="contact_email" className="overline">Contact email</Label>
              <Input id="contact_email" type="email" required value={form.contact_email} onChange={upd("contact_email")} className={field} data-testid="reg-contact-email" />
            </div>
            <div>
              <Label htmlFor="country" className="overline">Country</Label>
              <Input id="country" value={form.country} onChange={upd("country")} className={field} data-testid="reg-country" />
            </div>
          </div>

          <div className="overline mt-10 mb-4">Owner account</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <Label htmlFor="owner_full_name" className="overline">Full name</Label>
              <Input id="owner_full_name" required minLength={2} value={form.owner_full_name} onChange={upd("owner_full_name")} className={field} data-testid="reg-owner-name" />
            </div>
            <div>
              <Label htmlFor="owner_email" className="overline">Email</Label>
              <Input id="owner_email" type="email" required value={form.owner_email} onChange={upd("owner_email")} className={field} data-testid="reg-owner-email" />
            </div>
            <div className="md:col-span-2">
              <Label htmlFor="owner_password" className="overline">Password (min 8)</Label>
              <Input id="owner_password" type="password" required minLength={8} value={form.owner_password} onChange={upd("owner_password")} className={field} data-testid="reg-owner-password" />
            </div>
          </div>

          <Button
            data-testid="register-submit"
            type="submit"
            disabled={busy}
            className="mt-10 h-12 rounded-none bg-[var(--klein)] hover:bg-[var(--klein-hover)] text-white px-8 transition-colors"
          >
            {busy ? "Creating…" : (<>Onboard school <ArrowRight size={18} className="ml-2" /></>)}
          </Button>
          <div className="mt-4 text-sm text-[var(--tinted-grey-500)]">
            Already onboarded? <Link to="/login" className="klein-underline text-[var(--klein)] font-semibold" data-testid="reg-link-login">Sign in →</Link>
          </div>
        </motion.form>
      </div>
    </div>
  );
}
