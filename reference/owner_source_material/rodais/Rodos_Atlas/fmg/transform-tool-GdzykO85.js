import{Bn as e,j as t}from"./utils-Cob8vHf9.js";import{t as n}from"./layers-Bh4OWBXX.js";import{a as r}from"./pins-D6mEpUZC.js";import{Et as i,F as a,G as o,M as s,Mt as c,N as l,Tt as u,lt as d,m as f}from"./index-DsIn6sTp.js";var p=!1,m=0,h=0;function g(){_(),v(),b(),$(`#transformTool`).dialog({title:`Transform map`,resizable:!1,position:{my:`center`,at:`center`,of:`svg`},close:y,buttons:{Transform:function(){D(),$(this).dialog(`close`)},Cancel:function(){$(this).dialog(`close`)}}})}function _(){d(`transformTool`);let e=String(options.generation.graph.density),n=r[+e],i=`<div id="transformTool" class="dialog">
    <div style="padding-top: 0.5em; width: 40em; font-weight: bold">
      This operation is destructive and irreversible. It will create a completely new map based on the current one.
      Don't forget to save the .map file to your machine first!
    </div>
    <div
      id="transformToolBody"
      style="
        padding: 0.5em 0;
        width: 100%;
        display: grid;
        grid-template-columns: 1fr 1fr;
        grid-template-rows: repeat(5, 1fr);
        align-items: center;
      "
    >
      <div>Points number</div>
      <div>
        <input id="transformPointsInput" type="range" min="1" max="13" value="${e}" />
        <output id="transformPointsFormatted" style="color: ${s(n)}">${n/1e3}K</output>
      </div>
      <div>Shift</div>
      <div>
        <label>X: <input id="transformShiftX" type="number" size="4" value="0" /></label>
        <label>Y: <input id="transformShiftY" type="number" size="4" value="0" /></label>
      </div>
      <div>Rotate</div>
      <div>
        <input id="transformAngleInput" type="range" min="0" max="359" value="0" />
        <output id="transformAngleOutput">0</output>°
      </div>
      <div>Scale</div>
      <div>
        <input id="transformScaleInput" type="range" min="-25" max="25" value="0" />
        <output id="transformScaleResult">1</output>x
      </div>
      <div>Mirror</div>
      <div style="display: flex; gap: 0.5em">
        <input type="checkbox" class="checkbox" id="transformMirrorH" />
        <label for="transformMirrorH" class="checkbox-label">horizontally</label>
        <input type="checkbox" class="checkbox" id="transformMirrorV" />
        <label for="transformMirrorV" class="checkbox-label">vertically</label>
      </div>
    </div>
    <div id="transformPreview" style="position: relative; overflow: hidden; outline: 1px solid #666">
      <canvas id="transformPreviewCanvas" style="position: absolute; transform-origin: center"></canvas>
    </div>
  </div>`;t(`dialogs`).insertAdjacentHTML(`beforeend`,i)}function v(){t(`transformToolBody`).addEventListener(`input`,S),t(`transformPointsInput`).oninput=x;let e=t(`transformPreview`);e.addEventListener(`mousedown`,C),e.addEventListener(`mouseup`,w),e.addEventListener(`mousemove`,T),e.addEventListener(`wheel`,E)}function y(){p=!1,d(`transformTool`)}async function b(){let e=Math.min(400,window.innerWidth*.5),n=e/options.map.graph.width,r=options.map.graph.height*n;t(`transformPreview`).style.width=`${e}px`,t(`transformPreview`).style.height=`${r}px`;let i=await window.Services.ExportMap.getMapURL(`png`,{noWater:!0,fullMap:!0,noLabels:!0,noScaleBar:!0,noVignette:!0,noIce:!0}),a=new Image;a.src=i,a.onload=()=>{let n=t(`transformPreviewCanvas`);n.style.width=`${e}px`,n.style.height=`${r}px`,n.width=e*4,n.height=r*4,n.getContext(`2d`)?.drawImage(a,0,0,e*4,r*4)}}function x(e){let n=r[+e.target.value],i=t(`transformPointsFormatted`);i.value=`${n/1e3}K`,i.style.color=s(n)}function S(){let n=Math.min(400,window.innerWidth*.5)/options.map.graph.width,r=t(`transformAngleInput`).value;t(`transformAngleOutput`).value=r;let i=r/180*Math.PI,a=+t(`transformShiftX`).value,o=+t(`transformShiftY`).value,s=t(`transformMirrorH`).checked,c=t(`transformMirrorV`).checked,l=e(1.0965**t(`transformScaleInput`).value,2);t(`transformScaleResult`).value=String(l),t(`transformPreviewCanvas`).style.transform=`
    translate(${a*n}px, ${o*n}px)
    scale(${s?-l:l}, ${c?-l:l})
    rotate(${i}rad)
  `}function C(e){let n=Math.min(400,window.innerWidth*.5)/options.map.graph.width;p=!0;let r=+t(`transformShiftX`).value,i=+t(`transformShiftY`).value;m=r-e.clientX/n,h=i-e.clientY/n}function w(){p=!1}function T(e){if(!p)return;e.preventDefault();let n=Math.min(400,window.innerWidth*.5)/options.map.graph.width;t(`transformShiftX`).value=String(Math.round(m+e.clientX/n)),t(`transformShiftY`).value=String(Math.round(h+e.clientY/n)),S()}function E(e){let n=t(`transformScaleInput`);n.value=String(n.valueAsNumber-Math.sign(e.deltaY)),S()}function D(){INFO&&console.group(`transformMap`);let e=t(`transformPointsInput`).value;e!==String(options.generation.graph.density)&&l(+e);let[r,s]=O();u(),i(),resetZoom(0),o(),f.process({projection:r,inverse:s,scale:1}),n.drawAll(),a(),c(),INFO&&console.groupEnd()}function O(){let e=options.map.graph.width/2,n=options.map.graph.height/2,r=+t(`transformShiftX`).value,i=+t(`transformShiftY`).value,a=t(`transformAngleInput`).value/180*Math.PI,o=Math.cos(a),s=Math.sin(a),c=+t(`transformScaleResult`).value,l=t(`transformMirrorH`).checked,u=t(`transformMirrorV`).checked;function d(t,d){return t-=e,d-=n,c!==1&&(t*=c,d*=c),a&&([t,d]=[t*o-d*s,t*s+d*o]),l&&(t=-t),u&&(d=-d),[t+e+r,d+n+i]}function f(t,d){return t-=e+r,d-=n+i,u&&(d=-d),l&&(t=-t),a!==0&&([t,d]=[t*o+d*s,-t*s+d*o]),c!==1&&(t/=c,d/=c),[t+e,d+n]}return[d,f]}var k={open:g};export{k as TransformTool};