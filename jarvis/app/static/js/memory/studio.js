(function () {
  const panel = document.getElementById("memory-panel");
  if (!panel) return;

  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
  const api = async (path, options = {}) => {
    const response = await fetch(path, options);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || payload.error || `Request failed (${response.status})`);
    return payload;
  };
  const icons = {home:"🏠", work:"💼", study:"📚", project:"🧩", recipes:"🍲", personal:"★", person:"★", template:"▦", blank:"＋", learning:"🎓", health:"♥", travel:"✈"};
  Object.assign(icons, {people:"P", hobbies:"H"});
  const icon = (name) => icons[String(name || "").toLowerCase()] || String(name || "◆").slice(0, 2).toUpperCase();
  const state = {loaded:false, spaces:[], categories:[], templates:[], category:"All", selectedSpace:"", selectedNote:"", createCategory:"", createTemplate:"blank", editingTemplate:"", editingCategory:""};
  const displayNote = (name) => String(name || "").replace(/\.md$/i, "");
  const displayMemoryPath = (path) => String(path || "").replace(/^Spaces\//, "").replace(/\.md$/i, "");
  const formatNoteDate = (timestamp) => timestamp ? new Intl.DateTimeFormat(document.documentElement.lang || undefined, {dateStyle:"medium", timeStyle:"short"}).format(new Date(Number(timestamp) * 1000)) : "";
  const renderMemoryMarkdown = (content) => typeof renderMarkdownText === "function" ? renderMarkdownText(content) : `<p>${esc(content).replace(/\n/g, "<br>")}</p>`;

  panel.innerHTML = `
    <div class="memory-studio">
      <aside class="memory-studio-nav">
        <div class="memory-studio-brand"><span class="memory-studio-brand-icon">M</span><div><h2>My Memory</h2><p>ZBRANO organizes it for you</p></div></div>
        <button type="button" class="active" data-memory-view="database"><span class="memory-studio-nav-symbol">M</span><span><strong>My memory</strong><small>Remember, find, and review</small></span></button>
        <button type="button" data-memory-view="templates"><span class="memory-studio-nav-symbol">&#9881;</span><span><strong>Customize</strong><small>Optional organization tools</small></span></button>
        <div class="memory-local-note">Everything here stays on this ZBRANO installation and is included in your backups.</div>
      </aside>
      <div class="memory-studio-main">
        <section id="memory-database-view" class="memory-view">
          <section class="memory-capture">
            <span class="memory-capture-icon" aria-hidden="true">&#10022;</span>
            <div class="memory-capture-copy"><span class="memory-eyebrow">QUICK MEMORY</span><h2>What should ZBRANO remember?</h2><p>Write it naturally. ZBRANO will choose where it belongs and organize it for you.</p></div>
            <form id="memory-quick-form" class="memory-quick-form">
              <label class="memory-quick-input"><span class="sr-only">What should ZBRANO remember?</span><textarea id="memory-quick-content" required maxlength="50000" placeholder="For example: The living-room air conditioner filter is 40 x 60 cm."></textarea></label>
              <div class="memory-quick-actions"><button type="submit" id="memory-quick-save" class="memory-primary">Remember this</button><details class="memory-destination-choice"><summary>Choose an area instead</summary><select id="memory-quick-area" aria-label="Memory area"><option value="auto">Let ZBRANO choose</option><option value="home">Home</option><option value="people">People</option><option value="health">Health</option><option value="work">Work &amp; projects</option><option value="travel">Travel</option><option value="learning">Learning</option><option value="food">Food &amp; recipes</option><option value="hobbies">Hobbies</option><option value="general">General</option></select></details><span id="memory-quick-status" class="memory-status" role="status"></span></div>
            </form>
            <div id="memory-quick-result" class="memory-quick-result" hidden></div>
          </section>
          <header class="memory-heading"><div><h2>Your organized memory</h2><p>Browse what ZBRANO has filed, or search across everything.</p></div><div class="memory-heading-actions"><button type="button" id="memory-refresh">Refresh</button><button type="button" id="memory-new-space">Organize manually</button></div></header>
          <div class="memory-dashboard"><div class="memory-stat"><strong id="memory-space-count">0</strong><span>Memory areas</span></div><div class="memory-stat"><strong id="memory-note-count">0</strong><span>Organized notes</span></div><div class="memory-stat"><strong id="memory-template-count">Ready</strong><span>Automatic organization</span></div></div>
          <section id="memory-space-composer" class="memory-composer" hidden>
            <div class="memory-heading"><div><span class="memory-eyebrow">OPTIONAL</span><h2>Organize a space manually</h2><p>Use this only when you want to control the structure yourself.</p></div><button type="button" data-memory-cancel="space">Cancel</button></div>
            <div class="memory-step"><strong>1 · WHAT IS IT FOR?</strong><div id="memory-create-categories" class="memory-choice-grid"></div></div>
            <div class="memory-step"><strong>2 · HOW SHOULD IT BE ORGANIZED?</strong><div id="memory-create-templates" class="memory-choice-grid"></div></div>
            <form id="memory-space-form" class="memory-form-grid">
              <label>Name<input id="memory-space-name" required maxlength="80" placeholder="For example, Garden plans"></label>
              <label>What will you keep here?<input id="memory-space-purpose" maxlength="500" placeholder="A short description helps ZBRANO use it well"></label>
              <div class="wide memory-actions"><button type="submit" class="memory-primary">Create space</button><span id="memory-space-form-status" class="memory-status"></span></div>
            </form>
          </section>
          <section id="memory-category-composer" class="memory-composer" hidden>
            <div class="memory-heading"><div><h2 id="memory-category-title">Add your own category</h2><p>Categories are simple labels for grouping related memory spaces.</p></div><button type="button" data-memory-cancel="category">Cancel</button></div>
            <form id="memory-category-form" class="memory-form-grid">
              <label>Category name<input id="memory-category-name" required maxlength="60" placeholder="For example, Health"></label>
              <label>Symbol<select id="memory-category-icon"><option value="personal">★ Personal</option><option value="home">🏠 Home</option><option value="people">P People</option><option value="work">💼 Work</option><option value="study">📚 Learning</option><option value="health">♥ Health</option><option value="travel">✈ Travel</option><option value="recipes">🍲 Recipes</option><option value="hobbies">H Hobbies</option></select></label>
              <label class="wide">What belongs here?<input id="memory-category-description" maxlength="240" placeholder="A friendly description"></label>
              <div class="wide memory-actions"><button type="submit" id="memory-category-save" class="memory-primary">Add category</button><span id="memory-category-status" class="memory-status"></span></div>
            </form>
          </section>
          <div class="memory-filter-row"><input id="memory-search" type="search" placeholder="Search everything ZBRANO remembers"><button type="button" id="memory-add-category">+ Custom area</button></div>
          <div class="memory-section-label">BROWSE BY AREA</div>
          <div id="memory-category-chips" class="memory-category-chips"></div>
          <div id="memory-search-results"></div>
          <div id="memory-space-grid" class="memory-card-grid"></div>
          <section id="memory-space-details" hidden></section>
        </section>
        <section id="memory-templates-view" class="memory-view" hidden>
          <header class="memory-heading"><div><h2>Customize organization</h2><p>Optional tools for people who want to design their own reusable layouts.</p></div><button type="button" id="memory-new-template" class="memory-primary">+ New layout</button></header>
          <div class="memory-advanced-note"><strong>You do not need to set this up.</strong><span>ZBRANO can organize ordinary memories automatically. Create a layout only when you want the same special note structure again and again.</span></div>
          <div id="memory-template-grid" class="memory-template-grid"></div>
          <section id="memory-template-composer" class="memory-composer" hidden>
            <div class="memory-heading"><div><h2 id="memory-template-editor-title">Create a template</h2><p>Each note card becomes a ready-to-use note whenever this template is chosen.</p></div><button type="button" data-memory-cancel="template">Cancel</button></div>
            <form id="memory-template-form" class="memory-template-builder">
              <div class="memory-template-fields">
                <label>Template name<input id="memory-template-name" required maxlength="80" placeholder="For example, Client project"></label>
                <label>Category<select id="memory-template-category"></select></label>
                <label class="wide">What is this template for?<input id="memory-template-description" maxlength="500" placeholder="Explain when someone should choose it"></label>
                <label>Symbol<select id="memory-template-icon"><option value="template">▦ General</option><option value="project">🧩 Project</option><option value="home">🏠 Home</option><option value="work">💼 Work</option><option value="study">📚 Learning</option><option value="recipes">🍲 Recipes</option></select></label>
              </div>
              <div class="memory-heading"><div><h2>Note cards</h2><p>Give every card a clear name and purpose.</p></div><button type="button" id="memory-add-blueprint">+ Add note card</button></div>
              <div id="memory-note-blueprints" class="memory-note-blueprints"></div>
              <div class="memory-actions"><button type="submit" class="memory-primary">Save template</button><button type="button" id="memory-delete-template" class="memory-danger" hidden>Delete template</button><span id="memory-template-status" class="memory-status"></span></div>
            </form>
          </section>
        </section>
      </div>
    </div>`;

  const $ = (id) => document.getElementById(id);
  const setStatus = (id, text) => { const node = $(id); if (node) node.textContent = text || ""; };
  function categoryByName(name) { return state.categories.find((item) => item.name === name) || {name:name || "Personal", icon:"personal", description:""}; }
  function templateById(id) { return state.templates.find((item) => item.id === id || item.name === id); }

  function renderCategories() {
    const usedCategories = new Set(state.spaces.map((item) => item.category));
    const chips = [{name:"All", icon:"template"}, ...state.categories.filter((item) => usedCategories.has(item.name))];
    $("memory-category-chips").innerHTML = chips.map((item) => item.name === "All"
      ? `<button type="button" class="${state.category === item.name ? "active" : ""}" data-memory-category="${esc(item.name)}">${esc(icon(item.icon))} ${esc(item.name)}</button>`
      : `<span class="memory-category-chip"><button type="button" class="${state.category === item.name ? "active" : ""}" data-memory-category="${esc(item.name)}">${esc(icon(item.icon))} ${esc(item.name)}</button><button type="button" class="memory-icon-button" data-edit-category="${esc(item.name)}" title="Edit ${esc(item.name)}" aria-label="Edit ${esc(item.name)}">&#9998;</button></span>`
    ).join("");
    $("memory-create-categories").innerHTML = state.categories.map((item) => `<button type="button" class="memory-choice ${state.createCategory === item.name ? "active" : ""}" data-create-category="${esc(item.name)}"><strong>${esc(icon(item.icon))} ${esc(item.name)}</strong><small>${esc(item.description || "Your own collection")}</small></button>`).join("");
    $("memory-template-category").innerHTML = state.categories.map((item) => `<option value="${esc(item.name)}">${esc(icon(item.icon))} ${esc(item.name)}</option>`).join("");
  }

  function renderSpaces() {
    const query = $("memory-search").value.trim().toLowerCase();
    const visible = state.spaces.filter((space) => (state.category === "All" || space.category === state.category) && (!query || `${space.name} ${space.purpose} ${space.category}`.toLowerCase().includes(query)));
    $("memory-space-count").textContent = state.spaces.length;
    $("memory-note-count").textContent = state.spaces.reduce((sum, item) => sum + Number(item.note_count || 0), 0);
    $("memory-template-count").textContent = "Ready";
    $("memory-space-grid").innerHTML = visible.length ? visible.map((space) => {
      const category = categoryByName(space.category);
      return `<article class="memory-card ${state.selectedSpace === space.name ? "selected" : ""}" data-memory-space="${esc(space.name)}"><span class="memory-icon">${esc(icon(category.icon))}</span><div class="memory-card-body"><h3>${esc(space.name)}</h3><p>${esc(space.purpose || "A flexible place for your knowledge")}</p><div class="memory-card-meta"><span class="memory-pill">${esc(space.category || "Personal")}</span><span>${Number(space.note_count || 0)} notes</span></div></div></article>`;
    }).join("") : `<div class="memory-empty">No spaces match this view. Create one when you are ready.</div>`;
  }

  function renderTemplates() {
    $("memory-template-grid").innerHTML = state.templates.map((item) => `<article class="memory-card" data-memory-template="${esc(item.id)}"><span class="memory-icon">${esc(icon(item.icon))}</span><div class="memory-card-body"><h3>${esc(item.name)}</h3><p>${esc(item.description || "A flexible starting layout")}</p><div class="memory-card-meta"><span class="memory-pill">${esc(item.category || "Personal")}</span><span>${(item.notes || []).length} note cards</span><span>${item.built_in ? "Built in" : "Your template"}</span></div></div></article>`).join("");
    const relevant = state.templates.filter((item) => item.id === "blank" || item.category === "All" || item.category === state.createCategory);
    if (!relevant.some((item) => item.id === state.createTemplate)) state.createTemplate = relevant.find((item) => item.id !== "blank")?.id || "blank";
    $("memory-create-templates").innerHTML = relevant.map((item) => `<button type="button" class="memory-choice ${state.createTemplate === item.id ? "active" : ""}" data-create-template="${esc(item.id)}"><strong>${esc(icon(item.icon))} ${esc(item.name)}</strong><small>${esc(item.description || "Flexible layout")}</small></button>`).join("");
  }

  function renderBlueprint(note = {}) {
    const node = document.createElement("div");
    node.className = "memory-blueprint";
    node.innerHTML = `<input data-template-note-name maxlength="100" required placeholder="Note name, e.g. Decisions" value="${esc(displayNote(note.name))}"><input data-template-note-purpose maxlength="240" placeholder="What belongs in this note?" value="${esc(note.purpose || "")}"><textarea data-template-note-content maxlength="20000" placeholder="Optional starter text">${esc(note.content || "")}</textarea><button type="button" data-remove-blueprint class="memory-danger">Remove</button>`;
    $("memory-note-blueprints").appendChild(node);
  }

  async function loadAll() {
    if (!state.selectedSpace) $("memory-database-view").classList.remove("memory-details-open");
    setStatus("memory-space-form-status", "Loading…");
    const [spaces, categories, templates] = await Promise.all([
      api("api/knowledge-memory/spaces"), api("api/knowledge-memory/categories"), api("api/knowledge-memory/templates")
    ]);
    state.spaces = spaces.spaces || [];
    state.categories = categories.categories || [];
    state.templates = templates.templates || [];
    if (!state.createCategory) state.createCategory = state.categories[0]?.name || "Personal";
    if (!templateById(state.createTemplate)) state.createTemplate = state.templates[0]?.id || "blank";
    renderCategories(); renderTemplates(); renderSpaces(); setStatus("memory-space-form-status", ""); state.loaded = true;
  }

  function showView(name) {
    $("memory-database-view").hidden = name !== "database";
    $("memory-templates-view").hidden = name !== "templates";
    panel.querySelectorAll("[data-memory-view]").forEach((button) => button.classList.toggle("active", button.dataset.memoryView === name));
    panel.scrollTop = 0;
    panel.querySelector(".memory-studio-main").scrollTop = 0;
  }

  function openSpaceComposer(templateId = "") {
    if (templateId) state.createTemplate = templateId;
    const selected = templateById(state.createTemplate);
    if (templateId && selected?.category && selected.category !== "All") state.createCategory = selected.category;
    renderCategories(); renderTemplates();
    $("memory-space-composer").hidden = false; $("memory-category-composer").hidden = true; $("memory-space-details").hidden = true;
    $("memory-space-name").focus();
  }

  function openCategoryEditor(item = null) {
    state.editingCategory = item?.name || "";
    $("memory-category-title").textContent = item ? "Edit category" : "Add your own category";
    $("memory-category-save").textContent = item ? "Save changes" : "Add category";
    $("memory-category-name").value = item?.name || "";
    $("memory-category-icon").value = item?.icon || "personal";
    $("memory-category-description").value = item?.description || "";
    $("memory-category-composer").hidden = false;
    $("memory-space-composer").hidden = true;
    setStatus("memory-category-status", "");
    $("memory-category-name").focus();
  }

  async function openSpace(name) {
    state.selectedSpace = name; state.selectedNote = ""; renderSpaces();
    const space = state.spaces.find((item) => item.name === name);
    const payload = await api(`api/knowledge-memory/spaces/${encodeURIComponent(name)}/notes`);
    const details = $("memory-space-details");
    $("memory-database-view").classList.add("memory-details-open");
    details.hidden = false;
    const categoryNames = [...new Set(state.spaces.map((item) => item.category).filter(Boolean))];
    const categoryTabs = categoryNames.map((categoryName) => {
      const category = categoryByName(categoryName);
      return `<button type="button" class="${space?.category === categoryName ? "active" : ""}" data-open-memory-category="${esc(categoryName)}">${esc(icon(category.icon))} ${esc(categoryName)}</button>`;
    }).join("");
    const noteDates = new Map((payload.note_details || []).map((item) => [item.note, item.updated_at]));
    details.innerHTML = `<nav class="memory-space-category-tabs" aria-label="Memory categories"><button type="button" data-close-space>All memory</button>${categoryTabs}</nav><div class="memory-heading memory-space-heading"><div><h2>${esc(name)}</h2><p>${esc(space?.purpose || "Your organized notes")}</p></div><div class="memory-heading-actions"><button type="button" data-new-note>+ New note</button><button type="button" data-delete-space class="memory-danger">Delete space</button><button type="button" data-close-space>Close</button></div></div><div class="memory-space-layout"><aside class="memory-note-list"><strong>Notes</strong><div id="memory-notes">${(payload.notes || []).map((note) => `<button type="button" data-memory-note="${esc(note)}"><span>${esc(displayNote(note))}</span><small>${esc(formatNoteDate(noteDates.get(note)))}</small></button>`).join("") || `<span class="memory-muted">No notes yet.</span>`}</div></aside><form id="memory-note-form" class="memory-editor"><div class="memory-heading"><div><h2 id="memory-note-heading">Choose a note</h2><p id="memory-note-date">Select a note to read it.</p></div><div class="memory-heading-actions"><button type="button" id="memory-edit-note" hidden>Edit</button><button type="button" id="memory-print-note" class="memory-icon-button" title="Print note" aria-label="Print note" hidden>&#128424;</button></div></div><section id="memory-note-reader" class="memory-note-reader" hidden><div id="memory-note-rendered" class="memory-note-rendered"></div></section><label class="memory-edit-field">Note title<input id="memory-note-name" maxlength="180" placeholder="For example, Important contacts" disabled></label><label class="memory-note-content-label memory-edit-field">Contents<textarea id="memory-note-content" maxlength="1000000" placeholder="Write what should be remembered" disabled></textarea></label><div class="memory-actions memory-edit-field"><button id="memory-save-note" type="submit" class="memory-primary" disabled>Save changes</button><button id="memory-delete-note" type="button" class="memory-danger" hidden>Delete note</button><span id="memory-note-status" class="memory-status"></span></div></form></div>`;
    details.scrollIntoView({behavior:"smooth", block:"start"});
    if (payload.notes?.length) await openNote(payload.notes[0]);
  }

  async function openNote(note) {
    const payload = await api(`api/knowledge-memory/spaces/${encodeURIComponent(state.selectedSpace)}/note?note=${encodeURIComponent(note)}`);
    state.selectedNote = payload.note;
    panel.querySelectorAll("[data-memory-note]").forEach((button) => button.classList.toggle("active", button.dataset.memoryNote === payload.note));
    $("memory-note-heading").textContent = displayNote(payload.note);
    $("memory-note-date").textContent = payload.updated_at ? `Last updated ${formatNoteDate(payload.updated_at)}` : "";
    $("memory-note-name").value = displayNote(payload.note); $("memory-note-name").disabled = false;
    $("memory-note-content").value = payload.content || ""; $("memory-note-content").disabled = false;
    $("memory-note-rendered").innerHTML = renderMemoryMarkdown(payload.content || "");
    $("memory-note-reader").hidden = false; $("memory-note-form").classList.add("is-reading");
    $("memory-edit-note").hidden = false; $("memory-save-note").disabled = false; $("memory-delete-note").hidden = false; $("memory-print-note").hidden = false; setStatus("memory-note-status", "");
  }

  function newNote() {
    state.selectedNote = "";
    panel.querySelectorAll("[data-memory-note]").forEach((button) => button.classList.remove("active"));
    $("memory-note-heading").textContent = "Create a note";
    $("memory-note-date").textContent = "New note";
    $("memory-note-name").value = ""; $("memory-note-name").disabled = false;
    $("memory-note-content").value = ""; $("memory-note-content").disabled = false;
    $("memory-note-reader").hidden = true; $("memory-note-form").classList.remove("is-reading"); $("memory-edit-note").hidden = true;
    $("memory-save-note").disabled = false; $("memory-delete-note").hidden = true; $("memory-print-note").hidden = true; $("memory-note-name").focus();
  }

  function printCurrentNote() {
    if (!state.selectedNote) return;
    const sheet = document.createElement("section");
    sheet.id = "memory-print-sheet";
    const title = document.createElement("h1");
    title.textContent = state.selectedSpace || "My Memory";
    const noteTitle = document.createElement("h2");
    noteTitle.textContent = $("memory-note-name").value.trim() || displayNote(state.selectedNote);
    const date = document.createElement("p");
    date.className = "memory-print-date";
    date.textContent = $("memory-note-date").textContent;
    const content = document.createElement("div");
    content.className = "memory-note-rendered";
    content.innerHTML = renderMemoryMarkdown($("memory-note-content").value);
    sheet.append(title, noteTitle, date, content);
    document.body.appendChild(sheet);
    const cleanup = () => sheet.remove();
    window.addEventListener("afterprint", cleanup, {once:true});
    window.print();
    window.setTimeout(cleanup, 1000);
  }

  function openTemplateEditor(item = null) {
    state.editingTemplate = item && !item.built_in ? item.name : "";
    $("memory-template-editor-title").textContent = state.editingTemplate ? "Edit your template" : "Create a template";
    $("memory-template-name").value = state.editingTemplate ? item.name : "";
    $("memory-template-description").value = state.editingTemplate ? (item.description || "") : "";
    $("memory-template-category").value = state.editingTemplate ? (item.category || state.categories[0]?.name) : (state.categories[0]?.name || "Personal");
    $("memory-template-icon").value = state.editingTemplate ? (item.icon || "template") : "template";
    $("memory-note-blueprints").innerHTML = "";
    const notes = state.editingTemplate ? (item.notes || []) : [{name:"Overview.md", purpose:"A clear summary", content:"# Overview\n"}];
    notes.forEach(renderBlueprint);
    $("memory-delete-template").hidden = !state.editingTemplate;
    $("memory-template-composer").hidden = false; setStatus("memory-template-status", "");
    $("memory-template-composer").scrollIntoView({behavior:"smooth", block:"start"});
  }

  let searchTimer = 0;
  async function runSearch() {
    const query = $("memory-search").value.trim(); renderSpaces();
    const root = $("memory-search-results");
    if (query.length < 2) { root.innerHTML = ""; return; }
    try {
      const payload = await api(`api/knowledge-memory/search?query=${encodeURIComponent(query)}&limit=30`);
      root.innerHTML = payload.results?.length ? `<section class="memory-composer"><strong>Matches inside notes</strong>${payload.results.map((item) => `<button type="button" class="memory-choice" data-search-path="${esc(item.relative_path)}"><strong>${esc(displayMemoryPath(item.relative_path))}</strong><small>${esc(String(item.excerpt || "").replace(/[#*_`]/g, " ").slice(0, 180))}</small></button>`).join("")}</section>` : "";
    } catch (error) { root.innerHTML = `<div class="memory-status">${esc(error.message)}</div>`; }
  }

  panel.addEventListener("click", async (event) => {
    const button = event.target.closest("button, [data-memory-space], [data-memory-template]");
    if (!button) return;
    try {
      if (button.dataset.memoryView) { showView(button.dataset.memoryView); return; }
      if (button.id === "memory-refresh") { await loadAll(); return; }
      if (button.id === "memory-new-space") { openSpaceComposer(); return; }
      if (button.id === "memory-add-category") { openCategoryEditor(); return; }
      if (button.dataset.editCategory) { openCategoryEditor(categoryByName(button.dataset.editCategory)); return; }
      if (button.dataset.memoryCancel === "space") { $("memory-space-composer").hidden = true; return; }
      if (button.dataset.memoryCancel === "category") { $("memory-category-composer").hidden = true; state.editingCategory = ""; return; }
      if (button.dataset.memoryCancel === "template") { $("memory-template-composer").hidden = true; state.editingTemplate = ""; return; }
      if (button.dataset.memoryCategory) { state.category = button.dataset.memoryCategory; renderCategories(); renderSpaces(); return; }
      if (button.dataset.openMemoryCategory) {
        state.category = button.dataset.openMemoryCategory;
        const matches = state.spaces.filter((item) => item.category === state.category);
        if (matches.length === 1) { await openSpace(matches[0].name); return; }
        $("memory-space-details").hidden = true;
        $("memory-database-view").classList.remove("memory-details-open");
        state.selectedSpace = "";
        renderCategories(); renderSpaces();
        return;
      }
      if (button.dataset.createCategory) { state.createCategory = button.dataset.createCategory; renderCategories(); renderTemplates(); return; }
      if (button.dataset.createTemplate) { state.createTemplate = button.dataset.createTemplate; renderTemplates(); return; }
      if (button.dataset.memorySpace) { await openSpace(button.dataset.memorySpace); return; }
      if (button.dataset.memoryNote) { await openNote(button.dataset.memoryNote); return; }
      if (button.hasAttribute("data-new-note")) { newNote(); return; }
      if (button.hasAttribute("data-close-space")) { $("memory-space-details").hidden = true; $("memory-database-view").classList.remove("memory-details-open"); state.selectedSpace = ""; renderSpaces(); return; }
      if (button.hasAttribute("data-delete-space") && confirm(`Delete the memory space “${state.selectedSpace}” and all of its notes?`)) { await api(`api/knowledge-memory/spaces/${encodeURIComponent(state.selectedSpace)}`, {method:"DELETE"}); $("memory-space-details").hidden = true; state.selectedSpace = ""; await loadAll(); return; }
      if (button.id === "memory-new-template") { openTemplateEditor(); return; }
      if (button.dataset.memoryTemplate) { const item = templateById(button.dataset.memoryTemplate); if (item?.built_in) { showView("database"); openSpaceComposer(item.id); } else if (item) openTemplateEditor(item); return; }
      if (button.id === "memory-add-blueprint") { renderBlueprint(); return; }
      if (button.hasAttribute("data-remove-blueprint")) { button.closest(".memory-blueprint")?.remove(); return; }
      if (button.id === "memory-delete-template" && state.editingTemplate && confirm(`Delete the template “${state.editingTemplate}”?`)) { await api(`api/knowledge-memory/templates/${encodeURIComponent(state.editingTemplate)}`, {method:"DELETE"}); $("memory-template-composer").hidden = true; state.editingTemplate = ""; await loadAll(); return; }
      if (button.id === "memory-delete-note" && state.selectedNote && confirm(`Delete “${displayNote(state.selectedNote)}”?`)) { await api(`api/knowledge-memory/spaces/${encodeURIComponent(state.selectedSpace)}/note?note=${encodeURIComponent(state.selectedNote)}`, {method:"DELETE"}); await openSpace(state.selectedSpace); return; }
      if (button.id === "memory-edit-note") { $("memory-note-form").classList.remove("is-reading"); $("memory-note-reader").hidden = true; button.hidden = true; $("memory-note-content").focus(); return; }
      if (button.id === "memory-print-note") { printCurrentNote(); return; }
      if (button.dataset.searchPath) {
        const match = button.dataset.searchPath.match(/^Spaces\/([^/]+)\/(.+)$/);
        if (match) { await openSpace(match[1]); await openNote(match[2]); }
      }
    } catch (error) { setStatus("memory-space-form-status", error.message || String(error)); setStatus("memory-template-status", error.message || String(error)); }
  });

  const saveQuickMemory = async (content, organization = "auto", destinationNote = "") => {
    const button = $("memory-quick-save");
    button.disabled = true;
    setStatus("memory-quick-status", "Organizing…");
    try {
      const payload = await api("api/knowledge-memory/remember", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({content, preferred_area:$("memory-quick-area").value, organization, destination_note:destinationNote}),
      });
      setStatus("memory-quick-status", "");
      const result = $("memory-quick-result");
      if (payload.choice_required) {
        result.innerHTML = `<div><strong>Choose how to organize this memory</strong><small>${esc(payload.question)}</small></div><div class="memory-quick-actions">${(payload.choices || []).map(choice => `<button type="button" class="memory-primary" data-memory-organization="${esc(choice.id)}" data-memory-destination-note="${esc(choice.destination_note)}">${esc(choice.label)}</button>`).join("")}</div>`;
        for (const choice of result.querySelectorAll("[data-memory-organization]")) {
          choice.addEventListener("click", () => saveQuickMemory(content, choice.dataset.memoryOrganization, choice.dataset.memoryDestinationNote));
        }
        result.hidden = false;
        return;
      }
      $("memory-quick-content").value = "";
      await loadAll();
      result.innerHTML = `<span class="memory-quick-result-icon">${esc(icon(payload.icon))}</span><div><strong>${payload.duplicate ? "Already remembered" : "Saved and organized"}</strong><small>${esc(payload.space)} &rarr; ${esc(String(payload.note || "").replace(/\.md$/i, ""))}</small></div><button type="button" data-memory-space="${esc(payload.space)}">Open</button>`;
      result.hidden = false;
    } catch (error) {
      setStatus("memory-quick-status", `Could not save this memory: ${error.message || error}`);
    } finally {
      button.disabled = false;
    }
  };

  $("memory-quick-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const content = $("memory-quick-content").value.trim();
    if (!content) return;
    $("memory-quick-result").hidden = true;
    await saveQuickMemory(content);
  });

  $("memory-space-form").addEventListener("submit", async (event) => {
    event.preventDefault(); setStatus("memory-space-form-status", "Creating…");
    try {
      await api("api/knowledge-memory/spaces", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({name:$("memory-space-name").value.trim(), purpose:$("memory-space-purpose").value.trim(), template:state.createTemplate, category:state.createCategory})});
      const name = $("memory-space-name").value.trim(); event.target.reset(); $("memory-space-composer").hidden = true; await loadAll(); await openSpace(name);
    } catch (error) { setStatus("memory-space-form-status", `Could not create space: ${error.message || error}`); }
  });

  $("memory-category-form").addEventListener("submit", async (event) => {
    if (state.editingCategory) {
      event.preventDefault();
      setStatus("memory-category-status", "Saving...");
      try {
        const originalName = state.editingCategory;
        const name = $("memory-category-name").value.trim();
        await api("api/knowledge-memory/categories", {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({original_name:originalName, name, icon:$("memory-category-icon").value, description:$("memory-category-description").value.trim()})});
        if (state.category === originalName) state.category = name;
        state.createCategory = name;
        state.editingCategory = "";
        event.target.reset();
        $("memory-category-composer").hidden = true;
        await loadAll();
      } catch (error) { setStatus("memory-category-status", `Could not save category: ${error.message || error}`); }
      return;
    }
    event.preventDefault(); setStatus("memory-category-status", "Adding…");
    try {
      const name = $("memory-category-name").value.trim();
      await api("api/knowledge-memory/categories", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({name, icon:$("memory-category-icon").value, description:$("memory-category-description").value.trim()})});
      state.createCategory = name; event.target.reset(); $("memory-category-composer").hidden = true; await loadAll();
    } catch (error) { setStatus("memory-category-status", `Could not add category: ${error.message || error}`); }
  });

  $("memory-template-form").addEventListener("submit", async (event) => {
    event.preventDefault(); setStatus("memory-template-status", "Saving…");
    try {
      const notes = [...panel.querySelectorAll(".memory-blueprint")].map((row) => ({name:row.querySelector("[data-template-note-name]").value.trim(), purpose:row.querySelector("[data-template-note-purpose]").value.trim(), content:row.querySelector("[data-template-note-content]").value}));
      await api("api/knowledge-memory/templates", {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({name:$("memory-template-name").value.trim(), original_name:state.editingTemplate, description:$("memory-template-description").value.trim(), category:$("memory-template-category").value, icon:$("memory-template-icon").value, notes})});
      $("memory-template-composer").hidden = true; state.editingTemplate = ""; await loadAll();
    } catch (error) { setStatus("memory-template-status", `Could not save template: ${error.message || error}`); }
  });

  panel.addEventListener("submit", async (event) => {
    if (event.target.id !== "memory-note-form") return;
    event.preventDefault(); setStatus("memory-note-status", "Saving…");
    try {
      const note = $("memory-note-name").value.trim();
      const payload = await api(`api/knowledge-memory/spaces/${encodeURIComponent(state.selectedSpace)}/note`, {method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify({note, original_note:state.selectedNote, content:$("memory-note-content").value, mode:state.selectedNote ? "replace" : "create"})});
      const savedNote = payload.note || note;
      await openSpace(state.selectedSpace); await openNote(savedNote); setStatus("memory-note-status", "Saved locally"); await loadAll();
    } catch (error) { setStatus("memory-note-status", `Could not save note: ${error.message || error}`); }
  });

  $("memory-search").addEventListener("input", () => { clearTimeout(searchTimer); renderSpaces(); searchTimer = setTimeout(runSearch, 250); });
  document.getElementById("memory-tab")?.addEventListener("click", () => { if (!state.loaded) loadAll().catch((error) => { $("memory-space-grid").innerHTML = `<div class="memory-empty">Memory Studio is unavailable: ${esc(error.message || error)}</div>`; }); });
  document.querySelector('[data-settings-target="memory"]')?.addEventListener("dblclick", () => document.getElementById("memory-tab")?.click());
  window.zbranoMemoryStudio = {refresh:loadAll, open:() => document.getElementById("memory-tab")?.click()};
})();
