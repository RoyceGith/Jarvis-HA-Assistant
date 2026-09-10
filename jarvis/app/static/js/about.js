"use strict";

(() => {
  const developerTab = document.getElementById("developer-tab");
  const developerPanel = document.getElementById("developer-panel");
  if (!developerTab || !developerPanel) return;

  const tab = document.createElement("button");
  tab.id = "about-tab";
  tab.className = "primary-icon-tab primary-labeled-tab";
  tab.type = "button";
  tab.setAttribute("aria-label", "About ZBRANO");
  tab.title = "About ZBRANO";
  tab.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 10v7M12 7h.01"/></svg><span>About</span>';
  developerTab.before(tab);

  const panel = document.createElement("section");
  panel.id = "about-panel";
  panel.className = "panel hidden";
  panel.setAttribute("aria-labelledby", "about-title");
  panel.innerHTML = `
    <div class="about-shell">
      <section class="about-hero">
        <div class="about-hero-copy">
          <span class="about-eyebrow">HOME INTELLIGENCE, ON YOUR TERMS</span>
          <h2 id="about-title">One assistant for your home, routines, and everyday context.</h2>
          <p>ZBRANO brings conversation, Home Assistant, organized files and memory, visual automations, notifications, and connected services into one clear workspace.</p>
          <div class="about-badges" aria-label="ZBRANO principles"><span>Built for Home Assistant</span><span>Owner-controlled access</span><span>Your choice of AI</span><span>Four interface languages</span></div>
          <div class="about-actions"><button id="about-start-chat" class="about-primary" type="button">Start a conversation</button><button id="about-open-setup" type="button">Review setup</button></div>
        </div>
        <div class="about-orbit" aria-hidden="true">
          <span class="about-orbit-core">Z</span><i class="orbit-one"></i><i class="orbit-two"></i><i class="orbit-three"></i>
          <b class="orbit-node node-home">HOME</b><b class="orbit-node node-memory">MEMORY</b><b class="orbit-node node-action">ACTION</b>
        </div>
      </section>

      <section class="about-section" aria-labelledby="about-capabilities-title">
        <div class="about-section-heading"><span>CAPABILITIES</span><h3 id="about-capabilities-title">Everything works as one assistant</h3><p>Use only what you need now, then add more capabilities when they become useful.</p></div>
        <div class="about-feature-grid">
          <article class="about-feature"><span class="about-feature-icon" aria-hidden="true">CHAT</span><h4>Natural conversation</h4><p>Talk or type, keep separate conversations, attach files, search the web when allowed, and hear spoken replies.</p><ul><li>Saved text and voice conversations</li><li>Optional wake phrase and follow-ups</li><li>Web search with visible sources</li><li>Adjustable models, reasoning, and response style</li></ul></article>
          <article class="about-feature"><span class="about-feature-icon" aria-hidden="true">HOME</span><h4>Home awareness and control</h4><p>Understand live Home Assistant state and act only through devices the owner explicitly allows.</p><ul><li>Sensor and control device inventory</li><li>Live values, areas, and labels</li><li>History and event timelines</li><li>Separate read and control access</li></ul></article>
          <article class="about-feature"><span class="about-feature-icon" aria-hidden="true">FLOW</span><h4>Visual automations</h4><p>Build understandable WHEN, IF, ELSE IF, message, and action paths without losing the full flow diagram.</p><ul><li>Natural-language drafts and templates</li><li>Branch-specific decisions and messages</li><li>Ask-first or automatic actions</li><li>Safe tests, activity, outcomes, and recovery</li></ul></article>
          <article class="about-feature"><span class="about-feature-icon" aria-hidden="true">MEM</span><h4>Memory and knowledge</h4><p>Keep useful preferences and knowledge close to the assistant while staying in control of what is remembered.</p><ul><li>Automatic Knowledge Memory organization</li><li>Custom spaces and reusable layouts</li><li>Formatted, editable, and printable notes</li><li>Private conversational Fast Memory</li></ul></article>
          <article class="about-feature"><span class="about-feature-icon" aria-hidden="true">FILE</span><h4>Files and everyday organization</h4><p>Keep the documents and details you use every day organized, searchable, and ready for conversation.</p><ul><li>Shared Files folders and subfolders</li><li>Upload, move, and attach documents</li><li>Local contacts and birthdays</li><li>Calendar, reminders, and notifications</li></ul></article>
          <article class="about-feature"><span class="about-feature-icon" aria-hidden="true">LINK</span><h4>Connected services</h4><p>Add optional services deliberately through plugins and integrations, without making them a requirement for the core assistant.</p><ul><li>Plugin catalog with explicit permissions</li><li>Google Calendar, Contacts, and Gmail</li><li>GitHub connection and developer tools</li><li>Home Assistant and Telegram notifications</li></ul></article>
          <article class="about-feature"><span class="about-feature-icon" aria-hidden="true">YOU</span><h4>Language and personalization</h4><p>Shape the interface and assistant around how you prefer to read, speak, and work.</p><ul><li>English, Greek, Italian, and French</li><li>Automatic or manual interface language</li><li>Theme, density, and text-size controls</li><li>Your preferred compatible AI provider</li></ul></article>
          <article class="about-feature"><span class="about-feature-icon" aria-hidden="true">SAFE</span><h4>Safety and ownership</h4><p>Keep sensitive actions bounded with explicit device access, per-automation authority, visible activity, and recoverable data.</p><ul><li>Approval where it matters</li><li>Quiet hours and presence checks</li><li>Backups, installation reports, and audit trails</li><li>Diagnostics and guarded failure recovery</li></ul></article>
        </div>
      </section>

      <section class="about-journey" aria-labelledby="about-journey-title">
        <div class="about-section-heading"><span>HOW IT COMES TOGETHER</span><h3 id="about-journey-title">From a connected home to useful action</h3></div>
        <ol>
          <li><b>01</b><div><strong>Connect</strong><span>Run ZBRANO inside Home Assistant and verify the AI connection.</span></div></li>
          <li><b>02</b><div><strong>Choose access</strong><span>Select Sensor devices for information and Control devices only for actions.</span></div></li>
          <li><b>03</b><div><strong>Ask or automate</strong><span>Start with a conversation or build a visual flow for a repeatable routine.</span></div></li>
          <li><b>04</b><div><strong>Stay informed</strong><span>Review messages, approvals, outcomes, and activity in one place.</span></div></li>
        </ol>
      </section>

      <section class="about-trust">
        <div><span class="about-eyebrow">DESIGNED TO STAY YOURS</span><h3>Capabilities are optional. Permission is explicit.</h3><p>ZBRANO runs as a Home Assistant app. Credentials remain in protected app configuration, persistent assistant data stays in its Home Assistant data area, and external providers are used only for the capabilities you configure.</p></div>
        <div class="about-actions"><button id="about-open-memory" type="button">Open memory</button><button id="about-open-files" type="button">Browse files</button><button id="about-open-devices" type="button">Choose device access</button><button id="about-open-automations" type="button">Explore automations</button></div>
      </section>
    </div>`;
  developerPanel.before(panel);
})();
