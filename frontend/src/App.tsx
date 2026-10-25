import { CategoriesView } from "./components/CategoriesView";
import { Inbox } from "./components/Inbox";
import { RunButton } from "./components/RunButton";
import { SourcesView } from "./components/SourcesView";
import { useLocation } from "./router";

export function App() {
  const { location, go } = useLocation();
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
    <>
      <header>
        <h1>Lookout</h1>
        <nav aria-label="Main">
          {link("/", "Inbox")}
          {link("/categories", "Categories")}
          {link("/sources", "Sources")}
        </nav>
        <RunButton />
      </header>
      <main>
        {location.path === "/sources" ? (
          <SourcesView />
        ) : location.path === "/categories" ? (
          <CategoriesView />
        ) : (
          <Inbox
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
    </>
  );
}
