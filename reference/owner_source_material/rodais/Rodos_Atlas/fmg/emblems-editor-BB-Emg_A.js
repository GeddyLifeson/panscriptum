import{Bn as e,L as t,R as n,et as r,hn as i,j as a,z as o}from"./utils-Cob8vHf9.js";import{K as s,X as c,Z as l}from"./layers-Bh4OWBXX.js";import{t as u}from"./drag-hfHVCxdY.js";import{r as d}from"./highlight-Qtqc1_QO.js";import{i as f,t as p}from"./tooltips-BTSHGd98.js";import{t as m}from"./emblems-generator-C2sA4EpN.js";import{lt as h}from"./index-DsIn6sTp.js";var g=null,_=null,v,y,b,x;async function S(){let e=pack.states.find(e=>e.i&&!e.removed&&e.coa),t=pack.burgs.find(e=>e.i&&!e.removed&&e.coa),n=e?`state`:`burg`,r=e??t;if(!r?.coa){f(`No emblems to edit, please generate states and burgs first`,!1,`error`);return}let i=`${n}COA${r.i}`;await l.trigger(i,r.coa),C(n,i,r)}function C(e,t,n,r){if(!customization){if(!t&&r)T(r);else{if(!e||!t||!n?.coa)return;v=e,y=t,b=n}w(),Z(),x?.(),x=c(Z),E(),$(`#emblemEditor`).dialog({title:`Edit Emblem`,resizable:!0,width:`18.2em`,height:`auto`,position:{my:`left top`,at:`left+10 top+10`,of:`svg`,collision:`fit`},close:Q})}}function w(){h(`emblemEditor`),a(`dialogs`).insertAdjacentHTML(`beforeend`,`<div id="emblemEditor" class="dialog stable">
      <svg viewBox="0 0 200 200"><use id="emblemImage"></use></svg>
      <div id="emblemBody">
        <div>
          <b id="emblemArmiger"></b>
        </div>
        <hr />
        <div data-tip="Select state">
          <div class="label">State:</div>
          <select id="emblemStates"></select>
        </div>
        <div data-tip="Select province in state">
          <div class="label">Province:</div>
          <select id="emblemProvinces"></select>
        </div>
        <div data-tip="Select burg in province or state">
          <div class="label">Burg:</div>
          <select id="emblemBurgs"></select>
        </div>
        <hr />
        <div data-tip="Select shape of the emblem">
          <div class="label">Shape:</div>
          <select id="emblemShapeSelector">
            <optgroup label="Basic">
              <option value="heater">Heater</option>
              <option value="spanish">Spanish</option>
              <option value="french">French</option>
            </optgroup>
            <optgroup label="Regional">
              <option value="horsehead">Horsehead</option>
              <option value="horsehead2">Horsehead Edgy</option>
              <option value="polish">Polish</option>
              <option value="hessen">Hessen</option>
              <option value="swiss">Swiss</option>
            </optgroup>
            <optgroup label="Historical">
              <option value="boeotian">Boeotian</option>
              <option value="roman">Roman</option>
              <option value="kite">Kite</option>
              <option value="oldFrench">Old French</option>
              <option value="renaissance">Renaissance</option>
              <option value="baroque">Baroque</option>
            </optgroup>
            <optgroup label="Specific">
              <option value="targe">Targe</option>
              <option value="targe2">Targe2</option>
              <option value="pavise">Pavise</option>
              <option value="wedged">Wedged</option>
            </optgroup>
            <optgroup label="Banner">
              <option value="flag">Flag</option>
              <option value="pennon">Pennon</option>
              <option value="guidon">Guidon</option>
              <option value="banner">Banner</option>
              <option value="dovetail">Dovetail</option>
              <option value="gonfalon">Gonfalon</option>
              <option value="pennant">Pennant</option>
            </optgroup>
            <optgroup label="Simple">
              <option value="round">Round</option>
              <option value="oval">Oval</option>
              <option value="vesicaPiscis">Vesica Piscis</option>
              <option value="square">Square</option>
              <option value="diamond">Diamond</option>
            </optgroup>
            <optgroup label="Fantasy">
              <option value="fantasy1">Fantasy1</option>
              <option value="fantasy2">Fantasy2</option>
              <option value="fantasy3">Fantasy3</option>
              <option value="fantasy4">Fantasy4</option>
              <option value="fantasy5">Fantasy5</option>
            </optgroup>
            <optgroup label="Middle Earth">
              <option value="noldor">Noldor</option>
              <option value="gondor">Gondor</option>
              <option value="easterling">Easterling</option>
              <option value="erebor">Erebor</option>
              <option value="ironHills">Iron Hills</option>
              <option value="urukHai">UrukHai</option>
              <option value="moriaOrc">Moria Orc</option>
            </optgroup>
          </select>
        </div>
        <div
          data-tip="Set size of particular Emblem. To hide set to 0. To change the entire category go to Menu ⭢ Style ⭢ Emblems"
        >
          <div class="label" style="width: 2.8em">Size:</div>
          <input id="emblemSizeSlider" type="range" min="0" max="5" step=".1" style="width: 7em" />
          <input id="emblemSizeNumber" type="number" min="0" max="5" step=".1" />
        </div>
      </div>
      <div id="emblemsBottom">
        <button id="emblemsRegenerate" data-tip="Regenerate emblem" class="icon-shuffle"></button>
        <button
          id="emblemsArmoria"
          data-tip="Edit the emblem in Armoria - dedicated heraldry editor. Download emblem and upload it back map the generator"
          class="icon-brush"
        ></button>
        <button
          id="emblemsDownload"
          data-tip="Set size, select file format and download emblem image"
          class="icon-download"
        ></button>
        <button
          id="emblemsUpload"
          data-tip="Upload png, jpg or svg image from Armoria or other sources as emblem"
          class="icon-upload"
        ></button>
        <button
          id="emblemsGallery"
          data-tip="Download emblems gallery as html document (open in browser; downloading takes some time)"
          class="icon-layer-group"
        ></button>
        <button id="emblemsFocus" data-tip="Show emblem associated area or place" class="icon-target"></button>
      </div>
      <div id="emblemUploadControl" class="hidden">
        <button
          id="emblemsUploadImage"
          data-tip="Upload SVG or PNG image from any source. Make sure background is transparent"
        >
          Any image
        </button>
        <button
          id="emblemsUploadSVG"
          data-tip="Upload prepared SVG image (SVG from Armoria or SVG processed with 'Optimize vector' tool)"
        >
          Prepared SVG
        </button>
        <a
          href="https://www.iloveimg.com/compress-image"
          target="_blank"
          data-tip="Use external tool to compress/resize raster images before upload"
          >Comperess raster</a
        >
        <span> | </span>
        <a
          href="https://jakearchibald.github.io/svgomg"
          target="_blank"
          data-tip="Use external tool to optimize vector images before upload"
          >Optimize vector</a
        >
      </div>
      <div id="emblemDownloadControl" class="hidden">
        <input
          id="emblemsDownloadSize"
          data-tip="Set image size in pixels"
          type="number"
          value="500"
          step="100"
          min="100"
          max="10000"
        />
        <button
          id="emblemsDownloadSVG"
          data-tip="Download as SVG: scalable vector image. Best quality, can be opened in browser or Inkscape"
        >
          SVG
        </button>
        <button id="emblemsDownloadPNG" data-tip="Download as PNG: lossless raster image with transparent background">
          PNG
        </button>
        <button
          id="emblemsDownloadJPG"
          data-tip="Download as JPG: lossy compressed raster image with solid white background"
        >
          JPG
        </button>
      </div>
    </div>`),a(`emblemStates`).oninput=O,a(`emblemProvinces`).oninput=k,a(`emblemBurgs`).oninput=A,a(`emblemShapeSelector`).oninput=j,a(`emblemSizeSlider`).oninput=N,a(`emblemSizeNumber`).oninput=N,a(`emblemsRegenerate`).onclick=P,a(`emblemsArmoria`).onclick=F,a(`emblemsUpload`).onclick=I;let e=e=>{let t=L(e);t.onchange=()=>R(e),t.click()};a(`emblemsUploadImage`).onclick=()=>e(`image`),a(`emblemsUploadSVG`).onclick=()=>e(`svg`),a(`emblemsDownload`).onclick=z,a(`emblemsDownloadSVG`).onclick=()=>B(`svg`),a(`emblemsDownloadPNG`).onclick=()=>B(`png`),a(`emblemsDownloadJPG`).onclick=()=>B(`jpeg`),a(`emblemsGallery`).onclick=G,a(`emblemsFocus`).onclick=M}function T(e){let t=e.parentNode,n=t.id===`burgEmblems`?`burg`:t.id===`provinceEmblems`?`province`:`state`,r=+e.dataset.i,i=Y(n,r);if(!i)throw Error(`Cannot edit ${n} emblem ${r}`);v=n,y=`${v}COA${r}`,b=i}function E(){let e=v,t=b,n=a(`emblemStates`),r=a(`emblemProvinces`),i=a(`emblemBurgs`),o=0,s=0,c=0;n.parentElement.className=e===`state`?`active`:``,r.parentElement.className=e===`province`?`active`:``,i.parentElement.className=e===`burg`?`active`:``,e===`state`?o=t.i:e===`province`?(s=t.i,o=pack.states[t.state].i):(c=t.i,s=pack.cells.province[t.cell]?pack.provinces[pack.cells.province[t.cell]].i:0,o=t.state??0);let u=pack.burgs.filter(e=>e.i&&!e.removed&&e.coa);n.options.length=0,u.filter(e=>!e.state).length&&n.options.add(new Option(pack.states[0].name,`0`,!1,!o)),pack.states.filter(e=>e.i&&!e.removed).forEach(e=>{n.options.add(new Option(e.name,String(e.i),!1,e.i===o))}),r.options.length=0,r.options.add(new Option(``,`0`,!1,!s)),pack.provinces.filter(e=>!e.removed&&e.state===o).forEach(e=>{r.options.add(new Option(e.name,String(e.i),!1,e.i===s))}),i.options.length=0,i.options.add(new Option(``,`0`,!1,!c)),u.filter(e=>s?pack.cells.province[e.cell]===s:e.state===o).forEach(e=>{i.options.add(new Option(e.capital?`👑 ${e.name}`:e.name,String(e.i),!1,e.i===c))}),i.options[0].disabled=!0,l.trigger(y,t.coa),D()}function D(){let e=b;if(!e.coa)return;a(`emblemImage`).setAttribute(`href`,`#${y}`);let t=e.fullName||e.name;v===`burg`&&(t=`Burg of ${t}`),a(`emblemArmiger`).innerText=t??``;let n=a(`emblemShapeSelector`);e.coa.custom?n.disabled=!0:(n.disabled=!1,n.value=e.coa.shield??`heater`);let r=e.coa.size??1;a(`emblemSizeSlider`).value=String(r),a(`emblemSizeNumber`).value=String(r)}function O(){let e=+a(`emblemStates`).value;if(e){if(!X(`state`,e))return}else{let e=pack.burgs.filter(e=>e.i&&!e.removed&&!e.state);if(!e.length||!X(`burg`,e[0].i))return}E()}function k(){let e=+a(`emblemProvinces`).value;if(e){if(!X(`province`,e))return}else if(!X(`state`,+a(`emblemStates`).value))return;E()}function A(){X(`burg`,+a(`emblemBurgs`).value)&&E()}function j(){b.coa.shield=a(`emblemShapeSelector`).value;let e=document.getElementById(y);e&&e.remove(),l.trigger(y,b.coa)}function M(){d(v,b)}function N(e){let t=+e.currentTarget.value;a(`emblemSizeSlider`).value=String(t),a(`emblemSizeNumber`).value=String(t),b.coa.size=t,s(v,b.i)}function P(){let e=b,t;if(v===`province`)t=pack.states[e.state];else if(v===`burg`){let n=pack.cells.province[e.cell];t=n?pack.provinces[n]:pack.states[e.state]}let n=e.coa.shield||m.getShield(e.culture||t?.culture||0,e.state),{size:r,x:i,y:o}=e.coa;e.coa={...m.generate(t?t.coa:null,.3,.1,void 0),shield:n,size:r,x:i,y:o};let c=a(`emblemShapeSelector`);c.disabled=!1,c.value=e.coa.shield??`heater`,l.trigger(y,e.coa),s(v,b.i)}function F(){let e=b.coa&&!b.coa.custom?b.coa:{t1:`sable`};r(`https://azgaar.github.io/Armoria/?coa=${JSON.stringify(e).replaceAll(`#`,`%23`)}&from=FMG`)}function I(){a(`emblemDownloadControl`).classList.add(`hidden`),a(`emblemUploadControl`).classList.toggle(`hidden`)}function L(e){return e===`image`?(g??=t(`image/*`),g):(_??=t(`.svg`),_)}function R(e){let t=b,n=L(e),r=n.files[0];if(n.value=``,r.size>5e5){f(`File is too big, please optimize file size up to 500kB and re-upload. Recommended size is 200x200 px and up to 100kB`,!0,`error`,5e3);return}let i=new FileReader;i.onload=n=>{let r=n.target.result,i=a(`defs-emblems`),o=r;if(e===`svg`){let e=document.createElement(`html`);e.innerHTML=r,e.querySelectorAll(`*`).forEach(e=>{e.id===`adobe_illustrator_pgf`&&e.remove(),e.getAttributeNames().forEach(t=>{(t.includes(`inkscape`)||t.includes(`sodipodi`))&&e.removeAttribute(t)})});let t=e.querySelector(`svg`);if(!t){f(`The file is not a valid SVG. Please use Armoria or other relevant tools`,!1,`error`);return}let n=new XMLSerializer().serializeToString(t);o=`data:image/svg+xml;base64,${window.btoa(n)}`}let c=`<svg id="${y}" viewBox="0 0 200 200"><image width="200" height="200" href="${o}"/></svg>`;l.remove(y),i.insertAdjacentHTML(`beforeend`,c);let u={custom:!0};t.coa.size!==void 0&&(u.size=t.coa.size),t.coa.x!==void 0&&(u.x=t.coa.x),t.coa.y!==void 0&&(u.y=t.coa.y),t.coa=u,s(v,b.i),a(`emblemShapeSelector`).disabled=!0},e===`image`?i.readAsDataURL(r):i.readAsText(r)}function z(){a(`emblemUploadControl`).classList.add(`hidden`),a(`emblemDownloadControl`).classList.toggle(`hidden`)}async function B(e){let t=document.getElementById(y),n=+a(`emblemsDownloadSize`).value,r=await U(t,n),i=document.createElement(`a`);i.download=`${o(`Emblem ${b.fullName||b.name}`)}.${e}`,e===`svg`?V(r,i):H(e,r,i,n),a(`emblemDownloadControl`).classList.add(`hidden`)}function V(e,t){t.href=e,t.click()}function H(e,t,n,r){let i=document.createElement(`canvas`),a=i.getContext(`2d`);i.width=r,i.height=r;let o=new Image;o.src=t,o.onload=()=>{e===`jpeg`&&(a.fillStyle=`#fff`,a.fillRect(0,0,i.width,i.height)),a.drawImage(o,0,0,i.width,i.height);let t=i.toDataURL(`image/${e}`,.92);n.href=t,n.click(),window.setTimeout(()=>window.URL.revokeObjectURL(t),6e3)}}async function U(e,t){let n=W(e,t),r=new Blob([n],{type:`image/svg+xml;charset=utf-8`}),i=window.URL.createObjectURL(r);return window.setTimeout(()=>window.URL.revokeObjectURL(i),6e3),i}function W(e,t){let n=e.cloneNode(!0);return n.setAttribute(`width`,String(t)),n.setAttribute(`height`,String(t)),new XMLSerializer().serializeToString(n)}async function G(){let e=o(`Emblems Gallery`),t=pack.states.filter(e=>e.i&&!e.removed&&e.coa),r=pack.provinces.filter(e=>e.i&&!e.removed&&e.coa),i=pack.burgs.filter(e=>e.i&&!e.removed&&e.coa);await K(t,r,i);let a=`<a href="javascript:history.back()">Go Back</a>`,s=`<div><h2>States</h2>${t.map(e=>{let t=document.getElementById(`stateCOA${e.i}`);return`<figure id="state_${e.i}"><a href="#provinces_${e.i}"><figcaption>${e.fullName}</figcaption>${W(t,200)}</a></figure>`}).join(``)}</div>`,c=t.map(e=>{let t=r.filter(t=>t.state===e.i),n=t.map(e=>{let t=document.getElementById(`provinceCOA${e.i}`);return`<figure id="province_${e.i}"><a href="#burgs_${e.i}"><figcaption>${e.fullName}</figcaption>${W(t,200)}</a></figure>`}).join(``);return t.length?`<div id="provinces_${e.i}">${a}<h2>${e.fullName} provinces</h2>${n}</div>`:``}).join(``),l=t.map(e=>{let t=i.filter(t=>t.state===e.i),n=r.filter(t=>t.state===e.i).map(e=>{let n=t.filter(t=>pack.cells.province[t.cell]===e.i),r=n.map(e=>{let t=document.getElementById(`burgCOA${e.i}`);return t?`<figure id="burg_${e.i}"><figcaption>${e.name}</figcaption>${W(t,200)}</figure>`:``}).join(``);return n.length?`<div id="burgs_${e.i}">${a}<h2>${e.fullName} burgs</h2>${r}</div>`:``}).join(``),o=t.filter(e=>!pack.cells.province[e.cell]).map(e=>{let t=document.getElementById(`burgCOA${e.i}`);return t?`<figure id="burg_${e.i}"><figcaption>${e.name}</figcaption>${W(t,200)}</figure>`:``}).join(``);return o&&(n+=`<div><h2>${e.fullName} burgs under direct control</h2>${o}</div>`),n}).join(``),u=i.filter(e=>!e.state),d=u.length?`<div><h2>Independent burgs</h2>${u.map(e=>{let t=document.getElementById(`burgCOA${e.i}`);return t?`<figure id="burg_${e.i}"><figcaption>${e.name}</figcaption>${W(t,200)}</figure>`:``}).join(``)}</div>`:``;n(`<!DOCTYPE html>
    <html>
      <head>
        <title>${options.map.lore.name} Emblems Gallery</title>
      </head>
      <style type="text/css">
        body { margin: 0; padding: 1em; font-family: serif; }
        h1, h2 { font-family: "Forum"; }
        div { width: 100%; max-width: 1018px; margin: 0 auto; border-bottom: 1px solid #ddd; }
        figure { margin: 0 0 2em; display: inline-block; transition: 0.2s; }
        figure:hover { background-color: #f6f6f6; }
        figcaption { text-align: center; margin: 0.4em 0; width: 200px; font-family: "Overlock SC"; }
        address { width: 100%; max-width: 1018px; margin: 0 auto; }
        a { color: black; }
        figure > a { text-decoration: none; }
        div > a { float: right; font-family: var(--monospace); margin-top: 0.8em; }
      </style>
      <link href="https://fonts.googleapis.com/css2?family=Forum&family=Overlock+SC" rel="stylesheet" />
      <body>
        <div><h1>${options.map.lore.name} Emblems Gallery</h1></div>
        ${s} ${c} ${l} ${d}
        <address>Generated by <a href="https://azgaar.github.io/Fantasy-Map-Generator" target="_blank">Azgaar's Fantasy Map Generator</a>. The tool is free, but images may be copyrighted, see <a target="_blank" href="https://github.com/Azgaar/Armoria#license">the license</a></address>
      </body>
    </html>`,`${e}.html`,`text/plain`)}async function K(e,t,n){f(`Preparing for download...`,!0,`warn`);let r=e.map(e=>l.trigger(`stateCOA${e.i}`,e.coa)),i=t.map(e=>l.trigger(`provinceCOA${e.i}`,e.coa)),a=n.map(e=>l.trigger(`burgCOA${e.i}`,e.coa)),o=[...r,...i,...a];await Promise.allSettled(o),p()}function q(t){let n=Number(this.getAttribute(`x`))-t.x,r=Number(this.getAttribute(`y`))-t.y;t.on(`drag`,function(e){this.setAttribute(`x`,String(n+e.x)),this.setAttribute(`y`,String(r+e.y))}),t.on(`end`,function(t){let i=Number(this.parentNode.getAttribute(`font-size`))*Number.parseFloat(this.getAttribute(`width`)||`1`)/2,a=J(this.parentElement?.id),o=Number(this.dataset.i),c=a&&Number.isInteger(o)?Y(a,o):void 0;!a||!c||(c.coa.x=e(n+t.x+i,2),c.coa.y=e(r+t.y+i,2),s(a,o))})}function J(e){if(e===`burgEmblems`)return`burg`;if(e===`provinceEmblems`)return`province`;if(e===`stateEmblems`)return`state`}function Y(e,t){let n=e===`burg`?pack.burgs[t]:e===`province`?pack.provinces[t]:pack.states[t];return n?.coa?n:void 0}function X(e,t){let n=Y(e,t);return n?(v=e,y=`${e}COA${t}`,b=n,!0):!1}function Z(){i(`#emblems`).selectAll(`use`).call(u().on(`drag`,q)).classed(`draggable`,!0)}function Q(){x?.(),x=void 0,i(`#emblems`).selectAll(`use`).on(`.drag`,null).attr(`class`,null),$(`#emblemEditor`).dialog(`destroy`),a(`emblemEditor`).remove()}var ee={open:C,openDefault:S};export{ee as EmblemsEditor};