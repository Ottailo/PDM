import {
  createContext,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";
import type {
  ReactNode,
  FormEvent,
  InputHTMLAttributes,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";
import { useMutation } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  Check,
  LoaderCircle,
  X,
} from "lucide-react";
import { ApiError } from "./api";
import { queryClient, refreshData } from "./query";
import { plainStatus } from "./permissions";

const ToastContext = createContext<(message: string) => void>(() => {
  throw new Error("Toast provider missing");
});
export function ToastProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState("");
  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => setMessage(""), 6000);
    return () => clearTimeout(timer);
  }, [message]);
  return (
    <ToastContext.Provider value={setMessage}>
      {children}
      <div className="toast-region" aria-live="polite" aria-atomic="true">
        {message && (
          <div className="toast">
            <Check size={18} aria-hidden />
            <span>{message}</span>
            <button aria-label="Dismiss message" onClick={() => setMessage("")}>
              <X size={18} />
            </button>
          </div>
        )}
      </div>
    </ToastContext.Provider>
  );
}
export function useAction<T, V>(
  fn: (value: V) => Promise<T>,
  message: string,
  success?: (data: T) => void | Promise<void>,
) {
  const toast = useContext(ToastContext);
  return useMutation({
    gcTime: 0,
    mutationFn: fn,
    onError: (error) => {
      if (
        error instanceof ApiError &&
        error.status === 401 &&
        error.code !== "mfa_required"
      )
        void queryClient.invalidateQueries({ queryKey: ["v1", "identity"] });
    },
    onSuccess: async (data) => {
      await success?.(data);
      if (message) toast(message);
      await refreshData();
    },
  });
}
export function ErrorNotice({
  error,
  retry,
}: {
  error: Error | null | undefined;
  retry?: () => void;
}) {
  if (!error) return null;
  return (
    <div className="notice error" role="alert">
      <AlertTriangle size={19} aria-hidden />
      <div>
        <strong>{error.message}</strong>
        {error instanceof ApiError && Object.keys(error.fields).length > 0 && (
          <ul>
            {Object.entries(error.fields).map(([field, message]) => (
              <li key={field}>
                {plainStatus(field)}: {message}
              </li>
            ))}
          </ul>
        )}
        {error instanceof ApiError && error.code === "revision_conflict" && (
          <p>
            Your changes were not saved. Refresh the record and check the latest
            version before retrying.
          </p>
        )}
        {error instanceof ApiError && error.requestId && (
          <small>Reference: {error.requestId}</small>
        )}
        {retry && (
          <button
            className="button secondary small"
            type="button"
            onClick={retry}
          >
            Try again
          </button>
        )}
      </div>
    </div>
  );
}
export function Loading({ label = "Loading records…" }: { label?: string }) {
  return (
    <div role="status" className="loading" aria-busy="true">
      <LoaderCircle size={20} aria-hidden />
      <span>{label}</span>
      <div className="skeleton" />
      <div className="skeleton" />
      <div className="skeleton short" />
    </div>
  );
}
export function Empty({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <span className="empty-rule" />
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  );
}
export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {description && <p className="page-description">{description}</p>}
      </div>
      {actions && <div className="header-actions">{actions}</div>}
    </header>
  );
}
export function Status({ value }: { value: string }) {
  return <span className={`status status-${value}`}>{plainStatus(value)}</span>;
}
export function Field({
  label,
  hint,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string }) {
  const id = useId();
  return (
    <label className="field" htmlFor={id}>
      <span>
        {label}
        {props.required && <span className="required"> *</span>}
      </span>
      <input
        {...props}
        id={id}
        aria-describedby={hint ? `${id}-hint` : undefined}
      />
      {hint && <small id={`${id}-hint`}>{hint}</small>}
    </label>
  );
}
export function Select({
  label,
  children,
  hint,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & { label: string; hint?: string }) {
  const id = useId();
  return (
    <label className="field" htmlFor={id}>
      <span>
        {label}
        {props.required && <span className="required"> *</span>}
      </span>
      <select {...props} id={id} aria-describedby={hint ? `${id}-hint` : undefined}>
        {children}
      </select>
      {hint && <small id={`${id}-hint`}>{hint}</small>}
    </label>
  );
}
export function Textarea({
  label,
  hint,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label: string;
  hint?: string;
}) {
  const id = useId();
  return (
    <label className="field" htmlFor={id}>
      <span>
        {label}
        {props.required && <span className="required"> *</span>}
      </span>
      <textarea {...props} id={id} rows={props.rows || 3} />
      {hint && <small>{hint}</small>}
    </label>
  );
}
export function Submit({
  pending,
  children,
}: {
  pending: boolean;
  children: ReactNode;
}) {
  return (
    <button className="button primary" type="submit" disabled={pending}>
      {pending ? (
        <>
          <LoaderCircle size={17} aria-hidden />
          Saving…
        </>
      ) : (
        <>
          {children}
          <ArrowRight size={17} aria-hidden />
        </>
      )}
    </button>
  );
}
export function Dialog({
  title,
  children,
  onClose,
  dismissible = true,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  dismissible?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const id = useId();
  useEffect(() => {
    const dialog = ref.current!;
    const previous = document.activeElement as HTMLElement | null;
    dialog.showModal();
    return () => {
      dialog.close();
      previous?.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      aria-labelledby={id}
      onCancel={(event) => {
        event.preventDefault();
        if (dismissible) onClose();
      }}
      onClick={(event) => {
        if (dismissible && event.target === ref.current) {
          const rect = ref.current.getBoundingClientRect();
          if (
            event.clientX < rect.left ||
            event.clientX > rect.right ||
            event.clientY < rect.top ||
            event.clientY > rect.bottom
          )
            onClose();
        }
      }}
    >
      <div className="dialog-header">
        <h2 id={id}>{title}</h2>
        <button
          className="icon-button"
          aria-label="Close dialog"
          type="button"
          disabled={!dismissible}
          onClick={onClose}
        >
          <X size={22} />
        </button>
      </div>
      <div className="dialog-content">{children}</div>
    </dialog>
  );
}
export function Form({
  children,
  onSubmit,
  className = "",
}: {
  children: ReactNode;
  onSubmit: (data: FormData, event: FormEvent<HTMLFormElement>) => void;
  className?: string;
}) {
  return (
    <form
      className={`form ${className}`}
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(new FormData(event.currentTarget), event);
      }}
    >
      {children}
    </form>
  );
}
export const value = (form: FormData, name: string) =>
  String(form.get(name) || "").trim();
export const numeric = (form: FormData, name: string) =>
  value(form, name) ? Number(value(form, name)) : null;
export function Definition({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="definitions">
      {items.map(([label, content]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{content || "Not recorded"}</dd>
        </div>
      ))}
    </dl>
  );
}
