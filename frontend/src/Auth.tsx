import { useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { ShieldCheck, Wrench, BookOpen } from "lucide-react";
import { ApiError, clearReplayContext, mutate, setReplayContext } from "./api";
import { useIdentity, queryClient } from "./query";
import {
  ErrorNotice,
  Field,
  Form,
  Loading,
  Submit,
  Textarea,
  useAction,
  value,
} from "./ui";
import type { Identity, Message } from "./types";
import { useQuery } from "@tanstack/react-query";
import { get } from "./api";

import { Brand } from "./Brand";

// Preserve existing workbench imports without coupling the public page to Auth.
export { Brand } from "./Brand";

export function AuthLayout({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="auth-layout">
      <a className="skip-link" href="#auth-content">
        Skip to account form
      </a>
      <aside className="auth-story" aria-label="About your workbench">
        <Brand />
        <div className="auth-story-body">
          <p className="eyebrow">A clearer shift starts here</p>
          <h1>
            Know the machine.
            <br />
            Finish the job.
            <br />
            Keep the record.
          </h1>
          <p>A practical place for the work that keeps your plant running.</p>
          <ul className="auth-features">
            <li>
              <Wrench aria-hidden size={20} />
              Machines and maintenance, together
            </li>
            <li>
              <BookOpen aria-hidden size={20} />
              Manuals beside the work
            </li>
            <li>
              <ShieldCheck aria-hidden size={20} />A shared record, protected by
              your team
            </li>
          </ul>
        </div>
        <span className="auth-footer">
          Machivital / Maintenance, made clear.
        </span>
      </aside>
      <main id="auth-content" className="auth-main" tabIndex={-1}>
        <div className="mobile-brand">
          <Brand />
        </div>
        <section className="auth-card" aria-labelledby="auth-title">
          <p className="eyebrow">Your workbench</p>
          <h2 id="auth-title">{title}</h2>
          <p className="page-description">{description}</p>
          {children}
        </section>
        <p className="auth-help">
          Use your work email. Your organization’s records stay private.
        </p>
      </main>
    </div>
  );
}
export function Signup() {
  const [email, setEmail] = useState("");
  const action = useAction(
    (body: Record<string, string>) =>
      mutate<Message>("/auth/signup", body).finally(() => {
        body.password = "";
      }),
    "",
  );
  if (action.isSuccess)
    return <VerificationPending email={email} message={action.data.message} />;
  return (
    <AuthLayout
      title="Create your workbench"
      description="Start with your organization. Add machines and invite your team after verifying your email."
    >
      <Form
        onSubmit={(data) => {
          const address = value(data, "email");
          setEmail(address);
          action.mutate({
            name: value(data, "name"),
            email: address,
            password: String(data.get("password")),
            company_name: value(data, "company_name"),
          });
        }}
      >
        <Field
          label="Your name"
          name="name"
          autoComplete="name"
          required
          maxLength={100}
        />
        <Field
          label="Work email"
          name="email"
          type="email"
          autoComplete="email"
          required
          maxLength={120}
        />
        <Field
          label="Organization name"
          name="company_name"
          autoComplete="organization"
          required
          maxLength={100}
        />
        <Field
          label="Password"
          name="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={12}
          maxLength={128}
          hint="Use a unique password of at least 12 characters."
        />
        <ErrorNotice error={action.error} />
        <Submit pending={action.isPending}>Create account</Submit>
      </Form>
      <p className="auth-switch">
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </AuthLayout>
  );
}
function VerificationPending({
  email = "",
  message,
}: {
  email?: string;
  message?: string;
}) {
  const resend = useAction(
    (body: { email: string }) =>
      mutate<Message>("/auth/resend-verification", body),
    "Verification request received.",
  );
  return (
    <AuthLayout
      title="Check your email"
      description={
        message ||
        "Open the verification link sent to your work email before signing in."
      }
    >
      <div className="notice">
        <ShieldCheck size={21} aria-hidden />
        <p>
          Verification protects your organization’s records. Mail may take a few
          minutes to arrive. Check your spam folder too.
        </p>
      </div>
      <Form onSubmit={(data) => resend.mutate({ email: value(data, "email") })}>
        <Field
          label="Email address"
          name="email"
          type="email"
          required
          defaultValue={email}
          autoComplete="email"
        />
        <ErrorNotice error={resend.error} />
        {resend.isSuccess && <p role="status">{resend.data.message}</p>}
        <Submit pending={resend.isPending}>Request another link</Submit>
      </Form>
      <p className="auth-switch">
        <Link to="/login">Back to sign in</Link>
      </p>
    </AuthLayout>
  );
}
export function VerifyEmail() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const verify = useAction(
    () => mutate<Message>("/auth/verify-email", { token }),
    "",
  );
  if (!token) return <VerificationPending />;
  return (
    <AuthLayout
      title={verify.isSuccess ? "Email verified" : "Verify your email"}
      description={
        verify.isSuccess
          ? verify.data.message
          : "Confirm this address to begin using your workbench."
      }
    >
      {verify.isSuccess ? (
        <Link className="button primary" to="/login">
          Continue to sign in
        </Link>
      ) : (
        <>
          <ErrorNotice error={verify.error} />
          <button
            className="button primary"
            disabled={verify.isPending}
            onClick={() => verify.mutate()}
          >
            {verify.isPending ? "Verifying…" : "Verify email address"}
          </button>
          <p className="auth-switch">
            <Link to="/verify-email">Request a new verification link</Link>
          </p>
        </>
      )}
    </AuthLayout>
  );
}
export function Login() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const identity = useIdentity();
  const [step, setStep] = useState<"password" | "mfa">("password");
  const [email, setEmail] = useState("");
  const destination = params.get("next");
  const next =
    destination?.startsWith("/app") || destination?.startsWith("/invite?")
      ? destination
      : "/app";
  const login = useAction(
    (body: { email: string; password: string; totp_code?: string }) =>
      mutate<Identity>("/auth/login", body).finally(() => {
        body.password = "";
      }),
    "",
    async () => {
      queryClient.removeQueries();
      const current = await queryClient.fetchQuery({
        queryKey: ["v1", "identity"],
        queryFn: () => get<Identity>("/auth/me"),
      });
      setReplayContext(current.user.id, current.company.id);
      navigate(next, { replace: true });
    },
  );
  if (identity.data && !identity.error) return <Navigate to={next} replace />;
  const mfa =
    step === "mfa" ||
    (login.error instanceof ApiError && login.error.code === "mfa_required");
  return (
    <AuthLayout
      title={mfa ? "Confirm it’s you" : "Welcome back"}
      description={
        mfa
          ? "Enter your password again and a code from your authenticator. A one-use recovery code also works."
          : "Sign in to pick up the work with your team."
      }
    >
      <Form
        key={mfa ? "mfa" : "password"}
        onSubmit={(data, event) => {
          const address = value(data, "email");
          setEmail(address);
          const form = event.currentTarget;
          const body = {
            email: address,
            password: String(data.get("password")),
            ...(mfa ? { totp_code: value(data, "totp_code") } : {}),
          };
          login.mutate(body, {
            onError: (error) => {
              if (error instanceof ApiError && error.code === "mfa_required") {
                form.reset();
                setStep("mfa");
              }
            },
          });
        }}
      >
        <Field
          label="Work email"
          name="email"
          type="email"
          autoComplete="username"
          required
          defaultValue={email}
        />
        <Field
          label="Password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          maxLength={128}
        />
        {mfa && (
          <Field
            label="Authenticator or recovery code"
            name="totp_code"
            autoComplete="one-time-code"
            required
            autoFocus
            spellCheck={false}
          />
        )}
        <ErrorNotice
          error={
            login.error instanceof ApiError &&
            login.error.code === "mfa_required"
              ? null
              : login.error
          }
        />
        <Submit pending={login.isPending}>
          {mfa ? "Confirm and sign in" : "Sign in"}
        </Submit>
      </Form>
      <div className="auth-links">
        <Link to="/forgot-password">Forgot password?</Link>
        <Link to="/verify-email">Verify email</Link>
      </div>
      <p className="auth-switch">
        New to Machivital? <Link to="/signup">Create an account</Link>
      </p>
    </AuthLayout>
  );
}
export function ForgotPassword() {
  const action = useAction(
    (body: { email: string }) => mutate<Message>("/auth/forgot-password", body),
    "Password reset requested.",
  );
  return (
    <AuthLayout
      title="Reset your password"
      description="Enter your work email. If an account exists, we’ll queue a password reset link."
    >
      <Form onSubmit={(data) => action.mutate({ email: value(data, "email") })}>
        <Field
          label="Work email"
          name="email"
          type="email"
          autoComplete="email"
          required
        />
        <ErrorNotice error={action.error} />
        {action.isSuccess && (
          <div className="notice" role="status">
            {action.data.message}
          </div>
        )}
        <Submit pending={action.isPending}>Request reset link</Submit>
      </Form>
      <p className="auth-switch">
        <Link to="/login">Back to sign in</Link>
      </p>
    </AuthLayout>
  );
}
export function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const action = useAction(
    (body: { password: string; token: string }) =>
      mutate<Message>("/auth/reset-password", body).finally(() => {
        body.password = "";
      }),
    "",
    () => { clearReplayContext(); queryClient.clear(); },
  );
  return (
    <AuthLayout
      title={action.isSuccess ? "Password updated" : "Choose a new password"}
      description={
        action.isSuccess
          ? "All previous sessions have been signed out. Sign in with your new password."
          : "Use a unique password you haven’t used before."
      }
    >
      {action.isSuccess ? (
        <Link className="button primary" to="/login">
          Sign in
        </Link>
      ) : !token ? (
        <>
          <div className="notice error" role="alert">
            This link is missing its reset code. Request a new link.
          </div>
          <Link to="/forgot-password" className="button primary">
            Request reset link
          </Link>
        </>
      ) : (
        <Form
          onSubmit={(data) =>
            action.mutate({ token, password: String(data.get("password")) })
          }
        >
          <Field
            label="New password"
            name="password"
            type="password"
            required
            minLength={12}
            maxLength={128}
            autoComplete="new-password"
            hint="At least 12 characters."
          />
          <ErrorNotice error={action.error} />
          <Submit pending={action.isPending}>Save new password</Submit>
        </Form>
      )}
    </AuthLayout>
  );
}
export function Invite() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const identity = useIdentity();
  const preview = useQuery({
    queryKey: ["v1", "invite-preview", token],
    queryFn: ({ signal }) =>
      get<{
        company?: { name: string };
        company_name?: string;
        email: string;
        role: string;
      }>(`/invitations/preview?token=${encodeURIComponent(token)}`, signal),
    enabled: !!token,
    retry: false,
  });
  const action = useAction(
    (body: Record<string, string>) =>
      mutate<Message>("/invitations/accept", body).finally(() => {
        if ("password" in body) body.password = "";
      }),
    "Invitation accepted.",
  );
  return (
    <AuthLayout
      title="Join your team"
      description="Accept your invitation to a shared maintenance workbench."
    >
      {!token ? (
        <div className="notice error" role="alert">
          This invitation link is incomplete. Ask your administrator for a new
          invitation.
        </div>
      ) : action.isSuccess ? (
        <>
          <p role="status">{action.data.message}</p>
          <Link
            to={identity.data ? "/app/team" : "/login"}
            className="button primary"
          >
            {identity.data ? "Open workbench" : "Sign in"}
          </Link>
        </>
      ) : preview.isPending ? (
        <Loading label="Checking invitation…" />
      ) : preview.error ? (
        <ErrorNotice error={preview.error} />
      ) : (
        <>
          <div className="invite-summary">
            <strong>
              {preview.data?.company?.name || preview.data?.company_name}
            </strong>
            <p>{preview.data?.email}</p>
            <span>{preview.data?.role}</span>
          </div>
          {!identity.data && (
            <p className="notice">
              Already have a Machivital account?{" "}
              <Link
                to={`/login?next=${encodeURIComponent(`/invite?token=${token}`)}`}
              >
                Sign in first
              </Link>
              . Accepting an invitation will not change your existing password.
            </p>
          )}
          <Form
            onSubmit={(data) =>
              action.mutate(
                identity.data
                  ? { token }
                  : {
                      token,
                      name: value(data, "name"),
                      password: String(data.get("password")),
                    },
              )
            }
          >
            {!identity.data && (
              <>
                <Field
                  label="Your name"
                  name="name"
                  autoComplete="name"
                  required
                  maxLength={100}
                />
                <Field
                  label="Create password"
                  name="password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={12}
                  maxLength={128}
                  hint="At least 12 characters. Existing account holders must sign in instead."
                />
              </>
            )}
            <ErrorNotice error={action.error} />
            <Submit pending={action.isPending}>Accept invitation</Submit>
          </Form>
        </>
      )}
    </AuthLayout>
  );
}
export function Mfa() {
  const identity = useIdentity();
  const [saved, setSaved] = useState(false);
  const status = useQuery({
    queryKey: ["v1", identity.data?.company.id, "mfa-status"],
    queryFn: ({ signal }) => get<{ enabled: boolean }>("/auth/mfa", signal),
    enabled: !!identity.data,
  });
  const setup = useAction(
    (body: { password: string }) =>
      mutate<{ secret: string; otpauth_url: string }>(
        "/auth/mfa/setup",
        body,
      ).finally(() => {
        body.password = "";
      }),
    "Authenticator setup started.",
  );
  const confirm = useAction(
    (body: { code: string }) =>
      mutate<{ recovery_codes: string[] }>("/auth/mfa/confirm", body),
    "Authenticator enabled.",
  );
  const [copyError, setCopyError] = useState("");
  if (identity.isPending)
    return (
      <AuthLayout title="Account security" description="Checking your account.">
        <Loading />
      </AuthLayout>
    );
  if (identity.error instanceof ApiError && identity.error.status === 401)
    return <Navigate to="/login" replace />;
  if (identity.error)
    return (
      <AuthLayout
        title="Account security"
        description="Your account could not be loaded."
      >
        <ErrorNotice
          error={identity.error}
          retry={() => void identity.refetch()}
        />
      </AuthLayout>
    );
  const codes = confirm.data?.recovery_codes;
  return (
    <AuthLayout
      title={codes ? "Save your recovery codes" : "Protect your workbench"}
      description={
        codes
          ? "These codes are shown once. Keep them somewhere safe, separate from your phone."
          : "Use an authenticator app to add a second check when you sign in."
      }
    >
      {codes ? (
        <>
          <div className="notice warning">
            Each recovery code works once. Leaving this page hides these codes
            permanently.
          </div>
          <pre className="recovery-codes">{codes.join("\n")}</pre>
          <button
            className="button secondary"
            onClick={() => {
              const blob = new Blob(
                [
                  `Machivital recovery codes\n\n${codes.join("\n")}\n\nEach code can be used once. Keep this file private.\n`,
                ],
                { type: "text/plain" },
              );
              const url = URL.createObjectURL(blob);
              const link = document.createElement("a");
              link.href = url;
              link.download = "machivital-recovery-codes.txt";
              link.click();
              URL.revokeObjectURL(url);
            }}
          >
            Download recovery codes
          </button>
          <label className="check-row">
            <input
              type="checkbox"
              checked={saved}
              onChange={(event) => setSaved(event.target.checked)}
            />
            I have saved my recovery codes
          </label>
          <Link
            className={`button primary ${!saved ? "disabled" : ""}`}
            aria-disabled={!saved}
            to="/app"
            onClick={(event) => {
              if (!saved) event.preventDefault();
            }}
          >
            Open workbench
          </Link>
        </>
      ) : status.isPending ? (
        <Loading label="Checking authenticator status…" />
      ) : status.error ? (
        <ErrorNotice error={status.error} retry={() => void status.refetch()} />
      ) : status.data?.enabled && !setup.data ? (
        <>
          <div className="notice">
            <ShieldCheck size={22} aria-hidden />
            <p>Your account has an authenticator enabled.</p>
          </div>
          <Link to="/app/team" className="button primary">
            Return to account settings
          </Link>
        </>
      ) : !setup.data ? (
        <>
          <div className="notice">
            {identity.data?.mfa_enrollment_required
              ? "Organization owners and administrators need an authenticator before making changes."
              : "Confirm your password, then add this account to your authenticator app."}
          </div>
          <Form
            onSubmit={(data, event) => {
              setup.mutate({ password: String(data.get("password")) });
              event.currentTarget.reset();
            }}
          >
            <Field
              label="Confirm your password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
            />
            <ErrorNotice error={setup.error} />
            <Submit pending={setup.isPending}>Set up authenticator</Submit>
          </Form>
        </>
      ) : (
        <>
          <ol className="setup-steps">
            <li>
              Open your authenticator app and choose to add an account manually.
            </li>
            <li>
              Choose a time-based code. Use{" "}
              <strong>{identity.data?.user.email}</strong> as the account name.
            </li>
            <li>
              Enter this setup key. Then type the current six-digit code below.
            </li>
          </ol>
          <Textarea
            label="Authenticator setup key"
            value={setup.data.secret}
            readOnly
            rows={2}
          />
          <button
            className="button secondary"
            onClick={() =>
              void navigator.clipboard
                .writeText(setup.data!.secret)
                .catch(() =>
                  setCopyError(
                    "Copy is unavailable. Select the setup key and copy it manually.",
                  ),
                )
            }
          >
            Copy setup key
          </button>
          {copyError && <p role="status">{copyError}</p>}
          <Form
            onSubmit={(data) => confirm.mutate({ code: value(data, "code") })}
          >
            <Field
              label="Six-digit authenticator code"
              name="code"
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]{6}"
              maxLength={6}
              minLength={6}
              required
            />
            <ErrorNotice error={confirm.error} />
            {confirm.error instanceof ApiError &&
              confirm.error.code === "enrollment_expired" && (
                <button
                  className="button secondary"
                  type="button"
                  onClick={() => {
                    setup.reset();
                    confirm.reset();
                  }}
                >
                  Start enrollment again
                </button>
              )}
            <Submit pending={confirm.isPending}>Enable authenticator</Submit>
          </Form>
        </>
      )}
    </AuthLayout>
  );
}
