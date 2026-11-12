import { Link } from "react-router-dom";

/** Shared identity, independent of authentication and workbench data. */
export function Brand({ home = "/app" }: { home?: string }) {
  return (
    <Link to={home} className="brand" aria-label="Machivital home">
      <img src="/mark.svg" width="38" height="38" alt="" />
      <span>
        machivital<small>Maintenance workbench</small>
      </span>
    </Link>
  );
}
