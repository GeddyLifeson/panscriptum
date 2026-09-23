import{Et as e,M as t,_ as n,a as r,bn as i,f as a,hn as o,j as s,nt as c,o as l}from"./utils-Cob8vHf9.js";import{B as u,t as d}from"./layers-Bh4OWBXX.js";import{t as f}from"./mean-4Awewi9R.js";import{i as p}from"./tooltips-BTSHGd98.js";import{t as m}from"./controllers-DnVd8NhQ.js";import{H as h,lt as g,s as _,st as v,vt as y}from"./index-DsIn6sTp.js";function b(e){for(var t=-1,n=e.length,r=e[n-1],i,a,o=r[0],s=r[1],c=0;++t<n;)i=o,a=s,r=e[t],o=r[0],s=r[1],i-=o,a-=s,c+=Math.hypot(i,a);return c}var x;function S(e){customization||(v(`.stable`),d.hide(`cells`),C(),x=o(e),T(),M(),$(`#lakeEditor`).dialog({title:`Edit Lake`,resizable:!1,position:{my:`center top+20`,at:`top`,of:`svg`,collision:`fit`},close:z}))}function C(){g(`lakeEditor`);let e=`<div id="lakeEditor" class="dialog">
    <div id="lakeBody" style="padding-bottom: 0.3em">
      <div>
        <div class="label" style="width: 4.8em">Name:</div>
        <span id="lakeNameCulture" data-tip="Generate culture-specific name for the lake" class="icon-book pointer"></span>
        <span id="lakeNameRandom" data-tip="Generate random name for the lake" class="icon-globe pointer"></span>
        <input id="lakeName" data-tip="Type to rename the lake" autocorrect="off" spellcheck="false" />
        <span id="lakeNameSpeak" data-tip="Speak the name. You can change voice and language in options" class="speaker">🔊</span>
      </div>
      <div data-tip="Lake subtype. Generators read it: burgs cannot port on dry, frozen or lava lakes">
        <div class="label" style="width: 7em">Subtype:</div>
        <select id="lakeSubtype" data-tip="Select lake subtype">
          ${y.map(e=>`<option value="${e}">${e}</option>`).join(``)}
        </select>
      </div>
      <div data-tip="Rendering group: the svg group the lake is drawn in. Does not affect generation">
        <div class="label" style="width: 4.8em">Group:</div>
        <span id="lakeGroupRemove" data-tip="Remove the group" class="icon-trash-empty pointer"></span>
        <span id="lakeGroupAdd" data-tip="Create a new group for the lake" class="icon-plus pointer"></span>
        <select id="lakeGroup" data-tip="Select lake rendering group"></select>
        <input id="lakeGroupName" placeholder="group name" data-tip="Provide a name for the new group" style="display: none" />
        <span id="lakeEditStyle" data-tip="Edit lake group style in Style Editor" class="icon-brush pointer"></span>
      </div>
      <div data-tip="Lake area in selected units">
        <div class="label">Area:</div>
        <input id="lakeArea" disabled />
      </div>
      <div data-tip="Lake shore length in selected units">
        <div class="label">Shore length:</div>
        <input id="lakeShoreLength" disabled />
      </div>
      <div data-tip="Lake elevation in selected units">
        <div class="label">Elevation:</div>
        <input id="lakeElevation" disabled />
      </div>
      <div data-tip="Lake average depth in selected units">
        <div class="label">Average depth:</div>
        <input id="lakeAverageDepth" disabled />
      </div>
      <div data-tip="Lake maximum depth in selected units">
        <div class="label">Max depth:</div>
        <input id="lakeMaxDepth" disabled />
      </div>
      <div data-tip="Lake water supply. If supply > evaporation and there is an outlet, the lake water is fresh. If supply is very low, the lake becomes dry">
        <div class="label">Supply:</div>
        <input id="lakeFlux" disabled />
      </div>
      <div data-tip="Evaporation from lake surface. If evaporation > supply, the lake water is saline. If difference is high, the lake becomes dry">
        <div class="label">Evaporation:</div>
        <input id="lakeEvaporation" disabled />
      </div>
      <div data-tip="Number of lake inlet rivers">
        <div class="label">Inlets:</div>
        <input id="lakeInlets" disabled />
      </div>
      <div data-tip="Lake outlet river">
        <div class="label">Outlet:</div>
        <input id="lakeOutlet" disabled />
      </div>
    </div>
    <div id="lakeBottom">
      ${h.getButton(`lakeLegend`,`this lake`)}
    </div>
  </div>`;s(`dialogs`).insertAdjacentHTML(`beforeend`,e),s(`lakeName`).addEventListener(`input`,E),s(`lakeNameSpeak`).addEventListener(`click`,()=>c(s(`lakeName`).value)),s(`lakeNameCulture`).addEventListener(`click`,D),s(`lakeNameRandom`).addEventListener(`click`,O),s(`lakeSubtype`).addEventListener(`change`,k),s(`lakeGroup`).addEventListener(`change`,N),s(`lakeGroupAdd`).addEventListener(`click`,P),s(`lakeGroupName`).addEventListener(`change`,F),s(`lakeGroupRemove`).addEventListener(`click`,I),s(`lakeEditStyle`).addEventListener(`click`,L),s(`lakeLegend`).addEventListener(`click`,R)}function w(){let e=+x.attr(`data-f`);return pack.features.find(t=>t.i===e)}function T(){let{cells:e,vertices:t,rivers:o}=pack,c=w();s(`lakeName`).value=c.name,s(`lakeSubtype`).value=c.subtype||`freshwater`,s(`lakeArea`).value=`${n(r(c.area))} ${l()}`;let u=b(c.vertices.map(e=>t.p[e]));s(`lakeShoreLength`).value=`${n(u*options.map.units.distance.scale)} ${options.map.units.distance.unit}`;let d=Array.from(e.i.filter(t=>e.f[t]===c.i)).map(t=>e.h[t]);s(`lakeElevation`).value=a(c.height),s(`lakeAverageDepth`).value=a(f(d)??0,!0),s(`lakeMaxDepth`).value=a(i(d)??0,!0),s(`lakeFlux`).value=String(c.flux),s(`lakeEvaporation`).value=String(c.evaporation);let p=c.inlets?.map(e=>o.find(t=>t.i===e)?.name),m=c.outlet?o.find(e=>e.i===c.outlet)?.name:`no`,h=s(`lakeInlets`);h.value=p?String(p.length):`no`,h.title=p?p.join(`, `):``,s(`lakeOutlet`).value=m??`no`}function E(){w().name=this.value}function D(){let e=w();e.name=s(`lakeName`).value=Features.getName(e)}function O(){let t=w();t.name=s(`lakeName`).value=Names.getBase(e(Names.nameBases.length-1))}function k(){w().subtype=this.value}var A=e=>e in _.defaults.lakes.groups;function j(e,t){for(let n of e){if(!n.hasAttribute(`data-f`))continue;let e=pack.features[+(n.getAttribute(`data-f`)||0)];e&&(e.group=t)}}function M(){let e=w().group,t=s(`lakeGroup`);t.options.length=0,o(`#lakes`).selectAll(`g`).each(function(){t.options.add(new Option(this.id,this.id,!1,this.id===e))})}function N(){s(this.value).appendChild(x.node()),j([x.node()],this.value),u(d.get(`lakes`))}function P(){let e=s(`lakeGroupName`),t=s(`lakeGroup`);e.style.display===`none`?(e.style.display=`inline-block`,e.focus(),t.style.display=`none`):(e.style.display=`none`,t.style.display=`inline-block`)}function F(){if(!this.value){p(`Please provide a valid group name`);return}let e=this.value.toLowerCase().replace(/ /g,`_`).replace(/[^\w\s]/gi,``);if(t(e)){p(`Element with this id already exists. Please provide a unique name`,!1,`error`);return}if(Number.isFinite(+e.charAt(0))){p(`Group name should start with a letter`,!1,`error`);return}let n=x.node().parentNode,r=styles.lakes.groups[n.id]||styles.lakes.groups.freshwater;if(styles.lakes.groups[e]??=structuredClone(r),!A(n.id)&&n.childElementCount===1){s(`lakeGroup`).selectedOptions[0].remove(),s(`lakeGroup`).options.add(new Option(e,e,!1,!0)),n.id!==e&&delete styles.lakes.groups[n.id],n.id=e,n.dataset.group=e,j(Array.from(n.children),e),u(d.get(`lakes`)),P(),s(`lakeGroupName`).value=``;return}let i=x.node().parentNode.cloneNode(!1);s(`lakes`).appendChild(i),i.id=e,i.dataset.group=e,s(`lakeGroup`).options.add(new Option(e,e,!1,!0)),s(e).appendChild(x.node()),j([x.node()],e),u(d.get(`lakes`)),P(),s(`lakeGroupName`).value=``}function I(){let e=x.node().parentNode.id;if(A(e)){p(`This is one of the default groups, it cannot be removed`,!1,`error`);return}let t=x.node().parentNode.querySelectorAll(`use[data-f]`).length;alertMessage.innerHTML=`Are you sure you want to remove the group? All lakes of the group (${t}) will be turned into Freshwater`,$(`#alert`).dialog({resizable:!1,title:`Remove lake group`,width:`26em`,buttons:{Remove:function(){$(this).dialog(`close`);let t=s(`freshwater`),n=s(e);for(j(Array.from(n.children),`freshwater`);n.childNodes.length;)t.appendChild(n.childNodes[0]);n.remove(),u(d.get(`lakes`)),delete styles.lakes.groups[e],s(`lakeGroup`).selectedOptions[0].remove(),s(`lakeGroup`).value=`freshwater`},Cancel:function(){$(this).dialog(`close`)}}})}function L(){let e=x.node().parentNode.id;editStyle(`lakes`,e)}function R(){m.NotesEditor.open({type:`feature`,id:w().i})}function z(){g(`lakeEditor`),x=null}var B={open:S};export{B as LakesEditor};