import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowUpRight,
  Plus,
  Search,
  Pencil,
  Archive,
  Unplug,
} from "lucide-react";
import { ApiError, mutate, queryString } from "./api";
import { refreshData, useIdentity, useResource } from "./query";
import { can } from "./permissions";
import type { Asset, Location, Manual, WorkOrder } from "./types";
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
import { WorkQueue } from "./Today";

function AssetForm({ asset, onClose }: { asset?: Asset; onClose: () => void }) {
  const [selectedLocation, setSelectedLocation] = useState(String(asset?.location_id || ""));
  const locations = useResource<{ locations: Location[] }>(
    ["locations"],
    "/locations",
  );
  const save = useAction(
    (data: FormData) => {
      const body = {
        code: value(data, "code"),
        name: value(data, "name"),
        manufacturer: value(data, "manufacturer"),
        model: value(data, "model"),
        serial_number: value(data, "serial_number"),
        criticality: value(data, "criticality"),
        location_id: numeric(data, "location_id"),
        description: value(data, "description"),
        ...(asset ? { revision: asset.revision } : {}),
      };
      return mutate<{ asset: Asset }>(
        asset ? `/assets/${asset.id}` : "/assets",
        body,
        asset ? "PATCH" : "POST",
      );
    },
    asset ? "Machine updated." : "Machine recorded.",
    onClose,
  );
  return (
    <Dialog
      title={asset ? "Edit machine" : "Record a machine"}
      onClose={onClose}
    >
      <p className="form-intro">
        Record the equipment as it is. Sensors are not required.
      </p>
      <Form onSubmit={(data) => save.mutate(data)}>
        <div className="form-grid">
          <Field
            label="Machine name"
            name="name"
            required
            defaultValue={asset?.name}
            maxLength={100}
          />
          <Field
            label="Machine code"
            name="code"
            required
            defaultValue={asset?.code}
            maxLength={50}
            hint="Your organization’s unique equipment label."
          />
          <Field
            label="Manufacturer"
            name="manufacturer"
            defaultValue={asset?.manufacturer}
            maxLength={100}
          />
          <Field
            label="Model"
            name="model"
            defaultValue={asset?.model}
            maxLength={100}
          />
          <Field
            label="Serial number"
            name="serial_number"
            defaultValue={asset?.serial_number}
            maxLength={100}
          />
          <Select
            label="Criticality"
            name="criticality"
            defaultValue={asset?.criticality || "medium"}
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </Select>
        </div>
        <Select
          label="Location"
          name="location_id"
          value={selectedLocation}
          onChange={(event) => setSelectedLocation(event.target.value)}
          disabled={locations.isPending || !!locations.error}
        >
          <option value="">No location assigned</option>
          {locations.data?.locations.map((location) => (
            <option key={location.id} value={location.id}>
              {location.name} ({location.type})
            </option>
          ))}
        </Select>
        <ErrorNotice
          error={locations.error}
          retry={() => void locations.refetch()}
        />
        <Textarea
          label="Description"
          name="description"
          defaultValue={asset?.description}
          maxLength={4000}
        />
        <ErrorNotice error={save.error} />
        {save.error instanceof ApiError &&
          save.error.code === "revision_conflict" && (
            <button
              className="button secondary"
              type="button"
              onClick={() => {
                onClose();
                void refreshData();
              }}
            >
              Close and refresh record
            </button>
          )}
        <div className="form-actions">
          <button className="button secondary" type="button" onClick={onClose}>
            Cancel
          </button>
          <Submit pending={save.isPending}>
            {asset ? "Save changes" : "Record machine"}
          </Submit>
        </div>
      </Form>
    </Dialog>
  );
}
function LocationForm({ onClose }: { onClose: () => void }) {
  const locations = useResource<{ locations: Location[] }>(
    ["locations"],
    "/locations",
  );
  const [type, setType] = useState("Site");
  const save = useAction(
    (data: FormData) =>
      mutate("/locations", {
        name: value(data, "name"),
        type,
        parent_id: numeric(data, "parent_id"),
      }),
    "Location created.",
    onClose,
  );
  return (
    <Dialog title="Add a location" onClose={onClose}>
      <p className="form-intro">
        Organize your floor into sites, areas, and lines.
      </p>
      <Form onSubmit={(data) => save.mutate(data)}>
        <Field label="Location name" name="name" required maxLength={100} />
        <Select
          label="Location type"
          value={type}
          onChange={(event) => setType(event.target.value)}
        >
          <option>Site</option>
          <option>Area</option>
          <option>Line</option>
        </Select>
        <Select
          key={type}
          label="Parent location"
          name="parent_id"
          required={type !== "Site"}
          disabled={type === "Site" || locations.isPending || !!locations.error}
        >
          <option value="">
            {type === "Site"
              ? "Sites are top-level locations"
              : "Choose a parent"}
          </option>
          {locations.data?.locations
            .filter(
              (location) =>
                location.type.toLowerCase() ===
                (type === "Area" ? "site" : "area"),
            )
            .map((location) => (
              <option key={location.id} value={location.id}>
                {location.name}
              </option>
            ))}
        </Select>
        <ErrorNotice
          error={locations.error}
          retry={() => void locations.refetch()}
        />
        <ErrorNotice error={save.error} />
        <Submit pending={save.isPending}>Add location</Submit>
      </Form>
    </Dialog>
  );
}
export function Machines() {
  const identity = useIdentity().data!;
  const [params, setParams] = useSearchParams();
  const [dialog, setDialog] = useState<"asset" | "location" | null>(null);
  const query = params.get("q") || "";
  const location = params.get("location_id") || "";
  const archived = params.get("include_archived") === "true";
  const assets = useResource<{ assets: Asset[] }>(
    ["assets", query, location, archived],
    `/assets${queryString({ q: query, location_id: location, include_archived: archived })}`,
  );
  const locations = useResource<{ locations: Location[] }>(
    ["locations"],
    "/locations",
  );
  function filter(name: string, val: string) {
    const next = new URLSearchParams(params);
    if (val) next.set(name, val);
    else next.delete(name);
    setParams(next, { replace: true });
  }
  return (
    <>
      <PageHeader
        eyebrow="Equipment registry"
        title="Machines"
        description="A dependable record of what’s on your floor."
        actions={
          can(identity, "manage_registry") && (
            <>
              <button
                className="button secondary"
                onClick={() => setDialog("location")}
              >
                Add location
              </button>
              <button
                className="button primary"
                onClick={() => setDialog("asset")}
              >
                <Plus size={18} aria-hidden />
                Record machine
              </button>
            </>
          )
        }
      />
      <div className="toolbar">
        <label className="search-field">
          <Search size={19} aria-hidden />
          <span className="sr-only">Search machines</span>
          <input
            type="search"
            value={query}
            onChange={(event) => filter("q", event.target.value)}
            placeholder="Search name, code, or model"
          />
        </label>
        <Select
          label="Location"
          value={location}
          onChange={(event) => filter("location_id", event.target.value)}
          disabled={locations.isPending || !!locations.error}
        >
          <option value="">All locations</option>
          {locations.data?.locations.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </Select>
        <label className="check-row">
          <input
            type="checkbox"
            checked={archived}
            onChange={(event) =>
              filter("include_archived", event.target.checked ? "true" : "")
            }
          />
          Include archived
        </label>
      </div>
      <ErrorNotice
        error={locations.error}
        retry={() => void locations.refetch()}
      />
      <section className="panel">
        {assets.isPending ? (
          <Loading label="Loading machines…" />
        ) : assets.error ? (
          <ErrorNotice
            error={assets.error}
            retry={() => void assets.refetch()}
          />
        ) : !assets.data?.assets.length ? (
          <Empty
            title={
              query || location
                ? "No machines match these filters"
                : "Your machines start here"
            }
            action={
              can(identity, "manage_registry") && (
                <button
                  className="button primary"
                  onClick={() => setDialog("asset")}
                >
                  Record your first machine
                </button>
              )
            }
          >
            {query || location
              ? "Try a different search or location. Your other records have not been removed."
              : "Add equipment with its name and code. You can add a location and a manual now or later."}
          </Empty>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Machine</th>
                  <th>Location</th>
                  <th>Manufacturer / model</th>
                  <th>Criticality</th>
                  <th>Measurements</th>
                  <th>
                    <span className="sr-only">Open</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {assets.data.assets.map((asset) => (
                  <tr key={asset.id}>
                    <td>
                      <Link
                        className="record-name"
                        to={`/app/machines/${asset.id}`}
                      >
                        <strong>{asset.name}</strong>
                        <span>
                          {asset.code}
                          {asset.status === "archived" ? " / Archived" : ""}
                        </span>
                      </Link>
                    </td>
                    <td>{asset.location_name || "Not assigned"}</td>
                    <td>
                      {[asset.manufacturer, asset.model]
                        .filter(Boolean)
                        .join(" / ") || "Not recorded"}
                    </td>
                    <td>
                      <Status value={asset.criticality || "medium"} />
                    </td>
                    <td>
                      <span className="muted">Not connected</span>
                    </td>
                    <td>
                      <Link
                        className="icon-button"
                        to={`/app/machines/${asset.id}`}
                        aria-label={`Open ${asset.name}`}
                      >
                        <ArrowUpRight size={20} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      {dialog === "asset" && <AssetForm onClose={() => setDialog(null)} />}
      {dialog === "location" && (
        <LocationForm onClose={() => setDialog(null)} />
      )}
    </>
  );
}
export function MachineDetail() {
  const { id } = useParams();
  const identity = useIdentity().data!;
  const [edit, setEdit] = useState(false);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const asset = useResource<{ asset: Asset }>(["asset", id], `/assets/${id}`);
  const jobs = useResource<{ work_orders: WorkOrder[] }>(
    ["work-orders", "asset", id],
    `/work-orders?asset_id=${id}`,
  );
  const manuals = useResource<{ documents: Manual[] }>(
    ["documents", "asset", id],
    `/documents?asset_id=${id}`,
  );
  const archive = useAction(
    () => mutate(`/assets/${id}`, {}, "DELETE"),
    "Machine archived. Its history is preserved.",
    () => setArchiveOpen(false),
  );
  if (asset.isPending) return <Loading label="Loading machine record…" />;
  if (asset.error)
    return (
      <ErrorNotice error={asset.error} retry={() => void asset.refetch()} />
    );
  const machine = asset.data!.asset;
  return (
    <>
      <Link className="back-link" to="/app/machines">
        <ArrowLeft size={16} aria-hidden />
        All machines
      </Link>
      <PageHeader
        eyebrow={machine.code}
        title={machine.name}
        description={machine.location_name || "No location assigned"}
        actions={
          can(identity, "manage_registry") &&
          machine.status !== "archived" && (
            <>
              <button
                className="button secondary"
                onClick={() => setEdit(true)}
              >
                <Pencil size={17} aria-hidden />
                Edit machine
              </button>
              <button
                className="button secondary"
                onClick={() => setArchiveOpen(true)}
              >
                <Archive size={17} aria-hidden />
                Archive
              </button>
            </>
          )
        }
      />
      <div className="detail-columns">
        <section className="panel">
          <div className="section-heading">
            <h2>Equipment record</h2>
            <Status value={machine.status} />
          </div>
          <Definition
            items={[
              ["Manufacturer", machine.manufacturer],
              ["Model", machine.model],
              ["Serial number", machine.serial_number],
              ["Criticality", <Status value={machine.criticality} />],
              ["Location", machine.location_name],
              ["Description", machine.description],
            ]}
          />
        </section>
        <aside className="measurement-note">
          <Unplug size={28} aria-hidden />
          <p className="eyebrow">Measurements</p>
          <h2>Not connected</h2>
          <p>
            No sensor measurements are available for this machine. You can
            record equipment and complete maintenance without sensors.
          </p>
        </aside>
      </div>
      <section className="panel">
        <div className="section-heading">
          <h2>Maintenance history</h2>
          {can(identity, "request_work_orders") &&
            machine.status !== "archived" && (
              <Link
                className="button secondary small"
                to={`/app/maintenance?new=1&asset_id=${machine.id}`}
              >
                Create job
              </Link>
            )}
        </div>
        {jobs.isPending ? (
          <Loading />
        ) : jobs.error ? (
          <ErrorNotice error={jobs.error} retry={() => void jobs.refetch()} />
        ) : jobs.data?.work_orders.length ? (
          <WorkQueue jobs={jobs.data.work_orders} />
        ) : (
          <Empty title="No maintenance recorded">
            Jobs created for this machine will appear here, including completed
            work.
          </Empty>
        )}
      </section>
      <section className="panel">
        <div className="section-heading">
          <h2>Machine manuals</h2>
          <Link
            to={`/app/manuals?asset_id=${machine.id}`}
            className="text-link"
          >
            Open manuals
            <ArrowUpRight size={16} aria-hidden />
          </Link>
        </div>
        {manuals.isPending ? (
          <Loading />
        ) : manuals.error ? (
          <ErrorNotice
            error={manuals.error}
            retry={() => void manuals.refetch()}
          />
        ) : manuals.data?.documents.length ? (
          <ul className="simple-list">
            {manuals.data.documents.map((document) => (
              <li key={document.id}>
                <Link
                  to={`/app/manuals?asset_id=${machine.id}&document=${document.id}`}
                >
                  {document.title || document.filename}
                </Link>
                <Status value={document.status} />
              </li>
            ))}
          </ul>
        ) : (
          <Empty title="No manuals attached">
            Upload a PDF to keep the instructions with this machine.
          </Empty>
        )}
      </section>
      {edit && <AssetForm asset={machine} onClose={() => setEdit(false)} />}
      {archiveOpen && (
        <Dialog
          title="Archive this machine?"
          onClose={() => setArchiveOpen(false)}
        >
          <p>
            It will be hidden from the active registry. Maintenance history and
            manuals will remain attached.
          </p>
          <ErrorNotice error={archive.error} />
          <div className="form-actions">
            <button
              className="button secondary"
              onClick={() => setArchiveOpen(false)}
            >
              Keep machine
            </button>
            <button
              className="button danger"
              disabled={archive.isPending}
              onClick={() => archive.mutate()}
            >
              {archive.isPending ? "Archiving…" : "Archive machine"}
            </button>
          </div>
        </Dialog>
      )}
    </>
  );
}
