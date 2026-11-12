import { useEffect } from "react";
import {
  Link,
  Navigate,
  NavLink,
  Outlet,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import {
  CalendarDays,
  Factory,
  ClipboardList,
  BookOpen,
  Users,
  LogOut,
  ArrowUpRight,
} from "lucide-react";
import { ApiError, clearReplayContext, mutate } from "./api";
import { useIdentity, queryClient } from "./query";
import {
  Brand,
  ForgotPassword,
  Invite,
  Login,
  Mfa,
  ResetPassword,
  Signup,
  VerifyEmail,
} from "./Auth";
import { ErrorNotice, Loading, useAction } from "./ui";
import { Today } from "./Today";
import { Machines, MachineDetail } from "./Machines";
import { Maintenance, JobDetail } from "./Maintenance";
import { Preventive, PlanDetail } from "./Preventive";
import { Manuals } from "./Manuals";
import { Team } from "./Team";

const navigation = [
  { to: "/app", label: "Today", icon: CalendarDays, end: true },
  { to: "/app/machines", label: "Machines", icon: Factory },
  { to: "/app/maintenance", label: "Maintenance", icon: ClipboardList },
  { to: "/app/manuals", label: "Manuals", icon: BookOpen },
  { to: "/app/team", label: "Team & settings", icon: Users },
];
function Shell() {
  const identity = useIdentity();
  const location = useLocation();
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
  useEffect(() => {
    const name =
      navigation.find((item) =>
        item.end
          ? location.pathname === item.to
          : location.pathname.startsWith(item.to),
      )?.label || "Workbench";
    document.title = `${name} | Machivital`;
  }, [location.pathname]);
  if (identity.isPending)
    return (
      <main className="initial-loading">
        <Brand />
        <Loading label="Opening your workbench…" />
      </main>
    );
  if (identity.error instanceof ApiError && identity.error.status === 401)
    return (
      <Navigate
        to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`}
        replace
      />
    );
  if (identity.error)
    return (
      <main className="initial-loading">
        <Brand />
        <ErrorNotice
          error={identity.error}
          retry={() => void identity.refetch()}
        />
      </main>
    );
  if (!identity.data) return null;
  return (
    <div className="workbench">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <aside className="sidebar">
        <Brand />
        <div className="organization">
          <span className="eyebrow">Organization</span>
          <strong>{identity.data.company.name}</strong>
          <Link to="/app/team">
            {identity.data.membership.role}
            <ArrowUpRight size={14} aria-hidden />
          </Link>
        </div>
        <nav aria-label="Main navigation">
          {navigation.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} aria-label={label === "Maintenance" ? label : undefined}>
              <Icon size={20} aria-hidden />
              <span className="nav-label">{label}</span>
              <span className="nav-label-mobile">
                {label === "Team & settings" ? "Team" : label === "Maintenance" ? "Jobs" : label}
              </span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <p className="sidebar-note">
            A record of the work.
            <br />A clearer next shift.
          </p>
          <div className="signed-in">
            <span className="avatar" aria-hidden>
              {identity.data.user.name.slice(0, 1).toUpperCase()}
            </span>
            <div>
              <strong>{identity.data.user.name}</strong>
              <small>{identity.data.user.email}</small>
            </div>
          </div>
          <button
            className="logout-button"
            disabled={logout.isPending}
            onClick={() => logout.mutate()}
          >
            <LogOut size={17} aria-hidden />
            Sign out
          </button>
          <ErrorNotice error={logout.error} />
        </div>
      </aside>
      <div className="workspace">
        <header className="workspace-top">
          <span>{identity.data.company.name}</span>
          <span>Maintenance workbench</span>
        </header>
        <main id="main-content" className="main-content" tabIndex={-1}>
          {identity.data.mfa_enrollment_required && (
            <div className="notice warning enrollment-banner">
              <div>
                <strong>
                  Protect your organization before making changes.
                </strong>
                <p>
                  Set up your authenticator to add machines, manage jobs, and
                  invite your team.
                </p>
              </div>
              <Link className="button secondary small" to="/mfa">
                Set up authenticator
              </Link>
            </div>
          )}
          <Outlet />
        </main>
      </div>
    </div>
  );
}
function NotFound() {
  return (
    <main className="initial-loading">
      <Brand />
      <h1>This page isn’t in the workbench</h1>
      <p>The address may have changed. Return to your shift sheet.</p>
      <Link className="button primary" to="/app">
        Open Today
      </Link>
    </main>
  );
}
export function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/app" replace />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/login" element={<Login />} />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/invite" element={<Invite />} />
      <Route path="/mfa" element={<Mfa />} />
      <Route path="/app" element={<Shell />}>
        <Route index element={<Today />} />
        <Route path="machines" element={<Machines />} />
        <Route path="machines/:id" element={<MachineDetail />} />
        <Route path="maintenance" element={<Maintenance />} />
        <Route path="maintenance/plans" element={<Preventive />} />
        <Route path="maintenance/plans/:id" element={<PlanDetail />} />
        <Route path="maintenance/:id" element={<JobDetail />} />
        <Route path="manuals" element={<Manuals />} />
        <Route path="team" element={<Team />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
