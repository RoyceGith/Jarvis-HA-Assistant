(() => {
  const tab = document.querySelector('[data-auto-view="notifications"]');
  const $ = id => document.getElementById(id);
  if (!tab || !$('telegram-inbound-form')) return;
  let state = {settings:{}, linked_chats:[], listener:{}};
  const setupGuide = $('telegram-setup-guide');
  if (setupGuide) setupGuide.innerHTML = `
    <summary><span><strong>Set up a Telegram bot</strong><small>A guided four-step setup</small></span><span id="telegram-setup-status" class="telegram-setup-status">Checking setup</span></summary>
    <div class="telegram-setup-steps">
      <article><span class="telegram-step-number">1</span><div><h4>Create your bot</h4><p>Open Telegram’s official BotFather, send /newbot, choose its name, and securely copy the token it gives you.</p><a href="https://t.me/BotFather" target="_blank" rel="noopener noreferrer">Open BotFather</a></div></article>
      <article><span class="telegram-step-number">2</span><div><h4>Connect it to Home Assistant</h4><p>Open the Telegram Bot integration, choose Polling, and paste the token there. Polling needs no public Home Assistant address.</p><a href="https://my.home-assistant.io/redirect/config_flow_start/?domain=telegram_bot" target="_blank" rel="noopener noreferrer">Add to Home Assistant</a></div></article>
      <article><span class="telegram-step-number">3</span><div><h4>Allow your Telegram chat</h4><p>Get your ID from @id_bot. In Home Assistant, open the Telegram Bot integration menu and select Add allowed chat ID. Then message your new bot with /start.</p><a href="https://t.me/id_bot" target="_blank" rel="noopener noreferrer">Get my chat ID</a></div></article>
      <article><span class="telegram-step-number">4</span><div><h4>Pair it with ZBRANO</h4><p>Return here and select Refresh. Choose the Telegram reply channel, save the Inbox, generate a pairing code, and send that command to your bot.</p><button type="button" data-telegram-refresh>Refresh and detect bot</button></div></article>
    </div>
    <p class="telegram-token-boundary"><strong>Your token stays private.</strong> Enter it only in Home Assistant. ZBRANO never asks for it or stores it.</p>`;

  async function api(path, options={}) {
    const response = await fetch(path, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    return data;
  }

  async function load() {
    const status = $('telegram-inbound-status');
    try {
      const [inbound, notifications] = await Promise.all([api('api/telegram-inbound'), api('api/notifications')]);
      state = inbound;
      const telegramChannels = (notifications.channels || []).filter(item => item.platform === 'telegram');
      const setupStatus = $('telegram-setup-status');
      if (setupStatus) {
        setupStatus.textContent = telegramChannels.length ? `${telegramChannels.length} channel${telegramChannels.length === 1 ? '' : 's'} detected` : 'Not connected';
        setupStatus.dataset.status = telegramChannels.length ? 'ready' : 'attention';
      }
      $('telegram-inbound-enabled').checked = Boolean(state.settings?.enabled);
      $('telegram-remote-approvals').checked = Boolean(state.settings?.remote_approvals_enabled);
      const channel = $('telegram-inbound-channel');
      channel.replaceChildren(new Option('Use Notification Center default', ''));
      for (const item of telegramChannels) {
        channel.appendChild(new Option(`Telegram · ${item.friendly_name}`, item.entity_id));
      }
      channel.value = state.settings?.reply_channel || '';
      const badge = $('telegram-inbound-state');
      badge.textContent = !state.settings?.enabled ? 'Disabled' : state.listener?.connected ? 'Online' : 'Waiting';
      badge.dataset.status = state.listener?.connected ? 'online' : 'offline';
      status.textContent = state.listener?.last_error ? `Listener: ${state.listener.last_error}` : `${state.linked_chats?.length || 0} paired chat(s)`;
      $('telegram-credential-boundary').textContent = state.credential_boundary || '';
      const root = $('telegram-linked-chats'); root.replaceChildren();
      for (const item of state.linked_chats || []) {
        const row = document.createElement('div'); row.className = 'notification-channel telegram-linked-chat';
        const identity = document.createElement('strong'); identity.textContent = item.display_name || 'Telegram owner';
        const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = 'Unlink'; remove.dataset.telegramUnlink = item.chat_id;
        const detail = document.createElement('small'); detail.textContent = `${item.username ? '@' + item.username + ' · ' : ''}Chat ${item.chat_id} · ${item.last_message_at ? 'last message ' + new Date(item.last_message_at * 1000).toLocaleString(window.ZbranoI18n?.locale || undefined) : 'no messages yet'}`;
        row.append(identity, remove, detail); root.appendChild(row);
      }
      if (!state.linked_chats?.length) root.innerHTML = '<div class="autonomy-empty">No Telegram chats paired.</div>';
    } catch (error) { status.textContent = `Load failed: ${error.message || error}`; }
  }

  $('telegram-inbound-form').addEventListener('submit', async event => {
    event.preventDefault(); const status = $('telegram-inbound-status'); status.textContent = 'Saving…';
    const body = {enabled:$('telegram-inbound-enabled').checked, reply_channel:$('telegram-inbound-channel').value, remote_approvals_enabled:$('telegram-remote-approvals').checked};
    try { await api('api/telegram-inbound/settings', {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)}); status.textContent = 'Telegram Inbox saved.'; await load(); }
    catch (error) { status.textContent = `Save failed: ${error.message || error}`; }
  });

  $('telegram-generate-code').addEventListener('click', async () => {
    const status = $('telegram-inbound-status'); status.textContent = 'Generating secure code…';
    try {
      const result = await api('api/telegram-inbound/link-code', {method:'POST'});
      const output = $('telegram-pairing-command'); output.hidden = false;
      output.innerHTML = `Send this command to your Telegram bot within 10 minutes:<code></code>`;
      output.querySelector('code').textContent = result.command;
      status.textContent = 'Pairing code ready.';
    } catch (error) { status.textContent = `Pairing failed: ${error.message || error}`; }
  });

  setupGuide?.addEventListener('click', event => {
    const refresh = event.target.closest('[data-telegram-refresh]');
    if (!refresh) return;
    refresh.disabled = true;
    load().finally(() => { refresh.disabled = false; });
  });

  $('telegram-linked-chats').addEventListener('click', async event => {
    const button = event.target.closest('[data-telegram-unlink]'); if (!button) return;
    button.disabled = true;
    try { await api('api/telegram-inbound/unlink', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({chat_id:button.dataset.telegramUnlink})}); await load(); }
    catch (error) { $('telegram-inbound-status').textContent = `Unlink failed: ${error.message || error}`; button.disabled = false; }
  });

  tab.addEventListener('click', load);
  document.getElementById('notification-refresh')?.addEventListener('click', load);
  window.zbranoTelegramInbox = {load};
})();
