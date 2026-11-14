"use strict";

const fs = require("fs");
const vm = require("vm");
const assert = require("assert");
const root = require("path").resolve(__dirname, "..");
const dataContext = { window: {}, globalThis: {} };
vm.runInNewContext(fs.readFileSync(`${root}/assets/data.js`, "utf8"), dataContext);
const data = dataContext.window.NFL_LAB;
const appSource = fs.readFileSync(`${root}/assets/app.js`, "utf8");
const expected = {
  home: "NFL Decision Lab",
  "executive-summary": "Executive summary",
  strategies: "Strategy lab",
  validation: "Validation gates",
  lineups: "Injuries &amp; lineups",
  correlations: "Correlation lab",
  leaderboard: "Leaderboard",
  questions: "Open questions",
  suggestions: "Suggestions",
  flagged: "Flagged for review",
  sources: "Source register"
};
const approvedHosts = [
  "www.nfl.com", "nfl.com", "static.www.nfl.com", "operations.nfl.com",
  "www.itl.nist.gov", "scikit-learn.org"
];
const rowPattern = new RegExp('<tr data-search-row="[^"]*">[\\s\\S]*?</tr>', "g");

for (const [view, heading] of Object.entries(expected)) {
  const app = { innerHTML: "" };
  const document = {
    body: { dataset: { view } },
    title: "",
    getElementById(id) { return id === "app" ? app : null; },
    querySelectorAll() { return []; }
  };
  const localStorage = {
    getItem() { return "{}"; },
    setItem() {},
    removeItem() {}
  };
  const window = { NFL_LAB: data, location: { pathname: view === "home" ? "/X3/" : `/X3/pages/${view}.html` } };
  vm.runInNewContext(appSource, { window, document, localStorage, Math, String, Array, Object, JSON });
  assert(app.innerHTML.includes(heading), `${view} did not render the expected heading`);
  assert(!app.innerHTML.includes("undefined"), `${view} contains an undefined value`);

  if (view !== "home") {
    assert(app.innerHTML.includes("Official source(s)"), `${view} did not render the source column`);
    assert(app.innerHTML.includes("noopener noreferrer"), `${view} contains no safe external source link`);
  }

  const bodyRows = Array.from(app.innerHTML.matchAll(rowPattern), (match) => match[0]);
  for (const row of bodyRows) {
    assert(row.includes('class="source-cell"') && row.includes('class="source-link"'), `${view} has a table row without a source link`);
    const hrefs = Array.from(row.matchAll(/href="([^"]+)"/g), (match) => match[1]).filter((href) => href.startsWith("https://"));
    assert(hrefs.length > 0, `${view} has a table row with no external source URL`);
    for (const href of hrefs) {
      assert(approvedHosts.includes(new URL(href).hostname), `${view} contains a non-official table source: ${href}`);
    }
  }
}

console.log(`Render smoke test passed: ${Object.keys(expected).length} page views rendered; every data row has an approved official/technical source link.`);
