"use strict";

global.window = {};
require("../assets/data.js");
const data = global.window.NFL_LAB;
const approvedHosts = new Set([
  "www.nfl.com",
  "nfl.com",
  "static.www.nfl.com",
  "operations.nfl.com",
  "www.itl.nist.gov",
  "itl.nist.gov",
  "scikit-learn.org",
  "www.scikit-learn.org"
]);
const errors = [];

if (!data || !data.sources) errors.push("NFL_LAB source registry is missing");

for (const [id, source] of Object.entries((data && data.sources) || {})) {
  let parsed;
  try {
    parsed = new URL(source.url);
  } catch (_) {
    errors.push(`source ${id} has an invalid URL`);
    continue;
  }
  if (parsed.protocol !== "https:") errors.push(`source ${id} is not HTTPS`);
  if (!approvedHosts.has(parsed.hostname)) errors.push(`source ${id} is not on the approved official/technical host list: ${parsed.hostname}`);
  if (!source.label || !source.title || !source.publisher || !source.use || !source.reviewed) {
    errors.push(`source ${id} is missing register metadata`);
  }
}

const rowCollections = [
  "strategies", "correlations", "lineupFields", "validationGates",
  "leaderboardCategories", "questions", "suggestions", "flagged"
];
let totalRows = 0;
for (const collectionName of rowCollections) {
  const rows = (data && data[collectionName]) || [];
  if (!rows.length) errors.push(`${collectionName} has no entries`);
  for (const row of rows) {
    totalRows += 1;
    if (!Array.isArray(row.sources) || row.sources.length === 0) {
      errors.push(`${collectionName} row ${row.id || row.gate || row.category || row.field || row.title || row.question || row.issue || "(unknown)"} has no source link`);
      continue;
    }
    for (const sourceId of row.sources) {
      if (!data.sources[sourceId]) errors.push(`${collectionName} row references unknown source ${sourceId}`);
    }
  }
}

for (const row of (data && data.correlations) || []) {
  if (row.estimate !== "") errors.push(`correlation ${row.id} must remain blank until verified`);
  if (!String(row.status).toLowerCase().includes("unverified")) errors.push(`correlation ${row.id} is not visibly flagged unverified`);
}

if (errors.length) {
  console.error("Data/source audit FAILED:");
  for (const error of errors) console.error(` - ${error}`);
  process.exit(1);
}

console.log(`Data/source audit passed: ${Object.keys(data.sources).length} registered sources; ${totalRows} research rows all have valid source IDs; correlation estimates remain blank.`);
