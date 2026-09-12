(() => {
  const source = document.querySelector('main > nav');
  const mobile = document.createElement('nav'); mobile.id = 'mobile-navigation'; mobile.setAttribute('aria-label', source.getAttribute('aria-label'));
  const drawer = document.createElement('dialog'); drawer.id = 'mobile-more';
  const title = document.createElement('h2'); title.id = 'mobile-more-title'; title.textContent = 'More'; drawer.setAttribute('aria-labelledby', title.id);
  const list = document.createElement('div'); list.className = 'mobile-more-links'; drawer.append(title, list);
  const close = document.createElement('button'); close.type = 'button'; close.textContent = 'Close'; close.addEventListener('click', () => drawer.close()); drawer.append(close);
  const more = document.createElement('button'); more.type = 'button'; more.textContent = 'More'; more.setAttribute('aria-haspopup', 'dialog'); more.setAttribute('aria-controls', drawer.id); more.setAttribute('aria-expanded', 'false');
  more.addEventListener('click', () => { drawer.showModal(); more.setAttribute('aria-expanded', 'true'); });
  drawer.addEventListener('close', () => { more.setAttribute('aria-expanded', 'false'); more.focus(); });
  drawer.addEventListener('click', event => { if (event.target === drawer) { const r=drawer.getBoundingClientRect(); if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)drawer.close(); } });
  const primary = ['chat-tab', 'entities-tab', 'automations-tab'];
  const buttons = new Map();
  function sync() {
    for (const original of source.querySelectorAll('button')) {
      if (!original.id) continue;
      let button = buttons.get(original.id);
      if (!button) {
        button = document.createElement('button'); button.type = 'button'; button.dataset.mobileTab = original.id;
        button.addEventListener('click', () => { if(drawer.open)drawer.close(); original.click(); });
        buttons.set(original.id, button);
      }
      button.textContent = original.textContent.trim();
      button.classList.toggle('active', original.classList.contains('active'));
      button.setAttribute('aria-current', original.classList.contains('active') ? 'page' : 'false');
      button.disabled = original.disabled;
      button.hidden = original.hidden || original.classList.contains('hidden') || original.style.display === 'none';
      if(!primary.includes(original.id) && button.parentElement !== list)list.append(button);
    }
    for (const id of primary) { const button=buttons.get(id); if(button && button.parentElement!==mobile)mobile.append(button); }
    if(mobile.lastElementChild!==more)mobile.append(more);
    more.classList.toggle('active', [...buttons].some(([id,button])=>!primary.includes(id)&&button.classList.contains('active')));
  }
  document.body.append(mobile, drawer); sync();
  new MutationObserver(sync).observe(source, {subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['class','hidden','style','disabled']});
  matchMedia('(max-width:700px)').addEventListener('change', event => { if(!event.matches&&drawer.open)drawer.close(); });
})();
