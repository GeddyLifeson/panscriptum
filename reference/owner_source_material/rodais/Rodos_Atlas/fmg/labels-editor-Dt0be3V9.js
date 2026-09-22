import{Bn as e,Mn as t,P as n,Pt as r,hn as i,j as a,nt as o}from"./utils-Cob8vHf9.js";import{a as s,l as c,s as l,t as u}from"./layers-Bh4OWBXX.js";import{t as d}from"./drag-hfHVCxdY.js";import{t as f}from"./natural-QcNq1h5H.js";import{r as p}from"./viewport-CRAO29Z3.js";import{i as m,r as h}from"./tooltips-BTSHGd98.js";import{t as g}from"./controllers-DnVd8NhQ.js";import{H as _,V as v,W as ee,ct as te,lt as y,st as b}from"./index-DsIn6sTp.js";import{t as x}from"./label-arc-Bqa_qf1E.js";var S=``,C;function w(e,t){if(customization)return;b(`.stable`),u.show(`labels`);let n=document.querySelector(`#labels text[data-label-type='${e}'][data-id='${t}']`);if(!n)return;let r=s(e,t);r&&(C={...r},Q(n.id),i(`#viewbox`).on(`touchmove mousemove`,M),T(),$(`#labelEditor`).dialog({title:`Edit Label`,resizable:!1,width:`fit-content`,position:{my:`center top+10`,at:`bottom`,of:n,collision:`fit`},close:he}),N(),E(C.group),k(),D())}function T(){y(`labelEditor`);let e=`<div id="labelEditor" class="dialog">
      <button id="labelGroupShow" data-tip="Show the group selection" class="icon-tags"></button>
      <div id="labelGroupSection" style="display: none">
        <button id="labelGroupHide" data-tip="Hide the group selection" class="icon-tags"></button>
        <select id="labelGroupSelect" data-tip="Select a group for this label" style="width: 10em"></select>
        <button
          id="labelGroupsConfigure"
          data-tip="Open the Label Groups Configurator to create, edit and reorder groups"
          class="icon-cog"
        ></button>
      </div>
      <button id="labelTextShow" data-tip="Show the edit label text section" class="icon-pencil"></button>
      <div id="labelTextSection" style="display: none">
        <button id="labelTextHide" data-tip="Hide the edit label text section" class="icon-pencil"></button>
        <input
          id="labelText"
          data-tip='Type to change the label. Enter "|" to move to a new line'
          style="width: 12em"
        />
        <span id="labelTextSpeak" data-tip="Speak the name. You can change voice and language in options" class="speaker">🔊</span>
        <span id="labelTextRandom" data-tip="Generate random name" class="icon-shuffle pointer"></span>
      </div>
      <button id="labelEditStyle" data-tip="Edit label group style in Style Editor" class="icon-brush"></button>
      <button id="labelPathToggle"></button>
      <button id="labelSizeShow" data-tip="Show the font size section" class="icon-text-height"></button>
      <div id="labelSizeSection" style="display: none">
        <button id="labelSizeHide" data-tip="Hide the font size section" class="icon-text-height"></button>
        <span data-tip="Set relative size for the particular label">Size:</span>
        <input
          id="labelRelativeSize"
          data-tip="Set relative size for the particular label (% of group default)"
          type="number"
          min="30"
          max="300"
          step="1"
          style="width: 4.5em"
        />
      </div>
      <button id="labelOffsetShow" data-tip="Show the label offset section" class="icon-sliders"></button>
      <div id="labelOffsetSection" style="display: none">
        <button id="labelOffsetHide" data-tip="Hide the label offset section" class="icon-sliders"></button>
        <span data-tip="Set starting offset for the particular label">Offset:</span>
        <input
          id="labelStartOffset"
          data-tip="Set starting offset for the particular label (% along the path)"
          type="range"
          min="20"
          max="80"
          style="width: 8em"
        />
        <input
          id="labelStartOffsetValue"
          type="number"
          min="20"
          max="80"
          step="1"
          style="width: 3.5em"
          data-tip="Set starting offset numerically"
        />
      </div>
      <button id="labelLetterSpacingShow" data-tip="Show the letter spacing section" class="icon-text-width"></button>
      <div id="labelLetterSpacingSection" style="display: none">
        <button
          id="labelLetterSpacingHide"
          data-tip="Hide the letter spacing section"
          class="icon-text-width"
        ></button>
        <slider-input
          id="labelLetterSpacingSize"
          style="display: inline-block"
          data-tip="Set the letter spacing size for this label"
          min="0"
          max="20"
          step=".01"
          value="0"
        ></slider-input>
      </div>
      <button id="labelVisibility"></button>
      ${_.getButton(`labelLegend`,`this label`)}
      <button id="labelReset" data-tip="Restore the default label" class="icon-arrows-cw"></button>
      <button
        id="labelRemoveSingle"
        data-tip="Remove the label"
        data-shortcut="Delete"
        class="icon-trash fastDelete"
      ></button>
    </div>`;a(`dialogs`).insertAdjacentHTML(`beforeend`,e),a(`labelGroupShow`).addEventListener(`click`,B),a(`labelGroupHide`).addEventListener(`click`,V),a(`labelGroupSelect`).addEventListener(`change`,H),a(`labelGroupsConfigure`).addEventListener(`click`,()=>void g.LabelGroupsConfigurator.open()),a(`labelTextShow`).addEventListener(`click`,U),a(`labelTextHide`).addEventListener(`click`,W),a(`labelText`).addEventListener(`input`,G),a(`labelTextSpeak`).addEventListener(`click`,()=>o(a(`labelText`).value)),a(`labelTextRandom`).addEventListener(`click`,q),a(`labelEditStyle`).addEventListener(`click`,ne),a(`labelSizeShow`).addEventListener(`click`,J),a(`labelSizeHide`).addEventListener(`click`,Y),a(`labelOffsetShow`).addEventListener(`click`,X),a(`labelOffsetHide`).addEventListener(`click`,re),a(`labelStartOffset`).addEventListener(`input`,oe),a(`labelStartOffsetValue`).addEventListener(`input`,se),a(`labelRelativeSize`).addEventListener(`input`,ce),a(`labelLetterSpacingShow`).addEventListener(`click`,ie),a(`labelLetterSpacingHide`).addEventListener(`click`,ae),a(`labelLetterSpacingSize`).addEventListener(`input`,le),a(`labelPathToggle`).addEventListener(`click`,ue),a(`labelVisibility`).addEventListener(`click`,de),a(`labelLegend`).addEventListener(`click`,fe),a(`labelReset`).addEventListener(`click`,me),a(`labelRemoveSingle`).addEventListener(`click`,pe)}function E(e){S=e,V();let t=a(`labelGroupSelect`);t.options.length=0;for(let n of options.map.labels.groups)t.options.add(new Option(n.name,n.name,!1,n.name===e))}function D(){let e=O(),t=!a(`labelEditor`).classList.contains(`section-open`);a(`labelOffsetShow`).style.display=t&&e?`inline-block`:`none`,a(`labelRemoveSingle`).style.display=t&&C.type===`added`?`inline-block`:`none`,a(`labelReset`).style.display=t&&Labels.hasOverride(C.type,C.entityId)?`inline-block`:`none`;let n=a(`labelPathToggle`);n.className=e?`icon-resize-horizontal`:`icon-bezier-curve`,n.dataset.tip=e?`Remove the label path, render the label as a straight text`:`Curve the label along a path`;let r=a(`labelVisibility`);r.className=C.hidden?`icon-eye-off`:`icon-eye`,r.dataset.tip=C.hidden?`Show the label`:`Hide the label. You can toggle it on later in Labels Overview`}function O(){return!!C.pathPoints?.length}function k(){let e=C.startOffset||50;a(`labelText`).value=C.text||``,a(`labelStartOffset`).value=String(e),a(`labelStartOffsetValue`).value=String(e),a(`labelRelativeSize`).value=String(C.fontSize??100),a(`labelLetterSpacingSize`).value=String(C.letterSpacing??0)}function A(){a(`labelEditor`).classList.add(`section-open`),document.querySelectorAll(`#labelEditor > button`).forEach(e=>{e.style.display=`none`})}function j(){a(`labelEditor`).classList.remove(`section-open`),document.querySelectorAll(`#labelEditor > button`).forEach(e=>{e.style.display=`inline-block`}),D()}function M(e){h();let t=e.target,n=t.parentNode;t.closest(`#${C.id}`)?m(`Drag to move the label`):n?.id===`controlPoints`&&(t.tagName===`circle`&&m(`Drag to move, click to delete the control point`),t.tagName===`path`&&m(`Click to add a control point`))}function N(){if(i(`#debug`).select(`#controlPoints`).remove(),!O())return;let e=C.dx||C.dy?`translate(${C.dx||0}, ${C.dy||0})`:null;i(`#debug`).append(`g`).attr(`id`,`controlPoints`).attr(`transform`,e).append(`path`).attr(`d`,c(C)).style(`stroke-width`,Math.max(2.2/p.scale,.2)).on(`click`,R),C.pathPoints?.forEach(P)}function P(e){i(`#debug`).select(`#controlPoints`).append(`circle`).attr(`cx`,e[0]).attr(`cy`,e[1]).attr(`r`,Math.max(3/p.scale,.35)).style(`stroke-width`,Math.max(1/p.scale,.15)).call(d().on(`drag`,F)).on(`click`,L)}function F(e){this.setAttribute(`cx`,e.x),this.setAttribute(`cy`,e.y),I()}function I(){let n=[];i(`#debug > #controlPoints`).selectAll(`circle`).each(function(){let t=e(+this.getAttribute(`cx`),2),r=e(+this.getAttribute(`cy`),2);n.push([t,r])});let a=t(r().curve(f)(n)||``);i(`#debug`).select(`#controlPoints > path`).attr(`d`,a),C.pathPoints=n,Z(),n.length||N()}function L(){this.remove(),I()}function R(e){let t=n(e,this),r=[];i(`#debug #controlPoints`).selectAll(`circle`).each(function(){let e=+this.getAttribute(`cx`),n=+this.getAttribute(`cy`);r.push((t[0]-e)**2+(t[1]-n)**2)});let a=r.length;if(r.length>1){let e=r.slice(0).sort((e,t)=>e-t),t=r.indexOf(e[0]),n=r.indexOf(e[1]);a=t<=n?t+1:n+1}let o=`:nth-child(${a+2})`;i(`#debug`).select(`#controlPoints`).insert(`circle`,o).attr(`cx`,t[0]).attr(`cy`,t[1]).attr(`r`,2.5).attr(`stroke-width`,.8).call(d().on(`drag`,F)).on(`click`,L),I()}function z(t){let n=(C.dx||0)-t.x,r=(C.dy||0)-t.y;t.on(`drag`,t=>{C.dx=e(n+t.x,2),C.dy=e(r+t.y,2);let a=`translate(${C.dx}, ${C.dy})`;this.setAttribute(`transform`,a),i(`#debug #controlPoints`).attr(`transform`,a)}),t.on(`end`,()=>Z())}function B(){A(),a(`labelGroupSection`).style.display=`inline-block`}function V(){j(),a(`labelGroupSection`).style.display=`none`}function H(){let e=this.value,t=options.map.labels.groups.find(t=>t.name===e)?.type,n=()=>{S=e,C.group=e,Z()};if(t===C.type)return void n();te({title:`Assign cross-type Label Group`,message:`Assign this ${C.type} label to the ${t} group "${e}"? It's better to avoid such cross-type assignment.`,confirm:`Assign`,onConfirm:n,onCancel:()=>{this.value=C.group}})}function U(){A(),a(`labelTextSection`).style.display=`inline-block`}function W(){j(),a(`labelTextSection`).style.display=`none`}function G(){let e=a(`labelText`).value;C.text=e,Z(),C.type===`state`&&m(`Use States Editor to change the actual state name, not just a label`,!1,`warn`),C.type===`province`&&m(`Use Provinces Editor to change the actual province name, not just a label`,!1,`warn`)}var K={burg:e=>Names.getCulture(pack.burgs[e.entityId].culture??0),state:e=>{let t=pack.states[e.entityId].culture;return Names.getState(Names.getCulture(t,4,7,``),t)},province:e=>{let t=pack.provinces[e.entityId];return Names.getState(t.name,pack.cells.culture[t.center])},added:e=>{let t=Pack.findCell(...e.anchor);return t?Names.getCulture(pack.cells.culture[t]):``},river:e=>{let t=Pack.findCell(...e.anchor);return t?Rivers.getName(t):``},route:e=>{let t=pack.routes.find(t=>t.i===e.entityId)?.points??[];return Routes.generateName({group:e.group,points:t})||`Unnamed route segment`}};function q(){a(`labelText`).value=K[C.type](C),G()}function ne(){editStyle(`labels`,C.group)}function J(){A(),a(`labelSizeSection`).style.display=`inline-block`}function Y(){j(),a(`labelSizeSection`).style.display=`none`}function X(){A(),a(`labelOffsetSection`).style.display=`inline-block`}function re(){j(),a(`labelOffsetSection`).style.display=`none`}function ie(){A(),a(`labelLetterSpacingSection`).style.display=`inline-block`}function ae(){j(),a(`labelLetterSpacingSection`).style.display=`none`}function oe(){if(!O())return;let e=this.value;a(`labelStartOffsetValue`).value=e,C.startOffset=+e,Z(),m(`Label offset: ${e}%`)}function se(){if(!O())return;let e=Math.min(80,Math.max(20,+this.value));a(`labelStartOffset`).value=String(e),this.value=String(e),C.startOffset=e,Z(),m(`Label offset: ${e}%`)}function ce(){C.fontSize=+this.value,Z(),m(`Label relative size: ${this.value}%`)}function le(){C.letterSpacing=+this.value,Z(),m(`Label letter-spacing size: ${this.value}px`)}function ue(){C.pathPoints=O()?[]:x(C),Z(),N()}function de(){C.hidden?delete C.hidden:C.hidden=!0,Z()}function fe(){let e=ee.resolveElement(C.id);e&&g.NotesEditor.open(e)}function pe(){alertMessage.innerHTML=`Are you sure you want to remove the label?`,$(`#alert`).dialog({resizable:!1,title:`Remove label`,buttons:{Remove:function(){$(this).dialog(`close`),C.type===`added`&&(AddedLabels.remove(C.entityId),u.draw(`labels`),$(`#labelEditor`).dialog(`close`))},Cancel:function(){$(this).dialog(`close`)}}})}function Z(){let e=Labels.getEntity(C.type,C.entityId);e&&(e.label=ge(),l(C),Q(C.id),D())}function Q(e){i(`#${e}`).call(d().on(`start`,z)).classed(`draggable`,!0)}function me(){let{type:e,entityId:t}=C;Labels.resetOverride(e,t),u.draw(`labels`),C={...s(e,t)??C},Q(C.id),E(C.group),k(),D(),N()}function he(){i(`#debug`).select(`#controlPoints`).remove(),i(`#${C.id}`).on(`.drag`,null).classed(`draggable`,!1),v(),$(`#labelEditor`).dialog(`destroy`),a(`labelEditor`).remove()}function ge(){return{text:C.text,group:C.group,dx:C.dx,dy:C.dy,fontSize:C.fontSize,letterSpacing:C.letterSpacing,pathPoints:C.pathPoints??[],startOffset:C.startOffset,hidden:C.hidden}}var _e={open:w,getLastSelectedGroup:()=>S};export{_e as LabelsEditor};