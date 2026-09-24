import{Bn as e,F as t,G as n,P as r,R as i,Wt as a,_ as o,a as s,ft as c,hn as l,j as u,jn as d,o as f,z as p}from"./utils-Cob8vHf9.js";import{I as m,P as h,R as g,t as _}from"./layers-Bh4OWBXX.js";import{t as ee}from"./drag-hfHVCxdY.js";import{t as te}from"./sin-DXK16t1M.js";import{n as ne}from"./highlight-Qtqc1_QO.js";import{i as v,t as y}from"./tooltips-BTSHGd98.js";import{t as b}from"./state-B2hBYDzv.js";import{t as x}from"./controllers-DnVd8NhQ.js";import{H as re,V as S,ct as C,d as w,dt as T,lt as E,st as D,u as ie}from"./index-DsIn6sTp.js";import{t as ae}from"./highlighting-BxkDyRR_.js";import{a as oe,i as se,n as ce,r as le}from"./table-B6G2rlSI.js";var O=`religionsEditor`,k=`Religions`,A={my:`right top`,at:`right-10 top+10`,of:`svg`,collision:`fit`},j,M=[{key:`color`,width:`1.2em`,permanent:!0},{key:`name`,label:`Religion`,width:`14em`,permanent:!0,sortBy:e=>e.name||``,sortType:`alpha`},{key:`type`,label:`Type`,width:`6em`,defaultSort:`asc`,sortBy:e=>e.type||``,sortType:`alpha`},{key:`form`,label:`Form`,width:`7em`,mobileHidden:!0,sortBy:e=>e.form||``,sortType:`alpha`},{key:`deity`,label:`Deity`,width:`14em`,mobileHidden:!0,sortBy:e=>e.deity||``,sortType:`alpha`},{key:`area`,label:`Area`,width:`7em`,mobileHidden:!0,sortBy:e=>e.area||0},{key:`population`,label:`Population`,width:`6em`,sortBy:e=>(e.rural||0)*options.map.units.population.scale+(e.urban||0)*options.map.units.population.scale*options.map.units.population.urbanization.rate},{key:`expansion`,label:`Expansion`,width:`5em`,hidden:!0,mobileHidden:!0,sortBy:e=>e.expansion||``,sortType:`alpha`},{key:`expansionism`,label:`Expansionism`,width:`5em`,hidden:!0,mobileHidden:!0,sortBy:e=>e.expansionism||0},{key:`note`,width:`1.1em`},{key:`locate`,width:`1.1em`},{key:`lock`,width:`1.1em`},{key:`remove`,width:`1.4em`,permanent:!0}];function N(){return pack.religions.filter(e=>!e.removed&&!(e.i&&!e.cells&&!j.showExtinct))}var P=le({getData:()=>w(O,N(),M),onUpdate:z});function F(){customization||(j=b.get(O,`filters`,()=>({showExtinct:!1})),D(`#${O}, .stable`),_.show(`religions`),_.hide(`states`,`biomes`),_.hide(`cultures`,`provinces`),I(),R(),G(),P.reset(),$(`#${O}`).dialog({title:`Religions Editor`,resizable:!1,width:`fit-content`,close:Ae,position:A}))}function I(){E(`religionsEditor`);let e=`<div id="religionsEditor" class="dialog stable editorDialog">
    <div id="religionsBody" class="table" data-type="absolute">${se({dialogId:O,columns:M})}</div>

    <div id="religionsFooter" class="totalLine">
      <div data-tip="Total number of organized religions" style="margin-left: 12px">
        Organized:&nbsp;<span id="religionsOrganized">0</span>
      </div>
      <div data-tip="Total number of heresies" style="margin-left: 12px">
        Heresies:&nbsp;<span id="religionsHeresies">0</span>
      </div>
      <div data-tip="Total number of cults" style="margin-left: 12px">
        Cults:&nbsp;<span id="religionsCults">0</span>
      </div>
      <div data-tip="Total number of folk religions" style="margin-left: 12px">
        Folk:&nbsp;<span id="religionsFolk">0</span>
      </div>
      <div data-tip="Total land area" style="margin-left: 12px" data-col="area">
        Land Area:&nbsp;<span id="religionsFooterArea">0</span>
      </div>
      <div data-tip="Total number of believers (population)" style="margin-left: 12px" data-col="population">
        Believers:&nbsp;<span id="religionsFooterPopulation">0</span>
      </div>
    </div>

    <div id="religionsBottom" class="editorToolbar">
      <button id="religionsEditorRefresh" data-tip="Refresh the Editor" class="icon-cw"></button>
      <button id="religionsEditStyle" data-tip="Edit religions style in Style Editor" class="icon-adjust"></button>
      <button id="religionsLegend" data-tip="Toggle Legend box" class="icon-list-bullet"></button>
      <button id="religionsPercentage" data-tip="Toggle percentage / absolute values display mode" class="icon-percent"></button>
      <button id="religionsHeirarchy" data-tip="Show religions hierarchy tree" class="icon-sitemap"></button>
      <button id="religionsExtinct" data-tip="Show/hide extinct religions (religions without cells)" class="icon-eye-off"></button>

      <button id="religionsManually" data-tip="Manually re-assign religions" class="icon-brush"></button>
      <button id="religionsAdd" data-tip="Add a new religion. Hold Shift to add multiple" class="icon-plus"></button>
      <button id="religionsExport" data-tip="Download religions-related data" class="icon-download"></button>
      <button id="religionsRecalculate" data-tip="Recalculate religions based on current values of growth-related attributes" class="icon-retweet"></button>
      <span
        data-tip="Allow religion center, extent, and expansionism changes to take an immediate effect"
        class="editorToolbarPanel"
      >
        <input id="religionsAutoChange" class="checkbox" type="checkbox" />
        <label for="religionsAutoChange" class="checkbox-label"><i>auto-apply changes</i></label>
      </span>
    </div>
  </div>`;u(`dialogs`).insertAdjacentHTML(`beforeend`,e),J(),ie(O,P.reset),ae(O,({cellId:e})=>pack.cells.religion[e]),u(`religionsEditorRefresh`).addEventListener(`click`,L),ce({dialogId:O,columns:M,onUpdate:()=>T(O,{width:`fit-content`,position:A})}),u(`religionsEditStyle`).addEventListener(`click`,()=>editStyle(`relig`)),u(`religionsLegend`).addEventListener(`click`,Se),u(`religionsPercentage`).addEventListener(`click`,K),u(`religionsHeirarchy`).addEventListener(`click`,q),u(`religionsExtinct`).addEventListener(`click`,Ce),u(`religionsManually`).addEventListener(`click`,we),u(`religionsAdd`).addEventListener(`click`,Ee),u(`religionsExport`).addEventListener(`click`,De),u(`religionsRecalculate`).addEventListener(`click`,()=>Q(!0))}function L(){R(),P.refresh()}function R(){let{cells:e,religions:t,burgs:n}=pack;t.forEach(e=>{e.cells=e.area=e.rural=e.urban=0});for(let r of e.i){if(e.h[r]<20)continue;let i=e.religion[r];t[i].cells+=1,t[i].area+=e.area[r],t[i].rural+=e.pop[r];let a=e.burg[r];a&&(t[i].urban+=n[a].population)}}function z(t){let n=` ${f()}`,r=``,i=0,a=0;for(let n of t.all)i+=s(n.area??0),a+=e((n.rural??0)*options.map.units.population.scale+(n.urban??0)*options.map.units.population.scale*options.map.units.population.urbanization.rate);for(let i of t.rows){let t=s(i.area??0),a=(i.rural??0)*options.map.units.population.scale,c=(i.urban??0)*options.map.units.population.scale*options.map.units.population.urbanization.rate,l=e(a+c),u=`Believers: ${o(l)}; Rural areas: ${o(a)}; Urban areas: ${o(c)}. Click to change`;if(!i.i){r+=`<div
        class="states"
        data-id="${i.i}"
        data-name="${i.name}"
        data-color=""
        data-area="${t}"
        data-population="${l}"
        data-type=""
        data-form=""
        data-deity=""
        data-expansion=""
        data-expansionism=""
      >
        <svg width="9" height="9" class="placeholder" data-col="color"></svg>
        <input data-tip="Religion name. Click and type to change" class="religionName italic"
          value="${i.name}" autocorrect="off" spellcheck="false" data-col="name" />
        <select data-tip="Religion type" class="religionType placeholder" data-col="type">
          ${B(i.type)}
        </select>
        <input data-tip="Religion form" class="religionForm placeholder" value="" autocorrect="off" spellcheck="false" data-col="form" />
        <div data-col="deity">
          <span class="icon-arrows-cw placeholder"></span>
          <input class="religionDeity placeholder" value="" autocorrect="off" spellcheck="false" />
        </div>
        <div data-col="area">
          <span data-tip="Religion area" style="padding-right: 4px" class="icon-map-o"></span>
          <div data-tip="Religion area" class="religionArea">${o(t)+n}</div>
        </div>
        <div data-col="population">
          <span data-tip="${u}" class="icon-male"></span>
          <div data-tip="${u}" class="religionPopulation pointer">${o(l)}</div>
        </div>
        <div data-col="expansion">
          <span class="icon-resize-full-alt placeholder" style="padding-right: 2px"></span>
          <span class="religionExtent placeholder">n/a</span>
        </div>
        <div data-col="expansionism">
          <span class="icon-resize-full placeholder"></span>
          <input class="religionExpantion placeholder" disabled type="number" value="0" />
        </div>
        <div data-col="note"></div>
        <div data-col="locate"></div>
        <div data-col="lock"></div>
        <div data-col="remove"></div>
      </div>`;continue}r+=`<div
      class="states"
      data-id=${i.i}
      data-name="${i.name}"
      data-color="${i.color}"
      data-area=${t}
      data-population=${l}
      data-type="${i.type}"
      data-form="${i.form}"
      data-deity="${i.deity||``}"
      data-expansion="${i.expansion}"
      data-expansionism="${i.expansionism}"
    >
      <fill-box fill="${i.color}" data-col="color"></fill-box>
      <input data-tip="Religion name. Click and type to change" class="religionName"
        value="${i.name}" autocorrect="off" spellcheck="false" data-col="name" />
      <select data-tip="Religion type" class="religionType" data-col="type">
        ${B(i.type)}
      </select>
      <input data-tip="Religion form" class="religionForm"
        value="${i.form}" autocorrect="off" spellcheck="false" data-col="form" />
      <div data-col="deity">
        <span data-tip="Click to re-generate supreme deity" class="icon-arrows-cw pointer"></span>
        <input data-tip="Religion supreme deity" class="religionDeity"
          value="${i.deity||``}" autocorrect="off" spellcheck="false" />
      </div>
      <div data-col="area">
        <span data-tip="Religion area" style="padding-right: 4px" class="icon-map-o"></span>
        <div data-tip="Religion area" class="religionArea">${o(t)+n}</div>
      </div>
      <div data-col="population">
        <span data-tip="${u}" class="icon-male"></span>
        <div data-tip="${u}" class="religionPopulation pointer">${o(l)}</div>
      </div>
      ${V(i)}
      ${re.getIcon(`this religion`)}
      <span data-col="locate" data-tip="Locate the religion" class="icon-target"></span>
      <span data-col="lock" data-tip="Lock this religion" class="icon-lock${i.lock?``:`-open`}"></span>
      <span data-col="remove" data-tip="Remove religion" class="icon-trash-empty"></span>
    </div>`}let c=u(`religionsBody`);c.querySelectorAll(`:scope > .states`).forEach(e=>{e.remove()}),c.insertAdjacentHTML(`beforeend`,r);let l=pack.religions.filter(e=>e.i&&!e.removed);u(`religionsOrganized`).innerHTML=String(l.filter(e=>e.type===`Organized`).length),u(`religionsHeresies`).innerHTML=String(l.filter(e=>e.type===`Heresy`).length),u(`religionsCults`).innerHTML=String(l.filter(e=>e.type===`Cult`).length),u(`religionsFolk`).innerHTML=String(l.filter(e=>e.type===`Folk`).length),u(`religionsFooterArea`).innerHTML=o(i)+n,u(`religionsFooterPopulation`).innerHTML=o(a),u(`religionsFooterArea`).dataset.area=String(i),u(`religionsFooterPopulation`).dataset.population=String(a),oe(u(`religionsFooter`),t,P.goto),u(`religionsBody`).querySelectorAll(`:scope > .states`).forEach(e=>{e.addEventListener(`mouseenter`,U),e.addEventListener(`mouseleave`,W)}),u(`religionsBody`).querySelectorAll(`fill-box`).forEach(e=>void e.addEventListener(`click`,ue)),u(`religionsBody`).querySelectorAll(`div > input.religionName`).forEach(e=>void e.addEventListener(`input`,de)),u(`religionsBody`).querySelectorAll(`div > select.religionType`).forEach(e=>void e.addEventListener(`change`,fe)),u(`religionsBody`).querySelectorAll(`div > input.religionForm`).forEach(e=>void e.addEventListener(`input`,pe)),u(`religionsBody`).querySelectorAll(`div > input.religionDeity`).forEach(e=>void e.addEventListener(`input`,me)),u(`religionsBody`).querySelectorAll(`div > span.icon-arrows-cw`).forEach(e=>void e.addEventListener(`click`,he)),u(`religionsBody`).querySelectorAll(`div > div.religionPopulation`).forEach(e=>void e.addEventListener(`click`,ge)),u(`religionsBody`).querySelectorAll(`div > select.religionExtent`).forEach(e=>void e.addEventListener(`change`,_e)),u(`religionsBody`).querySelectorAll(`div > input.religionExpantion`).forEach(e=>void e.addEventListener(`change`,ve)),u(`religionsBody`).querySelectorAll(`div > span.icon-trash-empty`).forEach(e=>void e.addEventListener(`click`,ye)),u(`religionsBody`).querySelectorAll(`div > span.icon-book`).forEach(e=>void e.addEventListener(`click`,Oe)),u(`religionsBody`).querySelectorAll(`div > span.icon-target`).forEach(e=>void e.addEventListener(`click`,ke)),u(`religionsBody`).querySelectorAll(`div > span.icon-lock`).forEach(e=>void e.addEventListener(`click`,Z)),u(`religionsBody`).querySelectorAll(`div > span.icon-lock-open`).forEach(e=>void e.addEventListener(`click`,Z)),u(`religionsBody`).dataset.type===`percentage`&&(u(`religionsBody`).dataset.type=`absolute`,K()),T(O,{width:`fit-content`,position:A})}function B(e){let t=``;return[`Folk`,`Organized`,`Cult`,`Heresy`].forEach(n=>{t+=`<option ${e===n?`selected`:``} value="${n}">${n}</option>`}),t}function V(e){if(e.type===`Folk`){let e=`Folk religions are not competitive and do not expand. Initially they cover all cells of their parent culture, but get ousted by organized religions when they expand`;return`
      <div data-col="expansion">
        <span data-tip="${e}" class="icon-resize-full-alt" style="padding-right: 2px"></span>
        <span data-tip="${e}" class="religionExtent">culture</span>
      </div>
      <div data-col="expansionism">
        <span data-tip="${e}" class="icon-resize-full"></span>
        <input data-tip="${e}" class="religionExpantion" disabled type="number" value='0' />
      </div>`}return`
    <div data-col="expansion">
      <span data-tip="Potential religion extent" class="icon-resize-full-alt" style="padding-right: 2px"></span>
      <select data-tip="Potential religion extent" class="religionExtent">
        ${H(e.expansion)}
      </select>
    </div>
    <div data-col="expansionism">
      <span data-tip="Religion expansionism. Defines competitive size" class="icon-resize-full"></span>
      <input
        data-tip="Religion expansionism. Defines competitive size. Click to change, then click Recalculate to apply change"
        class="religionExpantion"
        type="number"
        min="0"
        max="99"
        step=".1"
        value=${e.expansionism}
      />
    </div>`}function H(e){let t=``;return[`global`,`state`,`culture`].forEach(n=>{t+=`<option ${e===n?`selected`:``} value="${n}">${n}</option>`}),t}var U=n(e=>{let t=Number(e.id||e.target.dataset.id),n=u(`religionsBody`).querySelector(`div[data-id='${t}']`);if(n&&n.classList.add(`active`),!_.isOn(`religions`)||customization)return;let r=a().duration(2e3).ease(te);l(`#relig`).select(`#religion${t}`).raise().transition(r).attr(`stroke-width`,2.5).attr(`stroke`,`#d0240f`),l(`#debug`).select(`#religionsCenter${t}`).raise().transition(r).attr(`r`,3).attr(`stroke`,`#d0240f`)},200);function W(e){let t=Number(e.id||e.target.dataset.id),n=u(`religionsBody`).querySelector(`div[data-id='${t}']`);n&&n.classList.remove(`active`),l(`#relig`).select(`#religion${t}`).transition().attr(`stroke-width`,null).attr(`stroke`,null),l(`#debug`).select(`#religionsCenter${t}`).transition().attr(`r`,2).attr(`stroke`,null)}function ue(){let e=this.getAttribute(`fill`)||`#ffffff`,t=+this.parentNode.dataset.id;x.ColorPicker.open(e,e=>{this.fill=e,pack.religions[t].color=e,l(`#relig`).select(`#religion${t}`).attr(`fill`,e),l(`#debug`).select(`#religionsCenter${t}`).attr(`fill`,e)})}function de(){let e=+this.parentNode.dataset.id;this.parentNode.dataset.name=this.value;let t=pack.religions;t[e].name=this.value,t[e].code=c(this.value,t.flatMap(e=>e.code?[e.code]:[]))}function fe(){let e=+this.parentNode.dataset.id;this.parentNode.dataset.type=this.value;let t=this.value;pack.religions[e].type=t}function pe(){let e=+this.parentNode.dataset.id;this.parentNode.dataset.form=this.value,pack.religions[e].form=this.value}function me(){let e=this.closest(`.states`),t=+e.dataset.id;e.dataset.deity=this.value,pack.religions[t].deity=this.value}function he(){let e=this.closest(`.states`),t=+e.dataset.id,n=pack.religions[t].culture,r=Religions.getDeityName(n)??``;e.dataset.deity=r,pack.religions[t].deity=r,this.nextElementSibling.value=r}function ge(){let t=+this.closest(`.states`).dataset.id,n=pack.religions[t];if(!n.cells){v(`Religion does not have any cells, cannot change population`,!1,`error`);return}let r=e((n.rural??0)*options.map.units.population.scale),i=e((n.urban??0)*options.map.units.population.scale*options.map.units.population.urbanization.rate),a=r+i,o=e=>Number(e).toLocaleString(),s=pack.burgs.filter(e=>!e.removed&&pack.cells.religion[e.cell]===t);alertMessage.innerHTML=`<div>
    <i>All population of religion territory is considered believers of this religion. It means believers number change will directly affect population</i>
    <div style="margin: 0.5em 0">
      Rural: <input type="number" min="0" step="1" id="ruralPop" value=${r} style="width:6em" />
      Urban: <input type="number" min="0" step="1" id="urbanPop" value=${i} style="width:6em"
        ${s.length?``:`disabled`} />
    </div>
    <div>Total population: ${o(a)} ⇒ <span id="totalPop">${o(a)}</span>
      (<span id="totalPopPerc">100</span>%)
    </div>
  </div>`;let c=u(`ruralPop`),l=u(`urbanPop`),d=u(`totalPop`),f=u(`totalPopPerc`),p=()=>{let t=c.valueAsNumber+l.valueAsNumber;Number.isNaN(t)||(d.innerHTML=o(t),f.innerHTML=String(e(t/a*100)))};c.oninput=()=>p(),l.oninput=()=>p(),$(`#alert`).dialog({resizable:!1,title:`Change believers number`,width:`24em`,buttons:{Apply:function(){m(),$(this).dialog(`close`)},Cancel:function(){$(this).dialog(`close`)}},position:{my:`center`,at:`center`,of:`svg`}});function m(){let n=+c.value/r;if(Number.isFinite(n)&&n!==1&&pack.cells.i.filter(e=>pack.cells.religion[e]===t).forEach(e=>{pack.cells.pop[e]*=n}),!Number.isFinite(n)&&+c.value>0){let n=+c.value/options.map.units.population.scale,r=pack.cells.i.filter(e=>pack.cells.religion[e]===t),i=e(n/r.length);r.forEach(e=>{pack.cells.pop[e]=i})}let a=+l.value/i;if(Number.isFinite(a)&&a!==1&&s.forEach(t=>{t.population=e((t.population??0)*a,4)}),!Number.isFinite(a)&&+l.value>0){let t=e(+l.value/options.map.units.population.scale/options.map.units.population.urbanization.rate/s.length,4);s.forEach(e=>{e.population=t})}_.draw(`population`),L()}}function _e(){let e=this.closest(`.states`),t=+e.dataset.id;e.dataset.expansion=this.value,pack.religions[t].expansion=this.value,Q()}function ve(){let e=this.closest(`.states`),t=+e.dataset.id;e.dataset.expansionism=this.value,pack.religions[t].expansionism=+this.value,Q()}function ye(){if(customization)return;let e=+this.closest(`.states`).dataset.id;C({title:`Remove religion`,message:`Are you sure you want to remove the religion? <br>This action cannot be reverted`,confirm:`Remove`,onConfirm:()=>be(e)})}function be(e){l(`#relig`).select(`#religion${e}`).remove(),l(`#relig`).select(`#religion-gap${e}`).remove(),l(`#debug`).select(`#religionsCenter${e}`).remove(),pack.cells.religion.forEach((t,n)=>{t===e&&(pack.cells.religion[n]=0)}),pack.religions[e].removed=!0,pack.religions.filter(e=>e.i&&!e.removed).forEach(t=>{t.origins=(t.origins??[]).filter(t=>t!==e),t.origins.length||(t.origins=[0])}),L()}function G(){let e=l(`#debug`);e.select(`#religionCenters`).remove();let t=e.append(`g`).attr(`id`,`religionCenters`).attr(`stroke-width`,.8).attr(`stroke`,`#444444`).style(`cursor`,`move`),n=pack.religions.filter(e=>e.i&&e.center&&!e.removed);j.showExtinct||(n=n.filter(e=>(e.cells??0)>0)),t.selectAll(`circle`).data(n).enter().append(`circle`).attr(`id`,e=>`religionsCenter${e.i}`).attr(`data-id`,e=>e.i).attr(`r`,2).attr(`fill`,e=>e.color).attr(`cx`,e=>pack.cells.p[e.center][0]).attr(`cy`,e=>pack.cells.p[e.center][1]).on(`mouseenter`,(e,t)=>{v(`${t.name}. Drag to move the religion center`,!0),U(e)}).on(`mouseleave`,e=>{v(``,!0),W(e)}).call(ee().on(`start`,xe))}function xe(e){let t=+this.dataset.id,r=d(this.getAttribute(`transform`)),i=+r[0]-e.x,a=+r[1]-e.y;function o(e){let{x:n,y:r}=e;this.setAttribute(`transform`,`translate(${i+n},${a+r})`);let o=Pack.findCell(n,r);o==null||pack.cells.h[o]<20||(pack.religions[t].center=o,Q())}let s=n(o,50);e.on(`drag`,s)}function Se(){if(g(k)){h(k);return}let e=pack.religions.filter(e=>e.i&&!e.removed&&e.area).sort((e,t)=>(t.area??0)-(e.area??0)).map(e=>[e.i,e.color,e.name]);if(!e.length)return void v(`No religions to show`,!1,`error`);m(k,e)}function K(){if(u(`religionsBody`).dataset.type===`absolute`){u(`religionsBody`).dataset.type=`percentage`;let t=+u(`religionsFooterArea`).dataset.area,n=+u(`religionsFooterPopulation`).dataset.population;u(`religionsBody`).querySelectorAll(`:scope > .states`).forEach(r=>{let{area:i,population:a}=r.dataset;r.querySelector(`.religionArea`).innerText=`${e(+i/t*100)}%`,r.querySelector(`.religionPopulation`).innerText=`${e(+a/n*100)}%`})}else u(`religionsBody`).dataset.type=`absolute`,P.refresh()}async function q(){customization||x.HierarchyTree.open({type:`religions`,data:pack.religions,onNodeEnter:U,onNodeLeave:W,getDescription:t=>{let{name:n,type:r,form:i,rural:a,urban:s}=t,c=()=>n.includes(r)||i.includes(r)?``:r===`Folk`||r===`Organized`?`. ${r} religion`:`. ${r}`,l=i===r?``:`. ${i}`,u=a*options.map.units.population.scale+s*options.map.units.population.scale*options.map.units.population.urbanization.rate,d=u>0?`${o(e(u))} people`:`Extinct`;return`${n}${c()}${l}. ${d}`},getShape:({type:e})=>{if(e===`Folk`)return`circle`;if(e===`Organized`)return`square`;if(e===`Cult`)return`hexagon`;if(e===`Heresy`)return`diamond`}})}function Ce(){j.showExtinct=!j.showExtinct,b.set(O,`filters`,j),J(),P.reset(),G()}function J(){u(`religionsBody`).dataset.extinct=j.showExtinct?`show`:`hide`,u(`religionsExtinct`).classList.toggle(`active`,j.showExtinct)}function we(){_.show(`religions`),x.PaintEditor.open({title:`Paint Religions`,parentDialogId:O,onClose:F,items:pack.religions.filter(e=>!e.removed&&(!e.i||e.cells)).map(e=>({id:e.i,name:e.name,color:e.color||`#ffffff`})),dontOverrideControl:!0,getValue:e=>pack.cells.religion[e],filterCell:e=>t(e,pack),onApply:Te})}function Te(e){for(let[t,n]of e)pack.cells.religion[t]=n;e.size&&(_.draw(`religions`),document.getElementById(O)&&L(),G())}function Ee(){if(this.classList.contains(`pressed`)){Y();return}customization=8,this.classList.add(`pressed`),v(`Click on the map to add a new religion`,!0),l(`#viewbox`).style(`cursor`,`crosshair`).on(`click`,X),u(`religionsBody`).querySelectorAll(`div > input, select, span, svg`).forEach(e=>{e.style.pointerEvents=`none`})}function Y(){customization=0,S(),y(),u(`religionsBody`).querySelectorAll(`div > input, select, span, svg`).forEach(e=>{e.style.removeProperty(`pointer-events`)});let e=u(`religionsAdd`);e.classList.contains(`pressed`)&&e.classList.remove(`pressed`)}function X(e){let[t,n]=r(e,this),i=Pack.findCell(t,n);if(pack.cells.h[i]<20){v(`You cannot place religion center into the water. Please click on a land cell`,!1,`error`);return}if(pack.religions.some(e=>!e.removed&&e.center===i)){v(`This cell is already a religion center. Please select a different cell`,!1,`error`);return}e.shiftKey===!1&&Y(),Religions.add(i),_.draw(`religions`),L(),G()}function De(){let t=`Id,Name,Color,Type,Form,Supreme Deity,Area ${f(`2`)},Believers,Origins,Potential,Expansionism`,n=P.view().all.map(t=>{let n=s(t.area??0),r=e((t.rural??0)*options.map.units.population.scale+(t.urban??0)*options.map.units.population.scale*options.map.units.population.urbanization.rate),i=`"${t.deity||``}"`,a=`"${(t.origins??[]).filter(e=>!!e).map(e=>pack.religions[e].name).join(`, `)}"`;return[t.i,t.name,t.color??``,t.type??``,t.form??``,i,n,r,a,t.expansion??``,t.i?t.expansionism??``:``].join(`,`)});i([t].concat(n).join(`
`),`${p(`Religions`)}.csv`)}function Oe(){let e=+this.closest(`.states`).dataset.id;x.NotesEditor.open({type:`religion`,id:e})}function ke(){let e=+this.closest(`.states`).dataset.id,t=l(`#relig`).select(`#religion${e}`).node();t&&ne(t,4)}function Z(){if(customization)return;let e=+this.closest(`.states`).dataset.id,t=this.classList,n=pack.religions[e];n.lock=!n.lock,t.toggle(`icon-lock-open`),t.toggle(`icon-lock`)}function Q(e){!e&&!u(`religionsAutoChange`).checked||(Religions.recalculate(),_.draw(`religions`),L(),G())}function Ae(){l(`#debug`).select(`#religionCenters`).remove(),customization===8&&Y(),x.ColorPicker.close();let e=P.view();e.rows=[],e.all=[],$(`#religionsEditor`).dialog(`destroy`),u(`religionsEditor`).remove()}var je={open:F,showHierarchy:q};export{je as ReligionsEditor};