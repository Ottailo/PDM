import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ShieldCheck, UserPlus, ArrowUpRight, Building2 } from "lucide-react";
import { ApiError, clearReplayContext, mutate, setReplayContext } from "./api";
import { queryClient, useIdentity, useResource } from "./query";
import { can } from "./permissions";
import type { Company, Identity, Invitation, Member, Message, Role } from "./types";
import {
  Definition,
  Dialog,
  Empty,
  ErrorNotice,
  Field,
  Form,
  Loading,
  numeric,
  PageHeader,
  Select,
  Status,
  Submit,
  Textarea,
  useAction,
  value,
} from "./ui";
function InviteForm({ onClose }: { onClose: () => void }) {
  const identity = useIdentity().data!;
  const action = useAction(
    (form: FormData) =>
      mutate<Message>("/invitations", {
        email: value(form, "email"),
        role: value(form, "role"),
      }),
    "Invitation queued.",
  );
  return (
    <Dialog title="Invite a teammate" onClose={onClose}>
      {action.isSuccess ? (
        <>
          <div className="notice" role="status">
            <strong>{action.data.message}</strong>
          </div>
          <p>
            The invitation will let them join this organization. They won’t
            appear in the member list until they accept.
          </p>
          <button className="button primary" onClick={onClose}>
            Done
          </button>
        </>
      ) : (
        <>
          <p className="form-intro">
            Give each person the access they need. An organization owner cannot
            be invited through this form.
          </p>
          <Form onSubmit={(form) => action.mutate(form)}>
            <Field
              label="Teammate’s work email"
              type="email"
              name="email"
              autoComplete="email"
              required
              maxLength={120}
            />
            <Select label="Role" name="role" defaultValue="technician">
              {identity.membership.role === "owner" && (
                <option value="admin">Administrator / registry, team, and jobs</option>
              )}
              <option value="planner">
                Planner / machines, assignment, and approval
              </option>
              <option value="technician">
                Technician / assigned work and manuals
              </option>
              <option value="stores">Stores / view machines and work</option>
              <option value="viewer">Viewer / read-only records</option>
            </Select>
            <ErrorNotice error={action.error} />
            <Submit pending={action.isPending}>Send invitation</Submit>
          </Form>
        </>
      )}
    </Dialog>
  );
}
type AccessChange =
  | { kind: "remove" | "role"; member: Member }
  | { kind: "cancel"; invitation: Invitation };
const roleOptions: Role[] = ["owner", "admin", "planner", "technician", "stores", "viewer"];
function manageable(identity: Identity, member: Member) {
  return can(identity, "manage_team") &&
    (identity.membership.role === "owner" || !["owner", "admin"].includes(member.role));
}
function AccessDialog({ change, onClose }: { change: AccessChange; onClose: () => void }) {
  const identity = useIdentity().data!;
  const [confirmed, setConfirmed] = useState(false);
  const reauth = useAction(
    (form: FormData) => {
      const credentials = { password: String(form.get("password")), totp_code: value(form, "totp_code") };
      return mutate<Message>("/auth/reauth", credentials).finally(() => { credentials.password = ""; credentials.totp_code = ""; });
    }, "", () => setConfirmed(true),
  );
  const save = useAction(
    (form: FormData) => {
      const reason = value(form, "reason");
      if (change.kind === "cancel") return mutate<Message>(`/invitations/${change.invitation.id}`, { reason }, "DELETE");
      if (change.kind === "role") return mutate(`/members/${change.member.id}`, { role: value(form, "role"), reason }, "PATCH");
      return mutate<Message>(`/members/${change.member.id}`, { reason }, "DELETE");
    }, "Access change recorded.", onClose,
  );
  const person = change.kind === "cancel" ? change.invitation.email : change.member.name;
  const title = change.kind === "remove" ? "Remove factory access" : change.kind === "role" ? "Change factory role" : "Cancel invitation";
  return <Dialog title={title} onClose={onClose} dismissible={!reauth.isPending && !save.isPending}>
    <p className="form-intro"><strong>{person}</strong> / {identity.company.name}</p>
    {!confirmed ? <>
      <p className="notice">Confirm your identity before changing access. This confirmation is valid briefly for this session.</p>
      <Form onSubmit={(form) => reauth.mutate(form)}>
        <Field label="Confirm your password" name="password" type="password" autoComplete="current-password" required maxLength={128} />
        <Field label="Authenticator or recovery code" name="totp_code" autoComplete="one-time-code" required maxLength={16} />
        <ErrorNotice error={reauth.error} />
        <Submit pending={reauth.isPending}>Confirm identity</Submit>
      </Form>
    </> : <>
      <p className="notice">{change.kind === "remove" ? "This removes access to this factory and revokes its sessions. Other factory memberships and past maintenance records remain. Files already downloaded cannot be recalled." : change.kind === "cancel" ? "The unused invitation link will stop working. An email already delivered cannot be recalled." : "The new role applies only to this factory. Existing sessions for this membership will be revoked; the person must sign in again."}</p>
      <Form onSubmit={(form) => save.mutate(form)}>
        {change.kind === "role" && <Select label="New role" name="role" defaultValue={change.member.role} required>
          {roleOptions.filter((role) => identity.membership.role === "owner" || !["owner", "admin"].includes(role)).map((role) => <option key={role} value={role}>{role.charAt(0).toUpperCase() + role.slice(1)}</option>)}
        </Select>}
        <Textarea label="Reason for this access change" name="reason" required maxLength={1000} />
        <ErrorNotice error={save.error} />
        {save.error instanceof ApiError && save.error.code === "reauthentication_required" && <button className="button secondary" type="button" onClick={() => { setConfirmed(false); save.reset(); }}>Confirm identity again</button>}
        <div className="form-actions"><button className="button secondary" type="button" onClick={onClose} disabled={save.isPending}>Keep current access</button>
          <Submit pending={save.isPending}>{change.kind === "remove" ? "Remove member" : change.kind === "cancel" ? "Cancel invitation" : "Save role"}</Submit>
        </div>
      </Form>
    </>}
  </Dialog>;
}
export function Team() {
  const identity = useIdentity().data!;
  const [invite, setInvite] = useState(false);
  const [accessChange, setAccessChange] = useState<AccessChange | null>(null);
  const invitations = useResource<{ invitations: Invitation[] }>(["invitations"], "/invitations", can(identity, "manage_team"));
  const navigate = useNavigate();
  const logout = useAction(
    () => mutate("/auth/logout"),
    "",
    () => {
      clearReplayContext();
      queryClient.clear();
      navigate("/login", { replace: true });
    },
  );
  const members = useResource<{ members: Member[] }>(["members"], "/members");
  const companies = useResource<{ companies: Company[] }>(
    ["companies"],
    "/companies",
  );
  const mfa = useResource<{
    enabled?: boolean;
    enrolled?: boolean;
    mfa_enabled?: boolean;
    recovery_codes_remaining?: number;
  }>(["mfa-status"], "/auth/mfa");
  const [selectedCompany, setSelectedCompany] = useState(String(identity.company.id));
  const changeCompany = useAction(
    (form: FormData) =>
      mutate<Identity>("/companies/switch", {
        company_id: numeric(form, "company_id"),
      }),
    "Organization switched.",
    async (data) => {
      setReplayContext(data.user.id, data.company.id);
      await queryClient.cancelQueries();
      queryClient.removeQueries();
      queryClient.setQueryData(["v1", "identity"], data);
      setSelectedCompany(String(data.company.id));
    },
  );
  return (
    <>
      <PageHeader
        eyebrow="People / organization / security"
        title="Team & settings"
        description="The people responsible for the work, and the account that keeps it private."
        actions={
          can(identity, "manage_team") && (
            <button className="button primary" onClick={() => setInvite(true)}>
              <UserPlus size={18} aria-hidden />
              Invite teammate
            </button>
          )
        }
      />
      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">{identity.company.name}</p>
            <h2>Your team</h2>
          </div>
          {members.data && (
            <span className="muted">
              {members.data.members.length}{" "}
              {members.data.members.length === 1 ? "member" : "members"}
            </span>
          )}
        </div>
        {members.isPending ? (
          <Loading label="Loading team members…" />
        ) : members.error ? (
          <ErrorNotice
            error={members.error}
            retry={() => void members.refetch()}
          />
        ) : !members.data?.members.length ? (
          <Empty title="No members returned">
            Refresh to check the organization’s member record.
          </Empty>
        ) : (
          <div className="table-wrap responsive-records">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Work email</th>
                  <th>Role</th>
                  {can(identity, "manage_team") && <th>Access</th>}
                </tr>
              </thead>
              <tbody>
                {members.data.members.map((member) => (
                  <tr key={member.id}>
                    <td data-label="Name">
                      <strong>{member.name}</strong>
                      {member.user_id === identity.user.id && (
                        <small>You</small>
                      )}
                    </td>
                    <td data-label="Work email">{member.email}</td>
                    <td data-label="Role">
                      <Status value={member.role} />
                    </td>
                    {can(identity, "manage_team") && <td data-label="Access">{manageable(identity, member) && <div className="form-actions">
                      <button className="button secondary small" aria-label={`Change role for ${member.name}`} onClick={() => setAccessChange({kind: "role", member})}>Change role</button>
                      <button className="button secondary small" aria-label={`Remove ${member.name}`} onClick={() => setAccessChange({kind: "remove", member})}>Remove access</button>
                    </div>}</td>}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      {can(identity, "manage_team") && <section className="panel">
        <div className="section-heading"><h2>Pending invitations</h2></div>
        {invitations.isPending ? <Loading label="Loading pending invitations…" /> : invitations.error ? <ErrorNotice error={invitations.error} retry={() => void invitations.refetch()} /> : !invitations.data?.invitations.length ? <Empty title="No pending invitations">Accepted or cancelled invitations are no longer waiting for a response.</Empty> : <div className="table-wrap responsive-records"><table><thead><tr><th>Email</th><th>Role</th><th>Expires</th><th>Access</th></tr></thead><tbody>
          {invitations.data.invitations.map((invitation) => <tr key={invitation.id}><td data-label="Email">{invitation.email}</td><td data-label="Role"><Status value={invitation.role} /></td><td data-label="Expires">{new Date(invitation.expires_at).toLocaleString()} (device time)</td><td data-label="Access">{(identity.membership.role === "owner" || !["owner", "admin"].includes(invitation.role)) && <button className="button secondary small" aria-label={`Cancel invitation for ${invitation.email}`} onClick={() => setAccessChange({kind: "cancel", invitation})}>Cancel invitation</button>}</td></tr>)}
        </tbody></table></div>}
      </section>}
      <div className="detail-columns">
        <section className="panel">
          <div className="section-heading">
            <h2>
              <Building2 size={20} aria-hidden />
              Organization
            </h2>
          </div>
          <div className="record-body">
            <Definition
              items={[
                ["Active organization", identity.company.name],
                ["Your role", <Status value={identity.membership.role} />],
              ]}
            />
            {companies.isPending ? (
              <Loading label="Loading your organizations…" />
            ) : companies.error ? (
              <ErrorNotice
                error={companies.error}
                retry={() => void companies.refetch()}
              />
            ) : (companies.data?.companies.length || 0) > 1 ? (
              <Form onSubmit={(data) => changeCompany.mutate(data)}>
                <Select
                  label="Switch organization"
                  name="company_id"
                  value={selectedCompany}
                  onChange={(event) => setSelectedCompany(event.target.value)}
                  disabled={changeCompany.isPending}
                  required
                >
                  {companies.data?.companies.map((company) => (
                    <option key={company.id} value={company.id}>
                      {company.name} ({company.role})
                    </option>
                  ))}
                </Select>
                <p className="muted">
                  Switching clears the current organization’s cached records.
                  You will only see records belonging to the selected
                  organization.
                </p>
                <ErrorNotice error={changeCompany.error} />
                <Submit pending={changeCompany.isPending}>
                  Switch organization
                </Submit>
              </Form>
            ) : (
              <p className="muted">
                You belong to this organization. Accept an invitation from
                another team to work in more than one organization.
              </p>
            )}
          </div>
        </section>
        <section className="panel">
          <div className="section-heading">
            <h2>
              <ShieldCheck size={20} aria-hidden />
              Account security
            </h2>
          </div>
          <div className="record-body">
            <Definition
              items={[
                ["Name", identity.user.name],
                ["Email", identity.user.email],
              ]}
            />
            <h3>Authenticator</h3>
            {mfa.isPending ? (
              <Loading label="Checking authenticator…" />
            ) : mfa.error ? (
              <ErrorNotice error={mfa.error} retry={() => void mfa.refetch()} />
            ) : (
              <>
                <p>
                  {identity.mfa_enrollment_required
                    ? "An authenticator is required before you can make changes."
                    : mfa.data?.enabled ||
                        mfa.data?.enrolled ||
                        mfa.data?.mfa_enabled
                      ? "Your authenticator adds a second check at sign-in."
                      : "An authenticator adds a second check at sign-in."}
                </p>
                {mfa.data?.recovery_codes_remaining !== undefined && (
                  <p className="muted">
                    {mfa.data.recovery_codes_remaining} one-use recovery codes
                    remaining.
                  </p>
                )}
                <Link className="button secondary" to="/mfa">
                  {identity.mfa_enrollment_required
                    ? "Set up authenticator"
                    : "Authenticator settings"}
                  <ArrowUpRight size={17} aria-hidden />
                </Link>
              </>
            )}
            <h3>Password</h3>
            <p>Changing your password signs out all existing sessions.</p>
            <Link to="/forgot-password" className="text-link">
              Request a password reset
              <ArrowUpRight size={16} aria-hidden />
            </Link>
            <h3>Sign out</h3>
            <p>End this session on this device.</p>
            <ErrorNotice error={logout.error} />
            <button
              className="button secondary"
              disabled={logout.isPending}
              onClick={() => logout.mutate()}
            >
              {logout.isPending ? "Signing out…" : "Sign out of this device"}
            </button>
          </div>
        </section>
      </div>
      {invite && <InviteForm onClose={() => setInvite(false)} />}
      {accessChange && <AccessDialog change={accessChange} onClose={() => setAccessChange(null)} />}
    </>
  );
}
