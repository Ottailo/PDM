import {
  ArrowDown,
  ArrowUp,
  ArrowUpRight,
  BookOpen,
  CalendarDays,
  ChevronDown,
  ClipboardCheck,
  Factory,
  LockKeyhole,
} from "lucide-react";
import { Brand } from "./Brand";
import "./pilot.css";

export function PilotPage() {
  return (
    <div className="pilot-page" id="top">
      <a className="skip-link" href="#pilot-content">
        Skip to product overview
      </a>
      <header className="pilot-header pilot-wrap">
        <Brand home="/" />
        <nav className="pilot-nav" aria-label="Page navigation">
          <a href="#workflow">The workflow</a>
          <a href="#scope">Pilot scope</a>
          <a href="#boundaries">Access & boundaries</a>
        </nav>
      </header>

      <main id="pilot-content" tabIndex={-1}>
        <section className="pilot-hero pilot-wrap" aria-labelledby="pilot-title">
          <div className="pilot-hero-copy">
            <p className="pilot-kicker">Private pilot</p>
            <h1 id="pilot-title">
              Good maintenance.
              <br />
              A clear record.
            </h1>
            <p className="pilot-lead">
              A practical workbench for the people who look after machines.
              Bring the machine, its maintenance plan, and the work completed
              into one shared record.
            </p>
            <a className="pilot-action" href="#workflow">
              Follow the work <ArrowDown size={19} aria-hidden="true" />
            </a>
          </div>
          <aside className="pilot-hero-note" aria-label="About this page">
            <span className="pilot-note-rule" aria-hidden="true" />
            <p className="pilot-kicker">An introduction, not a live workbench</p>
            <p>
              This public page explains the pilot. Accounts, organization
              records, and uploads are unavailable here.
            </p>
            <a href="#boundaries" className="pilot-inline-link">
              Read the boundaries <ArrowUpRight size={17} aria-hidden="true" />
            </a>
          </aside>
        </section>

        <section
          id="workflow"
          className="pilot-workflow"
          aria-labelledby="pilot-workflow-title"
        >
          <div className="pilot-wrap">
            <div className="pilot-section-intro">
              <p className="pilot-kicker">The thread through every job</p>
              <h2 id="pilot-workflow-title">From the machine to the next shift.</h2>
              <p>
                Know what needs care, plan the work, then keep what happened.
                Expand each step to see how the private workbench fits together.
              </p>
            </div>
            <ol className="pilot-sequence">
              <li>
                <details className="pilot-step" open>
                  <summary>
                    <span className="pilot-step-index" aria-hidden="true">01</span>
                    <Factory size={26} strokeWidth={1.5} aria-hidden="true" />
                    <span className="pilot-step-heading">
                      <span className="pilot-kicker">Start with the equipment</span>
                      <span className="pilot-step-title">Know the machine.</span>
                    </span>
                    <ChevronDown className="pilot-expand" size={21} aria-hidden="true" />
                  </summary>
                  <div className="pilot-step-body">
                    <p>
                      Keep a machine’s identity and maintenance history together.
                      Manuals sit beside the work, so the team can refer to the
                      equipment’s documentation without losing the job’s context.
                    </p>
                    <p className="pilot-step-outcome">
                      <strong>The starting point</strong>
                      A registered machine with a record your team can return to.
                    </p>
                  </div>
                </details>
              </li>
              <li>
                <details className="pilot-step">
                  <summary>
                    <span className="pilot-step-index" aria-hidden="true">02</span>
                    <CalendarDays size={26} strokeWidth={1.5} aria-hidden="true" />
                    <span className="pilot-step-heading">
                      <span className="pilot-kicker">Make the work repeatable</span>
                      <span className="pilot-step-title">Plan its maintenance.</span>
                    </span>
                    <ChevronDown className="pilot-expand" size={21} aria-hidden="true" />
                  </summary>
                  <div className="pilot-step-body">
                    <p>
                      Create a calendar-based maintenance plan for a machine.
                      Define the checklist, assign responsibility, and preview
                      the schedule in the organization’s timezone. Due plans
                      create jobs the team can work through.
                    </p>
                    <p className="pilot-step-outcome">
                      <strong>The handoff</strong>
                      A planned job with a due date, an assignee, and clear tasks.
                    </p>
                  </div>
                </details>
              </li>
              <li>
                <details className="pilot-step">
                  <summary>
                    <span className="pilot-step-index" aria-hidden="true">03</span>
                    <ClipboardCheck size={26} strokeWidth={1.5} aria-hidden="true" />
                    <span className="pilot-step-heading">
                      <span className="pilot-kicker">Close the loop</span>
                      <span className="pilot-step-title">Finish. Review. Keep the record.</span>
                    </span>
                    <ChevronDown className="pilot-expand" size={21} aria-hidden="true" />
                  </summary>
                  <div className="pilot-step-body">
                    <p>
                      The technician records checklist progress, work notes, and
                      labor, then submits the job for review. A manager reviews
                      the completion. The job’s history keeps the work and the
                      review connected to the machine.
                    </p>
                    <p className="pilot-step-outcome">
                      <strong>The lasting record</strong>
                      What was done, who did it, and how it was reviewed.
                    </p>
                  </div>
                </details>
              </li>
            </ol>
          </div>
        </section>

        <section
          id="scope"
          className="pilot-scope pilot-wrap"
          aria-labelledby="pilot-scope-title"
        >
          <div className="pilot-section-label">
            <BookOpen size={23} strokeWidth={1.5} aria-hidden="true" />
            <p className="pilot-kicker">Focused by design</p>
          </div>
          <div className="pilot-scope-copy">
            <h2 id="pilot-scope-title">The everyday work comes first.</h2>
            <p className="pilot-section-lead">
              The pilot brings together machines, manuals, maintenance jobs,
              recurring plans, and team responsibilities. Its focus is a usable
              path from scheduled work to a reviewed record.
            </p>
            <dl className="pilot-scope-list">
              <div>
                <dt>For the person planning</dt>
                <dd>Organize equipment, set maintenance intervals, and assign the work.</dd>
              </div>
              <div>
                <dt>For the person doing</dt>
                <dd>Find the job, follow its checklist, and record the work on a phone or desktop.</dd>
              </div>
              <div>
                <dt>For the person reviewing</dt>
                <dd>Review submitted work and return to the machine’s maintenance history.</dd>
              </div>
            </dl>
          </div>
        </section>

        <section
          id="boundaries"
          className="pilot-boundaries"
          aria-labelledby="pilot-boundaries-title"
        >
          <div className="pilot-wrap pilot-boundaries-layout">
            <div>
              <p className="pilot-kicker">Private pilot / Public overview</p>
              <h2 id="pilot-boundaries-title">A clear boundary around the work.</h2>
              <p>
                You are reading an informational page. No organization’s data is
                displayed, and there is no account or upload flow on this page.
              </p>
            </div>
            <div className="pilot-boundary-notes">
              <div className="pilot-boundary-note">
                <LockKeyhole size={23} strokeWidth={1.5} aria-hidden="true" />
                <div>
                  <h3>Private work stays private.</h3>
                  <p>
                    Accounts, records, and uploads are unavailable on this public
                    page. It is not an interactive preview of a team’s workbench.
                  </p>
                </div>
              </div>
              <div className="pilot-boundary-note">
                <CalendarDays size={23} strokeWidth={1.5} aria-hidden="true" />
                <div>
                  <h3>Scheduled care, not prediction.</h3>
                  <p>
                    This pilot covers calendar-based maintenance and work
                    records. It does not offer live machine monitoring, measured
                    equipment condition, or validated failure predictions.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="pilot-footer pilot-wrap">
        <p>Machivital <span aria-hidden="true">/</span> Maintenance, made clear.</p>
        <a href="#top">
          Back to top <ArrowUp size={17} aria-hidden="true" />
        </a>
      </footer>
    </div>
  );
}
