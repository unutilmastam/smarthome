import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../api/client";
import { qk, useMembers } from "../api/hooks";
import type { Role } from "../api/types";
import { errorText } from "../components/CommandStatus";
import { can } from "../lib/contracts";
import { useCurrentHome } from "../lib/home";

const ASSIGNABLE: Role[] = ["admin", "family", "guest", "viewer"];

export function Members() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { home } = useCurrentHome();
  const isOwner = can(home?.my_role, "manage_users");
  const members = useMembers(home?.id, can(home?.my_role, "configure"));
  const [form, setForm] = useState({ email: "", name: "", role: "family" as Role, initial_password: "" });
  const [err, setErr] = useState<string | null>(null);
  if (!isOwner) return <p className="muted">{t("members.ownerOnly")}</p>;
  const refresh = () => qc.invalidateQueries({ queryKey: qk.members(home!.id) });
  const act = async (fn: () => Promise<unknown>) => {
    setErr(null);
    try { await fn(); await refresh(); }
    catch (e) { setErr(e instanceof ApiError ? `${errorText(t, e.code, e.message)}` : t("errors.generic")); }
  };
  return (
    <div style={{ display: "grid", gap: 16 }}>
      <h2 style={{ margin: 0 }}>{t("members.title")}</h2>
      <section className="card">
        <table>
          <thead><tr><th>{t("members.name")}</th><th>{t("members.email")}</th><th>{t("members.role")}</th><th /></tr></thead>
          <tbody>{(members.data ?? []).map((m) => (
            <tr key={m.user_id}>
              <td>{m.name}</td><td>{m.email}</td>
              <td>{m.role === "owner" ? t("role.owner") : (
                <select aria-label={t("members.role")} value={m.role} style={{ width: "auto" }}
                  onChange={(e) => act(() => api.patch(`/homes/${home!.id}/members/${m.user_id}`, { role: e.target.value }))}>
                  {ASSIGNABLE.map((r) => <option key={r} value={r}>{t(`role.${r}`)}</option>)}
                </select>)}</td>
              <td>{m.role !== "owner" && <button onClick={() => act(() => api.del(`/homes/${home!.id}/members/${m.user_id}`))}>{t("members.remove")}</button>}</td>
            </tr>))}
          </tbody>
        </table>
      </section>
      <form className="card" onSubmit={(e) => {
        e.preventDefault();
        const body: Record<string, string> = { email: form.email, role: form.role };
        if (form.name) body.name = form.name;
        if (form.initial_password) body.initial_password = form.initial_password;
        void act(async () => { await api.post(`/homes/${home!.id}/members`, body); setForm({ email: "", name: "", role: "family", initial_password: "" }); });
      }}>
        <h3>{t("members.add")}</h3>
        <label>{t("members.email")}<input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
        <label>{t("members.name")}<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
        <label>{t("members.role")}
          <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })}>
            {ASSIGNABLE.map((r) => <option key={r} value={r}>{t(`role.${r}`)}</option>)}
          </select>
        </label>
        <label>{t("members.initialPassword")}<input type="password" autoComplete="new-password" minLength={10} value={form.initial_password} onChange={(e) => setForm({ ...form, initial_password: e.target.value })} /></label>
        {err && <p className="error" role="alert">{err}</p>}
        <button className="primary" type="submit">{t("app.add")}</button>
      </form>
    </div>
  );
}
