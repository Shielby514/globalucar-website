(()=>{'use strict';let mode='oe',seq=0;const input=document.getElementById('hub-search-input'),result=document.getElementById('hub-search-result');function renderPreview(doc,q,url,rfq){
 result.replaceChildren();const root=document.createElement('article');root.className='hub-preview';result.append(root);
 const el=(tag,text,parent=root)=>{const n=document.createElement(tag);if(text)n.textContent=text;parent.append(n);return n};
 el('h3',doc.querySelector('h1')?.textContent.trim()||'OE '+q);
 el('p','Exact catalogue reference matched. Product photo, vehicle fitment and availability are separate checks; confirm these before ordering.').className='hub-preview-note';
 const sections=[...doc.querySelectorAll('section')];const find=t=>sections.find(s=>s.querySelector('h2')?.textContent.trim()===t);
 const layout=el('div');layout.className='hub-preview-top';const photo=el('section','',layout);el('h4','1. Product Reference Image',photo);
 const figure=find('Product Reference Image')?.querySelector('[data-preview-image]');const src=figure?.dataset.previewImage;
 if(src&&/^\/assets\/parts\/own-stock\/[A-Za-z0-9_.-]+$/.test(src)){const img=el('img','',photo);img.src=src;img.alt='Catalogue reference image for OE '+q;img.className='hub-preview-image';img.addEventListener('error',()=>{img.remove();el('p','Reference image unavailable. Request a photo with your quotation.',photo)},{once:true});el('p','Catalogue image; confirm the proposed item with your quotation.',photo).className='hub-preview-note'}else el('div','A matching product photo is pending verification. Request a photo for this reference.',photo).className='hub-preview-no-image';
 const quote=el('a','Get a quote',photo);quote.href=rfq;quote.className='hub-preview-quote';
 const quick=el('section','',layout);el('h4','2. Quick Reference',quick);const dl=el('dl','',quick);const pairs=[['OE Number',q]];
 const source=find('Quick Reference');for(const node of source?.querySelectorAll('.oe-kv')||[]){const key=node.querySelector('b')?.textContent.trim(),value=node.querySelector('span')?.textContent.trim();if(['Component','Brand Coverage','System'].includes(key)&&value)pairs.push([key,value]);}
 pairs.push(['Wholesale Price','Contact for wholesale pricing'],['Availability / MOQ','Confirmed with quotation']);for(const [k,v] of pairs){el('dt',k,dl);const dd=el('dd','',dl);if(k==='Wholesale Price'){const a=el('a',v,dd);a.href=rfq}else dd.textContent=v;}
 const structure=el('section');el('h4','3. Part Number Structure',structure);el('p','Reference formatting only. A prefix or suffix does not establish fitment or interchangeability.',structure).className='hub-preview-note';
 const wrap=el('div','',structure);wrap.className='hub-preview-table-wrap';const table=el('table','',wrap),head=el('thead','',table),hr=el('tr','',head);for(const t of ['Field','Value'])el('th',t,hr);const body=el('tbody','',table);let rows=[['Full reference',q],['Normalized (no spaces / hyphens)',q.replace(/[ -]/g,'')]];const parts=q.split('-');if(parts.length===2)rows.push(['Prefix (as written)',parts[0]],['Suffix (as written)',parts[1]]);for(const [k,v] of rows){const tr=el('tr','',body);el('td',k,tr);el('td',v,tr)}const more=el('a','more detail',structure);more.href=url;more.className='hub-preview-more';
}
;function show(message,links=[]){result.replaceChildren();const box=document.createElement('div');box.className='hub-search-result-card';const p=document.createElement('p');p.textContent=message;box.append(p);for(const [text,url] of links){let a=document.createElement('a');a.textContent=text;a.href=url;box.append(a)}result.append(box)}document.querySelectorAll('.hub-search-tabs button').forEach(b=>b.addEventListener('click',()=>{seq++;mode=b.dataset.mode;document.querySelectorAll('.hub-search-tabs button').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));input.value='';input.placeholder=mode==='oe'?'e.g. 22311-2E100 or 54501-2H000':'Enter VIN or frame reference for identification review';document.querySelector('.hub-search-label').textContent=mode==='oe'?'OE part number':'VIN / frame reference';result.replaceChildren();input.focus()}));let indexPromise;const normalize=s=>s.toUpperCase().replace(/[ -]/g,'');
async function exactIndex(){if(!indexPromise)indexPromise=fetch('/assets/data/oe-exact-index.json?v=20261114').then(r=>{if(!r.ok)throw Error('Index unavailable');return r.json()}).catch(e=>{indexPromise=null;throw e});return indexPromise;}
document.getElementById('hub-search-form').addEventListener('submit',async e=>{
 e.preventDefault();const q=input.value.trim(),run=++seq;if(!q)return;
 const enquiry=ref=>'/contact.html?service=auto_parts&oe='+encodeURIComponent(ref)+'#contactForm';
 if(mode==='vin'){if(!/^[A-Za-z0-9-]{5,30}$/.test(q)){show('Enter a valid VIN or frame reference.');return}show('VIN / frame matching requires identification review. This form does not automatically decode the vehicle or confirm fitment.',[['Prepare a parts enquiry',enquiry(q)]]);return;}
 if(!/^[A-Za-z0-9 -]{3,80}$/.test(q)){show('Enter one complete OE reference using letters, numbers, spaces and hyphens.');return;}
 show('Checking the exact OE reference…');
 try {
  const index=await exactIndex();if(run!==seq)return;const matches=index.entries[normalize(q)]||[];
  if(matches.length===0){show('No exact catalogue reference found. Please check every character and suffix. Similar numbers are not substitutes.',[['Request identification review',enquiry(q)]]);return;}
  if(matches.length!==1){show('This reference has more than one catalogue record. Review the candidates; no substitute has been selected.',matches.map(x=>['Review '+x[0],'/oe/'+encodeURIComponent(x[1])+'.html']));return;}
  const [reference,slug]=matches[0];if(!/^[a-z0-9-]+$/.test(slug))throw Error('Invalid catalogue path');const url='/oe/'+slug+'.html';
  const r=await fetch(url);if(!r.ok)throw Error('Reference unavailable');const doc=new DOMParser().parseFromString(await r.text(),'text/html');if(run!==seq)return;
  const heading=doc.querySelector('h1')?.textContent.trim()||'',parsed=heading.match(/^OE\s+(.+?)\s+—/),canonical=doc.querySelector('link[rel="canonical"]')?.getAttribute('href');
  if(!parsed||normalize(parsed[1])!==normalize(reference)||!canonical||(new URL(canonical,location.origin).pathname!==url||new URL(canonical,location.origin).origin!=='https://www.global-ucars.com'))throw Error('Reference verification failed');
  renderPreview(doc,reference,url,enquiry(reference));
 }catch{if(run===seq)show('We could not verify this catalogue result. No product match has been confirmed. Please try later or request identification review.',[['Prepare an enquiry',enquiry(q)]]);}
});
const initial=new URLSearchParams(location.search);if(initial.get('q')){if(initial.get('mode')==='vin')document.querySelector('[data-mode="vin"]').click();input.value=initial.get('q').slice(0,80);document.getElementById('hub-search-form').requestSubmit();}
fetch('/oe/stats.json').then(r=>r.ok?r.json():null).then(s=>{if(s&&Number.isInteger(s.oe_pages))document.getElementById('hub-oe-count').textContent=s.oe_pages.toLocaleString('en-US')}).catch(()=>{});})();