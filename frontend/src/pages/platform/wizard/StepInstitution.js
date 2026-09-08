import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const field = "mt-2 h-11 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";

export default function StepInstitution({ value, set }) {
  const v = value.institution;
  const s = set("institution");
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div>
        <Label className="overline">School name</Label>
        <Input data-testid="w-school-name" required value={v.school_name} onChange={(e) => s({ school_name: e.target.value })} className={field} />
      </div>
      <div>
        <Label className="overline">Slug (URL)</Label>
        <Input data-testid="w-slug" required value={v.slug}
          onChange={(e) => s({ slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "") })}
          placeholder="e.g. oakwood" className={`${field} font-mono`} />
      </div>
      <div>
        <Label className="overline">Short name</Label>
        <Input data-testid="w-short-name" value={v.short_name} onChange={(e) => s({ short_name: e.target.value })} className={field} />
      </div>
      <div>
        <Label className="overline">School code</Label>
        <Input data-testid="w-school-code" value={v.school_code} onChange={(e) => s({ school_code: e.target.value })} placeholder="OAK-001" className={`${field} font-mono`} />
      </div>
      <div>
        <Label className="overline">Board</Label>
        <Select value={v.board} onValueChange={(x) => s({ board: x })}>
          <SelectTrigger data-testid="w-board" className="mt-2 rounded-none h-11 border-x-0 border-t-0 border-b-2 border-[var(--ink)]"><SelectValue /></SelectTrigger>
          <SelectContent>
            {[["cbse","CBSE"],["cisce","CISCE"],["state_board","State Board"],["ib","IB"],["cambridge","Cambridge"],["other","Other"]].map(([v,l])=>(
              <SelectItem key={v} value={v} data-testid={`w-board-${v}`}>{l}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label className="overline">School type</Label>
        <Select value={v.school_type} onValueChange={(x) => s({ school_type: x })}>
          <SelectTrigger data-testid="w-school-type" className="mt-2 rounded-none h-11 border-x-0 border-t-0 border-b-2 border-[var(--ink)]"><SelectValue /></SelectTrigger>
          <SelectContent>
            {[["pre_primary","Pre-primary"],["primary","Primary"],["secondary","Secondary"],["senior_secondary","Senior Secondary"],["k12","K-12"]].map(([v,l])=>(
              <SelectItem key={v} value={v} data-testid={`w-school-type-${v}`}>{l}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
