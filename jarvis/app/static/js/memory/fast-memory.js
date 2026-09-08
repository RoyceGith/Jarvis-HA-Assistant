(() => {
  const root = document.getElementById("fast-memory-list");
  const form = document.getElementById("fast-memory-form");
  if (!root || !form) return;
  const $ = id => document.getElementById(id);
  const t = value => window.ZbranoI18n?.t(value) || value;
  const esc = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"})[char]);
  let memories = [];

  const knowledgeCenter = document.createElement("section");
  knowledgeCenter.className = "fast-memory-center";
  knowledgeCenter.setAttribute("aria-labelledby", "knowledge-memory-heading");
  knowledgeCenter.innerHTML = `<div class="fast-memory-heading"><div><h3 id="knowledge-memory-heading">KNOWLEDGE MEMORY</h3><p>Built into ZBRANO. Organize durable notes in spaces that fit your life.</p></div><button id="knowledge-memory-refresh" type="button">Refresh</button></div><div id="knowledge-memory-status" class="fast-memory-status" role="status">Loading local spaces&hellip;</div><form id="knowledge-space-form" class="fast-memory-form"><input id="knowledge-space-name" required maxlength="100" placeholder="Space name, e.g. Home, Work or Recipes"><input id="knowledge-space-purpose" maxlength="1000" placeholder="What should ZBRANO keep here?"><select id="knowledge-space-template" aria-label="Starter layout"><option value="blank">Blank</option><option value="home">Home</option><option value="work">Work</option><option value="project">Project</option><option value="study">Study</option><option value="recipes">Recipes</option><option value="custom">Custom</option></select><div class="settings-actions"><button type="submit">Create space</button><span id="knowledge-space-form-status"></span></div></form><div id="knowledge-space-list" class="fast-memory-list"></div><p class="setting-note">Ask ZBRANO to add, find, or update notes in any space. Permanent writes still require your approval.</p>`;
  root.closest(".fast-memory-center")?.before(knowledgeCenter);

  async function api(path, options={}) {
    const response = await fetch(path, {cache:"no-store", ...options});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    return data;
  }

  async function loadKnowledgeSpaces() {
    const data = await api("api/knowledge-memory/spaces");
    const list = $("knowledge-space-list");
    const spaces = data.spaces || [];
    $("knowledge-memory-status").textContent = `${spaces.length} ${t(spaces.length === 1 ? "local space" : "local spaces")} · ${t("no server, domain, or MCP setup required")}`;
    list.replaceChildren();
    if (!spaces.length) {
      list.innerHTML = '<div class="calendar-empty">No spaces yet. Create only the categories that are useful to you.</div>';
      return;
    }
    for (const space of spaces) {
      const card = document.createElement("article");
      card.className = "fast-memory-item";
      const title = document.createElement("div");
      title.className = "fast-memory-item-title";
      title.textContent = space.name;
      const detail = document.createElement("div");
      detail.className = "fast-memory-value";
      detail.textContent = space.purpose || `${space.template || "custom"} space`;
      card.append(title, detail);
      list.appendChild(card);
    }
  }

  $("knowledge-space-form").addEventListener("submit", async event => {
    event.preventDefault();
    const status = $("knowledge-space-form-status");
    status.textContent = "Creating…";
    try {
      await api("api/knowledge-memory/spaces", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({name:$("knowledge-space-name").value.trim(), purpose:$("knowledge-space-purpose").value.trim(), template:$("knowledge-space-template").value})});
      event.currentTarget.reset();
      status.textContent = "Space created";
      await loadKnowledgeSpaces();
    } catch (error) { status.textContent = `Create failed: ${error.message || error}`; }
  });
  $("knowledge-memory-refresh").addEventListener("click", () => loadKnowledgeSpaces().catch(error => { $("knowledge-memory-status").textContent = error.message || error; }));

  function clearForm() {
    form.reset();
    $("fast-memory-id").value = "";
    $("fast-memory-edit-kind").value = "fact";
    $("fast-memory-importance").value = "3";
    $("fast-memory-form-status").textContent = "";
  }

  function render(data) {
    memories = data.memories || [];
    const status = data.status || {};
    const groups = Object.entries(status.by_kind || {}).map(([kind,count]) => `${kind.replaceAll("_"," ")}: ${count}`).join(" · ");
    const runtime = status.runtime || {};
    const process = runtime.running ? " · organizing the latest conversation…" : runtime.last_error ? ` · last organizer error: ${runtime.last_error}` : "";
    $("fast-memory-status").textContent = `${status.total || 0} organized memories · ${status.pinned || 0} pinned${groups ? ` · ${groups}` : ""}${process}`;
    root.replaceChildren();
    if (!memories.length) { root.innerHTML = '<div class="calendar-empty">No matching Fast Memory. Important details will appear here after conversations.</div>'; return; }
    for (const item of memories) {
      const node = document.createElement("article");
      node.className = "fast-memory-item";
      const date = new Date(Number(item.updated_at || 0) * 1000).toLocaleString(window.ZbranoI18n?.locale || undefined);
      node.innerHTML = `<div class="fast-memory-item-head"><div class="fast-memory-item-title"><span class="fast-memory-badge">${esc(item.kind.replaceAll("_"," "))}</span>${esc(item.subject)} · ${esc(item.key)}</div><span>${item.pinned ? "📌" : ""}</span></div><div class="fast-memory-value">${esc(item.summary || item.value)}</div><div class="fast-memory-meta"><span>importance ${esc(item.importance)}</span><span>confidence ${Math.round(Number(item.confidence || 0)*100)}%</span><span>revision ${esc(item.revision)}</span><span>${esc(date)}</span></div><div class="fast-memory-actions"><button type="button" data-memory-edit="${esc(item.id)}">Edit</button><button type="button" data-memory-pin="${esc(item.id)}">${item.pinned ? "Unpin" : "Pin"}</button><button type="button" data-memory-delete="${esc(item.id)}">Delete</button></div>`;
      root.appendChild(node);
    }
  }

  async function load() {
    const query = $("fast-memory-search").value.trim();
    const kind = $("fast-memory-kind").value;
    const data = await api(`api/fast-memory?query=${encodeURIComponent(query)}&kind=${encodeURIComponent(kind)}&limit=100`);
    render(data);
  }

  function edit(item) {
    $("fast-memory-id").value = item.id;
    $("fast-memory-edit-kind").value = item.kind === "session_summary" ? "fact" : item.kind;
    $("fast-memory-subject").value = item.subject;
    $("fast-memory-key").value = item.key;
    $("fast-memory-value").value = item.value;
    $("fast-memory-importance").value = String(item.importance || 3);
    $("fast-memory-pinned").checked = Boolean(item.pinned);
    form.scrollIntoView({behavior:"smooth", block:"center"});
  }

  form.addEventListener("submit", async event => {
    event.preventDefault();
    const id = $("fast-memory-id").value;
    const body = {
      kind: $("fast-memory-edit-kind").value, subject: $("fast-memory-subject").value.trim(),
      key: $("fast-memory-key").value.trim(), value: $("fast-memory-value").value.trim(),
      summary: $("fast-memory-value").value.trim(), keywords: [], importance: Number($("fast-memory-importance").value),
      confidence: 1, pinned: $("fast-memory-pinned").checked, expires_at: 0,
    };
    $("fast-memory-form-status").textContent = "Saving…";
    try {
      await api(id ? `api/fast-memory/${encodeURIComponent(id)}` : "api/fast-memory", {method:id ? "PUT" : "POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
      clearForm(); await load();
    } catch (error) { $("fast-memory-form-status").textContent = `Save failed: ${error.message || error}`; }
  });
  root.addEventListener("click", async event => {
    const editButton = event.target.closest("[data-memory-edit]");
    if (editButton) { const item = memories.find(memory => memory.id === editButton.dataset.memoryEdit); if (item) edit(item); return; }
    const pinButton = event.target.closest("[data-memory-pin]");
    if (pinButton) {
      const item = memories.find(memory => memory.id === pinButton.dataset.memoryPin); if (!item) return;
      await api(`api/fast-memory/${encodeURIComponent(item.id)}`, {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({...item, pinned:!item.pinned})}); await load(); return;
    }
    const deleteButton = event.target.closest("[data-memory-delete]");
    if (deleteButton && confirm("Delete this Fast Memory?")) { await api(`api/fast-memory/${encodeURIComponent(deleteButton.dataset.memoryDelete)}`, {method:"DELETE"}); await load(); }
  });
  $("fast-memory-refresh").addEventListener("click", () => load().catch(error => { $("fast-memory-status").textContent = error.message || error; }));
  $("fast-memory-search").addEventListener("input", () => { clearTimeout(window.zbranoFastMemorySearchTimer); window.zbranoFastMemorySearchTimer = setTimeout(() => load().catch(()=>{}), 250); });
  $("fast-memory-kind").addEventListener("change", () => load().catch(()=>{}));
  $("fast-memory-form-clear").addEventListener("click", clearForm);
  document.querySelector('[data-settings-target="memory"]')?.addEventListener("click", () => {
    loadKnowledgeSpaces().catch(error => { $("knowledge-memory-status").textContent = `Knowledge Memory unavailable: ${error.message || error}`; });
    load().catch(error => { $("fast-memory-status").textContent = `Fast Memory unavailable: ${error.message || error}`; });
  });
  window.zbranoFastMemory = {refresh:load};
})();
