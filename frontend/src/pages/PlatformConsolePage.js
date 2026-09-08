import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Buildings, ShieldCheck, Users, ClockCounterClockwise } from "@phosphor-icons/react";
import AppHeader from "@/components/AppHeader";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

function KpiCard({ icon: Icon, label, value, hint }) {
  return (
    <motion.div
      whileHover={{ y: -4 }}
      transition={{ duration: 0.2 }}
      className="bg-white border border-[var(--tinted-grey-200)] p-6 h-full"
    >
      <div className="flex items-start justify-between">
        <Icon size={22} weight="duotone" className="text-[var(--klein)]" />
        <span className="overline">{label}</span>
      </div>
      <div className="mt-6 font-heading font-black text-4xl tracking-tight tabular">{value}</div>
      {hint && <div className="mt-1 text-xs text-[var(--tinted-grey-500)]">{hint}</div>}
    </motion.div>
  );
}

export default function PlatformConsolePage() {
  const [stats, setStats] = useState(null);
  const [tenants, setTenants] = useState([]);
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    (async () => {
      try {
        const [s, t, l] = await Promise.all([
          api.get("/platform/stats"),
          api.get("/platform/tenants"),
          api.get("/platform/audit-logs?limit=50"),
        ]);
        setStats(s.data);
        setTenants(t.data);
        setLogs(l.data);
      } catch (e) {
        toast.error(formatApiError(e));
      }
    })();
  }, []);

  return (
    <div className="min-h-screen bg-[var(--paper)]" data-testid="platform-console">
      <AppHeader variant="console" />
      <div className="max-w-[1400px] mx-auto px-6 lg:px-10 py-10">
        <div className="overline mb-3">Platform · Super admin</div>
        <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="platform-title">
          Every school. One console.
        </h1>

        <div className="mt-10 grid grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
          <KpiCard icon={Buildings} label="Tenants" value={stats?.tenants ?? "—"} hint={`${stats?.active_tenants ?? 0} active`} />
          <KpiCard icon={Users} label="Users" value={stats?.users ?? "—"} hint="Across all tenants" />
          <KpiCard icon={ClockCounterClockwise} label="Audit events" value={stats?.audit_events ?? "—"} hint="Since inception" />
          <KpiCard icon={ShieldCheck} label="API" value="v1" hint="/api/v1 · JWT" />
        </div>

        <div className="mt-12">
          <Tabs defaultValue="tenants">
            <TabsList className="rounded-none bg-transparent h-auto border-b border-[var(--tinted-grey-200)] w-full justify-start p-0">
              <TabsTrigger value="tenants" data-testid="tab-tenants" className="rounded-none border-b-2 border-transparent data-[state=active]:border-[var(--klein)] data-[state=active]:bg-transparent data-[state=active]:shadow-none px-6 py-3 font-heading font-semibold">
                Tenants
              </TabsTrigger>
              <TabsTrigger value="audit" data-testid="tab-audit" className="rounded-none border-b-2 border-transparent data-[state=active]:border-[var(--klein)] data-[state=active]:bg-transparent data-[state=active]:shadow-none px-6 py-3 font-heading font-semibold">
                Audit log
              </TabsTrigger>
            </TabsList>

            <TabsContent value="tenants" className="mt-6">
              <div className="bg-white border border-[var(--tinted-grey-200)]">
                <Table data-testid="tenants-table">
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[280px]">School</TableHead>
                      <TableHead>Slug</TableHead>
                      <TableHead>Contact</TableHead>
                      <TableHead>Plan</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Created</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tenants.length === 0 && (
                      <TableRow><TableCell colSpan={6} className="text-center py-10 text-[var(--tinted-grey-500)]">No schools yet.</TableCell></TableRow>
                    )}
                    {tenants.map((t) => (
                      <TableRow key={t.id} data-testid={`tenant-row-${t.slug}`}>
                        <TableCell className="font-heading font-semibold">{t.name}</TableCell>
                        <TableCell className="font-mono text-xs">{t.slug}</TableCell>
                        <TableCell>{t.contact_email}</TableCell>
                        <TableCell><Badge variant="outline" className="rounded-none uppercase text-[10px] tracking-widest">{t.plan}</Badge></TableCell>
                        <TableCell>
                          <span className={`inline-flex items-center gap-2 text-xs ${t.status === "active" ? "text-[var(--klein)]" : "text-[var(--accent-red)]"}`}>
                            <span className={`h-1.5 w-1.5 rounded-full ${t.status === "active" ? "bg-[var(--klein)]" : "bg-[var(--accent-red)]"}`} />
                            {t.status}
                          </span>
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs tabular">{new Date(t.created_at).toISOString().slice(0, 10)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>

            <TabsContent value="audit" className="mt-6">
              <div className="bg-white border border-[var(--tinted-grey-200)]">
                <Table data-testid="platform-audit-table">
                  <TableHeader>
                    <TableRow>
                      <TableHead>Timestamp</TableHead>
                      <TableHead>Action</TableHead>
                      <TableHead>Actor</TableHead>
                      <TableHead>Resource</TableHead>
                      <TableHead>Tenant</TableHead>
                      <TableHead>IP</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logs.length === 0 && (
                      <TableRow><TableCell colSpan={6} className="text-center py-10 text-[var(--tinted-grey-500)]">No audit events yet.</TableCell></TableRow>
                    )}
                    {logs.map((l) => (
                      <TableRow key={l.id}>
                        <TableCell className="font-mono text-xs tabular">{new Date(l.created_at).toISOString().replace("T", " ").slice(0, 19)}</TableCell>
                        <TableCell><code className="text-xs text-[var(--klein)]">{l.action}</code></TableCell>
                        <TableCell className="text-xs">{l.actor_email || "—"}</TableCell>
                        <TableCell className="text-xs">{l.resource}{l.resource_id ? ` · ${l.resource_id.slice(-6)}` : ""}</TableCell>
                        <TableCell className="font-mono text-xs">{l.tenant_id ? l.tenant_id.slice(-6) : "platform"}</TableCell>
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
