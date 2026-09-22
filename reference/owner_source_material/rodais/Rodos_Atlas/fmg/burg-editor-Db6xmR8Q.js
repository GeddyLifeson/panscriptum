import{Bn as e,Et as t,P as n,Rn as r,et as i,f as a,h as o,hn as s,j as c,n as l,nt as u}from"./utils-Cob8vHf9.js";import{J as d,Z as ee,t as f}from"./layers-Bh4OWBXX.js";import{i as p,t as m}from"./tooltips-BTSHGd98.js";import{t as h}from"./controllers-DnVd8NhQ.js";import{H as te,V as ne,ct as re,lt as ie,st as g}from"./index-DsIn6sTp.js";var _={k:1,x:0,y:0};function v({k:e,x:t,y:n},i){return{k:e,x:r(t,i.width*(1-e),0),y:r(n,i.height*(1-e),0)}}function y(e,t,n,i,a=32){let o=r(e.k*n,1,Math.max(1,a)),s=o/e.k;return v({k:o,x:t.x-(t.x-e.x)*s,y:t.y-(t.y-e.y)*s},i)}function ae(e,t,n,r){return v({k:e.k,x:e.x+t,y:e.y+n},r)}var b=null,x=null,S={..._},C=32,w=1,T=0,E=!1;function oe(e){customization||(g(`.stable`),f.show(`burgIcons`,`labels`),x=+e,b=s(`#labels`).select(`[data-label-type='burg'][data-id='${e}']`),b.size()||(b=s(`#burgIcons`).select(`[data-id='${e}']`)),se(),ce(),le(),$(`#burgEditor`).dialog({title:`Edit Burg`,resizable:!1,close:Oe,position:{my:`left top`,at:`left+10 top+10`,of:`svg`,collision:`fit`}}))}function se(){ie(`burgEditor`);let e=`<div id="burgEditor" class="dialog" data-burg-id="${D()}">
      <div id="burgBody" style="padding-bottom: 0.3em">
        <div style="display: flex; align-items: center">
          <svg data-tip="Burg emblem. Click to edit" class="pointer" viewBox="0 0 200 200" width="13em" height="13em">
            <use id="burgEmblem"></use>
          </svg>
          <div style="display: grid; grid-auto-rows: minmax(1.6em, auto)">
            <div id="burgProvinceAndState" style="font-weight: bold; max-width: 16em"></div>
            <div>
              <div class="label">Name:</div>
              <input
                id="burgName"
                data-tip="Type to rename the burg"
                autocorrect="off"
                spellcheck="false"
                style="width: 9em"
              />
              <span id="burgNameSpeak" data-tip="Speak the name. You can change voice and language in options" class="speaker">🔊</span>
              <span
                id="burgNameReRandom"
                data-tip="Generate random name for the burg"
                class="icon-globe pointer"
              ></span>
            </div>
            <div data-tip="Select burg group. Groups defines burg icon, label size and style">
              <div class="label">Group:</div>
              <select id="burgGroup" style="width: 9em"></select>
              <span id="burgGroupConfigure" data-tip="Configure burg groups" class="icon-cog pointer"></span>
            </div>
            <div data-tip="Select burg type. Type slightly affects emblem generation">
              <div class="label">Type:</div>
              <select id="burgType" style="width: 9em">
                <option value="Generic">Generic</option>
                <option value="River">River</option>
                <option value="Lake">Lake</option>
                <option value="Naval">Naval</option>
                <option value="Nomadic">Nomadic</option>
                <option value="Hunting">Hunting</option>
                <option value="Highland">Highland</option>
              </select>
            </div>
            <div data-tip="Select dominant culture">
              <div class="label">Culture:</div>
              <select id="burgCulture" style="width: 9em"></select>
              <span
                id="burgNameReCulture"
                data-tip="Generate culture-specific name for the burg"
                class="icon-book pointer"
              ></span>
            </div>
            <div data-tip="Set burg population">
              <div class="label">Population:</div>
              <input id="burgPopulation" type="number" min="0" step="1" style="width: 9em" />
            </div>
            <div data-tip="Burg average yearly temperature" style="display: flex; justify-content: space-between">
              <div>
                <div class="label">Temperature:</div>
                <span id="burgTemperature"></span>
              </div>
              <div style="display: flex; gap: 0.5em">
                <i class="icon-info-circled" id="burgTemperatureLikeIn"></i>
                <i
                  id="burgTemperatureGraph"
                  data-tip="Show temperature graph for the burg"
                  class="icon-chart-area pointer"
                ></i>
              </div>
            </div>
            <div data-tip="Burg height above mean sea level">
              <div class="label">Elevation:</div>
              <span id="burgElevation"></span> above sea level
            </div>
            <div>
              <div class="label">Features:</div>
              <span
                id="burgCapital"
                data-tip="Shows whether the burg is a state capital. Click to toggle"
                data-feature="capital"
                class="burgFeature icon-star"
              ></span>
              <span
                id="burgPort"
                data-tip="Shows whether the burg is a port. Click to toggle"
                data-feature="port"
                class="burgFeature icon-anchor"
              ></span>
              <span
                id="burgCitadel"
                data-tip="Shows whether the burg has a citadel (castle). Click to toggle"
                data-feature="palace"
                class="burgFeature icon-chess-rook"
                style="font-size: 1.1em"
              ></span>
              <span
                id="burgWalls"
                data-tip="Shows whether the burg is walled. Click to toggle"
                data-feature="walls"
                class="burgFeature icon-fort-awesome"
              ></span>
              <span
                id="burgPlaza"
                data-tip="Shows whether the burg is a trade center (market center). Click to toggle"
                data-feature="plaza"
                class="burgFeature icon-store"
                style="font-size: 1em"
              ></span>
              <span
                id="burgTemple"
                data-tip="Shows whether the burg is a religious center. Click to toggle"
                data-feature="temple"
                class="burgFeature icon-chess-bishop"
                style="font-size: 1.1em; margin-left: 3px"
              ></span>
              <span
                id="burgShanty"
                data-tip="Shows whether the burg has a shanty town. Click to toggle"
                data-feature="shanty"
                class="burgFeature icon-campground"
                style="font-size: 1em"
              ></span>
            </div>
            <div data-tip="Burg average daily production">
              <div class="label">Production:</div>
              <span id="burgProduction" style="display: inline-flex; flex-wrap: wrap; column-gap: 0.3em; max-width: 110px;"></span>
            </div>
            <div data-tip="Gross product per population point, daily average">
              <div class="label">Wealth</div>
              <span id="burgWealth"></span>
            </div>
            <div data-tip="Set treasury balance. Production won't be changed automatically">
              <div class="label"><label for="burgTreasury">Treasury:</label></div>
              <input id="burgTreasury" type="number" step="0.01" style="width: 9em" /> 🟡
            </div>
          </div>
        </div>
        <div id="burgPreviewSection" data-tip="Burg map preview: scroll to zoom, drag to pan" style="display: flex; flex-direction: column">
          <div style="display: flex; justify-content: space-between">
            <span>Burg preview:</span>
            <div style="display: flex; gap: 0.5em">
              <i id="burgPreviewReset" data-tip="Reset preview zoom" class="icon-ccw pointer"></i>
              <i id="burgLinkOpen" data-tip="Open burg map in a new tab" class="icon-link-ext pointer"></i>
            </div>
          </div>
          <div
            id="burgPreviewObject"
            style="overflow: hidden; position: relative; touch-action: none; height: 320px; max-width: 60vw; max-height: 60vh"
          ></div>
        </div>
      </div>
      <div id="burgBottom">
        <button id="burgStyleShow" data-tip="Show style edit section" class="icon-brush"></button>
        <div id="burgStyleSection" style="display: none">
          <button id="burgStyleHide" data-tip="Hide style edit section" class="icon-brush"></button>
          <button
            id="burgEditLabelStyle"
            data-tip="Edit label style for burg group in Style Editor"
            class="icon-font"
          ></button>
          <button
            id="burgEditIconStyle"
            data-tip="Edit icon style for burg group in Style Editor"
            class="icon-dot-circled"
          ></button>
          <button
            id="burgEditAnchorStyle"
            data-tip="Edit port icon (anchor) style for burg group in Style Editor"
            class="icon-anchor"
          ></button>
        </div>
        <button id="burgEditLabel" data-tip="Edit this burg label" class="icon-font"></button>
        <button id="burgEditEmblem" data-tip="Edit emblem" class="icon-shield-alt"></button>
        <button id="burgSetPreviewLink" data-tip="Set custom burg map URL" class="icon-map-o"></button>
        <button id="burgLocate" data-tip="Zoom map and center view in the burg" class="icon-target"></button>
        <button
          id="burgProductionOverview"
          data-tip="Show production overview for this burg"
          class="icon-chart-bar"
        ></button>
        <button
          id="burgRelocate"
          data-tip="Relocate burg. Click on map to move the burg"
          class="icon-map-pin"
        ></button>
        ${te.getButton(`burglLegend`,`this burg`)}
        <button id="burgLock" class="icon-lock-open" onmouseover="showElementLockTip(event)"></button>
        <button
          id="burgRemove"
          data-tip="Remove non-capital burg"
          data-shortcut="Delete"
          class="icon-trash fastDelete"
        ></button>
      </div>
    </div>`;c(`dialogs`).insertAdjacentHTML(`beforeend`,e),c(`burgName`).addEventListener(`input`,O),c(`burgNameSpeak`).addEventListener(`click`,()=>u(c(`burgName`).value)),c(`burgNameReRandom`).addEventListener(`click`,ue),c(`burgGroup`).addEventListener(`change`,de),c(`burgGroupConfigure`).addEventListener(`click`,De),c(`burgType`).addEventListener(`change`,k),c(`burgCulture`).addEventListener(`change`,A),c(`burgNameReCulture`).addEventListener(`click`,j),c(`burgPopulation`).addEventListener(`change`,M),c(`burgTreasury`).addEventListener(`change`,N),c(`burgBody`).querySelectorAll(`.burgFeature`).forEach(e=>void e.addEventListener(`click`,P)),c(`burgLinkOpen`).addEventListener(`click`,be),c(`burgPreviewReset`).addEventListener(`click`,G),c(`burgPreviewObject`).addEventListener(`wheel`,he,{passive:!1}),c(`burgPreviewObject`).addEventListener(`dblclick`,ge),c(`burgPreviewObject`).addEventListener(`pointerdown`,_e),c(`burgStyleShow`).addEventListener(`click`,z),c(`burgStyleHide`).addEventListener(`click`,B),c(`burgEditLabelStyle`).addEventListener(`click`,V),c(`burgEditIconStyle`).addEventListener(`click`,pe),c(`burgEditAnchorStyle`).addEventListener(`click`,me),c(`burgEmblem`).addEventListener(`click`,Y),c(`burgSetPreviewLink`).addEventListener(`click`,xe),c(`burgEditEmblem`).addEventListener(`click`,Y),c(`burgLocate`).addEventListener(`click`,Se),c(`burgEditLabel`).addEventListener(`click`,fe),c(`burgRelocate`).addEventListener(`click`,Z),c(`burglLegend`).addEventListener(`click`,we),c(`burgLock`).addEventListener(`click`,L),c(`burgRemove`).addEventListener(`click`,Ee),c(`burgTemperatureGraph`).addEventListener(`click`,Q),c(`burgProductionOverview`).addEventListener(`click`,Te)}function D(){return x??+b.attr(`data-id`)}function ce(){let e=c(`burgGroup`);e.options.length=0;for(let{name:t}of options.map.burgs.groups)e.options.add(new Option(t,t))}function le(){let t=D(),n=pack.burgs[t],r=pack.cells.province[n.cell],i=r?`${pack.provinces[r].fullName}, `:``,s=pack.states[n.state].fullName||pack.states[n.state].name;c(`burgProvinceAndState`).innerHTML=i+s,c(`burgName`).value=n.name,c(`burgGroup`).value=n.group,c(`burgType`).value=n.type||`Generic`,c(`burgPopulation`).value=String(e(n.population*options.map.units.population.scale*options.map.units.population.urbanization.rate)),c(`burgWealth`).innerHTML=`🟡 ${e(n.population>0?(n.product||0)/n.population:0,2)}`,c(`burgTreasury`).value=String(e(n.treasury||0,2)),c(`burgEditAnchorStyle`).style.display=+n.port?`inline-block`:`none`;let u=c(`burgCulture`);u.options.length=0,pack.cultures.filter(e=>!e.removed).forEach(e=>void u.options.add(new Option(e.name,String(e.i),!1,e.i===n.culture)));let d=grid.cells.temp[pack.cells.g[n.cell]];c(`burgTemperature`).innerHTML=l(d),c(`burgTemperatureLikeIn`).dataset.tip=`Average yearly temperature is like in ${o(d)}`,c(`burgElevation`).innerHTML=a(pack.cells.h[n.cell]),c(`burgCapital`).classList.toggle(`inactive`,!n.capital),c(`burgPort`).classList.toggle(`inactive`,!n.port),c(`burgCitadel`).classList.toggle(`inactive`,!n.citadel),c(`burgWalls`).classList.toggle(`inactive`,!n.walls),c(`burgPlaza`).classList.toggle(`inactive`,!n.plaza),c(`burgTemple`).classList.toggle(`inactive`,!n.temple),c(`burgShanty`).classList.toggle(`inactive`,!n.shanty),c(`burgProduction`).innerHTML=ke(Production.getBurgProduction(n)),R();let f=`burgCOA${t}`;ee.trigger(f,n.coa),c(`burgEmblem`).setAttribute(`href`,`#${f}`),J(n)}function O(){let e=D(),t=c(`burgName`).value;pack.burgs[e].name=t,pack.burgs[e].label||(pack.burgs[e].label={}),Object.assign(pack.burgs[e].label,{text:t}),f.draw(`labels`)}function ue(){let e=t(Names.nameBases.length-1);c(`burgName`).value=Names.getBase(e),O()}function de(){let e=D(),t=pack.burgs[e];Burgs.changeGroup(t,this.value),f.draw(`burgIcons`,`labels`)}function k(){let e=D();pack.burgs[e].type=this.value}function A(){let e=D();pack.burgs[e].culture=+this.value}function j(){let e=D(),t=pack.burgs[e].culture;c(`burgName`).value=Names.getCulture(t),O()}function M(){let t=D(),n=pack.burgs[t];pack.burgs[t].population=e(c(`burgPopulation`).valueAsNumber/options.map.units.population.scale/options.map.units.population.urbanization.rate,4),J(n)}function N(){let t=pack.burgs[D()],n=this.valueAsNumber;Number.isFinite(n)?t.treasury=e(n,2):p(`Enter a valid treasury amount`,!1,`error`),this.value=String(e(t.treasury||0,2))}function P(){let e=D(),t=pack.burgs[e],n=this.dataset.feature,r=Number(this.classList.contains(`inactive`));n===`port`?F(e):n===`capital`?I(e):t[n]=r,this.classList.toggle(`inactive`,!t[n]),c(`burgEditAnchorStyle`).style.display=t.port?`inline-block`:`none`,J(t)}function F(e){let t=pack.burgs[e];if(t.port)t.port=0;else{let{cells:e,features:n}=pack,r=e.haven[t.cell],i;if(r){let t=e.f[r],a=n[t];i=a?.type===`lake`&&a.outlet?Rivers.resolveLakeDrainFeature(t)??t:t}else if(i=Rivers.resolveDrainFeature(t.cell),!i){p(`No navigable water body found downstream, cannot assign port`,!1,`warn`);return}t.port=i}f.draw(`burgIcons`)}function I(e){let{burgs:t,states:n}=pack;if(t[e].capital){p(`To change capital please assign a capital status to another burg of this state`,!1,`error`);return}let r=t[e].state;if(!r){p(`Neutral lands cannot have a capital`,!1,`error`);return}let i=n[r].capital;n[r].capital=e,n[r].center=t[e].cell;let a=t[e];a.capital=1,Burgs.changeGroup(a);let o=t[i];o.capital=0,Burgs.changeGroup(o),f.draw(`burgIcons`,`labels`)}function L(){let e=D(),t=pack.burgs[e];t.lock=!t.lock,R()}function R(){let e=D();pack.burgs[e].lock?(c(`burgLock`).classList.remove(`icon-lock-open`),c(`burgLock`).classList.add(`icon-lock`)):(c(`burgLock`).classList.remove(`icon-lock`),c(`burgLock`).classList.add(`icon-lock-open`))}function z(){document.querySelectorAll(`#burgBottom > button`).forEach(e=>{e.style.display=`none`}),c(`burgStyleSection`).style.display=`inline-block`}function B(){document.querySelectorAll(`#burgBottom > button`).forEach(e=>{e.style.display=`inline-block`}),c(`burgStyleSection`).style.display=`none`}function V(){let e=pack.burgs[D()];g(`.stable`),editStyle(`labels`,e.label?.group||e.group)}function fe(){let e=D();$(`#burgEditor`).dialog(`close`),h.LabelsEditor.open(`burg`,e)}function pe(){let e=pack.burgs[D()];g(`.stable`),editStyle(`burgIcons`,e.group)}function me(){let e=pack.burgs[D()];g(`.stable`),editStyle(`anchors`,e.group)}function H(){let e=c(`burgPreviewObject`);return{width:e.clientWidth,height:e.clientHeight}}function U(){let e=c(`burgPreviewObject`),t=e.querySelector(`iframe`);if(!t)return;let{k:n,x:r,y:i}=S;t.style.transformOrigin=`0 0`,t.style.transform=`translate(${r}px, ${i}px) scale(${n/w})`,t.style.left=`0`,t.style.top=`0`,e.style.cursor=n>1?`grab`:`default`,clearTimeout(T),E||(T=window.setTimeout(W,200))}function W(){if(E)return;let e=c(`burgPreviewObject`).querySelector(`iframe`);if(!e)return;let{k:t,x:n,y:r}=S;w=t,e.style.width=`${t*100}%`,e.style.height=`${t*100}%`,e.style.transform=`none`,e.style.left=`${n}px`,e.style.top=`${r}px`}function G(){S={..._},clearTimeout(T),E?U():W(),c(`burgPreviewObject`).style.cursor=`default`}function K(e){let t=c(`burgPreviewObject`).getBoundingClientRect();return{x:e.clientX-t.left,y:e.clientY-t.top}}function he(e){e.preventDefault();let t=Math.exp(-e.deltaY*(e.deltaMode===1?.05:e.deltaMode?1:.002));S=y(S,K(e),t,H(),C),U()}function ge(e){S=y(S,K(e),2,H(),C),U()}function _e(e){if(S.k<=1)return;e.preventDefault();let t=c(`burgPreviewObject`);t.setPointerCapture(e.pointerId),t.style.cursor=`grabbing`;let n={x:e.clientX,y:e.clientY},r=e=>{let t=e;S=ae(S,t.clientX-n.x,t.clientY-n.y,H()),n={x:t.clientX,y:t.clientY},U()},i=()=>{t.removeEventListener(`pointermove`,r),t.removeEventListener(`pointerup`,i),t.removeEventListener(`pointercancel`,i),t.style.cursor=`grab`};t.addEventListener(`pointermove`,r),t.addEventListener(`pointerup`,i),t.addEventListener(`pointercancel`,i)}var q=0;function ve(){if(!q){let e=document.createElement(`canvas`).getContext(`webgl`);q=e?e.getParameter(e.MAX_TEXTURE_SIZE):4096}return q}function ye(){let{width:e,height:t}=H(),n=Math.max(e,t,1);return ve()/2/(devicePixelRatio*n)}function J(e){let t=Burgs.getPreview(e).preview;if(!t){c(`burgPreviewSection`).style.display=`none`;return}c(`burgPreviewSection`).style.display=`block`;let n=c(`burgPreviewObject`);n.innerHTML=``;let r=document.createElement(`iframe`);if(r.style.position=`absolute`,r.style.border=`none`,r.style.pointerEvents=`none`,r.setAttribute(`sandbox`,`allow-scripts allow-same-origin`),r.src=t,n.insertBefore(r,null),E=t.includes(`watabou.github.io`),E){let e=Math.max(1,Math.min(4,ye()));w=e,r.style.width=`${e*100}%`,r.style.height=`${e*100}%`,C=Math.min(32,e*2.5)}else w=1,C=32;G()}function be(){let e=D(),t=pack.burgs[e],n=Burgs.getPreview(t).link;n&&i(n)}function xe(){let e=D(),t=pack.burgs[e];prompt(`Provide custom URL to the burg map. It can be a link to a generator or just an image. Leave empty to use the default map preview`,{default:Burgs.getPreview(t).link||``,required:!1},e=>{e?t.link=String(e):delete t.link,J(t)})}function Y(){let e=D(),t=pack.burgs[e];h.EmblemsEditor.open(`burg`,`burgCOA${e}`,t)}function Se(){let e=D(),t=pack.burgs[e];zoomTo(t.x,t.y,8,2e3)}var X=!1;function Z(){c(`burgRelocate`).classList.toggle(`pressed`),c(`burgRelocate`).classList.contains(`pressed`)?(s(`#viewbox`).style(`cursor`,`crosshair`).on(`click`,Ce),p(`Click on map to relocate burg. Hold Shift for continuous move`,!0),f.isOn(`cells`)||(f.show(`cells`),X=!0)):(m(),ne(),X&&=(f.hide(`cells`),!1))}function Ce(t){let r=pack.cells,i=n(t,this),a=Pack.findCell(i[0],i[1]),o=D(),s=pack.burgs[o];if(r.h[a]<20){p(`Cannot place burg into the water! Select a land cell`,!1,`error`);return}if(r.burg[a]&&r.burg[a]!==o){p(`There is already a burg in this cell. Please select a free cell`,!1,`error`);return}let c=r.state[a];if(c!==s.state&&s.capital){p(`Capital cannot be relocated into another state!`,!1,`error`);return}let l=e(i[0],2),u=e(i[1],2);r.burg[s.cell]=0,r.burg[a]=o,s.cell=a,s.state=c,s.x=l,s.y=u,s.capital&&(pack.states[c].center=s.cell),s.label&&Object.assign(s.label,{dx:0,dy:0,pathPoints:void 0}),f.draw(`burgIcons`,`labels`),t.shiftKey===!1&&Z()}function we(){h.NotesEditor.open({type:`burg`,id:D()})}function Q(){let e=D();h.TemperatureGraph.open(e)}function Te(){let e=D();h.ProductionOverview.open(e)}function Ee(){let e=D();pack.burgs[e].capital?(alertMessage.innerHTML=`You cannot remove the capital. You must change the state capital first`,$(`#alert`).dialog({resizable:!1,title:`Remove burg`,buttons:{Ok:function(){$(this).dialog(`close`)}}})):pack.markets?.some(t=>t.centerBurgId===e)?(alertMessage.innerHTML=`You cannot remove a market center burg. Please remove the market first`,$(`#alert`).dialog({resizable:!1,title:`Remove burg`,buttons:{Ok:function(){$(this).dialog(`close`)}}})):re({title:`Remove burg`,message:`Are you sure you want to remove the burg? <br>This action cannot be reverted`,confirm:`Remove`,onConfirm:()=>{Burgs.remove(e),d(`burg`,e),f.draw(`burgIcons`,`labels`),$(`#burgEditor`).dialog(`close`)}})}function De(){h.BurgGroupEditor.open()}function Oe(){clearTimeout(T),c(`burgRelocate`).classList.contains(`pressed`)&&Z(),b=null,$(`#burgEditor`).dialog(`destroy`),c(`burgEditor`).remove()}function ke(e){if(!e)return``;let t=``,n=Object.entries(e).sort(([,e],[,t])=>t-e);for(let[e,r]of n){let n=Goods.get(+e);if(!n)continue;let{name:i,unit:a,icon:o}=n,s=r===1?a:`${a}s`;t+=`<span data-tip="${i}: ${r} ${s} per day">
      <svg class="resIcon" width="1em" height="1em"><use href="#${o}"></use></svg>
      <span style="margin: 0 0.2em 0 -0.2em">${r}</span>
    </span>`}return t}var Ae={open:oe};export{Ae as BurgEditor};