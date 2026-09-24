import{M as e,P as t,R as n,Xt as r,hn as i,j as a,nn as o,pt as s,z as c}from"./utils-Cob8vHf9.js";import{Z as l,t as u}from"./layers-Bh4OWBXX.js";import{i as d,t as f}from"./tooltips-BTSHGd98.js";import{V as p,d as m,dt as h,lt as g,st as _,u as v}from"./index-DsIn6sTp.js";import{t as y}from"./highlighting-BxkDyRR_.js";import{a as b,i as x,n as S,r as C}from"./table-B6G2rlSI.js";var w={Ally:{inText:`is an ally of`,color:`#00b300`,tip:`Allies formed a defensive pact and protect each other in case of third party aggression`},Friendly:{inText:`is friendly to`,color:`#d4f8aa`,tip:`State is friendly to anouther state when they share some common interests`},Neutral:{inText:`is neutral to`,color:`#edeee8`,tip:`Neutral means states relations are neither positive nor negative`},Suspicion:{inText:`is suspicious of`,color:`#eeafaa`,tip:`Suspicion means state has a cautious distrust of another state`},Enemy:{inText:`is at war with`,color:`#e64b40`,tip:`Enemies are states at war with each other`},Unknown:{inText:`does not know about`,color:`#a9a9a9`,tip:`Relations are unknown if states do not have enough information about each other`},Rival:{inText:`is a rival of`,color:`#ad5a1f`,tip:`Rivalry is a state of competing for dominance in the region`},Vassal:{inText:`is a vassal of`,color:`#87CEFA`,tip:`Vassal is a state having obligation to its suzerain`},Suzerain:{inText:`is suzerain to`,color:`#00008B`,tip:`Suzerain is a state having some control over its vassals`}},T=`diplomacyEditor`,E=`diplomacyRelations`,D={my:`right top`,at:`right-10 top+10`,of:`svg`,collision:`fit`},O=0,k=[{key:`name`,label:`State`,width:`15em`,permanent:!0,sortBy:e=>e.fullName||e.name,sortType:`alpha`},{key:`relations`,label:`Relations`,width:`7em`,permanent:!0,sortBy:e=>e.diplomacy?.[O]??``,sortType:`alpha`}],A=C({getData:()=>m(T,pack.states.filter(e=>e.i&&!e.removed&&e.i!==O),k),onUpdate:F}),j=()=>pack.states[0].diplomacy;function M(){if(!customization){if(pack.states.filter(e=>e.i&&!e.removed).length<2){d(`There should be at least 2 states to edit the diplomacy`,!1,`error`);return}(!O||!pack.states[O]||pack.states[O].removed)&&(O=pack.states.find(e=>e.i&&!e.removed).i),_(`#${T}, .stable`),u.show(`states`,`borders`),u.hide(`provinces`,`cultures`),u.hide(`biomes`,`religions`),N(),P(),i(`#viewbox`).style(`cursor`,`crosshair`).on(`click`,z),$(`#${T}`).dialog({title:`Diplomacy Editor`,resizable:!1,width:`fit-content`,close:Z,position:D})}}function N(){g(T);let e=`<div id="${T}" class="dialog stable editorDialog">
      ${x({dialogId:T,columns:k})}
      <div id="diplomacyBodySection" class="table"></div>
      <div id="diplomacyFooter" class="totalLine"><div>States: <span id="diplomacyFooterStates">0</span></div></div>
      <div class="info-line">Click on state name to see relations.<br />Click on relations name to change it</div>
      <div id="diplomacyBottom" style="margin-top: 0.1em">
        <button id="diplomacyEditorRefresh" data-tip="Refresh the Editor" class="icon-cw"></button>
        <button
          id="diplomacyEditStyle"
          data-tip="Edit states (including diplomacy view) style in Style Editor"
          class="icon-adjust"
        ></button>
        <button id="diplomacyRegenerate" data-tip="Regenerate diplomatical relations" class="icon-retweet"></button>
        <button
          id="diplomacyReset"
          data-tip="Reset diplomatical relations of selected state to Neutral"
          class="icon-eraser"
        ></button>
        <button id="diplomacyHistory" data-tip="Show relations history" class="icon-hourglass-1"></button>
        <button id="diplomacyShowMatrix" data-tip="Show relations matrix" class="icon-list-bullet"></button>
        <button
          id="diplomacyExport"
          data-tip="Save state relations matrix as a text file (.csv)"
          class="icon-download"
        ></button>
      </div>
  </div>`;a(`dialogs`).insertAdjacentHTML(`beforeend`,e),v(T,A.reset),y(T,({cellId:e})=>pack.cells.state[e]),S({dialogId:T,columns:k,onUpdate:()=>h(T,{width:`fit-content`,position:D})}),a(`diplomacyEditorRefresh`).addEventListener(`click`,P),a(`diplomacyEditStyle`).addEventListener(`click`,()=>editStyle(`regions`)),a(`diplomacyRegenerate`).addEventListener(`click`,U),a(`diplomacyReset`).addEventListener(`click`,W),a(`diplomacyShowMatrix`).addEventListener(`click`,q),a(`diplomacyHistory`).addEventListener(`click`,G),a(`diplomacyExport`).addEventListener(`click`,X),a(`diplomacyBodySection`).addEventListener(`click`,e=>{let t=e.target,n=t.closest(`.states`);if(!(!n||n.classList.contains(`Self`))){if(t.closest(`.changeRelations`)){let e=+n.dataset.id,t=+a(`diplomacyBodySection`).querySelector(`div.Self`).dataset.id,r=n.dataset.relations;B(e,t,r);return}O=+n.dataset.id,P()}})}function P(){A.reset(),R()}function F(e){let t=a(`diplomacyBodySection`),n=pack.states,r=O,i=n[r].name;l.trigger(`stateCOA${r}`,n[r].coa);let o=`<div class="states Self" data-id=${r} data-tip="List below shows relations to ${i}">
    <div data-col="name"><svg class="coaIcon" viewBox="0 0 200 200"><use href="#stateCOA${r}"></use></svg><span>${n[r].fullName}</span></div>
    <div data-col="relations"></div>
  </div>`;for(let t of e.rows){let e=t.diplomacy?.[r]??`x`,n=Object.hasOwn(w,e)?e:`Invalid`,{color:a,inText:s}=w[n]??{color:`#a9a9a9`,inText:`has an invalid relation to`},c=`${t.name} ${s} ${i}`,u=`${c}. Click to see relations to ${t.name}`,d=`Click to change relations. ${c}`,f=t.fullName.length<23?t.fullName:t.name;l.trigger(`stateCOA${t.i}`,t.coa),o+=`<div class="states" data-id=${t.i} data-name="${f}" data-relations="${n}">
      <div data-col="name" data-tip="${u}"><svg class="coaIcon" viewBox="0 0 200 200"><use href="#stateCOA${t.i}"></use></svg><span>${f}</span></div>
      <div data-col="relations" data-tip="${d}" class="changeRelations">
        <fill-box fill="${a}" size=".9em"></fill-box>
        ${n}
      </div>
    </div>`}t.innerHTML=o,t.querySelectorAll(`div.states`).forEach(e=>{e.addEventListener(`mouseenter`,I)}),t.querySelectorAll(`div.states`).forEach(e=>{e.addEventListener(`mouseleave`,L)}),a(`diplomacyFooterStates`).textContent=String(e.all.length+1),b(a(`diplomacyFooter`),e,A.goto),h(T,{width:`fit-content`,position:D})}function I(e){if(!u.isOn(`states`))return;let t=+e.target.dataset.id;if(customization||!t)return;let n=i(`#regions`).select(`#state${t}`).attr(`d`),a=i(`#debug`).append(`path`).attr(`class`,`highlight`).attr(`d`,n).attr(`fill`,`none`).attr(`stroke`,`red`).attr(`stroke-width`,1).attr(`opacity`,1).attr(`filter`,`url(#blur1)`),o=a.node().getTotalLength(),s=(o+5e3)/2,c=r(`0,${o}`,`${o},${o}`);a.transition().duration(s).attrTween(`stroke-dasharray`,()=>e=>c(e))}function L(){i(`#debug`).selectAll(`.highlight`).each(function(){i(this).transition().duration(1e3).attr(`opacity`,0).remove()})}function R(){let e=a(`diplomacyBodySection`).querySelector(`div.Self`),t=e?+e.dataset.id:pack.states.find(e=>e.i&&!e.removed).i;t&&(u.show(`states`),i(`#statesBody`).selectAll(`path`).each(function(){if(this.id.slice(0,9)===`state-gap`)return;let e=+this.id.slice(5),n=w[pack.states[e].diplomacy?.[t]??`x`]?.color||`#4682b4`;this.setAttribute(`fill`,n),i(`#statesBody`).select(`#state-gap${e}`).attr(`stroke`,n),i(`#statesHalo`).select(`#state-border${e}`).attr(`stroke`,o(n).darker().hex())}))}function z(e){let n=t(e,this),r=Pack.findCell(n[0],n[1]),i=pack.cells.state[r];!i||!pack.states[i]||pack.states[i].removed||O===i||(O=i,P())}function B(n,r,o){V();let s=pack.states,c=s[n],l=Object.entries(w).map(([e,{color:t,inText:n,tip:r}])=>`
        <div data-tip="${r}">
          <label class="pointer">
            <input type="radio" name="relationSelect" value="${e}"
            ${o===e?`checked`:``} >
            <fill-box fill="${t}" size=".8em"></fill-box>
            ${n}
        </label>
        </div>
      `).join(``),u=s.filter(e=>e.i&&!e.removed&&e.i!==n).map(e=>`
        <div data-tip="${e.fullName}">
          <input id="selectState${e.i}" class="checkbox" type="checkbox" name="objectSelect" value="${e.i}"
          ${e.i===r?`checked`:``} />
          <label for="selectState${e.i}" class="checkbox-label">
            <svg class="coaIcon" viewBox="0 0 200 200">
              <use href="#stateCOA${e.i}"></use>
            </svg>
            ${e.fullName}
          </label>
        </div>
      `).join(``),f=document.createElement(`div`);f.id=E,f.className=`dialog`,f.innerHTML=`
    <form id='relationsForm' style="overflow: hidden; display: flex; flex-direction: column; gap: .3em; padding: 0.1em 0;">
      <header>
        <svg class="coaIcon" viewBox="0 0 200 200">
          <use href="#stateCOA${c.i}"></use>
        </svg>
        <b>${c.fullName}</b>
      </header>

      <div class="info-line">Choose a relation, then select target states in the list or click them on the map. Apply to save.</div>
      <main style='display: flex; gap: 1em;'>
        <section style="display: flex; flex-direction: column; gap: .3em;">${l}</section>
        <section style="display: flex; flex-direction: column; gap: .3em;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3em;">
            <label style="font-weight: 500; font-size: 0.95em;">States:</label>
            <button id="selectAllNoneBtn" type="button" style="padding: 0.3em 0.8em; cursor: pointer; font-size: 0.9em;" data-tip="Toggle selection of all states.">Select All / None</button>
          </div>
          <div id="stateSelectionContainer" style="display: flex; flex-direction: column; gap: .3em;">${u}</div>
        </section>
      </main>
    </form>
  `,a(`dialogs`).appendChild(f);let p=i(`#viewbox`),m=p.on(`click`);p.on(`click`,function(e){let[r,i]=t(e,this),a=Pack.findCell(r,i);if(a===void 0)return;let o=pack.cells.state[a];if(!o||o===n||!pack.states[o]||pack.states[o].removed)return;let s=f.querySelector(`#selectState${o}`);s&&(s.checked=!s.checked,v())}),$(f).dialog({width:`fit-content`,title:`Change relations`,close:()=>{m?p.on(`click`,m):p.on(`click`,null),g(E)},buttons:{Apply:function(){let t=new FormData(a(`relationsForm`)),r=t.get(`relationSelect`);if(typeof r!=`string`||!Object.hasOwn(w,r)){d(`Please choose a relation`,!1,`warn`);return}let i=[...t.getAll(`objectSelect`)].map(Number);for(let e of i)H(n,e,r);P(),e(`diplomacyMatrix`)&&q(),$(this).dialog(`close`)},Cancel:function(){$(this).dialog(`close`)}}});let h=a(`selectAllNoneBtn`),_=()=>document.querySelectorAll(`#stateSelectionContainer input[name='objectSelect']`);function v(){let e=_();Array.from(e).every(e=>e.checked)&&e.length>0?h.classList.add(`pressed`):h.classList.remove(`pressed`)}function y(){let e=_(),t=!Array.from(e).every(e=>e.checked);e.forEach(e=>{e.checked=t}),v()}h.addEventListener(`click`,e=>{e.preventDefault(),y()}),f.addEventListener(`change`,v),v()}function V(){e(E)&&$(`#${E}`).dialog(`close`)}function H(e,t,n){let r=pack.states;if(!t||e===t||!r[t]||r[t].removed)return;let i=r[e].diplomacy?.[t],a=n===`Vassal`?`Suzerain`:n===`Suzerain`?`Vassal`:n;if(n===i&&r[t].diplomacy?.[e]===a)return;let o=j(),c=r[e].name,l=r[t].name;r[e].diplomacy??=[],r[t].diplomacy??=[],r[e].diplomacy[t]=n,r[t].diplomacy[e]=a;let u=()=>[`Relations change`,`${c}-${s(l)} relations changed to ${n.toLowerCase()}`],d=()=>[`Defence pact`,`${c} entered into defensive pact with ${l}`],f=()=>[`Vassalization`,`${c} became a vassal of ${l}`],p=()=>[`Vassalization`,`${c} vassalized ${l}`],m=()=>[`Rivalization`,`${c} and ${l} became rivals`],h=()=>[`Relations severance`,`${c} recalled their ambassadors and wiped all the records about ${l}`];i===`Enemy`?o.push([`War termination`,`${c} and ${l} agreed to cease fire and signed a peace treaty`,(n===`Ally`?d():n===`Vassal`?f():n===`Suzerain`?p():n===`Unknown`?h():u())[1]]):n===`Enemy`?o.push([`War declaration`,`${c} declared a war on its enemy ${l}`]):n===`Vassal`?o.push(f()):n===`Suzerain`?o.push(p()):n===`Ally`?o.push(d()):n===`Unknown`?o.push(h()):n===`Rival`?o.push(m()):o.push(u())}function U(){States.generateDiplomacy(),P()}function W(){let t=+a(`diplomacyBodySection`).querySelector(`div.Self`).dataset.id;if(!t)return;let n=pack.states;for(let e of n)!e.i||e.i===t||e.removed||(n[t].diplomacy??=[],e.diplomacy??=[],n[t].diplomacy[e.i]=`Neutral`,e.diplomacy[t]=`Neutral`);P(),e(`diplomacyMatrix`)&&q()}function G(){let e=j(),t=`<div autocorrect="off" spellcheck="false">`;e.forEach((e,n)=>{t+=`<div>`,e.forEach((e,r)=>{t+=`<div contenteditable="true" data-id="${n}-${r}"
        ${r?``:`style='font-weight:bold'`}>${e}</div>`}),t+=`&#8205;</div>`}),e.length||(pack.states[0].diplomacy=[[]],t+=`<div><div contenteditable="true" data-id="0-0">No historical records</div>&#8205;</div>`),alertMessage.innerHTML=`${t}</div><div class="info-line">Type to edit. Press Enter to add a new line, empty the element to remove it</div>`,alertMessage.querySelectorAll(`div[contenteditable='true']`).forEach(e=>{e.addEventListener(`input`,K)}),$(`#alert`).dialog({title:`Relations history`,position:{my:`center`,at:`center`,of:`svg`},buttons:{Save:function(){n(this.querySelector(`div`).innerText.split(`
`).join(`\r
`),`${c(`Relations history`)}.txt`)},Clear:function(){pack.states[0].diplomacy=[],$(this).dialog(`close`)},Close:function(){$(this).dialog(`close`)}}})}function K(){let e=this.dataset.id.split(`-`),t=j()[+e[0]];this.innerHTML===``?(t.splice(+e[1],1),this.remove()):t[+e[1]]=this.innerHTML}function q(){J();let e=pack.states.filter(e=>e.i&&!e.removed),t=a(`diplomacyMatrixBody`),n=`<table><thead><tr><th data-tip='&#8205;'></th>`;n+=`${e.map(e=>`<th data-tip='Relations to ${e.fullName}'>${e.name}</th>`).join(``)}</tr>`,n+=`<tbody>`,e.forEach(t=>{n+=`<tr data-id=${t.i}><th data-tip='Relations of ${t.fullName}'>${t.name}</th>${e.map(e=>{if(t.i===e.i)return`<td class="x">x</td>`;let n=t.diplomacy?.[e.i]??`x`;if(!Object.hasOwn(w,n))return`<td data-id=${e.i} data-tip="Invalid relation. Click to choose a replacement" class="Unknown">Invalid</td>`;let r=`${t.fullName} ${w[n].inText} ${e.fullName}`;return`<td data-id=${e.i} data-tip='${r}' class='${n}'>${n}</td>`}).join(``)}</tr>`}),n+=`</tbody></table>`,t.innerHTML=n,t.querySelector(`table`).addEventListener(`click`,e=>{let t=e.target;if(t.tagName!==`TD`||!t.dataset.id)return;let n=t.textContent??``;B(+t.closest(`tr`).dataset.id,+t.dataset.id,n)}),$(`#diplomacyMatrix`).dialog({title:`Relations matrix`,position:{my:`center`,at:`center`,of:`svg`},close:Y,buttons:{}})}function J(){g(`diplomacyMatrix`),a(`dialogs`).insertAdjacentHTML(`beforeend`,`<div id="diplomacyMatrix" class="dialog">
      <div id="diplomacyMatrixBody" class="matrix-table"></div>
    </div>`)}function Y(){$(`#diplomacyMatrix`).dialog(`destroy`),a(`diplomacyMatrix`).remove()}function X(){let e=pack.states.filter(e=>e.i&&!e.removed),t=e.map(e=>e.i),r=`,${e.map(e=>e.name).join(`,`)}\n`;e.forEach(e=>{let n=e.diplomacy.filter((e,n)=>t.includes(n));r+=`${e.name},${n.join(`,`)}\n`});let i=`${c(`Relations`)}.csv`;n(r,i)}function Z(){V(),p(),f();let e=a(`diplomacyBodySection`).querySelector(`div.Self`);e&&e.classList.remove(`Self`),u.show(`states`),i(`#debug`).selectAll(`.highlight`).remove(),$(`#${T}`).dialog(`destroy`),a(T).remove()}var Q={open:M,showHistory:G,exportCsv:X};export{Q as DiplomacyEditor};