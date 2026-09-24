import{An as e,B as t,j as n}from"./utils-Cob8vHf9.js";import{t as r}from"./layers-Bh4OWBXX.js";import{i}from"./tooltips-BTSHGd98.js";import{t as a}from"./controllers-DnVd8NhQ.js";import{lt as o,ut as s}from"./index-DsIn6sTp.js";var c=`markersSettings`;function l(){customization||(o(c),n(`dialogs`).insertAdjacentHTML(`beforeend`,`<div id="${c}" class="dialog"></div>`),d(),$(`#${c}`).dialog({resizable:!1,title:`Markers generation settings`,maxHeight:600,position:{my:`left top`,at:`left+10 top+10`,of:`svg`,collision:`fit`},buttons:{Regenerate:()=>{u(),Markers.regenerate(),r.draw(`markers`),s(),d()},Close:function(){$(this).dialog(`close`)}},open:function(){let e=$(this).dialog(`widget`).find(`.ui-dialog-buttonset > button`);e[0].addEventListener(`mousemove`,()=>i(`Apply changes and regenerate markers`)),e[1].addEventListener(`mousemove`,()=>i(`Close the window`))},close:f}))}function u(){let e=n(c).querySelectorAll(`tbody > tr`),t=Array.from(e).map(e=>{let t=e.querySelector(`.type`),n=e.querySelector(`.image`),r=e.querySelector(`.emoji`),i=e.querySelector(`.multiplier`);if(!t||!n||!r||!i)throw Error(`Invalid markers configuration row`);return{type:t.value,icon:n.getAttribute(`src`)||r.textContent||``,multiplier:i.valueAsNumber}});Markers.setConfig(Markers.getConfig().map((e,n)=>({...e,...t[n]})))}function d(){let r=Markers.getConfig().map(({type:n,icon:r,multiplier:i})=>{let a=t(r);return`<tr>
      <td><input class="type" value="${n}" /></td>
      <td style="position: relative">
        <img class="image" src="${a?e(r):``}" ${a?``:`hidden`} style="width:1.2em; height:1.2em; vertical-align: middle;">
        <span class="emoji" style="font-size:1.2em">${a?``:e(r)}</span>
        <button class="changeIcon icon-pencil"></button>
      </td>
      <td><input class="multiplier" type="number" min="0" max="100" step="0.1" value="${i}" /></td>
      <td style="text-align:center">${pack.markers.filter(e=>e.type===n).length}</td>
    </tr>`}),i=n(c);i.innerHTML=`<table class="table"><thead style='font-weight:bold'><tr>
    <td data-tip="Marker type name">Type</td>
    <td data-tip="Marker icon">Icon</td>
    <td data-tip="Marker number multiplier">Multiplier</td>
    <td data-tip="Number of markers of that type on the current map">Number</td>
  </tr></thead><tbody>${r.join(``)}</tbody></table>`,i.querySelectorAll(`button.changeIcon`).forEach(e=>{e.addEventListener(`click`,e=>{let n=e.currentTarget.parentElement,r=n?.querySelector(`.image`),i=n?.querySelector(`.emoji`);!r||!i||a.IconSelector.open(r.getAttribute(`src`)||i.textContent||``,e=>{let n=t(e);r.setAttribute(`src`,n?e:``),r.hidden=!n,i.textContent=n?``:e})})})}function f(){o(c)}var p={open:l};export{p as MarkersSettings};