(() => {
  const source = document.querySelector('main > nav');
  const paths = {
    'chat-tab':'M4 4h16v12H9l-5 4V4Z',
    'entities-tab':'M5 3h14v18H5zM9 7h6M10 17h4',
    'automations-tab':'m13 2-8 12h6l-1 8 9-13h-6l1-7Z',
    'files-tab':'M3 6h7l2 3h9v11H3V6Z',
    'memory-tab':'M7 3h10v18H7zM3 7h4m-4 5h4m-4 5h4m10-10h4m-4 5h4m-4 5h4',
    'plugins-tab':'M8 3v5m8-5v5M6 8h12v3a6 6 0 0 1-12 0V8Zm6 9v4',
    'calendar-tab':'M4 5h16v16H4zM8 3v4m8-4v4M4 10h16',
    'contacts-tab':'M8 8a4 4 0 1 0 8 0 4 4 0 0 0-8 0M4 21a8 8 0 0 1 16 0',
    'settings-tab':'M4 6h16M4 12h16M4 18h16M8 3v6m8 0v6m-6 0v6',
    'about-tab':'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18M12 11v6m0-10v1',
    'developer-tab':'m8 6-6 6 6 6m8-12 6 6-6 6m-3-15-2 18',
    more:'M4 6h16M4 12h16M4 18h16'
  };
  function icon(id) {
    const svg=document.createElementNS('http://www.w3.org/2000/svg','svg'); svg.setAttribute('viewBox','0 0 24 24'); svg.setAttribute('aria-hidden','true');
    const path=document.createElementNS(svg.namespaceURI,'path'); path.setAttribute('d',paths[id] || paths.more); svg.append(path); return svg;
  }
  const mobile = document.createElement('nav'); mobile.id = 'mobile-navigation'; mobile.setAttribute('aria-label', source.getAttribute('aria-label'));
  const drawer = document.createElement('dialog'); drawer.id = 'mobile-more';
  const title = document.createElement('h2'); title.id = 'mobile-more-title'; title.textContent = 'More'; drawer.setAttribute('aria-labelledby', title.id);
  const list = document.createElement('div'); list.className = 'mobile-more-links'; drawer.append(title, list);
  const close = document.createElement('button'); close.type = 'button'; close.textContent = 'Close'; close.addEventListener('click', () => drawer.close()); drawer.append(close);
  const more = document.createElement('button'); more.type = 'button'; more.textContent = 'More'; more.setAttribute('aria-haspopup', 'dialog'); more.setAttribute('aria-controls', drawer.id); more.setAttribute('aria-expanded', 'false');
  const moreLabel=document.createElement('span'); moreLabel.textContent='More'; more.replaceChildren(icon('more'),moreLabel);
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
        const label=document.createElement('span'); label.className='mobile-tab-label'; button.append(icon(original.id),label);
        buttons.set(original.id, button);
      }
      const label=button.querySelector('.mobile-tab-label');
      const text=original.textContent.trim(); if(label.textContent!==text)label.textContent=text;
      button.classList.toggle('has-activity', original.classList.contains('zbrano-tab-unseen'));
      button.setAttribute('aria-label', original.getAttribute('aria-label') || text);
      button.classList.toggle('active', original.classList.contains('active'));
      button.setAttribute('aria-current', original.classList.contains('active') ? 'page' : 'false');
      button.disabled = original.disabled;
      button.hidden = original.hidden || original.classList.contains('hidden') || original.style.display === 'none';
      if(!primary.includes(original.id) && button.parentElement !== list)list.append(button);
    }
    for (const id of primary) { const button=buttons.get(id); if(button && button.parentElement!==mobile)mobile.append(button); }
    if(mobile.lastElementChild!==more)mobile.append(more);
    more.classList.toggle('has-activity', [...buttons].some(([id,button])=>!primary.includes(id)&&!button.hidden&&button.classList.contains('has-activity')));
    more.classList.toggle('active', [...buttons].some(([id,button])=>!primary.includes(id)&&button.classList.contains('active')));
  }
  document.body.append(mobile, drawer); sync();
  new MutationObserver(sync).observe(source, {subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['class','hidden','style','disabled','aria-label']});
  matchMedia('(max-width:700px)').addEventListener('change', event => { if(!event.matches&&drawer.open)drawer.close(); });
})();
