import { defineConfig } from "vitepress";

// The guide lives under /guide/ of the project site (GitHub Pages); the site's landing page is at the root.
export default defineConfig({
  title: "Lookout",
  description: "A self-hosted watch tower for the feeds, releases and advisories that matter to your work.",
  base: "/lookout/guide/",
  cleanUrls: true,
  lastUpdated: false,
  head: [
    [
      "link",
      {
        rel: "icon",
        href: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect x='6' y='6' width='20' height='20' rx='2' fill='%23a63a32' transform='rotate(-5 16 16)'/%3E%3C/svg%3E",
      },
    ],
  ],
  themeConfig: {
    nav: [
      { text: "Guide", link: "/getting-started" },
      { text: "Reference", link: "/reference/commands" },
      { text: "Website", link: "https://bhoudebert.github.io/lookout/", target: "_self" },
      { text: "GitHub", link: "https://github.com/bhoudebert/lookout" },
    ],
    sidebar: [
      {
        text: "Start",
        items: [
          { text: "Getting started", link: "/getting-started" },
          { text: "How Lookout thinks", link: "/concepts" },
        ],
      },
      {
        text: "Use it",
        items: [
          { text: "The dashboard", link: "/dashboard" },
          { text: "How priority is decided", link: "/priorities" },
          { text: "How it learns your taste", link: "/personalization" },
          { text: "Digests of many items", link: "/digest" },
          { text: "Sources", link: "/sources" },
          { text: "Keeping the inbox small", link: "/inbox-size" },
        ],
      },
      {
        text: "Run it",
        items: [
          { text: "Configuration", link: "/configuration" },
          { text: "Running and scheduling", link: "/running" },
          { text: "Local models and memory", link: "/local-models" },
          { text: "Self-hosting", link: "/self-hosting" },
          { text: "Troubleshooting", link: "/troubleshooting" },
        ],
      },
      {
        text: "Reference",
        items: [
          { text: "Commands", link: "/reference/commands" },
          { text: "HTTP API", link: "/reference/api" },
        ],
      },
    ],
    socialLinks: [{ icon: "github", link: "https://github.com/bhoudebert/lookout" }],
    search: { provider: "local" },
    editLink: { pattern: "https://github.com/bhoudebert/lookout/edit/main/docs/guide/:path" },
    footer: { message: "MIT licence", copyright: "Lookout" },
  },
});
