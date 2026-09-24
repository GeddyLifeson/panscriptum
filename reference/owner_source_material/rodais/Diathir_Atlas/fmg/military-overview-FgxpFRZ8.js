import{B as e,Bn as t,Pn as n,R as r,Xt as i,_ as a,hn as o,it as s,j as c,kn as l,z as u}from"./utils-Cob8vHf9.js";import{t as d}from"./layers-Bh4OWBXX.js";import{i as f}from"./tooltips-BTSHGd98.js";import{t as p}from"./controllers-DnVd8NhQ.js";import{At as m,d as h,dt as g,lt as _,st as v,u as y}from"./index-DsIn6sTp.js";import{t as b}from"./highlighting-BxkDyRR_.js";import{a as x,i as S,n as C,r as w}from"./table-B6G2rlSI.js";var T=`militaryOverview`,E={my:`right top`,at:`right-10 top+10`,of:`svg`,collision:`fit`},D=[],O=w({getData:I,onUpdate:R});function k(){customization||(v(`#militaryOverview, .stable`),d.show(`states`,`borders`,`military`),A(),O.reset(),$(`#militaryOverview`).dialog({title:`Military Overview`,resizable:!1,width:`fit-content`,close:j,position:E}))}function A(){D=N(),_(`militaryOverview`);let e=`<div id="${T}" class="dialog stable editorDialog">
      <div id="militaryBody" class="table" data-type="absolute">
        ${S({dialogId:T,columns:D})}
      </div>
      <div id="militaryFooter" class="totalLine">
        <div data-tip="States number" style="margin-left: 4px">
          States:&nbsp;<span id="militaryFooterStates">0</span>
        </div>
        <div data-tip="Total military forces" style="margin-left: 14px" data-col="total">
          Total forces:&nbsp;<span id="militaryFooterForcesTotal">0</span>
        </div>
        <div data-tip="Average military forces per state" style="margin-left: 14px" data-col="total">
          Average forces:&nbsp;<span id="militaryFooterForces">0</span>
        </div>
        <div data-tip="Average forces rate per state" style="margin-left: 14px" data-col="rate">
          Average rate:&nbsp;<span id="militaryFooterRate">0%</span>
        </div>
        <div data-tip="Average War Alert" style="margin-left: 14px" data-col="alert">
          Average alert:&nbsp;<span id="militaryFooterAlert">0</span>
        </div>
      </div>
      <div id="militaryBottom" class="editorToolbar">
        <button id="militaryOverviewRefresh" data-tip="Refresh the overview screen" class="icon-cw"></button>
        <button id="militaryOptionsButton" data-tip="Edit Military units" class="icon-cog"></button>
        <button id="militaryRegimentsList" data-tip="Show regiments list" class="icon-list-bullet"></button>
        <button
          id="militaryPercentage"
          data-tip="Toggle percentage / absolute values views"
          class="icon-percent"
        ></button>
        <button
          id="militaryOverviewRecalculate"
          data-tip="Recalculate military forces based on current options"
          class="icon-retweet"
        ></button>
        <button
          id="militaryExport"
          data-tip="Save military-related data as a text file (.csv)"
          class="icon-download"
        ></button>
        <button id="militaryWiki" data-tip="Open Military Forces Tutorial" class="icon-info"></button>
      </div>
    </div>`;c(`dialogs`).insertAdjacentHTML(`beforeend`,e),P(),b(`militaryOverview`,({cellId:e})=>pack.cells.state[e]);let t=c(`militaryBody`);c(`militaryOverviewRefresh`).addEventListener(`click`,L),c(`militaryPercentage`).addEventListener(`click`,U),c(`militaryOptionsButton`).addEventListener(`click`,W),c(`militaryRegimentsList`).addEventListener(`click`,()=>M(-1)),c(`militaryOverviewRecalculate`).addEventListener(`click`,q),c(`militaryExport`).addEventListener(`click`,J),c(`militaryWiki`).addEventListener(`click`,()=>s(`Military-Forces`)),t.addEventListener(`change`,e=>{let t=e.target,n=t.closest(`.states`);n&&z(+n.dataset.id,+t.value)}),t.addEventListener(`click`,e=>{let t=e.target,n=t.closest(`.states`);if(!n)return;let r=+n.dataset.id;t.tagName===`SPAN`&&M(r)})}function j(){$(`#militaryOverview`).dialog(`destroy`),c(`militaryOverview`).remove()}async function M(e){p.RegimentsOverview.open(e)}function N(){return[{key:`color`,width:`1.2em`,permanent:!0},{key:`state`,label:`State`,width:`7em`,permanent:!0,sortBy:e=>e.state.name||``,sortType:`alpha`},...options.map.military.units.map(e=>({key:`unit:${e.name}`,label:l(e.name.replace(/_/g,` `)),width:`5em`,mobileHidden:!0,tip:`State ${e.name} units number. Click to sort`,sortBy:t=>t.forces[e.name]||0})),{key:`total`,label:`Total`,width:`5em`,defaultSort:`desc`,sortBy:e=>e.total,tip:`Total military personnel (considering crew). Click to sort`},{key:`population`,label:`Population`,width:`6.5em`,mobileHidden:!0,sortBy:e=>e.population},{key:`rate`,label:`Rate`,width:`5em`,sortBy:e=>e.rate,tip:`Military personnel rate (% of state population). Depends on war alert. Click to sort`},{key:`alert`,label:`War Alert`,width:`5.5em`,sortBy:e=>e.alert,tip:`War Alert. Modifier to military forces number, depends on political situation. Click to sort`},{key:`regiments`,width:`1.4em`,permanent:!0}]}function P(){y(T,O.reset),C({dialogId:T,columns:D,onUpdate:()=>g(T,{width:`fit-content`,position:E})})}function F(){D=N(),c(`${T}Header`).outerHTML=S({dialogId:T,columns:D}),P(),O.reset()}function I(){return h(T,pack.states.filter(e=>e.i&&!e.removed).map(e=>{let n=Object.fromEntries(options.map.military.units.map(t=>[t.name,(e.military||[]).reduce((e,n)=>e+(n.u[t.name]||0),0)])),r=t(((e.rural||0)+(e.urban||0)*options.map.units.population.urbanization.rate)*options.map.units.population.scale),i=options.map.military.units.reduce((e,t)=>e+(n[t.name]||0)*t.crew,0);return{state:e,forces:n,total:i,population:r,rate:r?i/r*100:0,alert:e.alert??0}}),D)}function L(){O.refresh()}function R(e){let n=c(`militaryBody`),r=n.dataset.type===`percentage`,i=e.all.reduce((e,t)=>{e.total+=t.total,e.population+=t.population;for(let n of options.map.military.units)e.units[n.name]=(e.units[n.name]||0)+t.forces[n.name];return e},{total:0,population:0,units:{}}),o=(e,n)=>`${t(n?e/n*100:0)}%`,s=e.rows.map(e=>{let n=options.map.military.units.map(t=>{let n=e.forces[t.name]||0;return`<div data-col="${`unit:${t.name}`}" data-tip="State ${t.name} units number">${r?o(n,i.units[t.name]||0):n}</div>`}).join(``);return`<div class="states" data-id="${e.state.i}">
        <fill-box data-col="color" data-tip="${e.state.fullName}" fill="${e.state.color}" disabled></fill-box>
        <input data-col="state" data-tip="${e.state.fullName}" value="${e.state.name}" readonly />
        ${n}
        <div data-col="total" data-tip="Total state military personnel (considering crew)" style="font-weight:bold">${r?o(e.total,i.total):a(e.total)}</div>
        <div data-col="population" data-tip="State population">${r?o(e.population,i.population):a(e.population)}</div>
        <div data-col="rate" data-tip="Military personnel rate (% of state population). Depends on war alert">${t(e.rate,2)}%</div>
        <input data-col="alert" data-tip="War Alert. Editable modifier to military forces number, depends on political situation" type="number" min="0" step=".01" value="${t(e.alert,2)}" />
        <span data-col="regiments" data-tip="Show regiments list" class="icon-list-bullet pointer"></span>
      </div>`}).join(``);n.querySelectorAll(`:scope > .states`).forEach(e=>{e.remove()}),n.insertAdjacentHTML(`beforeend`,s),B(e),x(c(`militaryFooter`),e,O.goto),n.querySelectorAll(`:scope > .states`).forEach(e=>{e.addEventListener(`mouseenter`,V),e.addEventListener(`mouseleave`,H)}),g(T,{width:`fit-content`,position:E})}function z(e,n){let r=pack.states[e],i=r.alert??1,a=i?n/i:0;r.alert=n,(r.military||[]).forEach(e=>{Object.keys(e.u).forEach(n=>{e.u[n]=t(e.u[n]*a)}),e.a=m(Object.values(e.u)),o(`#armies > g > g#regiment${r.i}-${e.i} > text`).text(Military.getTotal(e))}),O.refresh()}function B(e){let n=e.all.length,r=m(e.all.map(e=>e.total));c(`militaryFooterStates`).innerHTML=String(n),c(`militaryFooterForcesTotal`).innerHTML=a(r),c(`militaryFooterForces`).innerHTML=a(n?r/n:0),c(`militaryFooterRate`).innerHTML=`${t(n?m(e.all.map(e=>e.rate))/n:0,2)}%`,c(`militaryFooterAlert`).innerHTML=String(t(n?m(e.all.map(e=>e.alert))/n:0,2))}function V(e){let t=+e.target.dataset.id;if(customization||!t||(o(`#armies > g > g#army${t}`).transition().duration(2e3).style(`fill`,`#ff0000`),!d.isOn(`states`)))return;let n=o(`#regions`).select(`#state${t}`).attr(`d`),r=o(`#debug`).append(`path`).attr(`class`,`highlight`).attr(`d`,n).attr(`fill`,`none`).attr(`stroke`,`red`).attr(`stroke-width`,1).attr(`opacity`,1).attr(`filter`,`url(#blur1)`),a=r.node().getTotalLength(),s=(a+5e3)/2,c=i(`0,${a}`,`${a},${a}`);r.transition().duration(s).attrTween(`stroke-dasharray`,()=>e=>c(e))}function H(e){o(`#debug`).selectAll(`.highlight`).each(function(){o(this).transition().duration(1e3).attr(`opacity`,0).remove()}),o(`#armies > g > g#army${+e.target.dataset.id}`).transition().duration(1e3).style(`fill`,null)}function U(){let e=c(`militaryBody`);e.dataset.type=e.dataset.type===`absolute`?`percentage`:`absolute`,O.refresh()}function W(){G();let t=[`melee`,`ranged`,`mounted`,`machinery`,`naval`,`armored`,`aviation`,`magical`],r=c(`militaryOptions`).querySelector(`tbody`);i(),options.map.military.units.map(e=>l(e)),$(`#militaryOptions`).dialog({title:`Edit Military Units`,resizable:!1,width:`fit-content`,position:{my:`center`,at:`center`,of:`svg`},close:K,buttons:{Apply:g,Add:()=>l({icon:`🛡️`,name:`custom${c(`militaryOptionsTable`).rows.length}`,rural:.2,urban:.5,crew:1,power:1,type:`melee`,separate:0}),Restore:m,Cancel:function(){$(this).dialog(`close`)}},open:function(){let e=$(this).dialog(`widget`).find(`.ui-dialog-buttonset > button`);e[0].addEventListener(`mousemove`,()=>f(`Apply military units settings. <span style='color:#cb5858'>All forces will be recalculated!</span>`)),e[1].addEventListener(`mousemove`,()=>f(`Add new military unit to the table`)),e[2].addEventListener(`mousemove`,()=>f(`Restore default military units and settings`)),e[3].addEventListener(`mousemove`,()=>f(`Close the window without saving the changes`))}}),r.addEventListener(`click`,e=>{let t=e.target.closest(`button`);if(!t)return;let n=t.dataset.type;if(n===`icon`){p.IconSelector.open(t.dataset.icon||``,e=>u(t,e));return}if(n===`biomes`){h(t,pack.biomes.filter(e=>!e.removed).map(({i:e,name:t,color:n})=>({i:e,name:t,color:n})));return}if(n===`states`)return h(t,pack.states);if(n===`cultures`)return h(t,pack.cultures);if(n===`religions`)return h(t,pack.religions)});function i(){r.querySelectorAll(`tr`).forEach(e=>{e.remove()})}function a(e){return e?.join(`,`)||``}function o(e){return e?.length?`some`:`all`}function s(e,t){return e?.length?e.map(e=>t?.[e]?.name||``).join(`, `):``}function l(e){let{type:n,icon:i,name:c,rural:l,urban:d,power:f,crew:p,separate:m}=e,h=document.createElement(`tr`),g=t.map(e=>`<option ${n===e?`selected`:``} value="${e}">${e}</option>`).join(` `),_=t=>{let n=t===`biomes`?[]:pack[t];return`<button
          data-tip="Select allowed ${t}"
          data-type="${t}"
          title="${s(e[t],n)}"
          data-value="${a(e[t])}">
          ${o(e[t])}
        </button>`};h.innerHTML=`<td>
          <button data-type="icon" data-tip="Click to select unit icon" translate="no"></button>
        </td>
        <td><input data-tip="Type unit name. If name is changed for existing unit, old unit will be replaced" value="${c}" /></td>
        <td>${_(`biomes`)}</td>
        <td>${_(`states`)}</td>
        <td>${_(`cultures`)}</td>
        <td>${_(`religions`)}</td>
        <td><input data-tip="Enter conscription percentage for rural population" type="number" min="0" max="100" step=".01" value="${l}" /></td>
        <td><input data-tip="Enter conscription percentage for urban population" type="number" min="0" max="100" step=".01" value="${d}" /></td>
        <td><input data-tip="Enter average number of people in crew (for total personnel calculation)" type="number" min="1" step="1" value="${p}" /></td>
        <td><input data-tip="Enter military power (used for battle simulation)" type="number" min="0" step=".1" value="${f}" /></td>
        <td>
          <select data-tip="Select unit type to apply special rules on forces recalculation">
            ${g}
          </select>
        </td>
        <td data-tip="Check if unit is <b>separate</b> and can be stacked only with the same units">
          <input id="${c}Separate" type="checkbox" class="checkbox" ${m?`checked`:``} />
          <label for="${c}Separate" class="checkbox-label"></label>
        </td>
        <td data-tip="Remove the unit">
          <span data-tip="Remove unit type" class="icon-trash-empty pointer" onclick="this.parentElement.parentElement.remove();"></span>
        </td>`,u(h.querySelector(`button[data-type='icon']`),i||``),r.appendChild(h)}function u(t,n){if(t.dataset.icon=n,t.textContent=``,e(n)){let e=document.createElement(`img`);e.src=n,e.style.cssText=`width: 1.2em; height: 1.2em; pointer-events: none`,t.appendChild(e)}else t.textContent=n}function m(){i(),Military.getDefaultOptions().map(e=>l(e))}function h(e,t){let n=e.dataset.type,r=e.dataset.value,i=r?r.split(`,`).map(e=>+e):[],a=t.filter(e=>e.i&&!e.removed).map(({i:e,name:t,fullName:n,color:r})=>`
          <tr data-tip="${t}">
            <td><span style="color:${r}">⬤</span></td>
            <td>
              <input data-i="${e}" id="el${e}" type="checkbox" class="checkbox"
                ${!i.length||i.includes(e)?`checked`:``} >
              <label for="el${e}" class="checkbox-label">${n||t}</label>
            </td>
          </tr>`);c(`alertMessage`).innerHTML=`<b>Limit unit by ${n}:</b>
        <table style="margin-top:.3em">
          <tbody>
            ${a.join(``)}
          </tbody>
        </table>`,$(`#alert`).dialog({width:`fit-content`,title:`Limit unit`,close:()=>$(`#alert`).dialog(`option`,`buttons`,{}),buttons:{Invert:()=>{alertMessage.querySelectorAll(`input`).forEach(e=>{e.checked=!e.checked})},Apply:function(){let n=Array.from(alertMessage.querySelectorAll(`input`)),r=n.reduce((e,t)=>(t.checked&&e.push(t.dataset.i),e),[]);if(!r.length){f(`Select at least one element`,!1,`error`);return}let i=r.length===n.length;e.dataset.value=i?``:r.join(`,`),e.innerHTML=i?`all`:`some`,e.setAttribute(`title`,s(r.map(Number),t)),$(this).dialog(`close`)},Cancel:function(){$(this).dialog(`close`)}}})}function g(){let e=Array.from(r.querySelectorAll(`tr`)),t=e.map(e=>n(e.querySelector(`input`).value));if(new Set(t).size!==t.length){f(`All units should have unique names`,!1,`error`);return}$(`#militaryOptions`).dialog(`close`);let i=e.map((e,n)=>{let[r,,i,a,o,s,c,l,u,d,f,p]=Array.from(e.querySelectorAll(`input, button, select`)).map(e=>{let{type:t,value:n}=e.dataset||{};return t===`icon`?e.dataset.icon?.trim()||`⠀`:t?n?n.split(`,`).map(e=>parseInt(e,10)):null:e.type===`number`?+e.value||0:e.type===`checkbox`?+e.checked||0:e.value}),m={icon:r,name:t[n],rural:c,urban:l,crew:u,power:d,type:f,separate:p};return i&&(m.biomes=i),a&&(m.states=a),o&&(m.cultures=o),s&&(m.religions=s),m});options.map.military.units=i,Options.save(),Military.generate(),d.draw(`military`),F()}}function G(){_(`militaryOptions`),c(`dialogs`).insertAdjacentHTML(`beforeend`,`<div id="militaryOptions" class="dialog stable">
      <div class="table">
        <table id="militaryOptionsTable">
          <thead>
            <tr>
              <th data-tip="Unit icon">Icon</th>
              <th data-tip="Unit name. If name is changed for existing unit, old unit will be replaced">Unit name</th>
              <th style="width: 5em" data-tip="Select allowed biomes">Biomes</th>
              <th style="width: 5em" data-tip="Select allowed states">States</th>
              <th style="width: 5em" data-tip="Select allowed cultures">Cultures</th>
              <th style="width: 5em" data-tip="Select allowed religions">Religions</th>
              <th data-tip="Conscription percentage for rural population">Rural</th>
              <th data-tip="Conscription percentage for urban population">Urban</th>
              <th data-tip="Average number of people in crew (used for total personnel calculation)">Crew</th>
              <th data-tip="Unit military power (used for battle simulation)">Power</th>
              <th data-tip="Unit type to apply special rules on forces recalculation">Type</th>
              <th data-tip="Check if unit is separate and can be stacked only with units of the same type">
                Separate
              </th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </div>`)}function K(){$(`#militaryOptions`).dialog(`destroy`),c(`militaryOptions`).remove()}function q(){c(`alertMessage`).innerHTML=`Are you sure you want to recalculate military forces for all states?<br>Regiments for all states will be regenerated`,$(`#alert`).dialog({resizable:!1,title:`Recalculate military`,buttons:{Recalculate:function(){$(this).dialog(`close`),Military.generate(),d.draw(`military`),L()},Cancel:function(){$(this).dialog(`close`)}}})}function J(){let e=options.map.military.units.map(e=>e.name),n=`Id,State,${e.map(e=>l(e)).join(`,`)},Total,Population,Rate,War Alert\n`;for(let r of I())n+=`${r.state.i},${r.state.name},${e.map(e=>r.forces[e]||0).join(`,`)},${r.total},${r.population},${t(r.rate,2)}%,${r.alert}\n`;let i=`${u(`Military`)}.csv`;r(n,i)}var Y={open:k,exportCsv:J};export{Y as MilitaryOverview};