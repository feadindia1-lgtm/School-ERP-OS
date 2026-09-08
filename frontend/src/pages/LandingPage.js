import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Buildings,
  UsersFour,
  ShieldCheck,
  Fingerprint,
  Stack,
  Graph,
  ArrowUpRight,
  Circle,
} from "@phosphor-icons/react";
import AppHeader from "@/components/AppHeader";
import { Button } from "@/components/ui/button";

const HERO_IMG =
  "https://images.unsplash.com/photo-1777378543333-b4fb4f96fdd3?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMzN8MHwxfHNlYXJjaHw0fHxtb2Rlcm4lMjBzY2hvb2wlMjBidWlsZGluZyUyMGV4dGVyaW9yfGVufDB8fHx8MTc4ODg2NjcxM3ww&ixlib=rb-4.1.0&q=85";
const STUDENTS_IMG =
  "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NjZ8MHwxfHNlYXJjaHwzfHxzdHVkZW50cyUyMGxlYXJuaW5nJTIwY2xhc3Nyb29tfGVufDB8fHx8MTc4ODg2NjcxM3ww&ixlib=rb-4.1.0&q=85";
const ADMIN_IMG =
  "https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzZ8MHwxfHNlYXJjaHwxfHxhZG1pbmlzdHJhdG9yJTIwd29ya2luZyUyMGxhcHRvcHxlbnwwfHx8fDE3ODg4NjY3MTN8MA&ixlib=rb-4.1.0&q=85";

const fadeIn = {
  hidden: { opacity: 0, y: 24 },
  show: (i = 0) => ({ opacity: 1, y: 0, transition: { duration: 0.55, delay: i * 0.06, ease: [0.2, 0.7, 0.2, 1] } }),
};

export default function LandingPage() {
  return (
    <div data-testid="landing-page" className="bg-[var(--paper)] min-h-screen">
      <AppHeader variant="marketing" />

      {/* HERO — bento asymmetric */}
      <section className="relative border-b border-[var(--tinted-grey-200)]">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-10 pt-16 pb-24">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-start">
            <div className="lg:col-span-8">
              <motion.div initial="hidden" animate="show" variants={fadeIn} className="overline mb-6" data-testid="hero-eyebrow">
                <Circle size={8} weight="fill" className="inline mr-2 text-[var(--klein)]" />
                Prompt 0 · Foundation live · v0.1
              </motion.div>
              <motion.h1
                initial="hidden"
                animate="show"
                custom={1}
                variants={fadeIn}
                data-testid="hero-title"
                className="font-heading font-black tracking-tighter text-5xl sm:text-6xl lg:text-[92px] leading-[0.95]"
              >
                Run a school<br />
                <span className="text-[var(--klein)]">the way it deserves</span> to be run.
              </motion.h1>
              <motion.p
                initial="hidden"
                animate="show"
                custom={2}
                variants={fadeIn}
                className="mt-6 text-lg text-[var(--tinted-grey-500)] max-w-xl leading-relaxed"
              >
                School OS is a production-grade, multi-tenant SaaS that unifies your admissions
                pipeline and your entire academic operation on one API-first backbone.
              </motion.p>
              <motion.div initial="hidden" animate="show" custom={3} variants={fadeIn} className="mt-10 flex flex-wrap gap-4">
                <Link to="/register">
                  <Button
                    data-testid="hero-cta-register"
                    className="rounded-full bg-[var(--klein)] hover:bg-[var(--klein-hover)] text-white h-12 px-7 text-base transition-colors"
                  >
                    Onboard your school <ArrowUpRight size={18} className="ml-2" />
                  </Button>
                </Link>
                <Link to="/login">
                  <Button
                    data-testid="hero-cta-login"
                    variant="outline"
                    className="rounded-full border-[var(--ink)] text-[var(--ink)] hover:bg-[var(--ink)] hover:text-white h-12 px-7 text-base transition-colors"
                  >
                    Sign in
                  </Button>
                </Link>
              </motion.div>

              <motion.div initial="hidden" animate="show" custom={4} variants={fadeIn} className="mt-16 grid grid-cols-3 gap-6 max-w-xl">
                {[
                  { k: "11", v: "Roles" },
                  { k: "24", v: "Permissions" },
                  { k: "∞", v: "Tenants" },
                ].map((m) => (
                  <div key={m.v} className="border-t-2 border-[var(--ink)] pt-3">
                    <div className="font-heading font-black text-3xl tabular">{m.k}</div>
                    <div className="overline mt-1">{m.v}</div>
                  </div>
                ))}
              </motion.div>
            </div>

            <div className="lg:col-span-4 lg:pt-8">
              <motion.div
                initial={{ opacity: 0, scale: 0.96 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.7, delay: 0.1 }}
                className="relative aspect-[3/4] overflow-hidden bg-[var(--ink)]"
                data-testid="hero-image"
              >
                <img src={HERO_IMG} alt="School" className="absolute inset-0 h-full w-full object-cover mix-blend-luminosity opacity-90" />
                <div className="absolute inset-0 bg-[var(--klein)] mix-blend-multiply opacity-30" />
                <div className="absolute bottom-6 left-6 right-6 text-white">
                  <div className="overline text-white/70">The SaaS backbone for</div>
                  <div className="font-heading font-black text-3xl tracking-tighter">Hundreds of schools.</div>
                </div>
              </motion.div>
              <div className="mt-4 font-mono text-xs text-[var(--tinted-grey-500)]">
                /api/v1 · JWT · multi-tenant · RBAC · audit
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FRONT PORCH */}
      <section id="front-porch" className="border-b border-[var(--tinted-grey-200)]">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-10 py-24 grid grid-cols-1 lg:grid-cols-12 gap-10">
          <div className="lg:col-span-5">
            <div className="overline mb-4">01 · Front Porch</div>
            <h2 className="font-heading font-black text-4xl lg:text-5xl tracking-tight">
              The CRM every admissions team wishes they had.
            </h2>
            <p className="mt-6 text-[var(--tinted-grey-500)] leading-relaxed">
              Inquiry → Follow-up → Campus Visit → Application → Documents → Approval → Admission Fee →
              Student. When an applicant is approved, they don't get re-entered into the ERP. They convert.
            </p>
          </div>
          <div className="lg:col-span-7">
            <div className="relative aspect-[16/10] overflow-hidden">
              <img src={STUDENTS_IMG} alt="Students" className="absolute inset-0 h-full w-full object-cover" />
              <div className="absolute inset-0 border border-[var(--ink)]" />
            </div>
            <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-px bg-[var(--tinted-grey-200)] border border-[var(--tinted-grey-200)]">
              {["Inquiry", "Application", "Approval", "Conversion"].map((s, i) => (
                <div key={s} className="bg-white p-5">
                  <div className="font-mono text-xs text-[var(--klein)]">STAGE 0{i + 1}</div>
                  <div className="mt-2 font-heading font-bold text-lg">{s}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* MAIN HOUSE */}
      <section id="main-house" className="border-b border-[var(--tinted-grey-200)] bg-[var(--ink)] text-white relative overflow-hidden">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-10 py-24 grid grid-cols-1 lg:grid-cols-12 gap-10">
          <div className="lg:col-span-7 order-2 lg:order-1">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-px bg-white/10 border border-white/10">
              {[
                { i: Buildings, t: "Students" },
                { i: UsersFour, t: "Attendance" },
                { i: Stack, t: "Timetable" },
                { i: Graph, t: "Fees" },
                { i: Fingerprint, t: "Payroll" },
                { i: ShieldCheck, t: "Exams" },
              ].map(({ i: Icon, t }) => (
                <div key={t} className="bg-[var(--ink)] p-6">
                  <Icon size={22} weight="duotone" className="text-[var(--accent-yellow)]" />
                  <div className="mt-3 font-heading font-bold">{t}</div>
                  <div className="mt-1 text-white/50 text-sm">Module scaffold</div>
                </div>
              ))}
            </div>
          </div>
          <div className="lg:col-span-5 order-1 lg:order-2">
            <div className="overline text-white/60 mb-4">02 · Main House</div>
            <h2 className="font-heading font-black text-4xl lg:text-5xl tracking-tight">
              The ERP that runs the school after the doors open.
            </h2>
            <p className="mt-6 text-white/70 leading-relaxed">
              Student management, attendance, timetables, fees, payroll, academics, exams, curriculum
              tracking, communications, analytics. All API-first — the mobile apps consume the same
              endpoints as the web console.
            </p>
          </div>
        </div>
      </section>

      {/* ARCHITECTURE */}
      <section id="architecture" className="border-b border-[var(--tinted-grey-200)]">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-10 py-24">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
            <div className="lg:col-span-4">
              <div className="overline mb-4">03 · Architecture</div>
              <h2 className="font-heading font-black text-4xl lg:text-5xl tracking-tight">
                Built for hundreds of schools.<br />Not one.
              </h2>
            </div>
            <div className="lg:col-span-8 grid grid-cols-1 sm:grid-cols-2 gap-px bg-[var(--tinted-grey-200)] border border-[var(--tinted-grey-200)]">
              {[
                { t: "Multi-tenant by default", d: "Every school-owned record is scoped by tenant_id — enforced at the service layer, never the UI." },
                { t: "Granular RBAC", d: "24 permissions across 11 roles. Authorization checks strings like fees.refund, never role names." },
                { t: "Audit everything", d: "Sensitive actions record actor, resource, IP, old + new value into a queryable audit trail." },
                { t: "API-first, versioned", d: "/api/v1 today, /api/v2 tomorrow. Native apps consume the exact same endpoints." },
              ].map((c) => (
                <div key={c.t} className="bg-white p-8">
                  <div className="font-heading font-bold text-xl">{c.t}</div>
                  <p className="mt-3 text-[var(--tinted-grey-500)] leading-relaxed text-sm">{c.d}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-b border-[var(--tinted-grey-200)] bg-[var(--klein)] text-white">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-10 py-20 flex flex-col lg:flex-row items-start lg:items-end justify-between gap-8">
          <div className="max-w-2xl">
            <div className="overline text-white/70 mb-4">Start now</div>
            <h3 className="font-heading font-black text-4xl lg:text-5xl tracking-tight">
              Register your school and boot your tenant in under sixty seconds.
            </h3>
          </div>
          <Link to="/register">
            <Button
              data-testid="cta-final-register"
              className="rounded-full bg-white text-[var(--klein)] hover:bg-[var(--accent-yellow)] h-12 px-7 text-base transition-colors"
            >
              Onboard a school <ArrowUpRight size={18} className="ml-2" />
            </Button>
          </Link>
        </div>
      </section>

      <footer className="py-10">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-sm text-[var(--tinted-grey-500)]">
          <div className="font-mono text-xs">© 2026 School OS · v0.1.0-foundation</div>
          <div className="flex items-center gap-6">
            <img src={ADMIN_IMG} alt="" className="hidden md:block h-10 w-10 object-cover rounded-full grayscale" />
            <span>API-first · Multi-tenant · RBAC · Audit</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
