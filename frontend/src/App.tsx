import { useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { DigestStatus } from "./components/DigestStatus";
import { DigestView } from "./components/DigestView";
import { CategoriesView } from "./components/CategoriesView";
import { Inbox } from "./components/Inbox";
import { RunButton } from "./components/RunButton";
import { SideFoot } from "./components/SideFoot";
import { SourcesView } from "./components/SourcesView";
import { inboxTotal } from "./categories";
import { useSources, useTaxonomy } from "./hooks";
import { useLocation } from "./router";
import { useShortcuts } from "./shortcuts";

export function App() {
  const { location, go } = useLocation();
  const [slot, setSlot] = useState<HTMLElement | null>(null);
  const search = useRef<HTMLInputElement>(null);
  const taxonomy = useTaxonomy();
  const sources = useSources();
  useShortcuts(
    useMemo(
      () => ({
        "/": () => {
          search.current?.focus();
        },
      }),
      [],
    ),
  );
  const link = (to: string, label: string, icon: ReactNode, count?: number) => (
    <a
      href={to}
      aria-current={location.path === to ? "page" : undefined}
      onClick={(e) => {
        e.preventDefault();
        go(to);
      }}
    >
      <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
        {icon}
      </svg>
      {label}
      {count !== undefined && (
        <span className="n" aria-hidden="true">
          {count}
        </span>
      )}
    </a>
  );
  return (
    <div className="app">
      <div className="side">
        <header>
          <p className="brand">
            <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true">
              <circle cx="11" cy="11" r="8.5" fill="none" stroke="currentColor" strokeWidth="2" />
              <circle cx="14.2" cy="8.2" r="2.6" fill="currentColor" />
            </svg>
            Lookout
          </p>
          <p className="scope">Personal watch</p>
          <nav aria-label="Main">
            {link(
              "/",
              "Inbox",
              <>
                <path d="M2 9.5l1.6-5.2A1 1 0 0 1 4.5 3.6h7a1 1 0 0 1 .9.7L14 9.5V12a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1z" />
                <path d="M2 9.5h3.2l.8 1.5h4l.8-1.5H14" />
              </>,
              taxonomy.data && inboxTotal(taxonomy.data.channels),
            )}
            {link(
              "/digest",
              "Digest",
              <>
                <path d="M3 2.5h10v11H3z" />
                <path d="M5.5 5.5h5M5.5 8h5M5.5 10.5h3" />
              </>,
            )}
            {link(
              "/sources",
              "Sources",
              <>
                <path d="M3 3a10 10 0 0 1 10 10M3 7a6 6 0 0 1 6 6" />
                <circle cx="3.6" cy="12.4" r=".9" />
              </>,
              sources.data?.length,
            )}
            {link("/categories", "Categories", <path d="M3 3h4v4H3zM9 3h4v4H9zM3 9h4v4H3zM9 9h4v4H9z" />)}
          </nav>
        </header>
        <div className="side-slot" ref={setSlot} />
        <SideFoot />
      </div>
      <div className="topbar">
        <label className="topsearch">
          <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
            <circle cx="7" cy="7" r="4.5" />
            <path d="M10.5 10.5L14 14" />
          </svg>
          <input
            ref={search}
            type="search"
            aria-label="Search items, sources, tags"
            placeholder="Search items, sources, tags"
            value={location.filters.text}
            onChange={(e) => {
              go("/", { ...location.filters, text: e.target.value });
            }}
          />
          <kbd>/</kbd>
        </label>
        <div className="top-right">
          <DigestStatus go={go} />
          <RunButton />
        </div>
      </div>
      <main className="sheet">
        {location.path === "/digest" || location.path.startsWith("/digest/") ? (
          <DigestView
            id={location.path.slice("/digest/".length) || null}
            onOpen={(id) => {
              go(id ? `/digest/${id}` : "/digest");
            }}
          />
        ) : location.path === "/sources" ? (
          <SourcesView />
        ) : location.path === "/categories" ? (
          <CategoriesView />
        ) : (
          <Inbox
            side={slot}
            filters={location.filters}
            openId={location.item}
            onFilters={(filters) => {
              go("/", filters, location.item);
            }}
            onOpen={(id, replace) => {
              go("/", location.filters, id, replace);
            }}
          />
        )}
      </main>
    </div>
  );
}
