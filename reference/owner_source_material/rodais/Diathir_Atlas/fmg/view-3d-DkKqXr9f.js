const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["./view-3d-renderer-dH2XqrPB.js","./index-DsIn6sTp.js","./chunk-QTnfLwEv.js","./controllers-DnVd8NhQ.js","./alea-DH2OApIU.js","./utils-Cob8vHf9.js","./layers-Bh4OWBXX.js","./minIndex-4vd4__Hw.js","./sin-DXK16t1M.js","./quadtree-DgASQllf.js","./catmullRom-DFVQdx1l.js","./natural-QcNq1h5H.js","./state-B2hBYDzv.js","./tooltips-BTSHGd98.js","./platform-DdqqRmnM.js","./viewport-CRAO29Z3.js","./draw-landmass-Zto91iBQ.js","./draw-trade-animation-DtXrERhx.js","./linear-BBVgsIex.js","./mean-4Awewi9R.js","./median-BS6PVqV9.js","./drag-hfHVCxdY.js","./highlight-Qtqc1_QO.js","./schemaUtils--OnEvw_L.js","./pins-D6mEpUZC.js","./cultures-generator-B9VhtNU6.js","./emblems-generator-C2sA4EpN.js"])))=>i.map(i=>d[i]);
import{j as e}from"./utils-Cob8vHf9.js";import{r as t}from"./viewport-CRAO29Z3.js";import{i as n}from"./tooltips-BTSHGd98.js";import{n as r}from"./controllers-DnVd8NhQ.js";import{St as i,nt as a,xt as o}from"./index-DsIn6sTp.js";var s=null,c=()=>s?Promise.resolve(s):r(()=>import(`./view-3d-renderer-dH2XqrPB.js`).then(e=>s=e),__vite__mapDeps([0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26]),import.meta.url),l=(e,t=`viewMesh`)=>c().then(n=>n.create(e,t)),u=()=>c().then(e=>e.redraw()),d=()=>c().then(e=>e.update()),f=()=>c().then(e=>e.stop()),p=e=>c().then(t=>t.setSunColor(e)),m=e=>c().then(t=>t.setScale(e)),h=e=>c().then(t=>t.setResolutionScale(e)),g=e=>c().then(t=>t.setLightness(e)),_=(e,t,n)=>c().then(r=>r.setSun(e,t,n)),ee=e=>c().then(t=>t.setRotation(e)),te=()=>c().then(e=>e.toggleLabels()),ne=()=>c().then(e=>e.toggle3dSubdivision()),re=()=>c().then(e=>e.toggleErosion()),ie=e=>c().then(t=>t.setErosionStrength(e)),v=e=>c().then(t=>t.setErosionRiverDepth(e)),y=e=>c().then(t=>t.setErosionDetail(e)),b=e=>c().then(t=>t.setErosionOctaves(e)),x=()=>c().then(e=>e.toggleSatellite()),S=()=>c().then(e=>e.toggleWireframe()),C=()=>c().then(e=>e.toggleSky()),w=e=>c().then(t=>t.setResolution(e)),T=(e,t)=>c().then(n=>n.setColors(e,t)),E=e=>c().then(t=>t.setTimeOfDay(e)),D=()=>c().then(e=>e.saveScreenshot()),O=()=>c().then(e=>e.saveOBJ()),k=()=>a(),A=e=>c().then(t=>t.isCached(e)),j=(e,t,n)=>c().then(r=>r.heightAt(e,t,n));function M(){document.getElementById(`canvas3d`)&&(f(),document.getElementById(`canvas3d`)?.remove(),document.getElementById(`options3d`)&&$(`#options3d`).dialog(`close`),document.getElementById(`preview3d`)&&$(`#preview3d`).dialog(`close`))}function N(){e(`viewMode`).querySelectorAll(`.pressed`).forEach(e=>{e.classList.remove(`pressed`)}),e(`heightmap3DView`).classList.remove(`pressed`),e(`viewStandard`).classList.add(`pressed`),M()}async function P(r){N(),e(`viewStandard`).classList.remove(`pressed`),e(r).classList.add(`pressed`);let i=document.createElement(`canvas`);if(i.id=`canvas3d`,i.dataset.type=r,r===`heightmap3DView`){let t=e(`preview3d`);i.width=parseFloat(t.style.width)||options.map.graph.width/3,i.height=i.width/(options.map.graph.width/options.map.graph.height),i.style.display=`block`}else i.width=t.width,i.height=t.height,i.style.position=`absolute`,i.style.display=`none`;await l(i,r)&&(i.style.display=`block`,i.onmouseenter=()=>{+i.dataset.hovered>2?n(``):n(`Drag to pan • Scroll to zoom • Right-click drag to rotate • <b>O</b> to toggle options`),i.dataset.hovered=String((i.dataset.hovered|0)+1)},r===`heightmap3DView`?(F(),e(`preview3d`).appendChild(i),$(`#preview3d`).dialog({title:`3D Preview`,resizable:!0,position:{my:`left bottom`,at:`left+10 bottom-20`,of:`svg`},resizeStop:ae,close:I})):document.body.insertBefore(i,e(`optionsContainer`)),L())}function F(){document.getElementById(`preview3d`)?.remove(),e(`dialogs`).insertAdjacentHTML(`beforeend`,`<div id="preview3d" class="dialog stable" style="padding: 0px"></div>`)}function I(){$(`#preview3d`).dialog(`destroy`),e(`preview3d`).remove(),N()}function ae(){let t=document.getElementById(`canvas3d`);if(!t)return;let n=e(`preview3d`);t.width=parseFloat(n.style.width),t.height=parseFloat(n.style.height)-2,u()}function L(){if(document.getElementById(`options3d`)){$(`#options3d`).dialog(`close`);return}R(),$(`#options3d`).dialog({title:`3D mode settings`,resizable:!1,width:`fit-content`,position:{my:`right top`,at:`right-30 top+10`,of:`svg`,collision:`fit`},close:z}),V()}function R(){document.getElementById(`options3d`)?.remove(),e(`dialogs`).insertAdjacentHTML(`beforeend`,`<div id="options3d" class="dialog stable">
      <div id="options3dMesh" style="display: none">
        <div data-tip="Set map rotation speed. Set to 0 is you want to toggle off the rotation">
          <div>Rotation:</div>
          <input id="options3dMeshRotationRange" type="range" min="0" max="10" step=".1" />
          <input id="options3dMeshRotationNumber" type="number" min="0" max="10" step=".1" style="width: 4em" />
        </div>
        <div data-tip="Set height scale">
          <div>Height scale:</div>
          <input id="options3dScaleRange" type="range" min="0" max="100" />
          <input id="options3dScaleNumber" type="number" min="0" max="1000" style="width: 4em" />
        </div>
        <div data-tip="Set scene lightness">
          <div>Lightness:</div>
          <input id="options3dLightnessRange" type="range" min="0" max="100" />
          <input id="options3dLightnessNumber" type="number" min="0" max="500" style="width: 4em" />
        </div>
        <div data-tip="Set mesh texture resolution">
          <div>Texture resolution:</div>
          <select id="options3dMeshSkinResolution" style="width: 10em">
            <option value="512">512x512px</option>
            <option value="1024">1024x1024px</option>
            <option value="2048">2048x2048px</option>
            <option value="4096" selected>4096x4096px</option>
            <option value="8192">8192x8192px</option>
          </select>
        </div>
        <div data-tip="Quick preset lighting for different times of day" style="margin-top: 0.4em">
          <label>Time of day:</label>
          <select id="options3dTimeOfDay" style="width: 10em; margin-bottom: 0.3em">
            <option value="custom">Custom</option>
            <option value="dawn">Dawn</option>
            <option value="noon" selected>Noon</option>
            <option value="evening">Evening</option>
            <option value="night">Night</option>
          </select>
        </div>
        <div data-tip="Set sun position (x, y) and color" style="margin-top: 0.4em">
          <label>Sun position and color:</label>
          <div style="display: flex; gap: 0.2em">
            <input id="options3dSunX" type="number" min="-2500" max="2500" step="100" style="width: 4.7em" />
            <input id="options3dSunY" type="number" min="0" max="5000" step="100" style="width: 4.7em" />
            <input id="options3dSunColor" type="color" style="padding: 0; height: 1.5em; border: none" />
          </div>
        </div>
        <div data-tip="Toggle 3d labels" style="margin: 0.6em 0 0.3em -0.2em">
          <input id="options3dMeshLabels3d" class="checkbox" type="checkbox" />
          <label for="options3dMeshLabels3d" class="checkbox-label"><i>Show 3D labels</i></label>
        </div>
        <div data-tip="Toggle sky mode" style="margin: 0.6em 0 0.3em -0.2em">
          <input id="options3dMeshSkyMode" class="checkbox" type="checkbox" />
          <label for="options3dMeshSkyMode" class="checkbox-label"><i>Show sky and extend water</i></label>
        </div>
        <div
          data-tip="Increases the polygon count to smooth the sharp points. Please note that it can take some time to calculate"
          style="margin: 0.6em 0 0.3em -0.2em"
        >
          <input id="options3dSubdivide" class="checkbox" type="checkbox" />
          <label for="options3dSubdivide" class="checkbox-label"
            ><i>Smooth geometry <small style="color: darkred">[slow]</small></i></label
          >
        </div>

        <div
          data-tip="Texture the terrain as a satellite image. Replaces the standard map texture"
          style="margin: 0.6em 0 0.3em -0.2em"
        >
          <input id="options3dSatellite" class="checkbox" type="checkbox" />
          <label for="options3dSatellite" class="checkbox-label"><i>Satellite texture</i></label>
        </div>

        <div
          data-tip="Bake procedural erosion detail into the 3D terrain. Visual only, the map data is not changed"
          style="margin: 0.6em 0 0.3em -0.2em"
        >
          <input id="options3dErosion" class="checkbox" type="checkbox" />
          <label for="options3dErosion" class="checkbox-label"><i>Erode terrain</i></label>
        </div>

        <div id="options3dErosionSection" style="display: none">
          <div data-tip="Set eroded mesh detail level (vertices on the long side)">
            <div>Mesh detail:</div>
            <select id="options3dErosionDetail" style="width: 10em">
              <option value="256">256</option>
              <option value="512">512</option>
              <option value="1024" selected>1024</option>
              <option value="2048">2048 [slow]</option>
            </select>
          </div>

          <div data-tip="Set the strength of erosion gullies and ridges">
            <div>Gully strength:</div>
            <input id="options3dErosionStrengthRange" type="range" min="0" max="100" />
            <input id="options3dErosionStrengthNumber" type="number" min="0" max="100" style="width: 4em" />
          </div>

          <div data-tip="Set how deep the valleys are carved along the rivers">
            <div>River valleys:</div>
            <input id="options3dErosionRiverDepthRange" type="range" min="0" max="100" />
            <input id="options3dErosionRiverDepthNumber" type="number" min="0" max="100" style="width: 4em" />
          </div>

          <div data-tip="Set the number of erosion detail layers. More octaves add finer gullies">
            <div>Detail octaves:</div>
            <select id="options3dErosionOctaves" style="width: 6em">
              <option value="1">1</option>
              <option value="2" selected>2</option>
              <option value="3">3</option>
              <option value="4">4</option>
            </select>
          </div>
        </div>

        <div data-tip="Toggle wireframe mode" style="margin: 0.6em 0 0.3em -0.2em">
          <input id="options3dMeshWireframeMode" class="checkbox" type="checkbox" />
          <label for="options3dMeshWireframeMode" class="checkbox-label"><i>Show wireframe</i></label>
        </div>
        <div data-tip="Set sky and water color" id="options3dColorSection" style="display: none">
          <span>Sky:</span
          ><input
            id="options3dMeshSky"
            type="color"
            style="width: 4.4em; height: 1em; border: 0; padding: 0; margin: 0 0.2em"
          />
          <span>Water:</span
          ><input
            id="options3dMeshWater"
            type="color"
            style="width: 4.4em; height: 1em; border: 0; padding: 0; margin: 0 0.2em"
          />
        </div>
      </div>
      <div id="options3dGlobe" style="display: none">
        <div data-tip="Set globe rotation speed. Set to 0 is you want to toggle off the rotation">
          <div>Rotation:</div>
          <input id="options3dGlobeRotationRange" type="range" min="0" max="10" step=".1" />
          <input id="options3dGlobeRotationNumber" type="number" min="0" max="10" step=".1" style="width: 4em" />
        </div>
        <div data-tip="Set globe texture resolution">
          <div>Texture resolution:</div>
          <select id="options3dGlobeResolution" style="width: 5em">
            <option value="0.5">0.5x</option>
            <option value="1">1x</option>
            <option value="2">2x</option>
            <option value="4">4x</option>
            <option value="8">8x</option>
          </select>
        </div>
        <div
          data-tip="Equirectangular projection is used: distortion is maximum on poles. Use map with aspect ratio 2:1 for best result"
          style="font-style: italic; margin: 0.2em 0"
        >
          Equirectangular projection is used
        </div>
      </div>
      <div id="options3dBottom" style="margin-top: 0.2em">
        <button id="options3dUpdate" data-tip="Update the scene" class="icon-cw"></button>
        <button
          data-tip="Configure world and map size and climate settings"
          onclick="window.Controllers.WorldConfigurator.open()"
          class="icon-globe"
        ></button>
        <button id="options3dSave" data-tip="Save screenshot of the 3d scene" class="icon-button-screenshot"></button>
        <button id="options3dOBJSave" data-tip="Save OBJ file of the 3d scene" class="icon-download"></button>
      </div>
    </div>`),e(`options3dUpdate`).addEventListener(`click`,()=>void d()),e(`options3dSave`).addEventListener(`click`,()=>void D()),e(`options3dOBJSave`).addEventListener(`click`,()=>void O()),e(`options3dScaleRange`).addEventListener(`input`,G),e(`options3dScaleNumber`).addEventListener(`change`,G),e(`options3dLightnessRange`).addEventListener(`input`,q),e(`options3dLightnessNumber`).addEventListener(`change`,q),e(`options3dSunX`).addEventListener(`change`,J),e(`options3dSunY`).addEventListener(`change`,J),e(`options3dMeshSkinResolution`).addEventListener(`change`,K),e(`options3dMeshRotationRange`).addEventListener(`input`,Y),e(`options3dMeshRotationNumber`).addEventListener(`change`,Y),e(`options3dGlobeRotationRange`).addEventListener(`input`,Y),e(`options3dGlobeRotationNumber`).addEventListener(`change`,Y),e(`options3dMeshLabels3d`).addEventListener(`change`,()=>void te()),e(`options3dMeshSkyMode`).addEventListener(`change`,de),e(`options3dMeshSky`).addEventListener(`input`,Q),e(`options3dMeshWater`).addEventListener(`input`,Q),e(`options3dGlobeResolution`).addEventListener(`change`,fe),e(`options3dMeshWireframeMode`).addEventListener(`change`,()=>void S()),e(`options3dSunColor`).addEventListener(`input`,oe),e(`options3dSubdivide`).addEventListener(`change`,()=>void ne()),e(`options3dTimeOfDay`).addEventListener(`change`,W),e(`options3dErosion`).addEventListener(`change`,se),e(`options3dErosionDetail`).addEventListener(`change`,ce),e(`options3dErosionStrengthRange`).addEventListener(`change`,X),e(`options3dErosionStrengthNumber`).addEventListener(`change`,X),e(`options3dErosionRiverDepthRange`).addEventListener(`change`,Z),e(`options3dErosionRiverDepthNumber`).addEventListener(`change`,Z),e(`options3dErosionOctaves`).addEventListener(`change`,ue),e(`options3dSatellite`).addEventListener(`change`,le)}function z(){$(`#options3d`).dialog(`destroy`),e(`options3d`).remove()}function B(t,n){e(t).value=String(n)}function V(){let t=options.app.threeD,n=document.getElementById(`canvas3d`)?.dataset.type===`viewGlobe`;e(`options3dMesh`).style.display=n?`none`:`block`,e(`options3dGlobe`).style.display=n?`block`:`none`,e(`options3dOBJSave`).style.display=n?`none`:`inline-block`,B(`options3dScaleRange`,t.scale),B(`options3dScaleNumber`,t.scale),B(`options3dLightnessRange`,t.lightness*100),B(`options3dLightnessNumber`,t.lightness*100),B(`options3dSunX`,t.sun.x),B(`options3dSunY`,t.sun.y),B(`options3dMeshRotationRange`,t.rotateMesh),B(`options3dMeshRotationNumber`,t.rotateMesh),B(`options3dMeshSkinResolution`,t.resolutionScale),B(`options3dGlobeRotationRange`,t.rotateGlobe),B(`options3dGlobeRotationNumber`,t.rotateGlobe),B(`options3dMeshLabels3d`,String(t.labels3d)),B(`options3dMeshSkyMode`,String(t.extendedWater)),e(`options3dColorSection`).style.display=t.extendedWater?`block`:`none`,B(`options3dMeshSky`,t.skyColor),B(`options3dMeshWater`,t.waterColor),B(`options3dGlobeResolution`,o(t.resolutionScale)),B(`options3dSunColor`,t.sunColor),B(`options3dSubdivide`,String(t.subdivide)),e(`options3dSubdivide`).disabled=!!t.erosion,e(`options3dErosion`).checked=!!t.erosion,e(`options3dErosionSection`).style.display=t.erosion?`block`:`none`,B(`options3dErosionDetail`,t.erosionDetail),B(`options3dErosionStrengthRange`,t.erosionStrength),B(`options3dErosionStrengthNumber`,t.erosionStrength),B(`options3dErosionRiverDepthRange`,t.erosionRiverDepth),B(`options3dErosionRiverDepthNumber`,t.erosionRiverDepth),B(`options3dErosionOctaves`,t.erosionOctaves),e(`options3dSatellite`).checked=!!t.satellite,H()}function H(){let t=e(`options3dTimeOfDay`),n=options.app.threeD,r=`custom`;for(let[e,t]of Object.entries(i))if(t.sun.x===n.sun.x&&t.sun.y===n.sun.y&&t.sun.z===n.sun.z&&t.sunColor===n.sunColor&&Math.abs(t.lightness-n.lightness)<.05){r=e;break}t.value=r}function U(){let t=e(`options3dTimeOfDay`);t.value!==`custom`&&(t.value=`custom`)}function W(){this.value!==`custom`&&(E(this.value),V())}function G(){B(`options3dScaleRange`,this.value),B(`options3dScaleNumber`,this.value),m(+this.value)}function K(){B(`options3dMeshSkinResolution`,this.value),h(+this.value)}function q(){B(`options3dLightnessRange`,this.value),B(`options3dLightnessNumber`,this.value),g(this.value/100),U()}function oe(){p(e(`options3dSunColor`).value),U()}function J(){_(+e(`options3dSunX`).value,+e(`options3dSunY`).value),U()}function Y(){let e=this.nextElementSibling||this.previousElementSibling;e&&(e.value=this.value),ee(+this.value)}function se(){let t=!options.app.threeD.erosion;e(`options3dErosionSection`).style.display=t?`block`:`none`,e(`options3dSubdivide`).disabled=t,t&&n(`Baking eroded terrain...`,!1,`warn`,4e3),re()}function ce(){y(+this.value)}function X(){B(`options3dErosionStrengthRange`,this.value),B(`options3dErosionStrengthNumber`,this.value),ie(+this.value)}function Z(){B(`options3dErosionRiverDepthRange`,this.value),B(`options3dErosionRiverDepthNumber`,this.value),v(+this.value)}function le(){options.app.threeD.satellite||n(`Baking satellite texture...`,!1,`warn`,4e3),x()}function ue(){b(+this.value)}function de(){let t=options.app.threeD.extendedWater;e(`options3dColorSection`).style.display=t?`none`:`block`,C()}function Q(){T(e(`options3dMeshSky`).value,e(`options3dMeshWater`).value)}function fe(){w(+this.value)}var pe={open:P,enterStandard:N,toggleOptions:L,redraw:u,update:d,isOn:k,isCached:A,heightAt:j};export{pe as View3d};