import{An as e,B as t,H as n,V as r,j as i}from"./utils-Cob8vHf9.js";import{i as a}from"./tooltips-BTSHGd98.js";import{lt as o}from"./index-DsIn6sTp.js";import{t as s}from"./icons-list-Be3mSoja.js";function c(e,n){let r=l(),s=i(`iconTable`),c=i(`iconInput`);if(c.value=e,!s.innerHTML){u(s);for(let e of d())p(e,n)}c.oninput=()=>n(c.value),s.onclick=e=>{let t=e.target;t.tagName===`TD`&&(c.value=t.textContent||``,n(c.value))},s.onmouseover=e=>{let t=e.target;t.tagName===`TD`&&a(`Click to select ${t.textContent} icon`)};let m=i(`addImage`);m.onclick=()=>{let e=m.previousElementSibling,r=e.value;if(!r)return a(`Enter image URL to add`,!1,`error`,4e3);if(!t(r))return a(`Enter valid URL`,!1,`error`,4e3);p(r,n),n(r),e.value=``};let h=i(`iconFileToLoad`);i(`uploadIconImage`).onclick=()=>h.click(),h.onchange=()=>f(h,e=>{p(e,n),n(e)});for(let e of Array.from(i(`addedIcons`).querySelectorAll(`div`)))e.onclick=()=>n(e.style.backgroundImage.slice(5,-2));$(r).dialog({width:`fit-content`,title:`Select Icon`,close:()=>o(`iconSelector`),buttons:{Apply:function(){$(this).dialog(`close`)},Close:function(){n(e),$(this).dialog(`close`)}}})}function l(){o(`iconSelector`);let e=document.createElement(`div`);return e.id=`iconSelector`,e.className=`dialog`,e.style.display=`none`,e.innerHTML=`<div>
      <b>Unicode emojis</b>
      <div style="font-style: italic">
        <span>Select from the list or paste a Unicode character here: </span>
        <input id="iconInput" style="width: 2.5em" />
        <span>. See <a href="https://emojidb.org" target="_blank">EmojiDB</a> to search for emojis</span>
      </div>
      <table id="iconTable" class="table pointer" style="font-size: 2em; text-align: center; width: 100%"></table>
    </div>
    <div style="margin-top: 0.5em">
      <b>External images</b>
      <div style="font-style: italic">
        <span>Paste link to the image here: </span>
        <input id="imageInput" style="width: 20em" />
        <button id="addImage" type="button">Add</button>
        <span> or </span>
        <button id="uploadIconImage" type="button" data-tip="Upload a local SVG or raster image, up to 200kB. It is stored inside the map file">Upload file</button>
        <input id="iconFileToLoad" type="file" accept="image/*,.svg" style="display: none" />
      </div>
      <div id="addedIcons" class="pointer" style="display: flex; flex-wrap: wrap; max-width: 420px"></div>
    </div>`,i(`dialogs`).appendChild(e),e}function u(e){let t=null;s.forEach((n,r)=>{r%17==0&&(t=e.insertRow(Math.floor(r/17))),t?.insertCell(r%17).appendChild(document.createTextNode(n))})}function d(){let e=new Set;for(let n of options.map.military.units)t(n.icon)&&e.add(n.icon);for(let n of pack.states)for(let r of n?.military||[])t(r.icon)&&e.add(r.icon);for(let n of pack.markers||[])t(n.icon)&&e.add(n.icon);return e}function f(e,i){let o=e.files?.[0];if(e.value=``,!o)return;if(o.size>2e5){a(`File is too big, please optimize it to below 200kB. Recommended size is up to 10kB`,!0,`error`,5e3);return}let s=o.type===`image/svg+xml`||o.name.toLowerCase().endsWith(`.svg`),c=new FileReader;c.onload=()=>{let e=c.result;if(!s)return t(e)?i(e):void a(`The file is not a supported image`,!1,`error`,4e3);let o=r(e);if(!o)return void a(`The file is not a valid SVG image`,!1,`error`,4e3);i(n(o.outerHTML))},s?c.readAsText(o):c.readAsDataURL(o)}function p(t,n){let r=document.createElement(`div`);r.style.cssText=`width: 2.2em; height: 2.2em; background-size: cover`,r.style.backgroundImage=`url("${t.replace(/["\\]/g,`\\$&`)}")`,r.onclick=()=>n(t),r.onmouseover=()=>a(`Click to select <img src="${e(t)}" style="width: 1em; height: 1em; vertical-align: middle"> icon`),i(`addedIcons`).appendChild(r)}var m={open:c};export{m as IconSelector};