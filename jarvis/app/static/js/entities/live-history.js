(() => {
  const historyTab=document.querySelector('[data-entity-view="history"]');
  const input=document.getElementById('ha-history-entities');
  const status=document.getElementById('ha-history-status');
  if(!historyTab||!input||!status)return;
  let loading=false;
  async function api(path){const response=await fetch(path,{cache:'no-store'});const data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(data.detail||`HTTP ${response.status}`);return data}
  async function initialize(){
    if(loading)return;loading=true;status.textContent='Loading recent approved Home Assistant activity…';
    try{
      const live=await api('api/ha/live-events?limit=100');
      const recent=[...new Set((live.events||[]).map(item=>item.entity_id).filter(Boolean))];
      const selected=input.value.split(',').map(value=>value.trim().toLowerCase()).filter(Boolean);
      let ids=[...new Set([...recent,...selected])].slice(0,8);
      if(!ids.length){const approved=await api('api/ha/approved');ids=[...new Set([...(approved.control_entities||[]),...(approved.read_entities||[])])].slice(0,8)}
      input.value=ids.join(', ');
      if(ids.length){
        await window.zbranoHaHistory?.load();
        status.textContent+=` · live capture ${live.connected?'connected':'disconnected'} · evidence ${Number(live.count||0)} · live changes ${Number(live.journal_count||0)}`;
      }else status.textContent='No approved entities are available for History.';
    }catch(error){status.textContent=`History initialization failed: ${error.message||error}`}finally{loading=false}
  }
  historyTab.addEventListener('click',()=>setTimeout(initialize,0));
})();
