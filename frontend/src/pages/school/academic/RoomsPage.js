import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Trash, DoorOpen } from "@phosphor-icons/react";
import { ROOM_TYPES } from "./_shared";

const field = "mt-2 h-10 rounded-none border-x-0 border-t-0 border-b-2 border-[var(--ink)] focus-visible:ring-0 focus-visible:border-[var(--klein)] px-0";

export default function RoomsPage() {
  const [rooms, setRooms] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", code: "", room_type: "classroom", capacity: 30, floor: "", building: "" });

  const load = async () => {
    try { const { data } = await api.get("/school/academic/rooms"); setRooms(data); }
    catch (e) { toast.error(formatApiError(e)); }
  };
  useEffect(() => { load(); }, []);

  const submit = async () => {
    if (!form.name || !form.code) return toast.error("Name & code required");
    try {
      const payload = { ...form };
      if (!payload.capacity) delete payload.capacity;
      Object.keys(payload).forEach(k => payload[k] === "" && delete payload[k]);
      await api.post("/school/academic/rooms", payload);
      toast.success("Room created"); setOpen(false);
      setForm({ name: "", code: "", room_type: "classroom", capacity: 30, floor: "", building: "" }); load();
    } catch (e) { toast.error(formatApiError(e)); }
  };
  const del = async (id) => {
    if (!window.confirm("Delete this room?")) return;
    try { await api.delete(`/school/academic/rooms/${id}`); toast.success("Deleted"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div data-testid="rooms-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="overline mb-2">Academic Framework</div>
          <h1 className="font-heading font-black text-4xl lg:text-5xl tracking-tighter" data-testid="rooms-title">Rooms</h1>
          <div className="mt-2 text-sm text-[var(--tinted-grey-500)]">{rooms.length} room{rooms.length === 1 ? "" : "s"}</div>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="btn-new-room" className="rounded-full bg-[var(--klein)] hover:opacity-90 text-white"><Plus size={14} className="mr-1" /> New room</Button>
          </DialogTrigger>
          <DialogContent className="rounded-none max-w-md">
            <DialogHeader><DialogTitle>New room</DialogTitle></DialogHeader>
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2"><Label className="overline">Name</Label><Input placeholder="Room 101" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className={field} data-testid="rm-name" /></div>
              <div><Label className="overline">Code</Label><Input placeholder="R101" value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} className={field} data-testid="rm-code" /></div>
              <div><Label className="overline">Type</Label>
                <Select value={form.room_type} onValueChange={v => setForm({ ...form, room_type: v })}>
                  <SelectTrigger className="rounded-none h-10 mt-2" data-testid="rm-type"><SelectValue /></SelectTrigger>
                  <SelectContent>{ROOM_TYPES.map(t => <SelectItem key={t} value={t} data-testid={`rmt-${t}`}>{t.replace("_"," ")}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div><Label className="overline">Capacity</Label><Input type="number" value={form.capacity} onChange={e => setForm({ ...form, capacity: parseInt(e.target.value || "0") })} className={field} data-testid="rm-cap" /></div>
              <div><Label className="overline">Floor</Label><Input value={form.floor} onChange={e => setForm({ ...form, floor: e.target.value })} className={field} data-testid="rm-floor" /></div>
              <div className="col-span-2"><Label className="overline">Building</Label><Input value={form.building} onChange={e => setForm({ ...form, building: e.target.value })} className={field} data-testid="rm-bldg" /></div>
            </div>
            <DialogFooter><Button onClick={submit} data-testid="rm-submit" className="rounded-none bg-[var(--klein)] text-white">Create</Button></DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="mt-8 bg-white border border-[var(--tinted-grey-200)]">
        <Table data-testid="rooms-table">
          <TableHeader>
            <TableRow>
              <TableHead>Code</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Capacity</TableHead>
              <TableHead>Location</TableHead>
              <TableHead className="text-right"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rooms.length === 0 && <TableRow><TableCell colSpan={6} className="text-center py-10 text-[var(--tinted-grey-500)]" data-testid="rooms-empty">No rooms yet.</TableCell></TableRow>}
            {rooms.map(r => (
              <TableRow key={r.id} data-testid={`room-row-${r.id}`}>
                <TableCell className="font-mono text-xs">{r.code}</TableCell>
                <TableCell className="font-heading font-semibold"><DoorOpen size={14} weight="duotone" className="text-[var(--klein)] inline mr-2"/>{r.name}</TableCell>
                <TableCell className="capitalize">{(r.room_type || "").replace("_"," ")}</TableCell>
                <TableCell>{r.capacity ?? "—"}</TableCell>
                <TableCell className="text-xs">{[r.building, r.floor].filter(Boolean).join(" · ") || "—"}</TableCell>
                <TableCell className="text-right"><button onClick={() => del(r.id)} className="text-[var(--tinted-grey-400)] hover:text-[var(--accent-red)]" data-testid={`btn-del-room-${r.id}`}><Trash size={14}/></button></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
