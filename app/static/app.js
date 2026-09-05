const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

let state = null;
let view = "command";

const TITLES = {
  command: ["Command", "Agents promote, sell, and run the full pipeline. You only get pinged when it is on fire."],
  pipeline: ["Pipeline", "Discover → attract → capture → qualify → pitch → close → verify → deliver → retain."],
  social: ["Social", "Kai writes and queues Instagram, TikTok, Facebook, X, LinkedIn, WhatsApp, and Google posts."],
  sales: ["Sales", "Cass qualifies, pitches, and closes. Delivery never starts until you verify payment."],
  delivery: ["Delivery", "Zero-trust gate. Pono will not ship until Xavier marks the money complete."],
  pings: ["Pings", "This is the only inbox that should interrupt you. HIGH and CRITICAL only."],
  agents: ["Agents", "Five workers stay silent. Watch is the only one allowed to ping the operator."],
};

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function money(n) {
  return `$${Number(n || 0).toLocaleString()}`;
}

function ago(iso) {
  if (!iso) return "";
  const t = iso.replace("T", " ").slice(11, 19);
  return t;
}

function render() {
  if (!state) return;
  const [title, lede] = TITLES[view];
  $("#view-title").textContent = title;
  $("#view-lede").textContent = lede;
  $("#autopilot").checked = state.autopilot;
  const pings = state.open_pings || [];
  const badge = $("#ping-badge");
  badge.textContent = pings.length;
  badge.dataset.count = String(pings.length);

  const banner = $("#ping-banner");
  if (pings.length) {
    banner.classList.remove("hidden");
    banner.textContent = `XAVIER — ${pings.length} HIGH/CRITICAL ping${pings.length > 1 ? "s" : ""}. Everyone else is handled.`;
  } else {
    banner.classList.add("hidden");
  }

  const k = state.kpis;
  $("#kpis").innerHTML = [
    ["Leads", k.leads, ""],
    ["Hot", k.hot, "lava"],
    ["Queued posts", k.posts_queued, "reef"],
    ["Published", k.posts_published, ""],
    ["Pending $", money(k.revenue_pending), "gold"],
    ["Cleared $", money(k.revenue_complete), "reef"],
    ["Open pings", k.open_pings, "lava"],
    ["Deliveries", k.deliveries_running, ""],
  ]
    .map(
      ([label, value, cls]) =>
        `<div class="kpi"><div class="label">${label}</div><div class="value ${cls}">${value}</div></div>`
    )
    .join("");

  $("#event-feed").innerHTML = state.events
    .slice(0, 18)
    .map(
      (e) => `<li>
        <div class="when">${ago(e.created_at)}<div class="who">${e.agent}</div></div>
        <div>${e.summary}${e.ping ? " · <strong>PING</strong>" : ""}</div>
      </li>`
    )
    .join("");

  $("#offers").innerHTML = state.offers
    .map(
      (o) => `<div class="offer">
        <div class="name">${o.name} <span class="price">${money(o.price)}</span></div>
        <div class="pitch">${o.pitch}</div>
      </div>`
    )
    .join("");

  $("#kanban").innerHTML = state.pipeline
    .map((col) => {
      const cards = col.leads
        .map(
          (l) => `<div class="chip">
            <div><strong>${l.business}</strong></div>
            <div class="score ${l.score}">${l.score} · ${l.island} · ${l.channel}</div>
            <div>${l.need}</div>
          </div>`
        )
        .join("");
      return `<div class="col"><h3>${col.label} · ${col.count}</h3>${cards || '<div class="empty">Quiet</div>'}</div>`;
    })
    .join("");

  const platforms = ["instagram", "tiktok", "facebook", "x", "linkedin", "whatsapp", "google_business"];
  const platSel = $("#social-platform");
  const skuSel = $("#social-sku");
  if (!platSel.options.length) {
    platforms.forEach((p) => platSel.insertAdjacentHTML("beforeend", `<option value="${p}">${p}</option>`));
    state.offers.forEach((o) => skuSel.insertAdjacentHTML("beforeend", `<option value="${o.sku}">${o.name}</option>`));
  }
  $("#posts").innerHTML = state.posts
    .map(
      (p) => `<article class="post">
        <div class="meta">${p.platform} · ${p.sku} · <span class="status">${p.status}</span></div>
        <div class="hook">${p.hook}</div>
        <pre>${p.caption}</pre>
        <div class="hint">${p.cta}</div>
        ${p.status !== "published" ? `<button class="btn tiny" data-publish="${p.id}">Publish now</button>` : ""}
      </article>`
    )
    .join("");

  const msgsByLead = {};
  for (const m of state.messages) {
    (msgsByLead[m.lead_id] ||= []).push(m);
  }
  $("#sales-list").innerHTML = state.leads
    .map((l) => {
      const thread = (msgsByLead[l.id] || [])
        .slice(-4)
        .map((m) => `<div class="bubble ${m.role}">${m.body.replace(/</g, "&lt;")}</div>`)
        .join("");
      return `<div class="thread">
        <h3>${l.business} <span class="score ${l.score}">${l.score}</span></h3>
        <div class="hint">${l.name} · ${l.island} · ${l.stage}</div>
        ${thread}
        <form class="reply-row" data-reply="${l.id}">
          <input name="message" placeholder="They replied…" />
          <button class="btn tiny" type="submit">Send</button>
        </form>
      </div>`;
    })
    .join("");

  $("#payments").innerHTML =
    state.payments
      .map((p) => {
        const lead = state.leads.find((l) => l.id === p.lead_id);
        return `<div class="pay">
          <strong>${lead ? lead.business : p.lead_id}</strong>
          <div>${money(p.amount)} · ${p.sku} · ${p.status}</div>
          ${
            p.status !== "complete"
              ? `<button class="btn tiny" data-verify="${p.id}">I verified the money</button>`
              : `<div class="status">verified by ${p.verified_by}</div>`
          }
        </div>`;
      })
      .join("") || `<div class="empty">No payments yet.</div>`;

  $("#deliveries").innerHTML =
    state.deliveries
      .map(
        (d) => `<div class="del"><strong>${d.status}</strong><div>${d.summary}</div></div>`
      )
      .join("") || `<div class="empty">Nothing in delivery. Zero-trust is holding.</div>`;

  $("#pings").innerHTML =
    (state.escalations || [])
      .map(
        (e) => `<div class="esc ${e.level}">
          <div class="score ${e.level === "critical" ? "hot" : "warm"}">${e.level.toUpperCase()} · ${e.trigger}</div>
          <h3>${e.title}</h3>
          <p>${e.detail}</p>
          <div class="hint">${e.status} · ping=${e.ping ? "YES" : "no"}</div>
          ${e.status === "open" ? `<button class="btn tiny ghost" data-ack="${e.id}">Acknowledge</button>` : ""}
        </div>`
      )
      .join("") || `<div class="empty">No pings. Factory is handling it.</div>`;

  $("#agents").innerHTML = state.agents
    .map(
      (a) => `<div class="agent">
        <div class="id">${a.id}</div>
        <div>${a.role}</div>
        <div class="${a.can_ping ? "can-ping" : "silent"}">${a.can_ping ? "Can ping Xavier" : "Silent worker"}</div>
      </div>`
    )
    .join("");
}

async function refresh() {
  state = await api("/api/state");
  render();
}

$$("#nav button").forEach((btn) => {
  btn.addEventListener("click", () => {
    view = btn.dataset.view;
    $$("#nav button").forEach((b) => b.classList.toggle("active", b === btn));
    $$(".panel").forEach((p) => p.classList.toggle("active", p.dataset.panel === view));
    render();
  });
});

$("#btn-tick").addEventListener("click", async () => {
  await api("/api/tick", { method: "POST" });
  await refresh();
});

$("#autopilot").addEventListener("change", async (e) => {
  await api("/api/autopilot", { method: "POST", body: { on: e.target.checked } });
});

$("#social-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  await api("/api/social/generate", {
    method: "POST",
    body: {
      platform: $("#social-platform").value,
      sku: $("#social-sku").value,
    },
  });
  await refresh();
});

$("#lead-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  await api("/api/leads", {
    method: "POST",
    body: Object.fromEntries(fd.entries()),
  });
  e.target.reset();
  await refresh();
});

document.body.addEventListener("submit", async (e) => {
  const form = e.target.closest("[data-reply]");
  if (!form) return;
  e.preventDefault();
  const message = form.message.value.trim();
  if (!message) return;
  await api(`/api/leads/${form.dataset.reply}/reply`, { method: "POST", body: { message } });
  await refresh();
});

document.body.addEventListener("click", async (e) => {
  const pub = e.target.closest("[data-publish]");
  if (pub) {
    await api(`/api/social/${pub.dataset.publish}/publish`, { method: "POST" });
    await refresh();
  }
  const ver = e.target.closest("[data-verify]");
  if (ver) {
    await api(`/api/payments/${ver.dataset.verify}/verify`, { method: "POST", body: {} });
    await refresh();
  }
  const ack = e.target.closest("[data-ack]");
  if (ack) {
    await api(`/api/escalations/${ack.dataset.ack}/ack`, { method: "POST" });
    await refresh();
  }
});

async function loop() {
  try {
    if ($("#autopilot").checked) {
      await api("/api/tick", { method: "POST" });
    }
    await refresh();
  } catch (err) {
    console.warn(err);
  }
}

refresh();
setInterval(loop, 9000);
