import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Users, ShieldCheck, ClockCounterClockwise, Plus, GraduationCap, ChalkboardTeacher,
  CurrencyDollar, ClipboardText, Calendar as CalendarIcon, Books, EnvelopeSimple, ChartLineUp,
  Sparkle,
} from "@phosphor-icons/react";
import AppHeader from "@/components/AppHeader";
import ImpersonationBanner from "@/components/ImpersonationBanner";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAuth } from "@/context/AuthContext";

const MODULE_CARDS = [
  { key: "crm", i: EnvelopeSimple, t: "CRM (Front Porch)", d: "Inquiry → Application → Conversion" },
  { key: "attendance", i: ChalkboardTeacher, t: "Attendance", d: "Class-teacher & biometric" },
  { key: "fees", i: CurrencyDollar, t: "Fees", d: "Structures, collect, refunds" },
  { key: "payroll", i: ClipboardText, t: "Payroll", d: "Salary + statutory" },
  { key: "examinations", i: GraduationCap, t: "Examinations", d: "Marks & report cards" },
  { key: "curriculum", i: Books, t: "Curriculum", d: "Syllabus & lesson plans" },
  { key: "communication", i: EnvelopeSimple, t: "Communication", d: "Announcements & SMS" },
  { key: "ai_assistance", i: Sparkle, t: "AI Assistance", d: "Copilots across modules" },
];

const tabTrig = "rounded-none border-b-2 border-transparent data-[state=active]:border-[var(--klein)] data-[state=active]:bg-transparent data-[state=active]:shadow-none px-6 py-3 font-heading font-semibold";
const field = "mt-2 h-11 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";

function KpiCard({ icon: Icon, label, value, hint }) {
  return (
    <motion.div whileHover={{ y: -4 }} transition={{ duration: 0.2 }} className="bg-white border border-[var(--tinted-grey-200)] p-6 h-full">
      <div className="flex items-start justify-between">
        <Icon size={22} weight="duotone" className="text-[var(--klein)]" />
        <span className="overline">{label}</span>
      </div>
      <div className="mt-6 font-heading font-black text-4xl tracking-tight tabular">{value}</div>
      {hint && <div className="mt-1 text-xs text-[var(--tinted-grey-500)]">{hint}</div>}
    </motion.div>
  );
}

export default function SchoolConsolePage() {
  const { user } = useAuth();
  const [school, setSchool] = useState(null);
  const [users, setUsers] = useState([]);
  const [logs, setLogs] = useState([]);
  const [rbac, setRbac] = useState(null);
  const [openCreate, setOpenCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newUser, setNewUser] = useState({ email: "", full_name: "", password: "", role: "teacher" });

  const load = async () => {
    try {
      const [s, u, l, r] = await Promise.all([
        api.get("/school/"),
        api.get("/school/users"),
        api.get("/school/audit-logs?limit=50"),
        api.get("/school/rbac"),
      ]);
      setSchool(s.data); setUsers(u.data); setLogs(l.data); setRbac(r.data);
    } catch (e) { toast.error(formatApiError(e)); }
  };
  useEffect(() => { load(); }, []);

  const submitCreateUser = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      await api.post("/school/users", newUser);
      toast.success("User created");
      setOpenCreate(false);
      setNewUser({ email: "", full_name: "", password: "", role: "teacher" });
      load();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setCreating(false); }
  };

  return (
    <div className="min-h-screen bg-[var(--paper)]" data-testid="school-console">
      <ImpersonationBanner />
      <AppHeader variant="console" />
      <div className="max-w-[1400px] mx-auto px-6 lg:px-10 py-10">
        <div className="overline mb-3">School Console</div>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="school-title">
              {school?.name || "Your school"}
            </h1>
            <div className="mt-2 font-mono text-xs text-[var(--tinted-grey-500)]">
              tenant · <span data-testid="school-slug">{school?.slug || "—"}</span> · plan {school?.plan}
            </div>
          </div>
        </div>

        <div className="mt-10 grid grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
          <KpiCard icon={Users} label="Users" value={users.length} hint={`Role: ${user?.role.replace(/_/g, " ")}`} />
          <KpiCard icon={ShieldCheck} label="Permissions" value={user?.permissions?.length ?? 0} hint="Granted to you" />
          <KpiCard icon={ClockCounterClockwise} label="Audit events" value={logs.length} hint="Recent" />
          <KpiCard icon={GraduationCap} label="Modules" value="0/8" hint="ERP coming soon" />
        </div>

        <div className="mt-12">
          <Tabs defaultValue="modules">
            <TabsList className="rounded-none bg-transparent h-auto border-b border-[var(--tinted-grey-200)] w-full justify-start p-0">
              <TabsTrigger value="modules" data-testid="tab-modules" className={tabTrig}>Modules</TabsTrigger>
              <TabsTrigger value="users" data-testid="tab-users" className={tabTrig}>Users</TabsTrigger>
              <TabsTrigger value="rbac" data-testid="tab-rbac" className={tabTrig}>Roles & Permissions</TabsTrigger>
              <TabsTrigger value="audit" data-testid="tab-audit" className={tabTrig}>Audit</TabsTrigger>
            </TabsList>

            <TabsContent value="modules" className="mt-6">
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-px bg-[var(--tinted-grey-200)] border border-[var(--tinted-grey-200)]">
                {MODULE_CARDS.map(({ key, i: Icon, t, d }) => {
                  const enabled = !!school?.modules?.[key];
                  return (
                    <div key={t} className={`bg-white p-6 relative overflow-hidden group ${enabled ? "" : "opacity-60"}`} data-testid={`module-${key}`}>
                      <Icon size={22} weight="duotone" className="text-[var(--klein)]" />
                      <div className="mt-4 font-heading font-bold text-lg">{t}</div>
                      <div className="text-sm text-[var(--tinted-grey-500)] mt-1">{d}</div>
                      <div className={`mt-6 overline ${enabled ? "text-[var(--klein)]" : "text-[var(--tinted-grey-400)]"}`}>
                        {enabled ? "Enabled · Coming soon" : "Disabled"}
                      </div>
                      <div className="absolute -right-6 -top-6 h-24 w-24 border border-[var(--tinted-grey-200)] rotate-45 group-hover:border-[var(--klein)] transition-colors" />
                    </div>
                  );
                })}
              </div>
            </TabsContent>

            <TabsContent value="users" className="mt-6">
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm text-[var(--tinted-grey-500)]">Users in <span className="font-mono">{school?.slug}</span></p>
                {user?.permissions?.includes("user.create") && (
                  <Dialog open={openCreate} onOpenChange={setOpenCreate}>
                    <DialogTrigger asChild>
                      <Button data-testid="btn-open-create-user" className="rounded-full bg-[var(--klein)] hover:bg-[var(--klein-hover)] text-white transition-colors">
                        <Plus size={16} className="mr-2" /> Add user
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="rounded-none max-w-md">
                      <DialogHeader><DialogTitle className="font-heading tracking-tight">New user</DialogTitle></DialogHeader>
                      <form onSubmit={submitCreateUser} data-testid="create-user-form">
                        <div className="space-y-4">
                          <div>
                            <Label htmlFor="nu-name" className="overline">Full name</Label>
                            <Input id="nu-name" required minLength={2} value={newUser.full_name} onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })} className={field} data-testid="new-user-name" />
                          </div>
                          <div>
                            <Label htmlFor="nu-email" className="overline">Email</Label>
                            <Input id="nu-email" required type="email" value={newUser.email} onChange={(e) => setNewUser({ ...newUser, email: e.target.value })} className={field} data-testid="new-user-email" />
                          </div>
                          <div>
                            <Label htmlFor="nu-password" className="overline">Password (min 8)</Label>
                            <Input id="nu-password" required type="password" minLength={8} value={newUser.password} onChange={(e) => setNewUser({ ...newUser, password: e.target.value })} className={field} data-testid="new-user-password" />
                          </div>
                          <div>
                            <Label className="overline">Role</Label>
                            <Select value={newUser.role} onValueChange={(v) => setNewUser({ ...newUser, role: v })}>
                              <SelectTrigger className="mt-2 rounded-none h-11 border-x-0 border-t-0 border-b-2 border-[var(--ink)]" data-testid="new-user-role">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {(rbac?.roles || []).map((r) => (
                                  <SelectItem key={r} value={r} data-testid={`role-option-${r}`}>{r.replace(/_/g, " ")}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                        <DialogFooter className="mt-6">
                          <Button type="submit" disabled={creating} className="rounded-none bg-[var(--ink)] hover:bg-[var(--klein)] text-white transition-colors" data-testid="submit-create-user">
                            {creating ? "Creating…" : "Create user"}
                          </Button>
                        </DialogFooter>
                      </form>
                    </DialogContent>
                  </Dialog>
                )}
              </div>

              <div className="bg-white border border-[var(--tinted-grey-200)]">
                <Table data-testid="users-table">
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {users.length === 0 && <TableRow><TableCell colSpan={4} className="text-center py-10 text-[var(--tinted-grey-500)]">No users yet.</TableCell></TableRow>}
                    {users.map((u) => (
                      <TableRow key={u.id} data-testid={`user-row-${u.email}`}>
                        <TableCell className="font-heading font-semibold">{u.full_name}</TableCell>
                        <TableCell className="font-mono text-xs">{u.email}</TableCell>
                        <TableCell><span className="px-2 py-0.5 bg-[var(--tinted-grey-100)] text-[10px] uppercase tracking-widest">{u.role.replace(/_/g, " ")}</span></TableCell>
                        <TableCell>
                          <span className={`inline-flex items-center gap-2 text-xs ${u.status === "active" ? "text-[var(--klein)]" : "text-[var(--accent-red)]"}`}>
                            <span className={`h-1.5 w-1.5 rounded-full ${u.status === "active" ? "bg-[var(--klein)]" : "bg-[var(--accent-red)]"}`} />
                            {u.status}
                          </span>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>

            <TabsContent value="rbac" className="mt-6">
              <div className="bg-white border border-[var(--tinted-grey-200)] p-6">
                <p className="text-sm text-[var(--tinted-grey-500)] mb-6">Role → permission catalog for your school. Authorization checks these strings — never role names.</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {rbac && Object.entries(rbac.role_permissions).map(([role, perms]) => (
                    <div key={role} className="border border-[var(--tinted-grey-200)] p-5" data-testid={`rbac-role-${role}`}>
                      <div className="font-heading font-bold">{role.replace(/_/g, " ")}</div>
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        {perms.length === 0 && <span className="text-xs text-[var(--tinted-grey-400)]">no permissions</span>}
                        {perms.map((p) => (
                          <code key={p} className="text-[11px] px-1.5 py-0.5 bg-[var(--tinted-grey-100)] text-[var(--klein)]">{p}</code>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </TabsContent>

            <TabsContent value="audit" className="mt-6">
              <div className="bg-white border border-[var(--tinted-grey-200)]">
                <Table data-testid="school-audit-table">
                  <TableHeader>
                    <TableRow>
                      <TableHead>Timestamp</TableHead>
                      <TableHead>Action</TableHead>
                      <TableHead>Actor</TableHead>
                      <TableHead>Resource</TableHead>
                      <TableHead>IP</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logs.length === 0 && <TableRow><TableCell colSpan={5} className="text-center py-10 text-[var(--tinted-grey-500)]">No audit events yet.</TableCell></TableRow>}
                    {logs.map((l) => (
                      <TableRow key={l.id}>
                        <TableCell className="font-mono text-xs tabular">{new Date(l.created_at).toISOString().replace("T", " ").slice(0, 19)}</TableCell>
                        <TableCell><code className="text-xs text-[var(--klein)]">{l.action}</code></TableCell>
                        <TableCell className="text-xs">{l.actor_email || "—"}</TableCell>
                        <TableCell className="text-xs">{l.resource}</TableCell>
                        <TableCell className="font-mono text-xs">{l.ip || "—"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
