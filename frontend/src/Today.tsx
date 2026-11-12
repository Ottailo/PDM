import { Link } from "react-router-dom";
import { ArrowUpRight, ClipboardList, Factory, BookOpen } from "lucide-react";
import { useIdentity, useResource } from "./query";
import type { Summary, WorkOrder } from "./types";
import { Empty, ErrorNotice, Loading, PageHeader, Status } from "./ui";
import { can, jobDateLabel, isOverdue } from "./permissions";
export function WorkQueue({ jobs }: { jobs: WorkOrder[] }) {
  return (
    <div className="queue">
      {jobs.map((job) => (
        <Link
          to={`/app/maintenance/${job.id}`}
          className="queue-row"
          key={job.id}
        >
          <div className="queue-code">{job.number}</div>
          <div className="queue-title">
            <strong>{job.title}</strong>
            <span>
              <span className="queue-machine"><span className="phone-label">Machine: </span>{job.asset_name}</span>
              <span className="queue-person"><span className="phone-label">Assigned person: </span>{job.assignee_name || "Unassigned"}</span>
            </span>
          </div>
          <div className="queue-due">
            <span className={isOverdue(job) ? "overdue" : ""}>
              {job.due_at
                ? `${isOverdue(job) ? "Overdue · " : "Due "}${jobDateLabel(job.due_at)}`
                : "No due date"}
            </span>
            <Status value={job.status} />
          </div>
          <ArrowUpRight size={18} aria-hidden />
        </Link>
      ))}
    </div>
  );
}
export function Today() {
  const identity = useIdentity().data!;
  const summary = useResource<Summary>(["summary"], "/summary");
  const work = useResource<{ work_orders: WorkOrder[] }>(
    ["work-orders", "today"],
    "/work-orders",
  );
  const open =
    work.data?.work_orders
      .filter((job) => !["completed", "cancelled"].includes(job.status))
      .sort(
        (a, b) =>
          (a.due_at ? new Date(a.due_at).getTime() : Infinity) -
          (b.due_at ? new Date(b.due_at).getTime() : Infinity),
      ) || [];
  const today = new Intl.DateTimeFormat(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
  }).format(new Date());
  return (
    <>
      <PageHeader
        eyebrow={today}
        title="A clear view of the work."
        description={`Welcome, ${identity.user.name.split(" ")[0]}. Here’s what needs attention in ${identity.company.name}.`}
        actions={
          can(identity, "request_work_orders") && (
            <Link className="button primary" to="/app/maintenance?new=1">
              Create job
              <ArrowUpRight size={18} aria-hidden />
            </Link>
          )
        }
      />
      <section
        aria-label="Organization record counts"
        className="shift-summary"
      >
        {summary.isPending ? (
          <Loading label="Loading your organization’s counts…" />
        ) : summary.error ? (
          <ErrorNotice
            error={summary.error}
            retry={() => void summary.refetch()}
          />
        ) : (
          summary.data && (
            <>
              <div className="summary-intro">
                <span className="eyebrow">The shift sheet</span>
                <p>
                  Actual records.
                  <br />
                  Ready for the next step.
                </p>
              </div>
              <Link to="/app/maintenance">
                <strong>{summary.data.open_work_order_count}</strong>
                <span>Open jobs</span>
              </Link>
              <Link to="/app/maintenance?status=awaiting_review">
                <strong>{summary.data.awaiting_review_count}</strong>
                <span>Awaiting review</span>
              </Link>
              <Link
                to="/app/maintenance?overdue=1"
                className={
                  summary.data.overdue_work_order_count ? "warning-count" : ""
                }
              >
                <strong>{summary.data.overdue_work_order_count}</strong>
                <span>Overdue jobs</span>
              </Link>
              <Link to="/app/machines">
                <strong>{summary.data.asset_count}</strong>
                <span>Machines recorded</span>
              </Link>
            </>
          )
        )}
      </section>
      <section className="panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Next up</p>
            <h2>Open work queue</h2>
            <Link className="text-link" to="/app/maintenance/plans">Preventive plans</Link>
          </div>
          <Link className="text-link" to="/app/maintenance">
            All maintenance
            <ArrowUpRight size={16} aria-hidden />
          </Link>
        </div>
        {work.isPending ? (
          <Loading label="Loading open jobs…" />
        ) : work.error ? (
          <ErrorNotice error={work.error} retry={() => void work.refetch()} />
        ) : open.length ? (
          <WorkQueue jobs={open.slice(0, 10)} />
        ) : (
          <Empty title="No open jobs">
            {summary.data?.asset_count === 0
              ? "Start by recording your machines. Then create maintenance jobs when work needs doing."
              : "There are no open maintenance jobs. Completed work stays in the maintenance record."}
          </Empty>
        )}
      </section>
      {summary.data?.asset_count === 0 && (
        <section className="getting-started">
          <div>
            <p className="eyebrow">Make the workbench yours</p>
            <h2>Start with what’s on your floor.</h2>
            <p>
              Machines don’t need sensors to belong here. Record the equipment,
              then build its maintenance history.
            </p>
          </div>
          <div className="start-links">
            <Link to="/app/machines">
              <Factory size={24} aria-hidden />
              <div>
                <strong>Record a machine</strong>
                <span>Name, location, and equipment details</span>
              </div>
              <ArrowUpRight size={18} aria-hidden />
            </Link>
            <Link to="/app/maintenance">
              <ClipboardList size={24} aria-hidden />
              <div>
                <strong>Plan the first job</strong>
                <span>A clear task, assignee, and checklist</span>
              </div>
              <ArrowUpRight size={18} aria-hidden />
            </Link>
            <Link to="/app/manuals">
              <BookOpen size={24} aria-hidden />
              <div>
                <strong>Keep a manual nearby</strong>
                <span>Private PDFs, linked to the machine</span>
              </div>
              <ArrowUpRight size={18} aria-hidden />
            </Link>
          </div>
        </section>
      )}
    </>
  );
}
