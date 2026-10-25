import { useState } from "react";
import { DigestStatus } from "./components/DigestStatus";
import { DigestView } from "./components/DigestView";
import { CategoriesView } from "./components/CategoriesView";
import { Inbox } from "./components/Inbox";
import { RunButton } from "./components/RunButton";
import { SourcesView } from "./components/SourcesView";
import { useLocation } from "./router";

export function App() {
  const { location, go } = useLocation();
  const [slot, setSlot] = useState<HTMLElement | null>(null);
  const link = (to: string, label: string) => (
    <a
      href={to}
      aria-current={location.path === to ? "page" : undefined}
      onClick={(e) => {
        e.preventDefault();
        go(to);
      }}
    >
      {label}
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
          <nav aria-label="Main">
            {link("/", "Inbox")}
            {link("/categories", "Categories")}
            {link("/digest", "Digest")}
            {link("/sources", "Sources")}
          </nav>
        </header>
        <div className="side-slot" ref={setSlot} />
      </div>
      <div className="topbar">
        <DigestStatus go={go} />
        <RunButton />
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
