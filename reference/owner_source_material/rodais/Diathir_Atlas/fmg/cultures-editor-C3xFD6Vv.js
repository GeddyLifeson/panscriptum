import{Bn as e,F as t,G as n,L as r,P as i,R as a,Tt as o,Wt as s,_ as c,a as l,ft as u,hn as d,j as f,jn as p,kn as ee,o as m,z as te}from"./utils-Cob8vHf9.js";import{I as ne,P as re,R as ie,Z as ae,t as h}from"./layers-Bh4OWBXX.js";import{t as oe}from"./drag-hfHVCxdY.js";import{t as se}from"./sin-DXK16t1M.js";import{n as ce}from"./highlight-Qtqc1_QO.js";import{i as g,t as le}from"./tooltips-BTSHGd98.js";import{t as _}from"./controllers-DnVd8NhQ.js";import{t as v}from"./emblems-generator-C2sA4EpN.js";import{n as y}from"./cultures-generator-B9VhtNU6.js";import{H as ue,V as de,ct as fe,d as pe,dt as b,lt as me,st as he,u as ge}from"./index-DsIn6sTp.js";import{t as _e}from"./highlighting-BxkDyRR_.js";import{a as ve,i as ye,n as be,o as xe,r as Se}from"./table-B6G2rlSI.js";var x={},S={},C=34,w=10,T=13;function E(e){return Function(`d`,`return {`+e.map(function(e,t){return JSON.stringify(e)+`: d[`+t+`] || ""`}).join(`,`)+`}`)}function Ce(e,t){var n=E(e);return function(r,i){return t(n(r),i,e)}}function D(e){var t=Object.create(null),n=[];return e.forEach(function(e){for(var r in e)r in t||n.push(t[r]=r)}),n}function O(e,t){var n=e+``,r=n.length;return r<t?Array(t-r+1).join(0)+n:n}function we(e){return e<0?`-`+O(-e,6):e>9999?`+`+O(e,6):O(e,4)}function Te(e){var t=e.getUTCHours(),n=e.getUTCMinutes(),r=e.getUTCSeconds(),i=e.getUTCMilliseconds();return isNaN(e)?`Invalid Date`:we(e.getUTCFullYear(),4)+`-`+O(e.getUTCMonth()+1,2)+`-`+O(e.getUTCDate(),2)+(i?`T`+O(t,2)+`:`+O(n,2)+`:`+O(r,2)+`.`+O(i,3)+`Z`:r?`T`+O(t,2)+`:`+O(n,2)+`:`+O(r,2)+`Z`:n||t?`T`+O(t,2)+`:`+O(n,2)+`Z`:``)}function Ee(e){var t=RegExp(`["`+e+`
\r]`),n=e.charCodeAt(0);function r(e,t){var n,r,a=i(e,function(e,i){if(n)return n(e,i-1);r=e,n=t?Ce(e,t):E(e)});return a.columns=r||[],a}function i(e,t){var r=[],i=e.length,a=0,o=0,s,c=i<=0,l=!1;e.charCodeAt(i-1)===w&&--i,e.charCodeAt(i-1)===T&&--i;function u(){if(c)return S;if(l)return l=!1,x;var t,r=a,o;if(e.charCodeAt(r)===C){for(;a++<i&&e.charCodeAt(a)!==C||e.charCodeAt(++a)===C;);return(t=a)>=i?c=!0:(o=e.charCodeAt(a++))===w?l=!0:o===T&&(l=!0,e.charCodeAt(a)===w&&++a),e.slice(r+1,t-1).replace(/""/g,`"`)}for(;a<i;){if((o=e.charCodeAt(t=a++))===w)l=!0;else if(o===T)l=!0,e.charCodeAt(a)===w&&++a;else if(o!==n)continue;return e.slice(r,t)}return c=!0,e.slice(r,i)}for(;(s=u())!==S;){for(var d=[];s!==x&&s!==S;)d.push(s),s=u();t&&(d=t(d,o++))==null||r.push(d)}return r}function a(t,n){return t.map(function(t){return n.map(function(e){return u(t[e])}).join(e)})}function o(t,n){return n??=D(t),[n.map(u).join(e)].concat(a(t,n)).join(`
`)}function s(e,t){return t??=D(e),a(e,t).join(`
`)}function c(e){return e.map(l).join(`
`)}function l(t){return t.map(u).join(e)}function u(e){return e==null?``:e instanceof Date?Te(e):t.test(e+=``)?`"`+e.replace(/"/g,`""`)+`"`:e}return{parse:r,parseRows:i,format:o,formatBody:s,formatRows:c,formatRow:l,formatValue:u}}var k=Ee(`,`),De=k.parse;k.parseRows,k.format,k.formatBody,k.formatRows,k.formatRow,k.formatValue;var A=`culturesEditor`,j=`Cultures`,M={my:`right top`,at:`right-10 top+10`,of:`svg`,collision:`fit`},N=null,P=[{key:`color`,width:`1.2em`,permanent:!0},{key:`name`,label:`Culture`,width:`10em`,permanent:!0,sortBy:e=>e.name||``,sortType:`alpha`},{key:`type`,label:`Type`,width:`6em`,mobileHidden:!0,sortBy:e=>e.type||``,sortType:`alpha`},{key:`base`,label:`Namesbase`,width:`9em`,mobileHidden:!0,sortBy:e=>e.base},{key:`cells`,label:`Cells`,width:`5em`,hidden:!0,sortBy:e=>e.cells||0},{key:`expansionism`,label:`Expansion`,width:`5em`,hidden:!0,mobileHidden:!0,sortBy:e=>e.expansionism||0},{key:`area`,label:`Area`,width:`7em`,mobileHidden:!0,sortBy:e=>e.area||0},{key:`population`,label:`Population`,width:`6em`,defaultSort:`desc`,sortBy:e=>(e.rural||0)*options.map.units.population.scale+(e.urban||0)*options.map.units.population.scale*options.map.units.population.urbanization.rate},{key:`emblems`,label:`Emblems`,width:`7em`,hidden:!0,mobileHidden:!0,sortBy:e=>e.shield||``,sortType:`alpha`},{key:`note`,width:`1.1em`},{key:`locate`,width:`1.1em`},{key:`lock`,width:`1.1em`},{key:`remove`,width:`1.4em`,permanent:!0}],F=Se({getData:()=>pe(A,pack.cultures.filter(e=>!e.removed),P),onUpdate:Oe});function I(){customization||(he(`#${A}, .stable`),h.show(`cultures`),h.hide(`states`,`biomes`),h.hide(`religions`,`provinces`),L(),z(),q(),F.reset(),$(`#${A}`).dialog({title:`Cultures Editor`,resizable:!1,width:`fit-content`,close:Je,position:M}))}function L(){me(`culturesEditor`);let e=`<div id="culturesEditor" class="dialog stable editorDialog">
    <div id="culturesBody" class="table" data-type="absolute">${ye({dialogId:A,columns:P})}</div>

    <div id="culturesFooter" class="totalLine">
      <div data-tip="Cultures number" style="margin-left: 12px">Cultures:&nbsp;<span id="culturesFooterCultures">0</span></div>
      <div data-tip="Total land cells number" style="margin-left: 12px" data-col="cells">Cells:&nbsp;<span id="culturesFooterCells">0</span></div>
      <div data-tip="Total land area" style="margin-left: 12px" data-col="area">Land Area:&nbsp;<span id="culturesFooterArea">0</span></div>
      <div data-tip="Total population" style="margin-left: 12px" data-col="population">Population:&nbsp;<span id="culturesFooterPopulation">0</span></div>
    </div>

    <div id="culturesBottom" class="editorToolbar">
      <button id="culturesEditorRefresh" data-tip="Refresh the Editor" class="icon-cw"></button>
      <button id="culturesEditStyle" data-tip="Edit cultures style in Style Editor" class="icon-adjust"></button>
      <button id="culturesLegend" data-tip="Toggle Legend box" class="icon-list-bullet"></button>
      <button id="culturesPercentage" data-tip="Toggle percentage / absolute values display mode" class="icon-percent"></button>
      <button id="culturesHeirarchy" data-tip="Show cultures hierarchy tree" class="icon-sitemap"></button>
      <button id="culturesManually" data-tip="Manually re-assign cultures" class="icon-brush"></button>
      <button id="culturesEditNamesBase" data-tip="Edit a database used for names generation" class="icon-font"></button>
      <button id="culturesAdd" data-tip="Add a new culture. Hold Shift to add multiple" class="icon-plus"></button>
      <button id="culturesExport" data-tip="Download cultures-related data" class="icon-download"></button>
      <button id="culturesImport" data-tip="Upload cultures-related data" class="icon-upload"></button>
      <button id="culturesRecalculate" data-tip="Recalculate cultures based on current values of growth-related attributes" class="icon-retweet"></button>
      <span
        data-tip="Allow culture centers, expansion and type changes to take an immediate effect"
        class="editorToolbarPanel"
        style="display: inline-flex"
      >
        <input id="culturesAutoChange" class="checkbox" type="checkbox" />
        <label for="culturesAutoChange" class="checkbox-label"><i>auto-apply changes</i></label>
      </span>
    </div>
  </div>`;f(`dialogs`).insertAdjacentHTML(`beforeend`,e),ge(A,F.reset),_e(A,({cellId:e})=>pack.cells.culture[e]),f(`culturesEditorRefresh`).addEventListener(`click`,R),be({dialogId:A,columns:P,onUpdate:()=>b(A,{width:`fit-content`,position:M})}),f(`culturesEditStyle`).addEventListener(`click`,()=>editStyle(`cults`)),f(`culturesLegend`).addEventListener(`click`,He),f(`culturesPercentage`).addEventListener(`click`,J),f(`culturesHeirarchy`).addEventListener(`click`,Y),f(`culturesRecalculate`).addEventListener(`click`,()=>X(!0)),f(`culturesManually`).addEventListener(`click`,Ue),f(`culturesEditNamesBase`).addEventListener(`click`,()=>_.NamesbaseEditor.open()),f(`culturesAdd`).addEventListener(`click`,Ge),f(`culturesExport`).addEventListener(`click`,qe),f(`culturesImport`).addEventListener(`click`,Ye)}function R(){z(),F.refresh(),q()}function z(){let{cells:e,cultures:t,burgs:n}=pack;t.forEach(e=>{e.cells=e.area=e.rural=e.urban=0});for(let r of e.i){if(e.h[r]<20)continue;let i=e.culture[r];t[i].cells+=1,t[i].area+=e.area[r],t[i].rural+=e.pop[r];let a=e.burg[r];a&&(t[i].urban+=n[a].population)}}function Oe(t){let n=m(),r=``,i=0,a=0;for(let n of t.all)i+=l(n.area??0),a+=e((n.rural??0)*options.map.units.population.scale+(n.urban??0)*options.map.units.population.scale*options.map.units.population.urbanization.rate);for(let i of t.rows){let t=l(i.area??0),a=(i.rural??0)*options.map.units.population.scale,o=(i.urban??0)*options.map.units.population.scale*options.map.units.population.urbanization.rate,s=e(a+o),u=`Total population: ${c(s)}. Rural population: ${c(a)}. Urban population: ${c(o)}. Click to edit`;if(!i.i){r+=`<div
          class="states"
          data-id="${i.i}"
          data-name="${i.name}"
          data-color=""
          data-cells="${i.cells}"
          data-area="${t}"
          data-population="${s}"
          data-base="${i.base}"
          data-type=""
          data-expansionism=""
          data-emblems="${i.shield}"
        >
          <svg width="11" height="11" class="placeholder" data-col="color"></svg>
          <div data-col="name">
            <input data-tip="Neutral culture name. Click and type to change" class="cultureName italic"
              value="${i.name}" autocorrect="off" spellcheck="false" />
            <span class="icon-cw placeholder"></span>
          </div>
          <select class="cultureType placeholder" data-col="type">${B(i.type)}</select>
          <div data-col="base">
            <span data-tip="Click to re-generate names for burgs with this culture assigned" class="icon-arrows-cw"></span>
            <select data-tip="Culture namesbase. Click to change. Click on arrows to re-generate names"
              class="cultureBase">${V(i.base)}</select>
          </div>
          <div data-col="cells">
            <span data-tip="Cells count" class="icon-check-empty"></span>
            <div data-tip="Cells count" class="cultureCells">${i.cells}</div>
          </div>
          <div data-col="expansionism">
            <span class="icon-resize-full placeholder"></span>
            <input class="cultureExpan placeholder" type="number" />
          </div>
          <div data-col="area">
            <span data-tip="Culture area" class="icon-map-o"></span>
            <div data-tip="Culture area" class="cultureArea">${c(t)} ${n}</div>
          </div>
          <div data-col="population">
            <span data-tip="${u}" class="icon-male"></span>
            <div data-tip="${u}" class="culturePopulation pointer">${c(s)}</div>
          </div>
          <div data-col="emblems">${H(v.isDiversiform,i.shield)}</div>
          <div data-col="note"></div>
          <div data-col="locate"></div>
          <div data-col="lock"></div>
          <div data-col="remove"></div>
        </div>`;continue}r+=`<div
        class="states"
        data-id="${i.i}"
        data-name="${i.name}"
        data-color="${i.color}"
        data-cells="${i.cells}"
        data-area="${t}"
        data-population="${s}"
        data-base="${i.base}"
        data-type="${i.type}"
        data-expansionism="${i.expansionism}"
        data-emblems="${i.shield}"
      >
        <fill-box fill="${i.color}" data-col="color"></fill-box>
        <div data-col="name">
          <input data-tip="Culture name. Click and type to change" class="cultureName"
            value="${i.name}" autocorrect="off" spellcheck="false" />
          <span data-tip="Regenerate culture name" class="icon-cw hiddenIcon" style="visibility: hidden"></span>
        </div>
        <select data-tip="Culture type. Defines growth model. Click to change"
          class="cultureType" data-col="type">${B(i.type)}</select>
        <div data-col="base">
          <span data-tip="Click to re-generate names for burgs with this culture assigned" class="icon-arrows-cw"></span>
          <select data-tip="Culture namesbase. Click to change. Click on arrows to re-generate names"
            class="cultureBase">${V(i.base)}</select>
        </div>
        <div data-col="cells">
          <span data-tip="Cells count" class="icon-check-empty"></span>
          <div data-tip="Cells count" class="cultureCells">${i.cells}</div>
        </div>
        <div data-col="expansionism">
          <span data-tip="Culture expansionism. Defines competitive size" class="icon-resize-full"></span>
          <input
            data-tip="Culture expansionism. Defines competitive size. Click to change, then click Recalculate to apply change"
            class="cultureExpan"
            type="number"
            min="0"
            max="99"
            step=".1"
            value=${i.expansionism}
          />
        </div>
        <div data-col="area">
          <span data-tip="Culture area" class="icon-map-o"></span>
          <div data-tip="Culture area" class="cultureArea">${c(t)} ${n}</div>
        </div>
        <div data-col="population">
          <span data-tip="${u}" class="icon-male"></span>
          <div data-tip="${u}" class="culturePopulation pointer">${c(s)}</div>
        </div>
        <div data-col="emblems">${H(v.isDiversiform,i.shield)}</div>
        ${ue.getIcon(`this culture`)}
        <span data-col="locate" data-tip="Locate the culture" class="icon-target"></span>
        <span data-col="lock" data-tip="Lock culture" class="icon-lock${i.lock?``:`-open`}"></span>
        <span data-col="remove" data-tip="Remove culture" class="icon-trash-empty"></span>
      </div>`}let o=f(`culturesBody`);o.querySelectorAll(`:scope > .states`).forEach(e=>{e.remove()}),o.insertAdjacentHTML(`beforeend`,r),f(`culturesFooterCultures`).innerHTML=String(pack.cultures.filter(e=>e.i&&!e.removed).length),f(`culturesFooterCells`).innerHTML=String(pack.cells.h.filter(e=>e>=20).length),f(`culturesFooterArea`).innerHTML=`${c(i)} ${n}`,f(`culturesFooterPopulation`).innerHTML=c(a),f(`culturesFooterArea`).dataset.area=String(i),f(`culturesFooterPopulation`).dataset.population=String(a),ve(f(`culturesFooter`),t,F.goto),f(`culturesBody`).querySelectorAll(`:scope > div.states`).forEach(e=>{e.addEventListener(`mouseenter`,U),e.addEventListener(`mouseleave`,W)}),f(`culturesBody`).querySelectorAll(`fill-box`).forEach(e=>void e.addEventListener(`click`,ke)),f(`culturesBody`).querySelectorAll(`div > input.cultureName`).forEach(e=>void e.addEventListener(`input`,Ae)),f(`culturesBody`).querySelectorAll(`div > span.icon-cw`).forEach(e=>void e.addEventListener(`click`,je)),f(`culturesBody`).querySelectorAll(`div > input.cultureExpan`).forEach(e=>void e.addEventListener(`change`,Me)),f(`culturesBody`).querySelectorAll(`div > select.cultureType`).forEach(e=>void e.addEventListener(`change`,Ne)),f(`culturesBody`).querySelectorAll(`div > select.cultureBase`).forEach(e=>void e.addEventListener(`change`,Pe)),f(`culturesBody`).querySelectorAll(`div > select.cultureEmblems`).forEach(e=>void e.addEventListener(`change`,Fe)),f(`culturesBody`).querySelectorAll(`div > div.culturePopulation`).forEach(e=>void e.addEventListener(`click`,Ie)),f(`culturesBody`).querySelectorAll(`div > span.icon-arrows-cw`).forEach(e=>void e.addEventListener(`click`,Le)),f(`culturesBody`).querySelectorAll(`div > span.icon-book`).forEach(e=>void e.addEventListener(`click`,Re)),f(`culturesBody`).querySelectorAll(`div > span.icon-target`).forEach(e=>void e.addEventListener(`click`,ze)),f(`culturesBody`).querySelectorAll(`div > span.icon-trash-empty`).forEach(e=>void e.addEventListener(`click`,Be)),f(`culturesBody`).querySelectorAll(`div > span.icon-lock`).forEach(e=>void e.addEventListener(`click`,Q)),f(`culturesBody`).querySelectorAll(`div > span.icon-lock-open`).forEach(e=>void e.addEventListener(`click`,Q)),xe(A,v.isDiversiform?[]:[`emblems`]),f(`culturesBody`).dataset.type===`percentage`&&(f(`culturesBody`).dataset.type=`absolute`,J()),b(A,{width:`fit-content`,position:M})}function B(e){let t=``;return y.forEach(n=>{t+=`<option ${e===n?`selected`:``} value="${n}">${n}</option>`}),t}function V(e){let t=``;return Names.nameBases.forEach((n,r)=>{t+=`<option ${e===r?`selected`:``} value="${r}">${n.name}</option>`}),Names.nameBases[e]||(t+=`<option selected value="${e}">removed</option>`),t}function H(e,t){return e?`<select data-tip="Emblem shape associated with culture. Click to change" class="cultureEmblems">${Object.keys(v.shields.types).flatMap(e=>Object.keys(v.shields[e])).map(e=>`<option ${e===t?`selected`:``} value="${e}">${ee(e)}</option>`)}</select>`:``}var U=n(e=>{let t=Number(e.id||e.target.dataset.id);if(!h.isOn(`cultures`)||customization)return;let n=s().duration(2e3).ease(se);d(`#cults`).select(`#culture${t}`).raise().transition(n).attr(`stroke-width`,2.5).attr(`stroke`,`#d0240f`),d(`#debug`).select(`#cultureCenter${t}`).raise().transition(n).attr(`r`,3).attr(`stroke`,`#d0240f`)},200);function W(e){let t=Number(e.id||e.target.dataset.id);h.isOn(`cultures`)&&(d(`#cults`).select(`#culture${t}`).transition().attr(`stroke-width`,null).attr(`stroke`,null),d(`#debug`).select(`#cultureCenter${t}`).transition().attr(`r`,2).attr(`stroke`,null))}function ke(){let e=this.getAttribute(`fill`)||`#ffffff`,t=+this.parentNode.dataset.id;_.ColorPicker.open(e,e=>{this.fill=e,pack.cultures[t].color=e,d(`#cults`).select(`#culture${t}`).attr(`fill`,e),d(`#debug`).select(`#cultureCenter${t}`).attr(`fill`,e)})}function Ae(){let e=this.closest(`.states`),t=+e.dataset.id;e.dataset.name=this.value;let n=pack.cultures;n[t].name=this.value,n[t].code=u(this.value,n.flatMap(e=>e.code?[e.code]:[]))}function je(){let e=+this.closest(`.states`).dataset.id,t=pack.cultures[e].base;if(!Names.nameBases[t]){g(`Namesbase is not defined, please select a valid namesbase`,!1,`error`,5e3);return}let n=Names.getCultureShort(e);this.parentNode.querySelector(`input.cultureName`).value=n,pack.cultures[e].name=n}function Me(){let e=this.closest(`.states`),t=+e.dataset.id;e.dataset.expansionism=this.value,pack.cultures[t].expansionism=+this.value,X()}function Ne(){let e=+this.parentNode.dataset.id;this.parentNode.dataset.type=this.value;let t=this.value;pack.cultures[e].type=t,X()}function Pe(){let e=this.closest(`.states`),t=+e.dataset.id,n=+this.value;pack.cultures[t].base=n,e.dataset.base=String(n)}function Fe(){let e=this.closest(`.states`),t=+e.dataset.id,n=this.value;e.dataset.emblems=pack.cultures[t].shield=n;let r=(e,t)=>{let n=document.getElementById(e);n&&(n.remove(),ae.trigger(e,t))};pack.states.forEach(e=>{e.culture!==t||!e.i||e.removed||!e.coa||e.coa.custom||n!==e.coa.shield&&(e.coa.shield=n,r(`stateCOA${e.i}`,e.coa))}),pack.provinces.forEach(e=>{pack.cells.culture[e.center]!==t||!e.i||e.removed||!e.coa||e.coa.custom||n!==e.coa.shield&&(e.coa.shield=n,r(`provinceCOA${e.i}`,e.coa))}),pack.burgs.forEach(e=>{e.culture!==t||!e.i||e.removed||!e.coa||e.coa.custom||n!==e.coa.shield&&(e.coa.shield=n,r(`burgCOA${e.i}`,e.coa))})}function Ie(){let t=+this.closest(`.states`).dataset.id,n=pack.cultures[t];if(!n.cells){g(`Culture does not have any cells, cannot change population`,!1,`error`);return}let r=e((n.rural??0)*options.map.units.population.scale),i=e((n.urban??0)*options.map.units.population.scale*options.map.units.population.urbanization.rate),a=r+i,o=e=>Number(e).toLocaleString(),s=pack.burgs.filter(e=>!e.removed&&e.culture===t);alertMessage.innerHTML=`<div>
    <i>Change population of all cells assigned to the culture</i>
    <div style="margin: 0.5em 0">
      Rural: <input type="number" min="0" step="1" id="ruralPop" value=${r} style="width:6em" />
      Urban: <input type="number" min="0" step="1" id="urbanPop" value=${i} style="width:6em"
        ${s.length?``:`disabled`} />
    </div>
    <div>Total population: ${o(a)} ⇒ <span id="totalPop">${o(a)}</span>
      (<span id="totalPopPerc">100</span>%)
    </div>
  </div>`;let c=f(`ruralPop`),l=f(`urbanPop`),u=f(`totalPop`),d=f(`totalPopPerc`),p=()=>{let t=c.valueAsNumber+l.valueAsNumber;Number.isNaN(t)||(u.innerHTML=o(t),d.innerHTML=String(e(t/a*100)))};c.oninput=()=>p(),l.oninput=()=>p(),$(`#alert`).dialog({resizable:!1,title:`Change culture population`,width:`24em`,buttons:{Apply:function(){G(r,i,+c.value,+l.value,t),$(this).dialog(`close`)},Cancel:function(){$(this).dialog(`close`)}},position:{my:`center`,at:`center`,of:`svg`}})}function G(t,n,r,i,a){let o=r/t;if(Number.isFinite(o)&&o!==1&&pack.cells.i.filter(e=>pack.cells.culture[e]===a).forEach(e=>{pack.cells.pop[e]*=o}),!Number.isFinite(o)&&+r>0){let t=r/options.map.units.population.scale,n=pack.cells.i.filter(e=>pack.cells.culture[e]===a),i=e(t/n.length);n.forEach(e=>{pack.cells.pop[e]=i})}let s=pack.burgs.filter(e=>!e.removed&&e.culture===a),c=i/n;if(Number.isFinite(c)&&c!==1&&s.forEach(t=>{t.population=e((t.population??0)*c,4)}),!Number.isFinite(c)&&+i>0){let t=e(i/options.map.units.population.scale/options.map.units.population.urbanization.rate/s.length,4);s.forEach(e=>{e.population=t})}h.draw(`population`),R()}function Le(){if(customization===4)return;let e=+this.closest(`.states`).dataset.id,t=pack.cultures[e].base;if(!Names.nameBases[t]){g(`Namesbase is not defined, please select a valid namesbase`,!1,`error`,5e3);return}let n=pack.burgs.filter(t=>t.culture===e&&!t.removed&&!t.lock);n.forEach(t=>{t.name=Names.getCulture(e)}),h.draw(`labels`),g(`Names for ${n.length} burgs are regenerated`,!1,`success`)}function K(e){d(`#cults`).select(`#culture${e}`).remove(),d(`#debug`).select(`#cultureCenter${e}`).remove();let{burgs:t,states:n,cells:r,cultures:i}=pack;t.filter(t=>t.culture===e).forEach(e=>{e.culture=0}),n.forEach(t=>{t.culture===e&&(t.culture=0)}),r.culture.forEach((t,n)=>{t===e&&(r.culture[n]=0)}),i[e].removed=!0,i.filter(e=>e.i&&!e.removed).forEach(t=>{t.origins=(t.origins??[]).filter(t=>t!==e),t.origins.length||(t.origins=[0])}),R()}function Re(){let e=+this.closest(`.states`).dataset.id;_.NotesEditor.open({type:`culture`,id:e})}function ze(){let e=+this.closest(`.states`).dataset.id;ce(d(`#cults`).select(`#culture${e}`).node(),4)}function Be(){if(customization)return;let e=+this.closest(`.states`).dataset.id;fe({title:`Remove culture`,message:`Are you sure you want to remove the culture? <br>This action cannot be reverted`,confirm:`Remove`,onConfirm:()=>K(e)})}function q(){let e=d(`#debug`);e.select(`#cultureCenters`).remove();let t=e.append(`g`).attr(`id`,`cultureCenters`).attr(`stroke-width`,.8).attr(`stroke`,`#444444`).style(`cursor`,`move`),n=pack.cultures.filter(e=>e.i&&!e.removed);t.selectAll(`circle`).data(n).enter().append(`circle`).attr(`id`,e=>`cultureCenter${e.i}`).attr(`data-id`,e=>e.i).attr(`r`,2).attr(`fill`,e=>e.color).attr(`cx`,e=>pack.cells.p[e.center][0]).attr(`cy`,e=>pack.cells.p[e.center][1]).on(`mouseenter`,(e,t)=>{g(`Drag to move the culture center (ancestral home)`,!0),f(`culturesBody`).querySelector(`div[data-id='${t.i}']`)?.classList.add(`selected`),U(e)}).on(`mouseleave`,(e,t)=>{g(``,!0),f(`culturesBody`).querySelector(`div[data-id='${t.i}']`)?.classList.remove(`selected`),W(e)}).call(oe().on(`start`,Ve))}function Ve(e){let t=+this.id.slice(13),r=p(this.getAttribute(`transform`)),i=+r[0]-e.x,a=+r[1]-e.y;function o(e){let{x:n,y:r}=e;this.setAttribute(`transform`,`translate(${i+n},${a+r})`);let o=Pack.findCell(n,r);o==null||pack.cells.h[o]<20||(pack.cultures[t].center=o,X())}let s=n(o,50);e.on(`drag`,s)}function He(){if(ie(j)){re(j);return}let e=pack.cultures.filter(e=>e.i&&!e.removed&&e.cells).sort((e,t)=>(t.area??0)-(e.area??0)).map(e=>[e.i,e.color,e.name]);if(!e.length)return void g(`No cultures to show`,!1,`error`);ne(j,e)}function J(){if(f(`culturesBody`).dataset.type===`absolute`){f(`culturesBody`).dataset.type=`percentage`;let t=+f(`culturesFooterCells`).innerText,n=+f(`culturesFooterArea`).dataset.area,r=+f(`culturesFooterPopulation`).dataset.population;f(`culturesBody`).querySelectorAll(`:scope > div.states`).forEach(i=>{let{cells:a,area:o,population:s}=i.dataset;i.querySelector(`.cultureCells`).innerText=`${e(+a/t*100)}%`,i.querySelector(`.cultureArea`).innerText=`${e(+o/n*100)}%`,i.querySelector(`.culturePopulation`).innerText=`${e(+s/r*100)}%`})}else f(`culturesBody`).dataset.type=`absolute`,F.refresh()}async function Y(){customization||_.HierarchyTree.open({type:`cultures`,data:pack.cultures,onNodeEnter:U,onNodeLeave:W,getDescription:t=>{let{name:n,type:r,rural:i,urban:a}=t,o=i*options.map.units.population.scale+a*options.map.units.population.scale*options.map.units.population.urbanization.rate;return`${n} culture. ${r}. ${o>0?`${c(e(o))} people`:`Extinct`}`},getShape:({type:e})=>{if(e===`Generic`)return`circle`;if(e===`River`)return`diamond`;if(e===`Lake`)return`hexagon`;if(e===`Naval`)return`square`;if(e===`Highland`)return`concave`;if(e===`Nomadic`)return`octagon`;if(e===`Hunting`)return`pentagon`}})}function X(e){(e||f(`culturesAutoChange`).checked)&&(Cultures.expand(),h.draw(`cultures`),pack.burgs.forEach(e=>{!e.i||e.removed||(e.culture=pack.cells.culture[e.cell])}),R())}function Ue(){h.show(`cultures`),_.PaintEditor.open({title:`Paint Cultures`,parentDialogId:A,onClose:I,items:pack.cultures.filter(e=>!e.removed).map(e=>({id:e.i,name:e.name,color:e.color||`#ffffff`})),dontOverrideControl:!0,getValue:e=>pack.cells.culture[e],filterCell:e=>t(e,pack),onApply:We})}function We(e){for(let[t,n]of e)pack.cells.culture[t]=n,pack.cells.burg[t]&&(pack.burgs[pack.cells.burg[t]].culture=n);e.size&&(h.draw(`cultures`),document.getElementById(A)&&R())}function Ge(){if(this.classList.contains(`pressed`)){Z();return}customization=9,this.classList.add(`pressed`),g(`Click on the map to add a new culture`,!0),d(`#viewbox`).style(`cursor`,`crosshair`).on(`click`,Ke),f(`culturesBody`).querySelectorAll(`div > input, select, span, svg`).forEach(e=>{e.style.pointerEvents=`none`})}function Z(){customization=0,de(),le(),f(`culturesBody`).querySelectorAll(`div > input, select, span, svg`).forEach(e=>{e.style.removeProperty(`pointer-events`)});let e=f(`culturesAdd`);e.classList.contains(`pressed`)&&e.classList.remove(`pressed`)}function Ke(e){let t=i(e,this),n=Pack.findCell(t[0],t[1]);if(pack.cells.h[n]<20){g(`You cannot place culture center into the water. Please click on a land cell`,!1,`error`);return}if(pack.cultures.some(e=>!e.removed&&e.center===n)){g(`This cell is already a culture center. Please select a different cell`,!1,`error`);return}e.shiftKey===!1&&Z(),Cultures.add(n),q(),F.refresh()}function qe(){let t=`Id,Name,Color,Cells,Expansionism,Type,Area ${m(`2`)},Population,Namesbase,Emblems Shape,Origins`,n=F.view().all.map(t=>{let n=l(t.area??0),r=e((t.rural??0)*options.map.units.population.scale+(t.urban??0)*options.map.units.population.scale*options.map.units.population.urbanization.rate),i=Names.nameBases[t.base].name,a=`"${(t.origins??[]).filter(e=>!!e).map(e=>pack.cultures[e].name).join(`, `)}"`;return[t.i,t.name,t.i&&t.color||``,t.cells||0,t.i?t.expansionism||0:``,t.i?t.type:``,n,r,i,t.shield,a].join(`,`)});a([t].concat(n).join(`
`),`${te(`Cultures`)}.csv`)}function Je(){d(`#debug #cultureCenters`).remove(),customization===9&&Z(),$(`#culturesEditor`).dialog(`destroy`),f(`culturesEditor`).remove()}function Ye(){N??=r(`.csv`),N.onchange=()=>void Xe.call(N),N.click()}async function Xe(){let e=this.files[0];this.value=``;let t=De(await e.text(),e=>({name:e.Name,i:+e.Id,color:e.Color,expansionism:+e.Expansionism,type:e.Type,population:+e.Population,emblemsShape:e[`Emblems Shape`],origins:e.Origins,namesbase:e.Namesbase})),{cultures:n,cells:r}=pack,i=Object.keys(v.shields.types).flatMap(e=>Object.keys(v.shields[e])),a=r.pop.map((e,t)=>e?t:null).filter(e=>e);n.forEach(e=>{e.i&&(e.removed=!0)});for(let e of t){let t;if(e.i<n.length){t=n[e.i];let r=t.urban/(t.rural+t.urban);G(t.rural,t.urban,e.population*(1-r),e.population*r,e.i)}else t={i:n.length,center:o(a),area:0,cells:0,origins:[0],rural:0,urban:0},n.push(t);t.removed=!1,t.name=e.name,t.i&&(t.code=u(t.name,n.map(e=>e.code)),t.color=e.color,t.expansionism=+e.expansionism,y.includes(e.type)?t.type=e.type:t.type=`Generic`),e.origins=t.i?r(e.origins||``):[null],t.shield=i.includes(e.emblemsShape)?e.emblemsShape:`heater`,t.base=Names.nameBases.findIndex(t=>t.name===e.namesbase);function r(e){let r=e.replaceAll(`"`,``).split(`,`).map(e=>e.trim()).filter(e=>e).map(e=>{let t=n.findIndex(t=>t.name===e);return t===-1?null:t});t.origins=r.filter(e=>e!==null),t.origins.length||(t.origins=[0])}}n.filter(e=>e.removed).forEach(e=>{K(e.i)}),h.draw(`cultures`),R()}function Q(){if(customization)return;let e=+this.closest(`.states`).dataset.id,t=this.classList,n=pack.cultures[e];n.lock=!n.lock,t.toggle(`icon-lock-open`),t.toggle(`icon-lock`)}var Ze={open:I,showHierarchy:Y};export{Ze as CulturesEditor};