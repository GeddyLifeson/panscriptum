import{M as e}from"./utils-Cob8vHf9.js";import{d as t,t as n}from"./layers-Bh4OWBXX.js";import{n as r,t as i}from"./highlight-Qtqc1_QO.js";import{r as a}from"./viewport-CRAO29Z3.js";import{i as o}from"./tooltips-BTSHGd98.js";import{Ot as s,U as c,W as l,k as u}from"./index-DsIn6sTp.js";var d=`fmg-omnibar-history`,f=10,p=50,m=60,h=100,g=800,_=document.createElement(`template`),v=class{root;input;list;status;events;previousFocus;keys=new Set;records=[];results=[];matched=0;history=[];selected=-1;busy=!1;open(){if(this.root)return void this.input?.focus();this.busy||(this.previousFocus=document.activeElement instanceof HTMLElement?document.activeElement:void 0,this.records=this.collect(),this.history=this.readHistory(),this.render(),this.listen(),this.search(),this.input?.focus())}close(){this.dismiss(!0)}collect(){let e=u.map(e=>({kind:`command`,id:e.id,name:e.name,context:`Command`,fields:{name:y(e.name),alias:y(e.aliases)},command:e}));if(typeof pack>`u`||!pack.cells?.i?.length)return e;let n=new Map;for(let e of c)for(let t of l.collect(e,{located:!0})){let{ref:e,entity:r}=t,i=l.key(e),a=l.getDisplay(e),o=l.getName(e)||r.name||``,s=[a.kind,l.getContext(e)].filter(Boolean).join(` · `),c=o?`${r.name||o} ${s}`:s;n.set(i,{kind:`entity`,id:`entity:${i}`,name:o||a.kind,context:s,fields:{...this.fields({name:o,alias:c,note:r.note}),unnamed:!o},target:t,display:a})}for(let e of t()){if(!e.text)continue;let t=e.type===`added`?`addedLabel`:e.type,r=n.get(l.key({type:t,id:e.entityId}));if(r?.kind!==`entity`||e.type===`added`)continue;let i=e.text.replaceAll(`|`,` `);n.set(`label:${e.id}`,{kind:`label`,id:`label:${e.id}`,name:i,context:`Label · ${r.context}`,fields:this.fields({name:i,alias:`${r.name} ${r.context}`}),target:r.target,label:e})}return[...e,...n.values()]}fields({name:e,alias:t,note:n}){let r=S(n||``);return{name:y(e),alias:y(t),note:r,normalizedNote:r?y(r):void 0}}readHistory(){try{let e=JSON.parse(localStorage.getItem(d)||`[]`),t=new Set(this.records.filter(e=>e.kind===`command`).map(e=>e.id));return Array.isArray(e)?[...new Set(e.filter(e=>typeof e==`string`&&t.has(e)))].slice(0,f):[]}catch{return[]}}render(){let e=document.createElement(`div`);e.id=`omnibar`,e.setAttribute(`role`,`dialog`),e.setAttribute(`aria-label`,`Search map and commands`),e.innerHTML=`
      <style>
        #omnibar {
          --line: color-mix(in srgb, var(--bg-main) 22%, transparent);
          --muted: color-mix(in srgb, currentColor 55%, transparent);
          position: fixed;
          top: 0.8em;
          left: 50%;
          transform: translateX(-50%);
          width: min(50em, calc(100vw - 2em));
          z-index: 100000;
          box-sizing: border-box;
          overflow: hidden;
          background: var(--bg-dialogs, rgb(250 250 250 / 97%));
          color: #30343b;
          box-shadow: 0 0.5em 1.5em #00000030;
          font: 1.2em/1.3 var(--sans-serif);
        }

        #omnibar .omnibar-search {
          display: flex;
          align-items: center;
          gap: 0.7em;
          padding: 0 0.9em;
        }

        #omnibar .omnibar-search > .icon-search {
          color: var(--dark-solid);
          font-size: 1em;
        }

        #omnibar input {
          box-sizing: border-box;
          flex: 1;
          min-width: 0;
          height: 2.7em;
          margin: 0;
          padding: 0;
          border: 0;
          border-radius: 0;
          outline: none;
          box-shadow: none;
          background: transparent;
          color: inherit;
          caret-color: var(--dark-solid);
          font: inherit;
        }

        #omnibar input::placeholder {
          color: var(--muted);
        }

        #omnibar .omnibar-escape {
          color: var(--muted);
          font-size: 0.75em;
        }

        #omnibar-list {
          max-height: min(26em, 50vh);
          overflow-y: auto;
          overscroll-behavior: contain;
          scrollbar-width: thin;
          scrollbar-color: var(--line) transparent;
        }

        #omnibar-list:not(:empty) {
          padding: 0.25em;
          border-top: 1px solid var(--line);
        }

        #omnibar [role="option"] {
          display: flex;
          align-items: center;
          gap: 0.6em;
          min-width: 0;
          padding: 0.3em 0.6em;
          cursor: pointer;
        }

        #omnibar [role="option"]:hover {
          background: color-mix(in srgb, var(--dark-solid) 5%, transparent);
        }

        #omnibar [role="option"][aria-selected="true"] {
          background: color-mix(in srgb, var(--dark-solid) 12%, transparent);
        }

        #omnibar [aria-disabled="true"] {
          color: var(--muted);
          cursor: default;
        }

        #omnibar .omnibar-icon {
          flex: 0 0 1.3em;
          color: var(--muted);
          font-size: 0.95em;
          text-align: center;
        }

        #omnibar [aria-selected="true"] .omnibar-icon {
          color: var(--dark-solid);
        }

        #omnibar .omnibar-name {
          flex: 1;
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        #omnibar .omnibar-detail {
          flex: 0 1 auto;
          max-width: 50%;
          margin-left: auto;
          overflow: hidden;
          color: var(--muted);
          font-size: 0.85em;
          text-align: right;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        #omnibar mark {
          background: transparent;
          color: var(--dark-solid);
          font-weight: 600;
        }

        #omnibar-status {
          padding: 0.35em 1.2em;
          border-top: 1px solid var(--line);
          color: var(--muted);
          font-size: 0.75em;
        }

        #omnibar-status:empty {
          display: none;
        }
      </style>

      <div class="omnibar-search">
        <span class="icon-search" aria-hidden="true"></span>
        <input
          id="omnibar-input"
          role="combobox"
          aria-label="Search map and commands"
          aria-expanded="true"
          aria-controls="omnibar-list"
          aria-autocomplete="list"
          autocomplete="off"
          spellcheck="false"
          placeholder="Search map and commands"
        >
        <span class="omnibar-escape" aria-hidden="true">esc</span>
      </div>

      <div id="omnibar-list" role="listbox" aria-label="Search results"></div>
      <div id="omnibar-status" role="status" aria-live="polite"></div>
    `,document.body.append(e),this.root=e,this.input=e.querySelector(`input`),this.list=e.querySelector(`#omnibar-list`),this.status=e.querySelector(`#omnibar-status`),this.input.addEventListener(`input`,()=>this.search()),this.list.addEventListener(`mousedown`,e=>e.preventDefault()),this.list.addEventListener(`click`,e=>{let t=e.target.closest(`[data-index]`);t&&this.activate(Number(t.dataset.index))})}listen(){if(this.events)return;this.events=new AbortController;let e={capture:!0,signal:this.events.signal};window.addEventListener(`keydown`,e=>{if(this.root){if(e.code===`Space`&&!this.input?.value){e.preventDefault(),e.stopImmediatePropagation();return}if(this.keys.add(e.code),e.stopImmediatePropagation(),!e.isComposing)if([`Escape`,`Enter`,`ArrowDown`,`ArrowUp`,`Tab`].includes(e.key)&&e.preventDefault(),((e.ctrlKey||e.metaKey)&&e.code===`KeyS`||/^F\d+$/.test(e.code))&&e.preventDefault(),e.key===`Escape`)this.close();else if(e.key===`Enter`&&!e.repeat)this.activate(this.selected);else if(e.key===`ArrowDown`||e.key===`ArrowUp`){let t=this.results.length;t&&this.select((this.selected+(e.key===`ArrowDown`?1:-1)+t)%t)}else e.key===`Tab`&&this.input?.focus()}},e),window.addEventListener(`keyup`,e=>{(this.root||this.keys.has(e.code))&&(e.stopImmediatePropagation(),e.preventDefault()),this.keys.delete(e.code),e.key===`Meta`&&this.keys.clear(),this.cleanup()},e),window.addEventListener(`pointerdown`,e=>{this.root&&!this.root.contains(e.target)&&this.close()},e),window.addEventListener(`blur`,()=>{this.keys.clear(),this.close()},{signal:this.events.signal}),window.addEventListener(`map:generated`,()=>{this.root&&(this.records=this.collect(),this.search(),this.report(`The map changed. Select a current result.`))},{signal:this.events.signal})}search(){let e=this.input?.value.trim()||``,t=e.startsWith(`>`),n=y(t?e.slice(1):e),r=!n||/[\p{L}\p{N}?]/u.test(n),i=this.records.filter(e=>!t||e.kind===`command`).map((e,i)=>({result:e,order:i,score:r?this.score(e,n,t,this.history.indexOf(e.id)):0})).filter(e=>e.score>0).sort((e,t)=>t.score-e.score||e.order-t.order);this.matched=i.length,this.results=i.slice(0,t?1/0:p).map(e=>e.result),this.selected=0,this.renderResults(n)}score(e,t,n,r){if(t){let{fields:n}=e,r=C(n.name,t),i=C(n.alias,t),a=n.normalizedNote?.includes(t)?h:0,o=e.kind===`command`&&e.command.matches?.(t)?g:0,s=Math.max(r&&r+400,i&&i+200,o,a);return n.unnamed?Math.min(s,h):s}return e.kind===`command`?r>=0?1e3-r:+!!n:0}renderResults(e){if(!this.list||!this.status)return;let t=w();this.list.replaceChildren(),this.results.forEach((r,i)=>{let a=document.createElement(`div`);a.id=`omnibar-result-${i}`,a.dataset.index=String(i),a.setAttribute(`role`,`option`),a.setAttribute(`aria-disabled`,String(!!t));let o=document.createElement(`span`);o.className=`omnibar-icon`,r.kind===`command`?o.textContent=`>`:o.classList.add(r.kind===`label`?`icon-font`:r.display.icon),o.setAttribute(`aria-hidden`,`true`);let s=document.createElement(`span`);s.className=`omnibar-name`,this.highlight(s,r.name,e);let c=document.createElement(`span`);c.className=`omnibar-detail`;let l=r.kind===`command`?r.command.layer:void 0;c.textContent=t||`${r.context}${l?` · ${n.isOn(l)?`Visible`:`Hidden`}`:``}`,a.append(o,s,c);let u=r.kind===`entity`?r.fields:void 0,d=r.kind===`entity`&&r.display.previewNote;if(u?.note&&(d||e&&u.normalizedNote?.includes(e))){let t=document.createElement(`span`);this.highlight(t,x(u.note,d?``:e),e),c.append(` · `,t)}a.title=`${r.name} · ${c.textContent}`,this.list.append(a)});let r=this.matched>this.results.length?`${this.results.length} of ${this.matched}`:this.results.length;this.status.textContent=this.results.length?`${r} results · ↑↓ navigate · ↵ select`:e?`No matches`:``,this.select(this.selected)}highlight(e,t,n){let{letters:r,haystack:i,owners:a}=b(t),o=new Set;for(let e of n.split(` `).filter(Boolean)){let t=i.indexOf(e);for(;t!==-1;){for(let n=t;n<t+e.length;n++)o.add(a[n]);t=i.indexOf(e,t+e.length)}}r.forEach((t,n)=>{if(!o.has(n)){e.append(t);return}let r=document.createElement(`mark`);r.textContent=t,e.append(r)})}select(e){this.selected=e,this.list?.querySelectorAll(`[role='option']`).forEach((t,n)=>{t.setAttribute(`aria-selected`,String(n===e))});let t=this.list?.children[e];t?(this.input?.setAttribute(`aria-activedescendant`,t.id),t.scrollIntoView({block:`nearest`})):this.input?.removeAttribute(`aria-activedescendant`)}async activate(e){let t=this.results[e];if(!(!t||this.busy)&&!this.unavailable()){if(t.kind!==`command`&&!this.current(t)){this.records=this.collect(),this.search(),this.report(`The map changed. Select a current result.`);return}this.busy=!0,this.dismiss(!1);try{if(t.kind===`command`)await t.command.run(),this.remember(t.id);else if(t.kind===`label`)this.navigate(t.target,{label:t.label});else{let e=l.open(t.target.ref);e?await e:this.navigate(t.target,{display:t.display})}}catch{o(`Could not open the search result. Please try again.`,!1,`error`)}finally{this.busy=!1}}}current(e){return l.get(e.target.ref)===e.target.entity}navigate(t,{label:o,display:c}={}){let u=o?[`labels`]:c?.layers||[],d=o?[[o.anchor[0]+(o.dx||0),o.anchor[1]+(o.dy||0)]]:l.getPoints(t.ref);if(!d.length){this.report(`This element has no map location`,`warn`);return}n.show(...u);let f=o&&options.map.labels.groups.find(e=>e.name===o.group);f?.layerDependency&&n.has(f.layerDependency)&&n.show(f.layerDependency);let[p,m,h,g]=[1/0,1/0,-1/0,-1/0];for(let[e,t]of d)[p,m,h,g]=[Math.min(p,e),Math.min(m,t),Math.max(h,e),Math.max(g,t)];let _=o?8:c?.scale??8,v=Math.min(_,a.width*.65/Math.max(1,h-p),a.height*.65/Math.max(1,g-m)),y=Math.max(1,v);f&&(y=Math.max(f.zoom.min??1,Math.min(f.zoom.max??20,y))),s((p+h)/2,(m+g)/2,y,1500),setTimeout(()=>{let n=o?o.id:l.getElementId(t.ref),a=o?e(o.id):c?.highlight&&document.querySelector(c.highlight)||(n?e(n):null);a?r(a):i({x:p,y:m,width:h-p,height:g-m})},750)}remember(e){this.history=[e,...this.history.filter(t=>t!==e)].slice(0,f);try{localStorage.setItem(d,JSON.stringify(this.history))}catch{}}report(e,t){t?o(e,!1,t,4e3):this.status&&(this.status.textContent=e)}unavailable(){let e=w();return e?(this.report(e),!0):!1}dismiss(e){this.root?.remove(),this.root=this.input=this.list=this.status=void 0,this.records=this.results=[],e&&this.previousFocus?.isConnected&&this.previousFocus.focus(),this.previousFocus=void 0,this.cleanup()}cleanup(){this.root||this.keys.size||(this.events?.abort(),this.events=void 0)}};function y(e){return e.normalize(`NFD`).replace(/\p{M}/gu,``).toLowerCase().replace(/\s+/g,` `).trim()}function b(e){let t=Array.from(e),n=t.map(e=>e.normalize(`NFD`).replace(/\p{M}/gu,``).toLowerCase()),r=n.flatMap((e,t)=>Array(e.length).fill(t));return{letters:t,haystack:n.join(``),owners:r}}function x(e,t){let{letters:n,haystack:r,owners:i}=b(e),a=t?r.indexOf(t):-1,o=a===-1?0:Math.max(0,i[a]-35);return`${o?`…`:``}${n.slice(o,o+m).join(``)}`}function S(e){if(!e)return``;_.innerHTML=e;for(let e of _.content.querySelectorAll(`script, style`))e.remove();for(let e of _.content.querySelectorAll(`br, p, div, li`))e.append(` `);let t=_.content.textContent||``;return _.innerHTML=``,t.replace(/\s+/g,` `).trim()}function C(e,t){if(e===t)return 1e3;if(e.startsWith(t))return 850;if(e.includes(t))return 700;let n=t.split(` `);return n.length>1&&n.every(t=>e.includes(t))?600:0}function w(){return typeof pack>`u`||!pack.cells?.i?.length?`Generate or load a map first`:typeof customization<`u`&&customization?`Exit customization mode first`:document.getElementById(`canvas3d`)?`Switch to the 2D map first`:``}var T=new v;export{T as Omnibar};