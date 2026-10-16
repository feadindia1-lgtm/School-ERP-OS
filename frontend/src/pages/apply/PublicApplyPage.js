import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ApplicantFormFields, ApplyShell, EMPTY_FORM, toPayload } from "./ApplicantFormFields";

export default function PublicApplyPage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [config, setConfig] = useState(null);
  const [error, setError] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [honey, setHoney] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get(`/public/admissions/schools/${slug}/form`)
      .then(({ data }) => setConfig(data))
      .catch((e) => setError(formatApiError(e)));
  }, [slug]);

  const submit = async (e) => {
    e.preventDefault();
    try {
      setBusy(true);
      const { data } = await api.post(`/public/admissions/schools/${slug}/apply`, { ...toPayload(form), website: honey || null });
      toast.success(`Application ${data.application_number} received`);
      navigate(data.url_path, { replace: true, state: { justSubmitted: true } });
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  if (error) return <ApplyShell><div className="text-sm" data-testid="apply-error">{error}</div></ApplyShell>;
  if (!config) return <ApplyShell><div className="text-sm text-[var(--tinted-grey-500)]">Loading…</div></ApplyShell>;
  return (
    <ApplyShell school={config.school}>
      <h1 className="font-heading font-black text-4xl sm:text-5xl tracking-tighter" data-testid="apply-title">Apply for admission</h1>
      {config.intro_text && <p className="mt-3 text-sm text-[var(--tinted-grey-500)] max-w-xl" data-testid="apply-intro">{config.intro_text}</p>}
      <form onSubmit={submit} className="mt-10 space-y-10">
        <ApplicantFormFields form={form} setForm={setForm} config={config} />
        <input type="text" tabIndex={-1} autoComplete="off" value={honey} onChange={(e) => setHoney(e.target.value)} className="hidden" aria-hidden="true" name="website" />
        {config.document_types.length > 0 && (
          <div className="text-xs text-[var(--tinted-grey-500)] border-l-2 border-[var(--klein)] pl-3" data-testid="apply-docs-hint">
            After you submit, you'll get a private link to upload: {config.document_types.map((d) => d.label).join(", ")}.
          </div>
        )}
        <Button type="submit" disabled={busy} className="rounded-full h-12 px-8 bg-[var(--klein)] text-white hover:opacity-90" data-testid="apply-submit">
          {busy ? "Submitting…" : "Submit application"}
        </Button>
      </form>
    </ApplyShell>
  );
}
