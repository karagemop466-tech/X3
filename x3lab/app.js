/* Shared rendering helpers. Every table row must end with a Source cell:
   either a link to a verified source or an UNVERIFIED badge. verify_data.py
   enforces the same rule on the JSON side. */
const PAGES = [
  ["index.html", "Dashboard"],
  ["executive-summary.html", "Executive Summary"],
  ["requirements.html", "Requirements"],
  ["lines.html", "Originated Lines"],
  ["injuries.html", "Injuries"],
  ["depth.html", "Depth & Deficiencies"],
  ["strategies.html", "Strategies & Signals"],
  ["leaderboard.html", "Leaderboard & Gates"],
  ["questions.html", "Questions & Gaps"],
  ["suggestions.html", "Suggestions"],
  ["results.html", "Results & Standings"],
  ["flagged.html", "Flagged for Review"],
  ["sources.html", "Sources"]
];

function renderNav(active) {
  const nav = document.createElement('nav');
  nav.className = 'site';
  for (const [href, label] of PAGES) {
    const a = document.createElement('a');
    a.href = href;
    a.textContent = label;
    if (href === active) a.className = 'active';
    nav.appendChild(a);
  }
  document.body.prepend(nav);
}

async function loadJSON(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error('Failed to load ' + path);
  return res.json();
}

function esc(s) {
  return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function sourceCell(url, label) {
  if (!url) return '<span class="badge unverified">UNVERIFIED</span>';
  return `<a class="src" href="${esc(url)}" target="_blank" rel="noopener">${esc(label || 'source')}</a>`;
}

function statusBadge(s) {
  const cls = { 'Out': 'out', 'Doubtful': 'doubtful', 'Questionable': 'questionable', 'Injured Reserve': 'ir' }[s] || 'status';
  return `<span class="badge ${cls}">${esc(s)}</span>`;
}

/* columns: [{key, label, fmt?}] ; rows: objects; every row must set row.source
   (a URL) or row.unverified = true */
function renderTable(elId, columns, rows, opts = {}) {
  const el = document.getElementById(elId);
  if (!el) return;
  const cols = columns.concat([{ key: '_src', label: 'Source' }]);
  let html = '<table><thead><tr>' + cols.map(c => `<th>${esc(c.label)}</th>`).join('') + '</tr></thead><tbody>';
  for (const row of rows) {
    html += '<tr>' + cols.map(c => {
      if (c.key === '_src') {
        return '<td>' + sourceCell(row.source, row.source_label) + '</td>';
      }
      const v = c.fmt ? c.fmt(row[c.key], row) : esc(row[c.key]);
      return `<td>${v ?? ''}</td>`;
    }).join('') + '</tr>';
  }
  html += '</tbody></table>';
  el.innerHTML = html;
  if (opts.countId) {
    const c = document.getElementById(opts.countId);
    if (c) c.textContent = rows.length;
  }
}

function record(w, l, t) {
  return t ? `${w}-${l}-${t}` : `${w}-${l}`;
}
