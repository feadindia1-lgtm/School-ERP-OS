import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const field = "mt-2 h-11 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";

export default function StepContact({ value, set }) {
  const v = value.contact;
  const s = set("contact");
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="md:col-span-2">
        <Label className="overline">Address</Label>
        <Input data-testid="w-address" value={v.address_line} onChange={(e) => s({ address_line: e.target.value })} className={field} />
      </div>
      <div><Label className="overline">City</Label><Input data-testid="w-city" value={v.city} onChange={(e)=>s({city:e.target.value})} className={field} /></div>
      <div><Label className="overline">District</Label><Input data-testid="w-district" value={v.district} onChange={(e)=>s({district:e.target.value})} className={field} /></div>
      <div><Label className="overline">State</Label><Input data-testid="w-state" value={v.state} onChange={(e)=>s({state:e.target.value})} className={field} /></div>
      <div><Label className="overline">PIN</Label><Input data-testid="w-pin" value={v.pin} onChange={(e)=>s({pin:e.target.value})} className={field} /></div>
      <div><Label className="overline">Country</Label><Input data-testid="w-country" value={v.country} onChange={(e)=>s({country:e.target.value})} className={field} /></div>
      <div><Label className="overline">Phone</Label><Input data-testid="w-phone" value={v.phone} onChange={(e)=>s({phone:e.target.value})} className={field} /></div>
      <div><Label className="overline">Email</Label><Input data-testid="w-contact-email" required type="email" value={v.email} onChange={(e)=>s({email:e.target.value})} className={field} /></div>
      <div className="md:col-span-2"><Label className="overline">Website</Label><Input data-testid="w-website" value={v.website} onChange={(e)=>s({website:e.target.value})} className={field} /></div>
    </div>
  );
}
