import { useEffect, useMemo, useRef, useState } from "react";
import type { CatalogRole } from "../types";

interface Props {
  roles: CatalogRole[];
  value: string;
  onChange: (v: string) => void;
}

/** Searchable role picker: type to filter, or enter a custom role. */
export default function RoleCombobox({ roles, value, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const wrapRef = useRef<HTMLDivElement>(null);

  const matches = useMemo(() => {
    const q = value.trim().toLowerCase();
    if (q.length < 2) return []; // dropdown stays closed until 2+ chars
    return roles.filter((r) => r.name.toLowerCase().includes(q));
  }, [roles, value]);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  function pick(name: string) {
    onChange(name);
    setOpen(false);
  }

  const noMatch = value.trim().length >= 2 && matches.length === 0;

  return (
    <div className="combobox" ref={wrapRef}>
      <input
        className="combobox__input"
        type="text"
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setOpen(e.target.value.trim().length >= 2);
          setActive(0);
        }}
        onFocus={() => setOpen(value.trim().length >= 2)}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setOpen(true);
            setActive((a) => Math.min(a + 1, matches.length - 1));
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setActive((a) => Math.max(a - 1, 0));
          } else if (e.key === "Enter" && open && matches[active]) {
            e.preventDefault();
            pick(matches[active].name);
          } else if (e.key === "Escape") {
            setOpen(false);
          }
        }}
        placeholder="Type a role, e.g. Backend Engineer"
        autoFocus
        autoComplete="off"
        role="combobox"
        aria-expanded={open}
        aria-autocomplete="list"
      />
      {open && matches.length > 0 && (
        <ul className="combobox__list" role="listbox">
          {matches.map((r, i) => (
            <li
              key={r.id}
              role="option"
              aria-selected={i === active}
              className={`combobox__option ${i === active ? "is-active" : ""}`}
              onMouseDown={(e) => {
                e.preventDefault();
                pick(r.name);
              }}
              onMouseEnter={() => setActive(i)}
            >
              {r.name}
            </li>
          ))}
        </ul>
      )}
      {open && noMatch && (
        <div className="combobox__hint">
          No preset match. “{value.trim()}” will be used as a custom role.
        </div>
      )}
    </div>
  );
}
