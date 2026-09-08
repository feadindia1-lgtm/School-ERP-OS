import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

const field = "mt-2 h-11 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";

export default function StepAdministrator({ value, set }) {
  const v = value.administrator;
  const s = set("administrator");
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div><Label className="overline">Full name</Label><Input data-testid="w-admin-name" required value={v.full_name} onChange={(e)=>s({full_name:e.target.value})} className={field} /></div>
      <div><Label className="overline">Email</Label><Input data-testid="w-admin-email" required type="email" value={v.email} onChange={(e)=>s({email:e.target.value})} className={field} /></div>
      <div><Label className="overline">Mobile</Label><Input data-testid="w-admin-mobile" value={v.mobile} onChange={(e)=>s({mobile:e.target.value})} className={field} /></div>
      <div>
        <Label className="overline">Temporary password (optional)</Label>
        <Input data-testid="w-admin-password" type="password" value={v.temp_password} onChange={(e)=>s({temp_password:e.target.value})} placeholder="Leave blank to auto-generate" className={field} />
      </div>
      <div className="md:col-span-2 mt-2 flex items-center gap-3 p-4 border border-[var(--tinted-grey-200)]">
        <Switch data-testid="w-admin-invite" checked={v.send_invite} onCheckedChange={(x)=>s({send_invite:x})} />
        <div>
          <div className="text-sm font-semibold">Send onboarding invite email</div>
          <div className="text-xs text-[var(--tinted-grey-500)]">Administrator receives a magic link and can set their own password.</div>
        </div>
      </div>
    </div>
  );
}
