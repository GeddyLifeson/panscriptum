import{An as e,B as t,Bn as n,M as r,hn as i,j as a}from"./utils-Cob8vHf9.js";import{M as o,j as s}from"./layers-Bh4OWBXX.js";import{t as c}from"./drag-hfHVCxdY.js";import{t as l}from"./tooltips-BTSHGd98.js";import{t as u}from"./controllers-DnVd8NhQ.js";import{H as d,ct as f,lt as p,st as m,ut as h}from"./index-DsIn6sTp.js";import{t as g}from"./map-placement-BLIMENo_.js";var _,v;function y(e,t){if(customization)return;m(`.stable`);let n=x(e,t);n&&([_,v]=n,i(_).raise().call(c().on(`start`,C)).classed(`draggable`,!0),r(`notesEditor`)&&u.NotesEditor.open({type:`marker`,id:v.i}),b(),w(),$(`#markerEditor`).dialog({title:`Edit Marker`,resizable:!1,position:{my:`left top`,at:`left+10 top+10`,of:`svg`,collision:`fit`},close:V}))}function b(){p(`markerEditor`);let e=`<div id="markerEditor" class="dialog">
    <div id="markerBody" style="padding-bottom: 0.3em">
      <div data-tip="Marker name, shown in the notes editor and overviews">
        <div class="label">Name:</div>
        <input id="markerName" style="width: 10.3em" />
      </div>
      <div data-tip="Marker type. Style changes will apply to all markers of the same type. Leave blank if the marker is unique">
        <div class="label">Type:</div>
        <input id="markerType" style="width: 10.3em" />
      </div>
      <div data-tip="Marker icon" style="display: flex; align-items: center">
        <div class="label">Icon:</div>
        <div id="markerIcon" style="font-size: 1.5em; width: 3.7em">👑</div>
        <button id="markerIconSelect" style="width: 5em">select</button>
      </div>
      <div data-tip="Marker marker element and icon sizes in pixels">
        <div class="label">Size:</div>
        <input data-tip="Marker element size in pixels" id="markerSize" type="number" min="2" max="500" style="width: 5em" />
        <input data-tip="Marker icon sizes in pixels" id="markerIconSize" type="number" min="2" max="20" step="0.5" style="width: 5em" />
      </div>
      <div data-tip="Marker icon shift (by X and by Y axis), percent. Set to 50 to position icon in center">
        <div class="label">Icon shift:</div>
        <input id="markerIconShiftX" type="number" min="0" max="100" step="1" style="width: 5em" />
        <input id="markerIconShiftY" type="number" min="0" max="100" step="1" style="width: 5em" />
      </div>
      <div data-tip="Marker pin shape">
        <div class="label">Pin shape:</div>
        <select id="markerPin" style="width: 10.3em">
          <option value="bubble">Bubble</option>
          <option value="pin">Pin</option>
          <option value="square">Square</option>
          <option value="squarish">Squarish</option>
          <option value="diamond">Diamond</option>
          <option value="hex">Hex</option>
          <option value="hexy">Hexy</option>
          <option value="shieldy">Shieldy</option>
          <option value="shield">Shield</option>
          <option value="pentagon">Pentagon</option>
          <option value="heptagon">Heptagon</option>
          <option value="circle">Circle</option>
          <option value="no">No</option>
        </select>
      </div>
      <div data-tip="Pin fill and stroke colors">
        <div class="label">Pin colors:</div>
        <input id="markerFill" type="color" style="width: 5em; height: 1.6em" />
        <input id="markerStroke" type="color" style="width: 5em; height: 1.6em" />
      </div>
    </div>
    <div id="markerBottom">
      ${d.getButton(`markerNotes`,`this marker`)}
      <button id="markerRadius" data-tip="Show markers within a radius of this one" class="icon-dot-circled"></button>
      <button id="markerLock" class="icon-lock-open" onmouseover="showElementLockTip(event)"></button>
      <button id="markerAdd" data-tip="Add additional marker of that type" class="icon-plus"></button>
      <button id="markerRemove" data-tip="Remove the marker" data-shortcut="Delete" class="icon-trash fastDelete"></button>
    </div>
  </div>`;a(`dialogs`).insertAdjacentHTML(`beforeend`,e),a(`markerName`).addEventListener(`change`,T),a(`markerType`).addEventListener(`change`,E),a(`markerIconSelect`).addEventListener(`click`,D),a(`markerIconSize`).addEventListener(`input`,O),a(`markerIconShiftX`).addEventListener(`input`,k),a(`markerIconShiftY`).addEventListener(`input`,A),a(`markerSize`).addEventListener(`input`,j),a(`markerPin`).addEventListener(`change`,M),a(`markerFill`).addEventListener(`input`,N),a(`markerStroke`).addEventListener(`input`,P),a(`markerNotes`).addEventListener(`click`,F),a(`markerRadius`).addEventListener(`click`,I),a(`markerLock`).addEventListener(`click`,L),a(`markerAdd`).addEventListener(`click`,R),a(`markerRemove`).addEventListener(`click`,z)}function x(e,t){let n=t?Number(t.closest(`svg`)?.id.slice(6)):e,i=pack.markers.find(({i:e})=>e===n);if(!i)return null;o(i);let a=r(`marker${n}`);return a||o(null),a?[a,i]:null}function S(){let e=v.type;return e?pack.markers.filter(({type:t})=>t===e):[v]}function C(e){let t=+this.getAttribute(`x`)-e.x,r=+this.getAttribute(`y`)-e.y;e.on(`drag`,function(e){this.setAttribute(`x`,String(t+e.x)),this.setAttribute(`y`,String(r+e.y))}),e.on(`end`,function(e){let{x:i,y:a}=e;this.setAttribute(`x`,String(n(t+i,2))),this.setAttribute(`y`,String(n(r+a,2)));let o=Number(this.getAttribute(`width`));v.x=n(i+t+o/2,1),v.y=n(a+r+o,1),v.cell=Pack.findCell(v.x,v.y),s()})}function w(){let n=v;a(`markerIcon`).innerHTML=t(n.icon)?`<img src="${e(n.icon)}" style="width: 1em; height: 1em;">`:e(n.icon),a(`markerName`).value=n.name||``,a(`markerType`).value=n.type||``,a(`markerIconSize`).value=String(n.px||12),a(`markerIconShiftX`).value=String(n.dx||50),a(`markerIconShiftY`).value=String(n.dy||50),a(`markerSize`).value=String(n.size||30),a(`markerPin`).value=n.pin||`bubble`,a(`markerFill`).value=n.fill||`#ffffff`,a(`markerStroke`).value=n.stroke||`#000000`,a(`markerLock`).className=n.lock?`icon-lock`:`icon-lock-open`}function T(){v.name=this.value,r(`notesEditor`)&&u.NotesEditor.open({type:`marker`,id:v.i})}function E(){v.type=this.value}function D(){u.IconSelector.open(v.icon,n=>{let r=t(n);a(`markerIcon`).innerHTML=r?`<img src="${e(n)}" style="width: 1em; height: 1em;">`:e(n),S().forEach(e=>{e.icon=n}),s()})}function O(){let e=+this.value;S().forEach(t=>{t.px=e}),s()}function k(){let e=+this.value;S().forEach(t=>{t.dx=e}),s()}function A(){let e=+this.value;S().forEach(t=>{t.dy=e}),s()}function j(){let e=+this.value;S().forEach(t=>{t.size=e}),s()}function M(){let e=this.value;S().forEach(t=>{t.pin=e}),s()}function N(){let e=this.value;S().forEach(t=>{t.fill=e}),s()}function P(){let e=this.value;S().forEach(t=>{t.stroke=e}),s()}function F(){u.NotesEditor.open({type:`marker`,id:v.i})}function I(){u.MarkersInRadius.open(v)}function L(){v.lock=!v.lock;let e=a(`markerLock`);e.classList.toggle(`icon-lock-open`),e.classList.toggle(`icon-lock`)}function R(){u.MarkerCreator.toggle(v)}function z(){f({title:`Remove marker`,message:`Are you sure you want to remove this marker? The action cannot be reverted`,confirm:`Remove`,onConfirm:B})}function B(){Markers.deleteMarker(v.i),s(),$(`#markerEditor`).dialog(`close`),h()}function V(){i(_).on(`.drag`,null).classed(`draggable`,!1),o(null),a(`addMarker`).classList.contains(`pressed`)&&g(),l(),p(`markerEditor`),_=null,v=null}var H={open:y};export{H as MarkersEditor};