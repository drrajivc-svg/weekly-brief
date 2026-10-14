const categories=[['All Stories','▦'],['Hospital Medicine','✚'],['Internal Medicine Research','◈'],['AI & Technology','✳'],['Gaming','◇'],['Politics & World','◎'],['Saved Stories','♡']];
let articles=[],active='All Stories',query='',sort='default';const $=s=>document.querySelector(s);const escapeHtml=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let saved=new Set();try{saved=new Set(JSON.parse(localStorage.getItem('weeklybrief-saved')||'[]'))}catch{};
function renderNav(){ $('#nav').innerHTML=categories.map(([name,icon])=>`<button class="navitem ${active===name?'active':''}" data-cat="${escapeHtml(name)}"><span>${icon}</span>${escapeHtml(name)}${name==='Saved Stories'&&saved.size?`<i>${saved.size}</i>`:''}</button>`).join('');$('#filters').innerHTML=categories.slice(0,-1).map(([name])=>`<button class="chip ${active===name?'selected':''}" data-cat="${escapeHtml(name)}">${escapeHtml(name)}</button>`).join('');document.querySelectorAll('[data-cat]').forEach(b=>b.onclick=()=>{active=b.dataset.cat;render()})}
function render(){renderNav();$('#articleCount').textContent=articles.length;$('#bookmarkCount').textContent=saved.size;$('#sectionTitle').textContent=active==='All Stories'?'Your weekly digest':active;$('#sectionSub').textContent=active==='Saved Stories'?'Stories you bookmarked for later.':'Explore clear, practical explanations and key takeaways.';let shown=articles.filter(a=>(active==='All Stories'||(active==='Saved Stories'?saved.has(a.id):a.category===active))&&[a.title,a.dek,a.category,a.tag,...a.summary].join(' ').toLowerCase().includes(query));if(sort==='title')shown.sort((a,b)=>a.title.localeCompare(b.title));$('#empty').hidden=shown.length>0;$('#articles').innerHTML=shown.map((a,i)=>`<article class="article ${a.featured&&active==='All Stories'&&i===0?'lead':''}"><div class="article-top"><span class="tag">${escapeHtml(a.tag)}</span><button class="save ${saved.has(a.id)?'saved':''}" data-save="${escapeHtml(a.id)}" aria-label="${saved.has(a.id)?'Remove bookmark':'Bookmark article'}">${saved.has(a.id)?'♥':'♡'}</button></div><div class="article-body"><div class="category">${escapeHtml(a.category)} <span>·</span> ${escapeHtml(a.readTime)} MIN READ</div><h3>${escapeHtml(a.title)}</h3><p>${escapeHtml(a.dek)}</p></div><div class="article-foot"><span>${escapeHtml(a.date)}</span><button data-open="${escapeHtml(a.id)}">Read briefing <span>↗</span></button></div></article>`).join('');document.querySelectorAll('[data-save]').forEach(b=>b.onclick=()=>{saved.has(b.dataset.save)?saved.delete(b.dataset.save):saved.add(b.dataset.save);try{localStorage.setItem('weeklybrief-saved',JSON.stringify([...saved]))}catch{}render()});document.querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>openArticle(b.dataset.open))}
function openArticle(id){const a=articles.find(x=>x.id===id);if(!a)return;$('#readerBody').innerHTML=`<div class="eyebrow dark">${escapeHtml(a.category)} · ${escapeHtml(a.readTime)} MIN READ</div><h2>${escapeHtml(a.title)}</h2><p class="reader-dek">${escapeHtml(a.dek)}</p>${a.summary.map(p=>`<p>${escapeHtml(p)}</p>`).join('')}<div class="takeaway"><b>WHY IT MATTERS</b><p>${escapeHtml(a.why)}</p></div><div class="evidence"><b>Evidence note:</b> ${escapeHtml(a.evidence)}</div>${a.source?`<a href="${escapeHtml(a.source)}" target="_blank" rel="noopener noreferrer">Read original source ↗</a>`:'<div class="demo-warning">Demonstration article — no live source attached.</div>'}`;$('#reader').showModal()}
$('#close').onclick=()=>$('#reader').close();$('#reader').onclick=e=>{if(e.target===$('#reader'))$('#reader').close()};$('#search').oninput=e=>{query=e.target.value.toLowerCase().trim();render()};$('#sort').onchange=e=>{sort=e.target.value;render()};$('#readTop').onclick=()=>$('#stories').scrollIntoView({behavior:'smooth'});$('#theme').onclick=()=>{document.body.classList.toggle('light');try{localStorage.setItem('weeklybrief-light',document.body.classList.contains('light'))}catch{}};try{if(localStorage.getItem('weeklybrief-light')==='true')document.body.classList.add('light')}catch{};$('#today').textContent=new Intl.DateTimeFormat('en-US',{month:'short',day:'numeric',year:'numeric'}).format(new Date());

fetch('articles.json')
  .then(r => {
    if (!r.ok) throw Error('Failed to load articles');
    return r.json();
  })
  .then(d => {
    articles = d.articles || [];

    const updated = d.updated
      ? new Date(d.updated + 'T12:00:00')
      : null;

    const editionLabel = updated && !isNaN(updated.getTime())
      ? 'Updated ' + new Intl.DateTimeFormat('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric'
        }).format(updated)
      : 'Latest edition';

    const status = document.querySelector('#editionStatus');
    if (status) {
      status.textContent = '● Live Edition';
    }

    const statusDate = document.querySelector('#editionDate');
    if (statusDate) {
      statusDate.textContent = editionLabel;
    }

    const footer = document.querySelector('#editionFooter');
    if (footer) {
      footer.textContent =
        'AI-assisted summaries. Verify clinical decisions against original research and guidelines.';
    }

    render();
  })
  .catch(() => {
    $('#articles').innerHTML =
      '<div class="empty">Could not load the latest articles. Please refresh the page.</div>';

    const status = document.querySelector('#editionStatus');
    if (status) status.textContent = 'Edition unavailable';
  });
