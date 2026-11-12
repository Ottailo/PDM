import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Download,
  FileText,
  RefreshCw,
  Trash2,
  Upload,
} from "lucide-react";
import { download, get, mutate, uploadManual } from "./api";
import { useIdentity, useResource, refreshData } from "./query";
import { can, dateLabel } from "./permissions";
import type { Asset, Manual } from "./types";
import {
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
  useAction,
  value,
} from "./ui";
const processing = (status: string) =>
  ["quarantined", "queued", "scanning", "processing", "parsing"].includes(
    status,
  );
function UploadForm({
  initialAsset,
  onClose,
}: {
  initialAsset: string;
  onClose: () => void;
}) {
  const assets = useResource<{ assets: Asset[] }>(
    ["assets", "manual-form"],
    "/assets",
  );
  const [progress, setProgress] = useState<number | null>(null);
  const [selectedAsset, setSelectedAsset] = useState(initialAsset);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [uploaded, setUploaded] = useState<Manual | null>(null);
  async function submit(form: FormData) {
    const file = form.get("file");
    if (
      !(file instanceof File) ||
      !file.size ||
      !file.name.toLowerCase().endsWith(".pdf")
    ) {
      setError(new Error("Choose a nonempty PDF file."));
      return;
    }
    const asset = numeric(form, "asset_id");
    if (!asset) {
      setError(new Error("Choose the machine this manual belongs to."));
      return;
    }
    setError(null);
    setPending(true);
    setProgress(null);
    try {
      const result = await uploadManual(
        file,
        asset,
        value(form, "title"),
        setProgress,
      );
      setUploaded(result.document);
      await refreshData();
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause
          : new Error("Upload could not be completed."),
      );
    } finally {
      setPending(false);
    }
  }
  return (
    <Dialog
      title={uploaded ? "Manual received" : "Upload a machine manual"}
      onClose={onClose}
      dismissible={!pending}
    >
      {uploaded ? (
        <>
          <div className="notice">
            <FileText size={23} aria-hidden />
            <div>
              <strong>{uploaded.title || uploaded.filename}</strong>
              <p>
                The file was received. It must pass security scanning and text
                extraction before it can be read or downloaded.
              </p>
            </div>
          </div>
          <Status value={uploaded.status} />
          <p className="muted">
            The manual list checks the actual processing status. It does not
            estimate completion time.
          </p>
          <button className="button primary" onClick={onClose}>
            Return to manuals
          </button>
        </>
      ) : (
        <>
          <p className="form-intro">
            Upload a PDF from your machine’s supplier or service team. Manuals
            stay private to your organization.
          </p>
          <Form onSubmit={(form) => void submit(form)}>
            <Select
              label="Machine"
              name="asset_id"
              required
              value={selectedAsset}
              onChange={(event) => setSelectedAsset(event.target.value)}
              disabled={pending || assets.isPending || !!assets.error}
            >
              <option value="">Choose a machine</option>
              {assets.data?.assets.map((asset) => (
                <option key={asset.id} value={asset.id}>
                  {asset.code} / {asset.name}
                </option>
              ))}
            </Select>
            <ErrorNotice
              error={assets.error}
              retry={() => void assets.refetch()}
            />
            {assets.data?.assets.length === 0 && (
              <p className="notice">
                Record a machine before uploading a manual.{" "}
                <Link to="/app/machines">Open machines</Link>
              </p>
            )}
            <Field
              label="Manual title"
              name="title"
              maxLength={200}
              disabled={pending}
              hint="Optional. If left empty, the file name is used."
            />
            <Field
              label="PDF file"
              name="file"
              type="file"
              accept="application/pdf,.pdf"
              required
              disabled={pending}
              hint="PDF only. The server checks file type, size, security, and page limits."
            />
            {pending && (
              <div className="upload-progress" role="status">
                <span>
                  {progress === 100
                    ? "Upload sent. Waiting for the server to accept the file…"
                    : progress === null
                      ? "Sending file…"
                      : `Sending file: ${progress}%`}
                </span>
                <progress
                  max={100}
                  {...(progress === null ? {} : { value: progress })}
                  aria-label="File transfer progress"
                />
                <p className="muted">
                  This shows file transfer only, not security processing.
                </p>
              </div>
            )}
            <ErrorNotice error={error} />
            <div className="form-actions">
              <button
                className="button secondary"
                type="button"
                disabled={pending}
                onClick={onClose}
              >
                Cancel
              </button>
              <button
                className="button primary"
                type="submit"
                disabled={pending || !assets.data?.assets.length}
              >
                {pending ? "Uploading…" : error ? "Retry upload" : "Upload PDF"}
                <Upload size={17} aria-hidden />
              </button>
            </div>
          </Form>
        </>
      )}
    </Dialog>
  );
}
function ManualReader({ id, onClose }: { id: number; onClose: () => void }) {
  const identity = useIdentity().data!;
  const [page, setPage] = useState(1);
  const manual = useQuery({
    queryKey: ["v1", identity.company.id, "document", id],
    queryFn: ({ signal }) =>
      get<{ document: Manual }>(`/documents/${id}`, signal),
    refetchInterval: (query) =>
      processing(query.state.data?.document.status || "") ? 3000 : false,
  });
  const document = manual.data?.document;
  const text = useQuery({
    queryKey: ["v1", identity.company.id, "document-page", id, page],
    queryFn: ({ signal }) =>
      get<{ page_number: number; text: string }>(
        `/documents/${id}/pages/${page}`,
        signal,
      ),
    enabled: document?.status === "ready",
  });
  const downloadFile = useAction(
    () =>
      download(
        `/documents/${id}/download`,
        document?.filename || `manual-${id}.pdf`,
      ),
    "Manual downloaded.",
  );
  return (
    <Dialog title={document?.title || "Machine manual"} onClose={onClose}>
      {manual.isPending ? (
        <Loading label="Loading manual…" />
      ) : manual.error ? (
        <ErrorNotice error={manual.error} retry={() => void manual.refetch()} />
      ) : (
        document && (
          <>
            <div className="reader-meta">
              <span>{document.asset_name}</span>
              <Status value={document.status} />
            </div>
            {document.status !== "ready" ? (
              <div
                className={`notice ${["failed", "blocked"].includes(document.status) ? "warning" : ""}`}
              >
                <div>
                  <strong>
                    {["failed", "blocked"].includes(document.status)
                      ? "This manual is not available to read."
                      : "Processing this manual."}
                  </strong>
                  <p>
                    {document.error ||
                      "The file must pass security scanning and text extraction before it can be opened."}
                  </p>
                  <button
                    className="button secondary small"
                    onClick={() => void manual.refetch()}
                  >
                    <RefreshCw size={16} aria-hidden />
                    Check status
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="reader-controls">
                  <button
                    className="button secondary small"
                    disabled={page <= 1}
                    onClick={() => setPage((current) => current - 1)}
                  >
                    <ChevronLeft size={17} aria-hidden />
                    Previous
                  </button>
                  <Select
                    label="Page"
                    value={page}
                    onChange={(event) => setPage(Number(event.target.value))}
                  >
                    {Array.from(
                      { length: document.page_count || 1 },
                      (_, index) => (
                        <option key={index} value={index + 1}>
                          {index + 1} of {document.page_count || 1}
                        </option>
                      ),
                    )}
                  </Select>
                  <button
                    className="button secondary small"
                    disabled={page >= (document.page_count || 1)}
                    onClick={() => setPage((current) => current + 1)}
                  >
                    Next
                    <ChevronRight size={17} aria-hidden />
                  </button>
                  <button
                    className="button secondary small"
                    disabled={downloadFile.isPending}
                    onClick={() => downloadFile.mutate()}
                  >
                    <Download size={16} aria-hidden />
                    Download PDF
                  </button>
                </div>
                <p className="reader-note">
                  Text view of the authenticated manual. Download the original
                  PDF for diagrams and page layout.
                </p>
                <ErrorNotice error={downloadFile.error} />
                {text.isPending ? (
                  <Loading label={`Loading page ${page}…`} />
                ) : text.error ? (
                  <ErrorNotice
                    error={text.error}
                    retry={() => void text.refetch()}
                  />
                ) : text.data?.text.trim() ? (
                  <article
                    className="page-text"
                    aria-label={`Manual page ${page}`}
                  >
                    <pre>{text.data.text}</pre>
                  </article>
                ) : (
                  <Empty title="No readable text on this page">
                    This page may contain an image or diagram. Download the
                    original PDF to view it.
                  </Empty>
                )}
              </>
            )}
          </>
        )
      )}
    </Dialog>
  );
}
export function Manuals() {
  const identity = useIdentity().data!;
  const [params, setParams] = useSearchParams();
  const assetId = params.get("asset_id") || "";
  const selected = Number(params.get("document")) || null;
  const [upload, setUpload] = useState(false);
  const [remove, setRemove] = useState<Manual | null>(null);
  const assets = useResource<{ assets: Asset[] }>(
    ["assets", "manual-filter"],
    "/assets?include_archived=true",
  );
  const documents = useQuery({
    queryKey: ["v1", identity.company.id, "documents", assetId],
    queryFn: ({ signal }) =>
      get<{ documents: Manual[] }>(
        `/documents${assetId ? `?asset_id=${assetId}` : ""}`,
        signal,
      ),
    refetchInterval: (query) =>
      query.state.data?.documents.some((document) =>
        processing(document.status),
      )
        ? 3000
        : false,
  });
  const deletion = useAction(
    () => mutate(`/documents/${remove!.id}`, {}, "DELETE"),
    "Manual access removed.",
    () => setRemove(null),
  );
  const downloadFile = useAction(
    (document: Manual) =>
      download(`/documents/${document.id}/download`, document.filename),
    "Manual downloaded.",
  );
  function filter(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key === "asset_id") next.delete("document");
    setParams(next, { replace: true });
  }
  return (
    <>
      <PageHeader
        eyebrow="Instructions, kept close"
        title="Manuals"
        description="Private machine manuals, with a safe page-by-page text reader."
        actions={
          can(identity, "upload_documents") && (
            <button className="button primary" onClick={() => setUpload(true)}>
              <Upload size={18} aria-hidden />
              Upload PDF
            </button>
          )
        }
      />
      <div className="toolbar">
        <Select
          label="Machine"
          value={assetId}
          onChange={(event) => filter("asset_id", event.target.value)}
          disabled={assets.isPending || !!assets.error}
        >
          <option value="">All machines</option>
          {assets.data?.assets.map((asset) => (
            <option key={asset.id} value={asset.id}>
              {asset.code} / {asset.name}
              {asset.status === "archived" ? " (Archived)" : ""}
            </option>
          ))}
        </Select>
        <button
          className="button secondary"
          onClick={() => void documents.refetch()}
          disabled={documents.isFetching}
        >
          <RefreshCw size={17} aria-hidden />
          Refresh status
        </button>
        <span className="muted">
          Files are read only after security processing.
        </span>
      </div>
      <ErrorNotice error={assets.error} retry={() => void assets.refetch()} />
      <ErrorNotice error={downloadFile.error} />
      <section className="panel">
        {documents.isPending ? (
          <Loading label="Loading machine manuals…" />
        ) : documents.error ? (
          <ErrorNotice
            error={documents.error}
            retry={() => void documents.refetch()}
          />
        ) : !documents.data?.documents.length ? (
          <Empty
            title="Instructions belong with the machine"
            action={
              can(identity, "upload_documents") && (
                <button
                  className="button primary"
                  onClick={() => setUpload(true)}
                >
                  Upload a manual
                </button>
              )
            }
          >
            No manuals have been attached{assetId ? " to this machine" : " yet"}
            . Add a PDF to keep the supplier’s instructions within reach.
          </Empty>
        ) : (
          <div className="manual-list">
            {documents.data.documents.map((document) => (
              <article className="manual-row" key={document.id}>
                <div className="manual-symbol">
                  <FileText size={25} aria-hidden />
                </div>
                <div className="manual-content">
                  <h3>
                    <button
                      className="record-button"
                      onClick={() => filter("document", String(document.id))}
                    >
                      {document.title || document.filename}
                    </button>
                  </h3>
                  <p>
                    <Link to={`/app/machines/${document.asset_id}`}>
                      {document.asset_name}
                    </Link>
                    <span> / {document.filename}</span>
                  </p>
                  <small>
                    Added {dateLabel(document.created_at)}
                    {document.page_count
                      ? ` / ${document.page_count} pages`
                      : ""}
                  </small>
                  {processing(document.status) && (
                    <p className="muted">
                      Checking actual security and text processing status.
                    </p>
                  )}
                  {document.error && (
                    <div className="manual-error" role="status">
                      {document.error}
                    </div>
                  )}
                </div>
                <div className="manual-actions">
                  <Status value={document.status} />
                  <button
                    className="button secondary small"
                    onClick={() => filter("document", String(document.id))}
                  >
                    <BookOpen size={16} aria-hidden />
                    {document.status === "ready"
                      ? "Read manual"
                      : "View status"}
                  </button>
                  {document.status === "ready" && (
                    <button
                      className="icon-button"
                      aria-label={`Download ${document.title}`}
                      disabled={downloadFile.isPending}
                      onClick={() => downloadFile.mutate(document)}
                    >
                      <Download size={19} />
                    </button>
                  )}
                  {can(identity, "manage_registry") && (
                    <button
                      className="icon-button"
                      aria-label={`Remove ${document.title}`}
                      onClick={() => {
                        deletion.reset();
                        setRemove(document);
                      }}
                    >
                      <Trash2 size={18} />
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
      <div className="manual-footnote">
        <FileText size={18} aria-hidden />
        <p>
          A failed or blocked file is not downloadable. Check the error, then
          upload the corrected file when the cause has been resolved. No
          automatic retry is claimed.
        </p>
      </div>
      {upload && (
        <UploadForm initialAsset={assetId} onClose={() => setUpload(false)} />
      )}
      {selected && (
        <ManualReader id={selected} onClose={() => filter("document", "")} />
      )}
      {remove && (
        <Dialog title="Remove this manual?" onClose={() => setRemove(null)}>
          <p>
            <strong>{remove.title}</strong> will no longer be readable or
            downloadable. Processing jobs will be cancelled. Private original
            files are retained until your organization’s retention process
            removes them.
          </p>
          <ErrorNotice error={deletion.error} />
          <div className="form-actions">
            <button
              className="button secondary"
              onClick={() => setRemove(null)}
            >
              Keep manual
            </button>
            <button
              className="button danger"
              disabled={deletion.isPending}
              onClick={() => deletion.mutate()}
            >
              {deletion.isPending ? "Removing…" : "Remove manual"}
            </button>
          </div>
        </Dialog>
      )}
    </>
  );
}
