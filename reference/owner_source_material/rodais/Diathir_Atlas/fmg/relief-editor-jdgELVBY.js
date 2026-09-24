import{Bn as e,P as t,hn as n,j as r,kn as i,v as a,yn as o}from"./utils-Cob8vHf9.js";import{E as s,T as c,t as l}from"./layers-Bh4OWBXX.js";import{t as u}from"./drag-hfHVCxdY.js";import{t as d}from"./quadtree-DgASQllf.js";import{i as f,r as p,t as m}from"./tooltips-BTSHGd98.js";import{D as h,E as g,T as _,V as v,f as y,lt as b,p as x,st as S}from"./index-DsIn6sTp.js";import{t as C}from"./brushUtils-B5xtY9tr.js";var w=40,T=null,E=()=>Object.entries(h).map(([e,{name:t}])=>`<option value="${e}">${t}</option>`).join(``),D=()=>Object.keys(h).map(e=>`<div data-type="${e}" style="display: none">${O(e)}</div>`).join(``),O=e=>g.filter(({set:t})=>t===h[e].base).flatMap(({type:t,variants:n,zoom:r=1})=>{let a=w*r,o=50-50*r,s=i(t.replace(/([A-Z])/g,` $1`).toLowerCase());return n.map(n=>{let r=_(t,n,e);return`<svg data-type="${r}" data-tip="Select ${s} icon">
          <use href="#${r}" x="${o}%" y="${o}%" width="${a}" height="${a}"></use>
        </svg>`})}).join(``);function k(e){customization||(S(`.stable`),l.show(`relief`),T=J(e),n(`#terrain`).call(u().on(`start`,j)).classed(`draggable`,!0),A(),M(),N(),P(),$(`#reliefEditor`).dialog({title:`Edit Relief Icons`,resizable:!1,width:`27em`,position:{my:`left top`,at:`left+10 top+10`,of:`#map`},close:Y}))}function A(){b(`reliefEditor`);let e=`<div id="reliefEditor" class="dialog">
    <div id="reliefTools" data-tip="Select mode of operation">
      <div class="reliefEditorLabel">Mode:</div>
      <button id="reliefIndividual" data-tip="Edit individual selected icon" class="icon-info pressed"></button>
      <button id="reliefBulkAdd" data-tip="Place icons in a bulk" class="icon-brush"></button>
      <button id="reliefBulkRemove" data-tip="Remove icons in a bulk" class="icon-eraser"></button>
      <div style="margin-left: 4.6em">Set:</div>
      <select id="reliefEditorSet">${E()}</select>
    </div>
    <div id="reliefSizeDiv" data-tip="Set icon size for individual icon or for bulk placement">
      <div class="reliefEditorLabel">Size:</div>
      <input
        id="reliefSize"
        oninput="reliefSizeNumber.value = this.value"
        type="range"
        min="2"
        max="50"
        value="5"
      />
      <input id="reliefSizeNumber" oninput="reliefSize.value = this.value" type="number" min="2" value="5" />
    </div>
    <div id="reliefRadiusDiv" data-tip="Set brush radius for icons placement on deletion" style="display: none">
      <div class="reliefEditorLabel">Radius:</div>
      <input
        id="reliefRadius"
        oninput="reliefRadiusNumber.value = this.value"
        type="range"
        min="1"
        max="100"
        value="15"
      />
      <input id="reliefRadiusNumber" oninput="reliefRadius.value = this.value" type="number" min="1" value="15" />
    </div>
    <div id="reliefSpacingDiv" data-tip="Set spacing between relief icons" style="display: none">
      <div class="reliefEditorLabel">Spacing:</div>
      <input
        id="reliefSpacing"
        oninput="reliefSpacingNumber.value = this.value"
        type="range"
        min="2"
        max="20"
        value="5"
      />
      <input id="reliefSpacingNumber" oninput="reliefSpacing.value = this.value" type="number" min="2" value="5" />
    </div>
    <div id="reliefIconsDiv" data-tip="Select icon">
${D()}
      <svg id="reliefIconsSeletionAny" data-tip="Select any type of icons"><text x="50%" y="50%">Any</text></svg>
    </div>
    <div id="reliefBottom">
      <button id="reliefEditStyle" data-tip="Edit Relief Icons style in Style Editor" class="icon-adjust"></button>
      <button id="reliefCopy" data-tip="Copy selected relief icon" class="icon-clone"></button>
      <button id="reliefMoveFront" data-tip="Move selected relief icon to front" class="icon-level-up"></button>
      <button id="reliefMoveBack" data-tip="Move selected relief icon back" class="icon-level-down"></button>
      <button
        id="reliefRemove"
        data-tip="Remove selected relief icon or icon type"
        data-shortcut="Delete"
        class="icon-trash fastDelete"
      ></button>
    </div>
  </div>`;r(`dialogs`).insertAdjacentHTML(`beforeend`,e),r(`reliefIndividual`).addEventListener(`click`,F),r(`reliefBulkAdd`).addEventListener(`click`,I),r(`reliefBulkRemove`).addEventListener(`click`,B),r(`reliefSize`).addEventListener(`input`,H),r(`reliefSizeNumber`).addEventListener(`input`,H),r(`reliefEditorSet`).addEventListener(`change`,U),r(`reliefIconsDiv`).querySelectorAll(`svg`).forEach(e=>{e.addEventListener(`click`,W)}),r(`reliefEditStyle`).addEventListener(`click`,()=>editStyle(`terrain`)),r(`reliefCopy`).addEventListener(`click`,G),r(`reliefMoveFront`).addEventListener(`click`,()=>K(`front`)),r(`reliefMoveBack`).addEventListener(`click`,()=>K(`back`)),r(`reliefRemove`).addEventListener(`click`,q),U()}function j(t){let n=J(t.sourceEvent?.target);if(!n)return;let r=n.x-t.x,i=n.y-t.y;t.on(`drag`,t=>{n.x=e(r+t.x,2),n.y=e(i+t.y,2),s()})}function M(){r(`reliefTools`).querySelector(`button.pressed`)?r(`reliefBulkAdd`).classList.contains(`pressed`)?I():r(`reliefBulkRemove`).classList.contains(`pressed`)&&B():F()}function N(){if(!T)return;let e=r(`reliefIconsDiv`),t=e.querySelector(`svg[data-type='${T.icon}']`);if(!t)return;e.querySelectorAll(`svg.pressed`).forEach(e=>{e.classList.remove(`pressed`)}),t.classList.add(`pressed`),e.querySelectorAll(`div`).forEach(e=>{e.style.display=`none`});let n=t.parentNode;n.style.display=`block`,r(`reliefEditorSet`).value=n.dataset.type}function P(){T&&(r(`reliefSize`).value=r(`reliefSizeNumber`).value=String(e(T.s)))}function F(){r(`reliefTools`).querySelectorAll(`button.pressed`).forEach(e=>{e.classList.remove(`pressed`)}),r(`reliefIndividual`).classList.add(`pressed`),r(`reliefSizeDiv`).style.display=`block`,r(`reliefRadiusDiv`).style.display=`none`,r(`reliefSpacingDiv`).style.display=`none`,r(`reliefIconsSeletionAny`).style.display=`none`,x(),P(),v(),m()}function I(){r(`reliefTools`).querySelectorAll(`button.pressed`).forEach(e=>{e.classList.remove(`pressed`)}),r(`reliefBulkAdd`).classList.add(`pressed`),r(`reliefSizeDiv`).style.display=`block`,r(`reliefRadiusDiv`).style.display=`block`,r(`reliefSpacingDiv`).style.display=`block`,r(`reliefIconsSeletionAny`).style.display=`none`;let e=r(`reliefIconsDiv`);e.querySelector(`svg.pressed`)?.id===`reliefIconsSeletionAny`&&(r(`reliefIconsSeletionAny`).classList.remove(`pressed`),e.querySelector(`svg`)?.classList.add(`pressed`)),n(`#viewbox`).style(`cursor`,`crosshair`).call(u().on(`start`,R)).on(`touchmove mousemove`,L),f(`Drag to place relief icons within radius`,!0)}function L(e){p();let n=t(e,this),i=+r(`reliefRadiusNumber`).value;y(n[0],n[1],i)}function R(n){let i=r(`reliefIconsDiv`).querySelector(`svg.pressed`);if(!i){f(`Please select an icon`,!1,`error`);return}let a=i.dataset.type,c=+r(`reliefRadiusNumber`).value,l=+r(`reliefSpacingNumber`).value,u=+r(`reliefSizeNumber`).value,p=d(pack.relief.map(({x:e,y:t,s:n})=>[e+n/2,t+n/2])),m=C(c/2,(t,n)=>{o(Math.ceil(c/10)).forEach(()=>{let r=Math.PI*2*Math.random(),i=c*Math.random(),o=t+i*Math.cos(r),s=n+i*Math.sin(r);if(p.find(o,s,l)||pack.cells.h[Pack.findCell(o,s)]<20)return;let d=e(u/2*(Math.random()*.4+.8),2);p.add([o,s]),z({icon:a,x:e(o-d,2),y:e(s-d,2),s:e(d*2,2)})})}),[h,g]=t(n,this),_=!1;n.on(`drag`,function(e){let[n,r]=t(e,this);y(n,r,c),_||(_=!0,m.moveTo(h,g)),m.moveTo(n,r),s()})}function z(e){let t=e.y+e.s,n=0,r=pack.relief.length;for(;n<r;){let e=n+r>>1;pack.relief[e].y+pack.relief[e].s<=t?n=e+1:r=e}pack.relief.splice(n,0,e)}function B(){r(`reliefTools`).querySelectorAll(`button.pressed`).forEach(e=>{e.classList.remove(`pressed`)}),r(`reliefBulkRemove`).classList.add(`pressed`),r(`reliefSizeDiv`).style.display=`none`,r(`reliefRadiusDiv`).style.display=`block`,r(`reliefSpacingDiv`).style.display=`none`,r(`reliefIconsSeletionAny`).style.display=`inline-block`,n(`#viewbox`).style(`cursor`,`crosshair`).call(u().on(`start`,V)).on(`touchmove mousemove`,L),f(`Drag to remove relief icons in radius`,!0)}function V(e){let n=r(`reliefIconsDiv`).querySelector(`svg.pressed`);if(!n){f(`Please select an icon`,!1,`error`);return}let i=+r(`reliefRadiusNumber`).value,o=n.dataset.type,c=d();for(let e of pack.relief)o&&e.icon!==o||c.add([e.x+e.s/2,e.y+e.s/2,e]);let l=C(i/2,(e,t)=>{let n=a(e,t,i,c);if(!n.length)return;let r=new Set(n.map(e=>e[2]));for(let e of n)c.remove(e);pack.relief=pack.relief.filter(e=>!r.has(e)),T&&r.has(T)&&(T=null),s()}),[u,p]=t(e,this),m=!1;e.on(`drag`,function(e){let[n,r]=t(e,this);y(n,r,i),m||(m=!0,l.moveTo(u,p)),l.moveTo(n,r)})}function H(){if(!T||!r(`reliefIndividual`).classList.contains(`pressed`))return;let t=+r(`reliefSizeNumber`).value,n=(t-T.s)/2;T.s=t,T.x=e(T.x-n,2),T.y=e(T.y-n,2),s()}function U(){let e=r(`reliefEditorSet`).value,t=r(`reliefIconsDiv`);t.querySelectorAll(`div`).forEach(e=>{e.style.display=`none`}),t.querySelector(`div[data-type='${e}']`).style.display=`block`}function W(){this.classList.contains(`pressed`)||(r(`reliefIconsDiv`).querySelectorAll(`svg.pressed`).forEach(e=>{e.classList.remove(`pressed`)}),this.classList.add(`pressed`),r(`reliefIndividual`).classList.contains(`pressed`)&&T&&(T.icon=this.dataset.type,s()))}function G(){if(!T)return;let{x:e,y:t}=T;do e-=3,t-=3;while(pack.relief.some(n=>n.x===e&&n.y===t));let n={...T,x:e,y:t};pack.relief.push(n),T=n,s()}function K(e){if(!T)return;let t=pack.relief.indexOf(T);t<0||(pack.relief.splice(t,1),e===`front`?pack.relief.push(T):pack.relief.unshift(T),s())}function q(){let e=r(`reliefTools`).querySelector(`button.pressed`)?.id===`reliefIndividual`,t=r(`reliefIconsDiv`).querySelector(`svg.pressed`)?.dataset.type,n=e?new Set(T?[T]:[]):new Set(pack.relief.filter(e=>!t||e.icon===t));e?alertMessage.innerHTML=`Are you sure you want to remove the icon?`:alertMessage.innerHTML=t?`Are you sure you want to remove all ${t} icons (${n.size})?`:`Are you sure you want to remove all icons (${n.size})?`,$(`#alert`).dialog({resizable:!1,title:`Remove relief icons`,buttons:{Remove:function(){pack.relief=pack.relief.filter(e=>!n.has(e)),T=null,s(),$(this).dialog(`close`),$(`#reliefEditor`).dialog(`close`)},Cancel:function(){$(this).dialog(`close`)}}})}function J(e){if(e?.tagName!==`use`)return null;let t=e.dataset.id;return t&&c(t)||null}function Y(){let e=!r(`reliefIndividual`).classList.contains(`pressed`);n(`#terrain`).on(`.drag`,null).classed(`draggable`,!1),T=null,x(),e&&v(),m(),$(`#reliefEditor`).dialog(`destroy`),r(`reliefEditor`).remove()}var X={open:k};export{X as ReliefEditor};