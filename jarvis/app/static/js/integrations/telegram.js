(() => {
  const tab = document.querySelector('[data-auto-view="notifications"]');
  const $ = id => document.getElementById(id);
  if (!tab || !$('telegram-inbound-form')) return;
  let state = {settings:{}, linked_chats:[], listener:{}};

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
      $('telegram-inbound-enabled').checked = Boolean(state.settings?.enabled);
      $('telegram-remote-approvals').checked = Boolean(state.settings?.remote_approvals_enabled);
      const channel = $('telegram-inbound-channel');
      channel.replaceChildren(new Option('Use Notification Center default', ''));
      for (const item of notifications.channels || []) {
        if (item.platform === 'telegram') channel.appendChild(new Option(`Telegram · ${item.friendly_name}`, item.entity_id));
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
        const detail = document.createElement('small'); detail.textContent = `${item.username ? '@' + item.username + ' · ' : ''}Chat ${item.chat_id} · ${item.last_message_at ? 'last message ' + new Date(item.last_message_at * 1000).toLocaleString() : 'no messages yet'}`;
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
