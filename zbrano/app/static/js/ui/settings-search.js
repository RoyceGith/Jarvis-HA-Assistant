(() => {
  const panel=document.getElementById('settings-panel');
  const input=document.getElementById('settings-find');
  const results=document.getElementById('settings-find-results');
  const empty=document.getElementById('settings-find-empty');
  const normalize=value=>String(value||'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase().trim();
  let highlighted=null, highlightTimer=0;
  function clear() { input.value=''; results.replaceChildren(); results.hidden=true; empty.hidden=true; }
  function search() {
    results.replaceChildren();
    const words=normalize(input.value).split(/\s+/).filter(Boolean);
    if(!words.length){results.hidden=true;empty.hidden=true;return;}
    let count=0;
    for(const label of panel.querySelectorAll('.settings-card[data-settings-category] label, .settings-card[data-settings-category] h2, .settings-card[data-settings-category] h3')) {
      const card=label.closest('[data-settings-category]');
      const category=card.dataset.settingsCategory;
      const subview=label.closest('[data-notification-panel]')?.dataset.notificationPanel;
      const tab=[...panel.querySelectorAll('[data-settings-target]')].find(button=>button.dataset.settingsTarget===category && (!subview||button.dataset.notificationView===subview));
      if(!tab||tab.disabled||tab.hidden)continue;
      const categoryLabel=tab.querySelector('span:last-child')?.textContent.trim()||category;
      // Index descriptions only: never input values, credentials or user instructions.
      const text=label.textContent.replace(/\s+/g,' ').trim();
      if(!text||!words.every(word=>normalize(categoryLabel+' '+text).includes(word)))continue;
      const button=document.createElement('button'); button.type='button'; button.className='settings-find-result'; button.dataset.i18nIgnore='';
      const title=document.createElement('strong');title.textContent=text;
      const context=document.createElement('small');context.textContent=categoryLabel;
      button.append(title,context);
      button.addEventListener('click',()=>{
        clear();tab.click();
        for(let parent=label.parentElement;parent&&parent!==card;parent=parent.parentElement)if(parent.tagName==='DETAILS')parent.open=true;
        requestAnimationFrame(()=>{
          if(!label.isConnected)return;
          if(highlighted)highlighted.classList.remove('settings-found');
          highlighted=label.closest('.setting-field,.toggle-row,.neural-range')||label;
          highlighted.classList.add('settings-found');
          label.scrollIntoView({block:'center',behavior:'instant'});
          const control=label.control||label.querySelector('input,select,textarea,button');
          if(control&&!control.disabled)control.focus({preventScroll:true});
          else {label.setAttribute('tabindex','-1');label.focus({preventScroll:true});}
          clearTimeout(highlightTimer);highlightTimer=setTimeout(()=>highlighted?.classList.remove('settings-found'),3500);
        });
      });
      results.append(button);count++;
      if(count===24)break;
    }
    results.hidden=count===0;empty.hidden=count!==0;
  }
  input.addEventListener('input',search);
  input.addEventListener('keydown',event=>{
    if(event.key==='Escape'){event.preventDefault();clear();}
    if(event.key==='ArrowDown'&&results.firstElementChild){event.preventDefault();results.firstElementChild.focus();}
  });
  results.addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();clear();input.focus();}});
  let locale=window.ZbranoI18n?.locale;
  window.addEventListener('zbrano:language-applied',()=>{
    if(locale===window.ZbranoI18n?.locale)return;
    locale=window.ZbranoI18n?.locale;
    if(input.value)search();
  });
})();
