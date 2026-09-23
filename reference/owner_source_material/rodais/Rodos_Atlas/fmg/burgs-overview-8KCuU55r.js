import{Bn as e,L as t,R as n,U as r,X as i,Y as a,_ as o,f as s,h as c,hn as l,j as u,n as d,z as f}from"./utils-Cob8vHf9.js";import{J as p,t as m}from"./layers-Bh4OWBXX.js";import{t as h}from"./stratify-CGdiYggi.js";import{t as g}from"./pack-CyBKcrr4.js";import{i as _}from"./tooltips-BTSHGd98.js";import{t as v}from"./state-B2hBYDzv.js";import{t as y}from"./controllers-DnVd8NhQ.js";import{ct as b,d as x,dt as S,lt as C,st as ee,u as w}from"./index-DsIn6sTp.js";import{t as T}from"./highlighting-BxkDyRR_.js";import{a as E,i as D,n as O,r as k}from"./table-B6G2rlSI.js";var A=`burgsOverview`,j={my:`right top`,at:`right-10 top+10`,of:`svg`,collision:`fit`},M,N=null,P=[{key:`locate`,width:`0.8em`,permanent:!0},{key:`name`,label:`Burg`,width:`8em`,permanent:!0,sortBy:e=>e.name||``,sortType:`alpha`},{key:`province`,label:`Province`,width:`8em`,hidden:!0,mobileHidden:!0,sortType:`alpha`,sortBy:e=>{let t=pack.cells.province[e.cell];return t&&pack.provinces[t]?.name||``}},{key:`state`,label:`State`,width:`8em`,sortBy:e=>pack.states[e.state]?.name||``,sortType:`alpha`},{key:`culture`,label:`Culture`,width:`10em`,mobileHidden:!0,sortBy:e=>pack.cultures[e.culture]?.name||``,sortType:`alpha`},{key:`group`,label:`Group`,width:`6em`,mobileHidden:!0,sortBy:e=>e.group||``,sortType:`alpha`},{key:`population`,label:`Population`,width:`7em`,defaultSort:`desc`,sortBy:e=>e.population*options.map.units.population.scale*options.map.units.population.urbanization.rate},{key:`grossproduct`,label:`Product`,width:`6.5em`,hidden:!0,mobileHidden:!0,sortBy:t=>e(t.product||0,2)},{key:`productpercapita`,label:`Wealth`,width:`6.5em`,mobileHidden:!0,tip:`Click to sort by burg wealth (gross product per capita)`,sortBy:t=>e(t.population>0?(t.product||0)/t.population:0,2)},{key:`treasury`,label:`Treasury`,width:`6.5em`,mobileHidden:!0,sortBy:t=>e(t.treasury||0,2)},{key:`features`,label:`Features`,width:`6em`,mobileHidden:!0,sortType:`alpha`,sortBy:e=>e.capital&&e.port?`a-capital-port`:e.capital?`c-capital`:e.port?`p-port`:`z-burg`},{key:`edit`,width:`1.1em`},{key:`lock`,width:`1.1em`},{key:`remove`,width:`1.4em`,permanent:!0}],F=k({getData:()=>x(A,H(),P),onUpdate:U});function I(e={}){customization||(M=v.get(A,`filters`,()=>({search:``,stateId:-1,cultureId:-1})),ee(`#${A}, .stable`),m.show(`burgIcons`,`labels`),e.stateId!=null&&(M.stateId=e.stateId),e.cultureId!=null&&(M.cultureId=e.cultureId),L(),B(),oe(),F.reset(),$(`#${A}`).dialog({title:`Burgs Overview`,resizable:!1,close:R,width:`fit-content`,position:j}))}function L(){C(`burgsOverview`);let e=`<div id="burgsOverview" class="dialog stable editorDialog">
      <div id="burgsBody" class="table">${D({dialogId:A,columns:P})}</div>
      <div id="burgsFilters" data-tip="Apply a filter" class="editorFilters">
        <label for="burgsSearch" data-tip="Filter by name, province, state, culture, or group"
          >Search: <input id="burgsSearch" type="search"
        /></label>
        <label for="burgsFilterState"
          >State:
          <select id="burgsFilterState"></select
        ></label>
        <label for="burgsFilterCulture"
          >Culture:
          <select id="burgsFilterCulture"></select
        ></label>
      </div>
      <div id="burgsFooter" class="totalLine">
        <div data-tip="Burgs displayed" style="margin-left: 5px">
          Burgs:&nbsp;<span id="burgsFooterBurgs">0 of 0</span>
        </div>
        <div data-tip="Average population" style="margin-left: 12px" data-col="population">
          Avg population:&nbsp;<span id="burgsFooterPopulation">0</span>
        </div>
        <div data-tip="Average gross product" style="margin-left: 12px" data-col="grossproduct">
          Avg product:&nbsp;<span id="burgsFooterGrossProduct">0</span> 🟡
        </div>
        <div data-tip="Average wealth (product per capita)" style="margin-left: 12px" data-col="productpercapita">
          Avg wealth:&nbsp;<span id="burgsFooterProductPerCapita">0</span> 🟡
        </div>
        <div data-tip="Average treasury" style="margin-left: 12px" data-col="treasury">
          Avg treasury:&nbsp;<span id="burgsFooterTreasury">0</span> 🟡
        </div>
      </div>
      <div id="burgsBottom" class="editorToolbar">
        <button id="burgsOverviewRefresh" data-tip="Refresh the Editor" class="icon-cw"></button>
        <button id="burgsGroupsEditorButton" data-tip="Edit burg groups" class="icon-cog"></button>
        <button id="burgsChart" data-tip="Show burgs bubble chart" class="icon-chart-area"></button>
        <button
          id="regenerateBurgNames"
          data-tip="Regenerate burg names based on assigned culture"
          class="icon-retweet"
        ></button>
        <button id="addNewBurg" data-tip="Add a new burg. Hold Shift to add multiple" class="icon-plus"></button>
        <button
          id="burgsExport"
          data-tip="Save burgs-related data as a text file (.csv)"
          class="icon-download"
        ></button>
        <button id="burgNamesImport" data-tip="Rename burgs in bulk" class="icon-upload"></button>
        <button id="burgsLockAll" data-tip="Lock or unlock all burgs" class="icon-lock"></button>
        <button
          id="burgsRemoveAll"
          data-tip="Remove all unlocked burgs except for capitals. To remove a capital remove its state first"
          class="icon-trash"
        ></button>
      </div>
    </div>`;u(`dialogs`).insertAdjacentHTML(`beforeend`,e),u(`burgsSearch`).value=M.search,w(A,F.reset),T(A,({target:e,cellId:t})=>{let n=pack.cells.burg[t];if(n)return n;let r=e.closest(`#labels [data-label-type='burg'][data-id], #burgIcons [data-id]`);return r?Number(r.dataset.id):void 0}),O({dialogId:A,columns:P,onUpdate:()=>S(A,{width:`fit-content`,position:j})}),u(`burgsOverviewRefresh`).addEventListener(`click`,z),u(`burgsGroupsEditorButton`).addEventListener(`click`,()=>y.BurgGroupEditor.open()),u(`burgsChart`).addEventListener(`click`,Z),u(`burgsFilterState`).addEventListener(`change`,V),u(`burgsFilterCulture`).addEventListener(`change`,V),u(`burgsSearch`).addEventListener(`input`,V),u(`regenerateBurgNames`).addEventListener(`click`,X),u(`addNewBurg`).addEventListener(`click`,()=>void y.BurgCreator.toggle()),u(`burgsExport`).addEventListener(`click`,Q),u(`burgNamesImport`).addEventListener(`click`,te),u(`burgsLockAll`).addEventListener(`click`,ae),u(`burgsRemoveAll`).addEventListener(`click`,ie)}function R(){document.getElementById(`addBurgTool`)?.classList.contains(`pressed`)&&y.BurgCreator.stop(),$(`#burgsOverview`).dialog(`destroy`),u(`burgsOverview`).remove()}function z(){B(),F.reset()}function B(){let e=u(`burgsFilterState`);new Set(pack.states.filter(e=>!e.removed).map(e=>e.i)).has(M.stateId)||(M.stateId=-1),e.options.length=0,e.options.add(new Option(`all`,`-1`,!1,M.stateId===-1)),e.options.add(new Option(pack.states[0].name,`0`,!1,M.stateId===0)),pack.states.filter(e=>e.i&&!e.removed).sort((e,t)=>e.name>t.name?1:-1).forEach(t=>void e.options.add(new Option(t.name,String(t.i),!1,t.i===M.stateId)));let t=u(`burgsFilterCulture`);new Set(pack.cultures.filter(e=>!e.removed).map(e=>e.i)).has(M.cultureId)||(M.cultureId=-1),t.options.length=0,t.options.add(new Option(`all`,`-1`,!1,M.cultureId===-1)),t.options.add(new Option(pack.cultures[0].name,`0`,!1,M.cultureId===0)),pack.cultures.filter(e=>e.i&&!e.removed).sort((e,t)=>e.name>t.name?1:-1).forEach(e=>void t.options.add(new Option(e.name,String(e.i),!1,e.i===M.cultureId))),v.set(A,`filters`,M)}function V(){M.search=u(`burgsSearch`).value,M.stateId=+u(`burgsFilterState`).value,M.cultureId=+u(`burgsFilterCulture`).value,v.set(A,`filters`,M),F.reset()}function H(){let e=M.search.toLowerCase().trim(),t=pack.burgs.filter(e=>e.i&&!e.removed);return e&&(t=t.filter(t=>{let n=t.name.toLowerCase(),r=(pack.states[t.state]?.name||``).toLowerCase(),i=pack.cells.province[t.cell],a=i?pack.provinces[i]?.name.toLowerCase():``,o=(pack.cultures[t.culture]?.name||``).toLowerCase();return n.includes(e)||r.includes(e)||a.includes(e)||o.includes(e)||t.group.toLowerCase().includes(e)})),M.stateId!==-1&&(t=t.filter(e=>e.state===M.stateId)),M.cultureId!==-1&&(t=t.filter(e=>e.culture===M.cultureId)),t}function U(t){let n=u(`burgsBody`),r=pack.burgs.filter(e=>e.i&&!e.removed).length;n.querySelectorAll(`:scope > .states`).forEach(e=>{e.remove()});let i=``,a=0,s=0,c=0,l=0;for(let n of t.all){let t=n.population*options.map.units.population.scale*options.map.units.population.urbanization.rate,r=e(n.product||0,2),i=e(n.population>0?(n.product||0)/n.population:0,2),o=e(n.treasury||0,2);a+=t,s+=r,c+=i,l+=o}for(let n of t.rows){let t=n.population*options.map.units.population.scale*options.map.units.population.urbanization.rate,r=e(n.product||0,2),a=e(n.population>0?(n.product||0)/n.population:0,2),s=e(n.treasury||0,2),c=n.capital&&n.port?`a-capital-port`:n.capital?`c-capital`:n.port?`p-port`:`z-burg`,l=pack.states[n.state].name,u=pack.cells.province[n.cell],d=u?pack.provinces[u].name:``,f=pack.cultures[n.culture].name;i+=`<div
        class="states"
        data-id=${n.i}
        data-name="${n.name}"
        data-state="${l}"
        data-province="${d}"
        data-culture="${f}"
        data-group="${n.group}"
        data-population=${t}
        data-grossproduct=${r}
        data-productpercapita=${a}
        data-treasury=${s}
        data-features="${c}"
      >
        <span data-tip="Click to zoom into view" class="icon-dot-circled pointer" data-col="locate"></span>
        <input data-tip="Burg name" class="burgName" value="${n.name}" data-col="name" disabled />
        <input data-tip="Burg province" value="${d}" data-col="province" disabled />
        <input data-tip="Burg state" value="${l}" data-col="state" disabled />
        <input data-tip="Dominant culture" value="${f}" data-col="culture" disabled />
        <input data-tip="Burg group" value="${n.group}" data-col="group" disabled />
        <div data-col="population">
          <span data-tip="Burg population" class="icon-male"></span>
          <input data-tip="Burg population" value=${o(t)} disabled />
        </div>
        <div data-col="grossproduct">
          <span data-tip="Gross Product: local sale revenue minus purchased ingredient costs during the production.">🟡</span>
          <input data-tip="Gross Product: local sale revenue minus purchased ingredient costs during the production." value=${r} disabled />
        </div>
        <div data-col="productpercapita">
          <span data-tip="Wealth: gross product divided by population">🟡</span>
          <input data-tip="Wealth: gross product divided by population" value=${a} disabled />
        </div>
        <div data-col="treasury">
          <span data-tip="Treasury: accumulated cash balance">🟡</span>
          <input data-tip="Treasury: accumulated cash balance" value=${s} disabled />
        </div>
        <div data-col="features">
          <span
            data-tip="${n.capital?` This burg is a state capital`:`This burg is a NOT state capital`}"
            class="icon-star-empty${n.capital?``:` inactive`}" style="padding: 0 1px;"></span>
          <span data-tip="${n.port?` This burg is a port`:`This burg is NOT a port`}"
          class="icon-anchor${n.port?``:` inactive`}" style="font-size: .9em; padding: 0 1px;"></span>
        </div>
        <span data-col="edit" data-tip="Edit burg" class="icon-pencil"></span>
        <span data-col="lock" class="locks pointer ${n.lock?`icon-lock`:`icon-lock-open inactive`}" onmouseover="showElementLockTip(event)"></span>
        <span data-col="remove" data-tip="Remove burg" class="icon-trash-empty"></span>
      </div>`}n.insertAdjacentHTML(`beforeend`,i),u(`burgsFooterBurgs`).innerHTML=`${t.all.length} of ${r}`,u(`burgsFooterPopulation`).innerHTML=t.all.length?o(a/t.all.length):`0`,u(`burgsFooterGrossProduct`).innerHTML=t.all.length?String(e(s/t.all.length,2)):`0`,u(`burgsFooterProductPerCapita`).innerHTML=t.all.length?String(e(c/t.all.length,2)):`0`,u(`burgsFooterTreasury`).innerHTML=t.all.length?String(e(l/t.all.length,2)):`0`,E(u(`burgsFooter`),t,F.goto),n.querySelectorAll(`div.states`).forEach(e=>void e.addEventListener(`mouseenter`,e=>W(e))),n.querySelectorAll(`div.states`).forEach(e=>void e.addEventListener(`mouseleave`,()=>G())),n.querySelectorAll(`div > span.icon-dot-circled`).forEach(e=>void e.addEventListener(`click`,K)),n.querySelectorAll(`div > span.locks`).forEach(e=>void e.addEventListener(`click`,q)),n.querySelectorAll(`div > span.icon-pencil`).forEach(e=>void e.addEventListener(`click`,J)),n.querySelectorAll(`div > span.icon-trash-empty`).forEach(e=>void e.addEventListener(`click`,Y))}function W(e){let t=+e.target.dataset.id,n=l(`#labels`).select(`[data-label-type='burg'][data-id='${t}']`);n.size()&&n.classed(`drag`,!0)}function G(){l(`#labels`).selectAll(`text[data-label-type='burg'].drag`).classed(`drag`,!1)}function K(){let e=+this.closest(`.states`).dataset.id,{x:t,y:n}=pack.burgs[e];zoomTo(t,n,8,2e3)}function q(){let e=+this.closest(`.states`).dataset.id,t=pack.burgs[e];t.lock=!t.lock,this.classList.contains(`icon-lock`)?(this.classList.remove(`icon-lock`),this.classList.add(`icon-lock-open`),this.classList.add(`inactive`)):(this.classList.remove(`icon-lock-open`),this.classList.add(`icon-lock`),this.classList.remove(`inactive`))}function J(){let e=+this.closest(`.states`).dataset.id;y.BurgEditor.open(e)}function Y(){let e=+this.closest(`.states`).dataset.id;if(pack.burgs[e].capital){_(`You cannot remove the capital. Please change the state capital first`,!1,`error`);return}b({title:`Remove burg`,message:`Are you sure you want to remove the burg? <br>This action cannot be reverted`,confirm:`Remove`,onConfirm:()=>{Burgs.remove(e),p(`burg`,e),F.refresh(),m.draw(`burgIcons`,`labels`)}})}function X(){for(let e of H())e.lock||(e.name=Names.getCulture(e.culture));F.refresh(),m.draw(`labels`)}function Z(){let e=pack.states.map(e=>{let t=e.color?e.color:`#ccc`,n=e.fullName?e.fullName:e.name;return{id:e.i,state:e.i?0:null,color:t,name:n}}),t=pack.burgs.filter(e=>e.i&&!e.removed).map(t=>{let n=t.i+e.length-1,r=t.population,i=t.capital,a=pack.cells.province[t.cell],o=a?a+e.length-1:t.state;return{id:n,i:t.i,state:t.state,culture:t.culture,province:a,parent:o,name:t.name,population:r,capital:i,x:t.x,y:t.y}}),n=e.concat(t);if(n.length<2){_(`No burgs to show`,!1,`error`);return}let r=h().parentId(e=>e.state)(n).sum(e=>e.population).sort((e,t)=>t.value-e.value),i=u(`uiSize`).valueAsNumber,a=150+200*i,s=150+200*i,c={top:0,right:-50,bottom:-10,left:-50},d=a-c.left-c.right,f=s-c.top-c.bottom,p=g().size([d,f]).padding(3);alertMessage.innerHTML=`<select id="burgsTreeType" style="display:block; margin-left:13px; font-size:11px">
      <option value="states" selected>Group by state</option>
      <option value="cultures">Group by culture</option>
      <option value="parent">Group by province and state</option>
      <option value="provinces">Group by province</option>
    </select>`,alertMessage.innerHTML+=`<div id='burgsInfo' class='chartInfo'>&#8205;</div>`;let m=l(`#alertMessage`).insert(`svg`,`#burgsInfo`).attr(`id`,`burgsTree`).attr(`width`,a).attr(`height`,s-10).attr(`stroke-width`,2).append(`g`).attr(`transform`,`translate(-50, -10)`);u(`burgsTreeType`).addEventListener(`change`,x),p(r);let v=m.selectAll(`circle`).data(r.leaves()).join(`circle`).attr(`data-id`,e=>e.data.i).attr(`r`,e=>e.r).attr(`fill`,e=>e.parent.data.color).attr(`cx`,e=>e.x).attr(`cy`,e=>e.y).on(`mouseenter`,(e,t)=>y(e,t)).on(`mouseleave`,e=>b(e)).on(`click`,(e,t)=>zoomTo(t.data.x,t.data.y,8,2e3));function y(e,t){l(e.target).transition().duration(1500).attr(`stroke`,`#c13119`);let n=t.data.name,r=t.parent.data.name,i=o(t.value*options.map.units.population.scale*options.map.units.population.urbanization.rate);u(`burgsInfo`).innerHTML=`${n}. ${r}. Population: ${i}`,W(e),_(`Click to zoom into view`)}function b(e){G(),u(`burgsInfo`)&&(u(`burgsInfo`).innerHTML=`&#8205;`,l(e.target).transition().attr(`stroke`,null),_(``))}function x(){let e=()=>pack.states.map(e=>{let t=e.color?e.color:`#ccc`,n=e.fullName?e.fullName:e.name;return{id:e.i,state:e.i?0:null,color:t,name:n}}),n=()=>pack.cultures.map(e=>{let t=e.color?e.color:`#ccc`;return{id:e.i,culture:e.i?0:null,color:t,name:e.name}}),r=()=>{let e=pack.states.map(e=>{let t=e.color?e.color:`#ccc`,n=e.fullName?e.fullName:e.name;return{id:e.i,parent:e.i?0:null,color:t,name:n}}),t=pack.provinces.filter(e=>e.i&&!e.removed).map(t=>({id:t.i+e.length-1,parent:t.state,color:t.color,name:t.fullName}));return e.concat(t)},i=()=>pack.provinces.map(e=>{let t=e.color?e.color:`#ccc`,n=e.fullName?e.fullName:e.name;return{id:e.i?e.i:0,province:e.i?0:null,color:t,name:n}}),a=e=>{if(this.value===`states`)return e.state;if(this.value===`cultures`)return e.culture;if(this.value===`parent`)return e.parent;if(this.value===`provinces`)return e.province},o={states:e,cultures:n,parent:r,provinces:i}[this.value]();t.forEach(e=>{e.id=e.i+o.length-1});let s=o.concat(t),c=h().parentId(e=>a(e))(s).sum(e=>e.population).sort((e,t)=>t.value-e.value);v.data(p(c).leaves()).transition().duration(2e3).attr(`data-id`,e=>e.data.i).attr(`fill`,e=>e.parent.data.color).attr(`cx`,e=>e.x).attr(`cy`,e=>e.y).attr(`r`,e=>e.r)}$(`#alert`).dialog({title:`Burgs bubble chart`,width:`fit-content`,position:{my:`left bottom`,at:`left+10 bottom-10`,of:`svg`},buttons:{},close:()=>alertMessage.innerHTML=``})}function Q(){let t=`Id,Burg,Province,Province Full Name,State,State Full Name,Culture,Religion,Group,Population,X,Y,Latitude,Longitude,Elevation (${options.map.units.height.unit}),Temperature,Temperature likeness,Capital,Port,Citadel,Walls,Plaza,Temple,Shanty Town,Emblem,Preview link\n`;pack.burgs.filter(e=>e.i&&!e.removed).forEach(n=>{t+=`${n.i},`,t+=`${n.name},`;let r=pack.cells.province[n.cell];t+=r?`${pack.provinces[r].name},`:`,`,t+=r?`${pack.provinces[r].fullName},`:`,`,t+=`${pack.states[n.state].name},`,t+=`${pack.states[n.state].fullName},`,t+=`${pack.cultures[n.culture].name},`,t+=`${pack.religions[pack.cells.religion[n.cell]].name},`,t+=`${n.group},`,t+=`${e(n.population*options.map.units.population.scale*options.map.units.population.urbanization.rate)},`,t+=`${n.x},`,t+=`${n.y},`,t+=`${a(n.y,options.map.geography.coordinates,options.map.graph.height,2)},`,t+=`${i(n.x,options.map.geography.coordinates,options.map.graph.width,2)},`,t+=`${parseInt(s(pack.cells.h[n.cell]),10)},`;let o=grid.cells.temp[pack.cells.g[n.cell]];t+=`${d(o)},`,t+=`${c(o)},`,t+=n.capital?`capital,`:`,`,t+=n.port?`port,`:`,`,t+=n.citadel?`citadel,`:`,`,t+=n.walls?`walls,`:`,`,t+=n.plaza?`plaza,`:`,`,t+=n.temple?`temple,`:`,`,t+=n.shanty?`shanty town,`:`,`,t+=n.coa?`${JSON.stringify(n.coa).replace(/"/g,``).replace(/,/g,`;`)},`:`,`,t+=Burgs.getPreview(n).link,t+=`
`});let r=`${f(`Burgs`)}.csv`;n(t,r)}function te(){alertMessage.innerHTML=`Download burgs list as a text file, make changes and re-upload the file. Make sure the file is a plain text document with each
    name on its own line (the dilimiter is CRLF). If you do not want to change the name, just leave it as is`,$(`#alert`).dialog({title:`Burgs bulk renaming`,width:`22em`,position:{my:`center`,at:`center`,of:`svg`},buttons:{Download:()=>{n(pack.burgs.filter(e=>e.i&&!e.removed).map(e=>e.name).join(`\r
`),`${f(`Burg names`)}.txt`)},Upload:ne,Cancel:function(){$(this).dialog(`close`)}}})}function ne(){N??=t(`.txt,.csv`),N.onchange=()=>r(N,re),N.click()}function re(e){if(!e){_(`Cannot load the file, please check the format`,!1,`error`);return}let t=e.replace(/\r\n|\r/g,`
`).split(`
`).filter(Boolean);if(!t.length){_(`Cannot parse the list, please check the file format`,!1,`error`);return}let n=[],r=`Burgs to be renamed as below:`;r+=`<table class="overflow-table"><tr><th>Id</th><th>Current name</th><th>New Name</th></tr>`;let i=pack.burgs.filter(e=>e.i&&!e.removed);for(let e=0;e<t.length&&e<=i.length;e++){let a=t[e];!a||!i[e]||a===i[e].name||(n.push({id:i[e].i,name:a}),r+=`<tr><td style="width:20%">${i[e].i}</td><td style="width:40%">${i[e].name}</td><td style="width:40%">${a}</td></tr>`)}r+=`</tr></table>`,n.length||(r=`No changes found in the file. Please change some names to get a result`),alertMessage.innerHTML=r,b({title:`Burgs bulk renaming`,message:r,confirm:`Rename`,onConfirm:()=>{for(let e=0;e<n.length;e++){let t=n[e].id;pack.burgs[t].name=n[e].name}F.refresh(),m.draw(`labels`)}})}function ie(){let e=pack.burgs.filter(e=>e.i&&!e.removed&&!e.capital&&!e.lock).length;b({title:`Remove ${e} burgs`,message:`
        Are you sure you want to remove all <i>unlocked</i> burgs except for capitals?
        <br><i>To remove a capital you have to remove its state first</i>`,confirm:`Remove`,onConfirm:()=>{pack.burgs.filter(e=>e.i&&!(e.capital||e.lock)).forEach(e=>{Burgs.remove(e.i),p(`burg`,e.i)}),F.refresh(),m.draw(`burgIcons`,`labels`)}})}function ae(){let e=pack.burgs.filter(e=>e.i&&!e.removed),t=e.every(e=>e.lock);e.forEach(e=>{e.lock=!t}),F.refresh(),u(`burgsLockAll`).className=t?`icon-lock`:`icon-lock-open`}function oe(){let e=pack.burgs.every(({lock:e,i:t,removed:n})=>e||!t||n);u(`burgsLockAll`).className=e?`icon-lock-open`:`icon-lock`}var se={open:I,showChart:Z,exportCsv:Q};export{se as BurgsOverview};