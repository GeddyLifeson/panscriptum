import{$ as e,$t as t,A as n,Bn as r,Ct as i,Dn as a,Jt as o,L as s,Ln as c,M as l,On as u,P as d,Qt as f,R as p,Rn as m,U as h,an as g,en as _,hn as v,j as y,on as b,rn as x,sn as S,tn as C,xn as w,yn as ee,z as te,zt as ne}from"./utils-Cob8vHf9.js";import{$ as re,J as ie,t as T}from"./layers-Bh4OWBXX.js";import{t as ae}from"./mean-4Awewi9R.js";import{t as oe}from"./drag-hfHVCxdY.js";import{n as se}from"./sin-DXK16t1M.js";import{t as ce}from"./quadtree-DgASQllf.js";import{r as le}from"./viewport-CRAO29Z3.js";import{i as E,r as ue,t as de}from"./tooltips-BTSHGd98.js";import{t as D}from"./state-B2hBYDzv.js";import{t as fe}from"./controllers-DnVd8NhQ.js";import{B as pe,Ct as me,G as he,V as ge,f as _e,lt as O,p as ve,st as k,tt as ye,ut as be,z as xe}from"./index-DsIn6sTp.js";import{t as Se}from"./brushUtils-B5xtY9tr.js";var A=18,Ce=.96422,we=1,Te=.82521,Ee=4/29,j=6/29,De=3*j*j,Oe=j*j*j;function ke(e){if(e instanceof M)return new M(e.l,e.a,e.b,e.opacity);if(e instanceof L)return Ne(e);e instanceof C||(e=g(e));var t=I(e.r),n=I(e.g),r=I(e.b),i=N((.2225045*t+.7168786*n+.0606169*r)/we),a,o;return t===n&&n===r?a=o=i:(a=N((.4360747*t+.3850649*n+.1430804*r)/Ce),o=N((.0139322*t+.0971045*n+.7141733*r)/Te)),new M(116*i-16,500*(a-i),200*(i-o),e.opacity)}function Ae(e,t,n,r){return arguments.length===1?ke(e):new M(e,t,n,r??1)}function M(e,t,n,r){this.l=+e,this.a=+t,this.b=+n,this.opacity=+r}b(M,Ae,S(_,{brighter(e){return new M(this.l+A*(e??1),this.a,this.b,this.opacity)},darker(e){return new M(this.l-A*(e??1),this.a,this.b,this.opacity)},rgb(){var e=(this.l+16)/116,t=isNaN(this.a)?e:e+this.a/500,n=isNaN(this.b)?e:e-this.b/200;return t=Ce*P(t),e=we*P(e),n=Te*P(n),new C(F(3.1338561*t-1.6168667*e-.4906146*n),F(-.9787684*t+1.9161415*e+.033454*n),F(.0719453*t-.2289914*e+1.4052427*n),this.opacity)}}));function N(e){return e>Oe?e**(1/3):e/De+Ee}function P(e){return e>j?e*e*e:De*(e-Ee)}function F(e){return 255*(e<=.0031308?12.92*e:1.055*e**(1/2.4)-.055)}function I(e){return(e/=255)<=.04045?e/12.92:((e+.055)/1.055)**2.4}function je(e){if(e instanceof L)return new L(e.h,e.c,e.l,e.opacity);if(e instanceof M||(e=ke(e)),e.a===0&&e.b===0)return new L(NaN,0<e.l&&e.l<100?0:NaN,e.l,e.opacity);var t=Math.atan2(e.b,e.a)*f;return new L(t<0?t+360:t,Math.sqrt(e.a*e.a+e.b*e.b),e.l,e.opacity)}function Me(e,t,n,r){return arguments.length===1?je(e):new L(e,t,n,r??1)}function L(e,t,n,r){this.h=+e,this.c=+t,this.l=+n,this.opacity=+r}function Ne(e){if(isNaN(e.h))return new M(e.l,0,0,e.opacity);var n=e.h*t;return new M(e.l,Math.cos(n)*e.c,Math.sin(n)*e.c,e.opacity)}b(L,Me,S(_,{brighter(e){return new L(this.h,this.c,this.l+A*(e??1),this.opacity)},darker(e){return new L(this.h,this.c,this.l-A*(e??1),this.opacity)},rgb(){return Ne(this).rgb()}}));var R=[{stroke:`#888`,width:.4,opacity:.8},{stroke:`#444`,width:.5,opacity:.8},{stroke:`#3d9df0`,width:.8,opacity:1},{stroke:`#1a6fd6`,width:1,opacity:1},{stroke:`#0a49ad`,width:1.2,opacity:1}],Pe=2,Fe=14,Ie=.5;function Le(e){let{cells:t,points:i,spacing:a}=grid,o=e?Grid.findDeepDepressionLakes(t,options.generation.lakeElevationLimit):[],s=Uint8Array.from(t.h);for(let e of o)for(let t of e)s[t]=19;let{target:c,flux:u,depth:d,river:f}=Ve({...t,h:s},Re(s)),p=a/Fe,h=a*.25,g=r(a*.35,2),_=R.map(()=>[]),v=[],b=e=>m(Math.floor(Math.log2(u[e]/30)/2)+Pe,0,f[e]?R.length-1:Pe-1),x=e=>r(Math.min(.5+e/30,1),2);for(let e of t.i){if(d[e]>=Ie&&v.push(`<polygon points="${Grid.getPolygon(e)}" fill-opacity="${x(d[e])}"/>`),c[e]===-1)continue;let[t,n]=i[e],[a,o]=i[c[e]],s=a-t,l=o-n,u=Math.hypot(s,l)||1,f=s/u,p=l/u,[m,g]=[t+f*u*.15,n+p*u*.15],[y,S]=[t+f*u*.7,n+p*u*.7],[C,w]=[y-h*(f*.87-p*.5),S-h*(p*.87+f*.5)],[ee,te]=[y-h*(f*.87+p*.5),S-h*(p*.87-f*.5)];_[b(e)].push(`M${r(m,1)},${r(g,1)}L${r(y,1)},${r(S,1)}M${r(C,1)},${r(w,1)}L${r(y,1)},${r(S,1)}L${r(ee,1)},${r(te,1)}`)}let S=_.map((e,t)=>{if(!e.length)return``;let{stroke:n,width:i,opacity:a}=R[t],o=`stroke="${n}" stroke-width="${r(i*p,2)}" opacity="${a}"`;return`<path d="${e.join(``)}" ${o}/>`}),C=o.flat().map(e=>`<polygon points="${Grid.getPolygon(e)}"/>`),w=()=>{let e=l(`drainage`);if(e)return e;let t=n(`g`,`drainage`,{"pointer-events":`none`});return y(`debug`).append(t),t};w().innerHTML=`
    <pattern id="drainageHatch" width="${g}" height="${g}" patternUnits="userSpaceOnUse">
      <path d="M0,${g}L${g},0" stroke="#333" stroke-width="${r(.5*p,2)}"/>
    </pattern>
    <pattern id="drainageLakeHatch" width="${g}" height="${g}" patternUnits="userSpaceOnUse">
      <path d="M0,0L${g},${g}" stroke="#1a5fc8" stroke-width="${r(.8*p,2)}"/>
    </pattern>
    <g fill="url(#drainageHatch)" stroke="#000" stroke-width="${r(.3*p,2)}">${v.join(``)}</g>
    <g fill="url(#drainageLakeHatch)" stroke="#1a5fc8" stroke-width="${r(.5*p,2)}">${C.join(``)}</g>
    <g fill="none">${S.join(``)}</g>`}var Re=e=>Precipitation.compute(e,Temperature.compute(e));function ze(){l(`drainage`)?.remove()}var Be=1e-4;function Ve(e,t){let{c:n,b:r,h:i}=e,a=e.i.length,o=new Float64Array(a),s=new Uint8Array(a),c=new FlatQueue;for(let e=0;e<a;e++)i[e]>=20&&!r[e]||(o[e]=i[e],s[e]=1,c.push(e,i[e]));for(;c.length;){let e=c.pop();for(let t of n[e])s[t]||(s[t]=1,o[t]=Math.max(i[t],o[e]+Be),c.push(t,o[t]))}let l=new Int32Array(a).fill(-1),u=new Float32Array(a),d=new Float32Array(a),f=[];for(let e=0;e<a;e++)if(!(i[e]<20||r[e])){f.push(e),d[e]=o[e]-i[e];for(let t of n[e])o[t]<o[l[e]===-1?e:l[e]]&&(l[e]=t)}let p=(Grid.getCellsDesired()/1e4)**.25;f.sort((e,t)=>o[t]-o[e]);for(let e of f)u[e]=Math.floor(u[e]+t[e]/p),l[e]!==-1&&(u[l[e]]+=u[e]);let m=new Uint8Array(a);for(let e of f)u[e]<30||l[e]===-1||(i[l[e]]>=20&&(m[e]=1),m[l[e]]=1);return{target:l,flux:u,depth:d,river:m}}var z=ne(re),B=`heightmapEditor`,He=[`renderOcean`,`showDrainage`,`allowErosion`],Ue=100,V,H=null,U=null;function We(e){V=D.get(B,`filters`,()=>({cellType:`all`})),[`all`,`land`,`water`].includes(V.cellType)||(V.cellType=`all`),D.set(B,`filters`,V);let{mode:t,tool:n}=e||{};HeightmapGenerator.clearData(),ct(),v(`#viewbox`).selectAll(`#heights`).remove(),v(`#viewbox`).insert(`g`,`#terrs`).attr(`id`,`heights`),t?G(t,n):Xe(n)}Je();function Ge(){O(`templateEditor`),y(`dialogs`).insertAdjacentHTML(`beforeend`,`<div id="templateEditor" class="dialog stable">
      <div id="templateTop">
        <i>Select template: </i>
        <select id="templateSelect" style="width: 16em" data-prev="templateCustom" data-tip="Select base template">
          <option value="custom" selected>Custom</option>
          <option value="volcano">Volcano</option>
          <option value="highIsland">High Island</option>
          <option value="lowIsland">Low Island</option>
          <option value="continents">Continents</option>
          <option value="archipelago">Archipelago</option>
          <option value="atoll">Atoll</option>
          <option value="mediterranean">Mediterranean</option>
          <option value="peninsula">Peninsula</option>
          <option value="pangea">Pangea</option>
          <option value="isthmus">Isthmus</option>
          <option value="shattered">Shattered</option>
          <option value="taklamakan">Taklamakan</option>
          <option value="oldWorld">Old World</option>
          <option value="fractious">Fractious</option>
        </select>
      </div>
      <div id="templateTools">
        <button data-type="Hill" data-tip="Hill: small blob">H</button>
        <button data-type="Pit" data-tip="Pit: round depression">P</button>
        <button data-type="Range" data-tip="Range: elongated elevation">R</button>
        <button data-type="Trough" data-tip="Trough: elongated depression">T</button>
        <button data-type="Strait" data-tip="Strait: centered vertical or horizontal depression">S</button>
        <button data-type="Mask" data-tip="Mask: lower cells near edges or in map center">M</button>
        <button data-type="Invert" data-tip="Invert heightmap along the axes">I</button>
        <button data-type="Add" data-tip="Add or subtract value from all heights in range">+</button>
        <button data-type="Multiply" data-tip="Multiply all heights in range by factor">*</button>
        <button
          data-type="Smooth"
          data-tip="Smooth the map replacing cell heights by an average values of its neighbors"
        >
          ~
        </button>
      </div>
      <div id="templateBody" data-changed="0" class="table" style="padding: 2px 0">
        <div data-type="Hill">
          <div class="icon-check" data-tip="Click to skip the step"></div>
          <div style="width: 4em">Hill</div>
          <i class="icon-trash-empty pointer" data-tip="Remove the step"></i>
          <i class="icon-resize-vertical" data-tip="Drag to reorder"></i>
          <span
            >y:<input class="templateY" data-tip="Y axis position in percentage (minY-maxY or Y)" value="47-53"
          /></span>
          <span
            >x:<input class="templateX" data-tip="X axis position in percentage (minX-maxX or X)" value="65-75"
          /></span>
          <span
            >h:<input
              class="templateHeight"
              data-tip="Blob maximum height, use hyphen to get a random number in range"
              value="90-100"
          /></span>
          <span
            >n:<input
              class="templateCount"
              data-tip="Blobs to add, use hyphen to get a random number in range"
              value="1"
          /></span>
        </div>
      </div>
      <div id="templateBottom">
        <button id="templateRun" data-tip="Execute the template" class="icon-play-circled2"></button>
        <button id="templateUndo" data-tip="Undo the latest action" class="icon-ccw" disabled></button>
        <button id="templateRedo" data-tip="Redo the action" class="icon-cw" disabled></button>
        <button id="templateSave" data-tip="Download the template as a text file" class="icon-download"></button>
        <button id="templateLoad" data-tip="Open previously downloaded template" class="icon-upload"></button>
        <button
          id="templateCA"
          data-tip="Find or share custom template on Cartography Assets portal"
          class="icon-drafting-compass"
          onclick="
            openURL('https://cartographyassets.com/asset-category/specific-assets/azgaars-generator/templates')
          "
        ></button>
        <button
          id="templateTutorial"
          data-tip="Open Template Editor Tutorial"
          class="icon-info"
          onclick="wiki('Heightmap-template-editor')"
        ></button>
        <label
          data-tip="Enter seed for template to generate the same heightmap each time"
        >
          Seed: <input id="templateSeed" value="" type="number" min="1" max="999999999" step="1" style="width: 8em" />
        </label>
      </div>
    </div>`);let e=y(`templateBody`);$(`#templateBody`).sortable({items:`> div`,handle:`.icon-resize-vertical`,containment:`#templateBody`,axis:`y`}),e.addEventListener(`click`,t=>{let n=t.target;if(n.classList.contains(`icon-check`)){n.classList.remove(`icon-check`),n.classList.add(`icon-check-empty`),n.parentElement.style.opacity=`0.5`,e.dataset.changed=`1`;return}if(n.classList.contains(`icon-check-empty`)){n.classList.add(`icon-check`),n.classList.remove(`icon-check-empty`),n.parentElement.style.opacity=`1`;return}n.classList.contains(`icon-trash-empty`)&&n.parentElement.remove()}),y(`templateEditor`).addEventListener(`keypress`,e=>{e.key===`Enter`&&(e.preventDefault(),Ft())}),y(`templateTools`).addEventListener(`click`,kt),y(`templateSelect`).addEventListener(`change`,Nt),y(`templateRun`).addEventListener(`click`,Ft),y(`templateUndo`).addEventListener(`click`,()=>X(edits.n-1)),y(`templateRedo`).addEventListener(`click`,()=>X(edits.n+1)),y(`templateSave`).addEventListener(`click`,It),y(`templateLoad`).addEventListener(`click`,Lt)}function Ke(){O(`imageConverter`),y(`dialogs`).insertAdjacentHTML(`beforeend`,`<div id="imageConverter" class="dialog stable">
      <div id="convertImageButtons">
        <button id="convertImageLoad" data-tip="Load image to convert" class="icon-upload"></button>
        <button
          id="convertAutoLum"
          data-tip="Auto-assign colors based on liminosity (good for monochrome images)"
          class="icon-adjust"
        ></button>
        <button
          id="convertAutoHue"
          data-tip="Auto-assign colors based on hue (good for colored images)"
          class="icon-paint-roller"
        ></button>
        <button
          id="convertAutoFMG"
          data-tip="Auto-assign colors using generator scheme (for exported colored heightmaps)"
          class="icon-layer-group"
        ></button>
        <button id="convertColorsButton" data-tip="Set maximum number of colors" class="icon-signal"></button>
        <input id="convertColors" value="100" style="display: none" />
        <button
          id="convertCancel"
          data-tip="Cancel the conversion. Previous heightmap will be restored"
          class="icon-cancel"
        ></button>
      </div>
      <div data-tip="Set opacity of the loaded image" style="padding-top: 0.4em">
        <i>Overlay opacity:</i><br />
        <input id="convertOverlay" type="range" min="0" max="1" step=".01" value="0" style="width: 12.6em" />
        <input id="convertOverlayNumber" type="number" min="0" max="1" step=".01" value="0" style="width: 4.2em" />
      </div>
      <div data-tip="Select a color below and assign a height value for it" id="colorsSelect" style="display: none">
        <i>Set height: </i>
        <span id="colorsSelectValue"></span>
        <span>(<span id="colorsSelectFriendly">0</span>)</span><br />
        <div id="imageConverterPalette"></div>
      </div>
      <div data-tip="Select a color to re-assign the height value" id="colorsAssigned" style="display: none">
        <i>Assigned colors (<span id="colorsAssignedNumber"></span>):</i>
        <div id="colorsAssignedContainer" class="colorsContainer"></div>
      </div>
      <div data-tip="Select a color to assign a height value" id="colorsUnassigned" style="display: none">
        <i>Unassigned colors (<span id="colorsUnassignedNumber"></span>):</i>
        <div id="colorsUnassignedContainer" class="colorsContainer"></div>
      </div>
      <button
        id="convertComplete"
        data-tip="Complete the conversion. All unassigned colors will be considered as ocean"
        style="margin: 0.4em 0"
        class="glow"
      >
        Complete the conversion
      </button>
    </div>`),v(`#imageConverterPalette`).selectAll(`div`).data(ee(101)).enter().append(`div`).attr(`data-color`,e=>e).style(`background-color`,e=>z(1-(e<20?e-5:e)/100)).style(`width`,e=>e<40||e>68?`.2em`:`.1em`).on(`touchmove mousemove`,Vt).on(`click`,Gt),y(`convertImageLoad`).addEventListener(`click`,zt),y(`convertAutoLum`).addEventListener(`click`,()=>Kt(`lum`)),y(`convertAutoHue`).addEventListener(`click`,()=>Kt(`hue`)),y(`convertAutoFMG`).addEventListener(`click`,()=>Kt(`scheme`)),y(`convertColorsButton`).addEventListener(`click`,qt),y(`convertComplete`).addEventListener(`click`,Yt),y(`convertCancel`).addEventListener(`click`,Xt),y(`convertOverlay`).addEventListener(`input`,function(){Jt(+this.value)}),y(`convertOverlayNumber`).addEventListener(`input`,function(){Jt(+this.value)})}var qe=[];function Je(){y(`paintBrushes`).addEventListener(`click`,lt),y(`applyTemplate`).addEventListener(`click`,Dt),y(`convertImage`).addEventListener(`click`,Bt),y(`heightmapPreview`).addEventListener(`click`,Qt),y(`heightmap3DView`).addEventListener(`click`,ye),y(`finalizeHeightmap`).addEventListener(`click`,$e);for(let e of He)y(e).addEventListener(`change`,function(){Options.set(t=>t.app.heightmapEditor[e]=this.checked),e===`renderOcean`&&q(),e!==`renderOcean`&&Ye()})}function Ye(){options.app.heightmapEditor.showDrainage?W():ze()}function W(){if(customization!==1||!options.app.heightmapEditor.showDrainage)return;let e=y(`heightmapEditMode`).innerHTML;Le(e!==`keep`&&options.app.heightmapEditor.allowErosion)}function Xe(t){alertMessage.innerHTML=`Heightmap is a core element on which all other data (rivers, burgs, states etc) is based. So the best edit approach is to
    <i>erase</i> the secondary data and let the system automatically regenerate it on edit completion.
    <p><i>Erase</i> mode also allows you Convert an Image into a heightmap or use Template Editor.</p>
    <p>You can <i>keep</i> the data, but you won't be able to change the coastline.</p>
    <p>Try <i>risk</i> mode to change the coastline and keep the data. The data will be restored as much as possible, but it can cause unpredictable errors.</p>
    <p>Please <span class="pseudoLink" onclick="window.Services.Save.toMachine()">save the map</span> before editing the heightmap!</p>
    <p style="margin-bottom: 0">Check out ${e(`https://github.com/Azgaar/Fantasy-Map-Generator/wiki/Heightmap-customization`,`wiki`)} for guidance.</p>`,$(`#alert`).dialog({resizable:!1,title:`Edit Heightmap`,width:`28em`,buttons:{Erase:()=>G(`erase`,t),Keep:()=>G(`keep`,t),Risk:()=>G(`risk`,t),Cancel:function(){$(this).dialog(`close`)}}})}function G(e,t){qe=T.state.active,T.set([]),customization=1,k(),E(`Heightmap edit mode is active. Click on "Exit Customization" to finalize the heightmap`,!0),y(`options`).querySelectorAll(`.tabcontent`).forEach(e=>{e.style.display=`none`}),y(`options`).querySelector(`.tab > .active`).classList.remove(`active`),y(`customizationMenu`).style.display=`block`,y(`toolsTab`).classList.add(`active`),y(`heightmapEditMode`).innerHTML=e;for(let e of He)y(e).checked=options.app.heightmapEditor[e];e===`erase`?(he(),V.cellType=`all`):e===`keep`?(T.get(`landmass`).getEl().replaceChildren(),V.cellType=`land`):e===`risk`&&(v(`#deftemp`).selectAll(`#land, #water`).selectAll(`path`).remove(),v(`#deftemp`).select(`#featurePaths`).selectAll(`path`).remove(),v(`#viewbox`).selectAll(`#coastline use, #lakes path, #oceanLayers path`).remove(),V.cellType=`all`);let n=l(`cellTypeFilter`);n&&(n.value=V.cellType),D.set(B,`filters`,V),y(`applyTemplate`).style.display=e===`erase`?`inline-block`:`none`,y(`convertImage`).style.display=e===`erase`?`inline-block`:`none`,y(`allowErosionBox`).style.display=e===`keep`?`none`:`inline-block`;let r=y(`exitCustomization`);if(sessionStorage.getItem(`noExitButtonAnimation`))r.style.display=`block`;else{sessionStorage.setItem(`noExitButtonAnimation`,`true`),r.style.opacity=`0`;let e=12*y(`uiSize`).value*11;r.style.right=`${(le.width-e)/2}px`,r.style.bottom=`${le.height/2}px`,r.style.transform=`scale(2)`,r.style.display=`block`,v(`#exitCustomization`).transition().duration(1e3).style(`opacity`,1).transition().duration(2e3).ease(se).style(`right`,`10px`).style(`bottom`,`10px`).style(`transform`,`scale(1)`)}let i=y(`layersPreset`);i.value=`heightmap`,i.disabled=!0,q(),W(),v(`#viewbox`).on(`touchmove mousemove`,Ze),v(`#map`).on(`dblclick.zoom`,null),t===`templateEditor`?Dt():t===`imageConverter`?Bt():lt()}function Ze(e){let[t,n]=d(e,this),i=Grid.findCell(t,n);y(`heightmapInfoX`).innerHTML=String(r(t)),y(`heightmapInfoY`).innerHTML=String(r(n)),y(`heightmapInfoCell`).innerHTML=String(i),y(`heightmapInfoHeight`).innerHTML=`${grid.cells.h[i]} (${Qe(grid.cells.h[i])})`,y(`tooltip`).dataset.main&&ue();let a=l(`brushesButtons`)?.querySelector(`button.pressed`);if(a){if(a.id===`brushLine`){v(`#debug`).select(`line`).attr(`x2`,t).attr(`y2`,n);return}if(a.id===`brushFill`){ve();return}_e(t,n,y(`heightmapBrushRadius`).valueAsNumber)}}function Qe(e){let t=options.map.units.height.unit,n=3.281;t===`m`?n=1:t===`f`&&(n=.5468);let i=-990;return e>=20?i=(e-18)**options.map.units.height.exponent:e<20&&e>0&&(i=(e-20)/e*50),`${r(i*n)} ${t}`}async function $e(){if(v(`#viewbox`).select(`#heights`).selectAll(`*`).size()<200){E(`Insufficient land area. There should be at least 200 land cells!`,!1,`error`);return}if(l(`imageConverter`)){E(`Please exit the Image Conversion mode first`,!1,`error`);return}Reflect.deleteProperty(window,`edits`),J(!0,!0),HeightmapGenerator.clearData(),customization=0,y(`customizationMenu`).style.display=`none`,y(`options`).querySelector(`.tab > button.active`).id===`toolsTab`&&(y(`toolsContent`).style.display=`block`),y(`layersPreset`).disabled=!1,y(`exitCustomization`).style.display=`none`,ge(),de(),k(),resetZoom(),document.getElementById(`preview`)?.remove(),document.getElementById(`canvas3d`)&&fe.View3d.enterStandard();let e=y(`heightmapEditMode`).innerHTML;try{e===`erase`?await et():e===`keep`?tt():e===`risk`&&rt()}catch(e){ERROR&&console.error(e),E(`Failed to apply the edited heightmap: ${e.message}`,!1,`error`,6e3)}v(`#viewbox`).selectAll(`#heights`).remove(),ze(),T.draw(`ocean`,`landmass`,`lakes`,`coastline`),T.set(qe)}async function et(){pack.cultures=[],pack.burgs=[],pack.states=[],pack.provinces=[],pack.religions=[],pack.relief=[];let e=options.app.heightmapEditor.allowErosion;await xe.run({erosion:e})}function tt(){for(let e of pack.cells.i)pack.cells.h[e]=grid.cells.h[pack.cells.g[e]]}var nt=e=>{let t=[];for(let n=0;n<e.p.length;n++)e.h[n]>=20&&t.push([e.p[n][0],e.p[n][1],n]);let n=ce(t);return(e,t)=>{let r=n.find(e,t);if(r)return n.remove(r),r[2]}};function rt(){INFO&&console.group(`Edit Heightmap`),TIME&&console.time(`restoreRiskedData`);let e=options.app.heightmapEditor.allowErosion,t=grid.cells.i.length,n=new Uint8Array(t),r=new Uint16Array(t),i={},a=new Uint16Array(t),o=new Uint16Array(t),s=new Uint16Array(t),c=new Uint16Array(t),l=new Uint16Array(t),d=new Uint16Array(t),f=new Uint16Array(t),p=new Uint16Array(t),m=new Uint16Array(t),h=new Uint8Array(t);for(let t of pack.cells.i){let u=pack.cells.g[t];n[u]=pack.cells.biome[t],l[u]=pack.cells.culture[t],r[u]=pack.cells.pop[t],i[u]=pack.cells.routes[t],a[u]=pack.cells.s[t],s[u]=pack.cells.state[t],c[u]=pack.cells.province[t],o[u]=pack.cells.burg[t],d[u]=pack.cells.religion[t],f[u]=pack.cells.good?.[t]||0,e||(p[u]=pack.cells.fl[t],m[u]=pack.cells.r[t],h[u]=pack.cells.conf[t])}for(let e of grid.cells.i)o[e]&&grid.cells.h[e]<20&&(grid.cells.h[e]=20);for(let e of pack.cultures){if(!e.i||e.removed)continue;let t=pack.cells.p[e.center];e.x=t[0],e.y=t[1]}let g=Features.captureUserData(),_=new Map;for(let e of pack.zones){if(!e.cells?.length)continue;let t=e.cells.map(e=>pack.cells.g[e]);_.set(e.i,u(t))}Features.markupGrid(),e&&Grid.addDeepDepressionLakes(),Temperature.generate(),Precipitation.generate(),Pack.generate(),Features.markupPack(),pe.restore(),e&&(Rivers.generate(!0),Features.defineGroups()),Features.restoreUserData(g);let y=pack.cells.i.length;pack.cells.pop=new Float32Array(y),pack.cells.routes={},pack.cells.s=new Uint16Array(y),pack.cells.burg=new Uint16Array(y),pack.cells.state=new Uint16Array(y),pack.cells.province=new Uint16Array(y),pack.cells.culture=new Uint16Array(y),pack.cells.religion=new Uint16Array(y),pack.cells.biome=new Uint8Array(y),pack.cells.good=new Uint16Array(y),e||(pack.cells.r=new Uint16Array(y),pack.cells.conf=new Uint8Array(y),pack.cells.fl=new Uint16Array(y));for(let t of pack.cells.i){let o=pack.cells.g[t],u=pack.cells.h[t]>=20;e||(pack.cells.r[t]=m[o],pack.cells.conf[t]=h[o],pack.cells.fl[t]=p[o]),pack.cells.biome[t]=u&&n[o]?n[o]:Biomes.getId(grid.cells.prec[o],grid.cells.temp[o],pack.cells.h[t],!!pack.cells.r[t]),pack.cells.good[t]=f[o],u&&(pack.cells.culture[t]=l[o],pack.cells.pop[t]=r[o],pack.cells.routes[t]=i[o],pack.cells.s[t]=a[o],pack.cells.state[t]=s[o],pack.cells.province[t]=c[o],pack.cells.religion[t]=d[o])}let b=nt(pack.cells);for(let e of pack.burgs){if(!e.i||e.removed)continue;let t=b(e.x,e.y);if(t===void 0){ERROR&&console.error(`[Data integrity] Burg ${e.i} has no available land cell after Risk restoration. Removing the burg`),Burgs.remove(e.i),ie(`burg`,e.i);continue}e.cell=t,e.feature=pack.cells.f[e.cell],pack.cells.burg[e.cell]=e.i,!e.capital&&pack.cells.h[e.cell]<20&&(Burgs.remove(e.i),ie(`burg`,e.i)),e.capital&&(pack.states[e.state].center=e.cell)}for(let e of pack.provinces){if(!e.i||e.removed)continue;let t=pack.cells.i.filter(t=>pack.cells.province[t]===e.i);if(!t.length){let t=e.state,n=pack.states[t].provinces;n.includes(e.i)&&pack.states[t].provinces.splice(n.indexOf(e.i),1),e.removed=!0;continue}e.burg&&!pack.burgs[e.burg].removed?e.center=pack.burgs[e.burg].cell:(e.center=t[0],e.burg=pack.cells.burg[e.center])}for(let e of pack.cultures)!e.i||e.removed||(e.center=Pack.findCell(e.x,e.y));States.getPoles(),States.findNeighbors(),States.collectStatistics(),e&&(Rivers.specify(),Features.defineNames());let x=new Map;for(let e of pack.cells.i){let t=pack.cells.g[e];x.has(t)||x.set(t,[]),x.get(t).push(e)}for(let e of pack.zones){let t=_.get(e.i);t?.length?e.cells=u(t.flatMap(e=>x.get(e)||[])):e.cells=[]}pack.goods?.length?(pack.markets=(pack.markets||[]).filter(e=>{let t=pack.burgs[e.centerBurgId];return!!(t&&!t.removed)}),Production.regenerateEconomy(),T.draw(`markets`,`goods`),T.draw(`trade`),be()):(Goods.generate(),Markets.generate(),Production.produce(),States.collectTaxes()),Ice.generate(),v(`#ice`).selectAll(`*`).remove(),TIME&&console.timeEnd(`restoreRiskedData`),INFO&&console.groupEnd()}function K(){let e=a(edits),t=grid.cells.h.reduce((t,n,r)=>n===e[r]?t:t+1,0);if(E(`Cells changed: ${t}`),!t)return;let n=l(`cellTypeFilter`)?.value??V.cellType;if(n===`land`)for(let t of grid.cells.i)(e[t]<20||grid.cells.h[t]<20)&&(grid.cells.h[t]=e[t]);if(n===`water`)for(let t of grid.cells.i)(e[t]>=20||grid.cells.h[t]>=20)&&(grid.cells.h[t]=e[t]);q(),Y()}function it(e,t=getColorScheme(`bright`)){return t(1-(e<20?e-5:e)/100)}function q(){let e=Array.from(grid.cells.i),t=options.app.heightmapEditor.renderOcean?e:e.filter(e=>grid.cells.h[e]>=20);v(`#viewbox`).select(`#heights`).selectAll(`polygon`).data(t).join(`polygon`).attr(`points`,e=>String(Grid.getPolygon(e))).attr(`id`,e=>`cell${e}`).attr(`fill`,e=>it(grid.cells.h[e]))}function at(e){let t=options.app.heightmapEditor.renderOcean;e.forEach(e=>{let n=v(`#viewbox`).select(`#heights`).select(`#cell${e}`);if(!t&&grid.cells.h[e]<20){n.remove();return}n.size()||(n=v(`#viewbox`).select(`#heights`).append(`polygon`).attr(`points`,String(Grid.getPolygon(e))).attr(`id`,`cell${e}`)),n.attr(`fill`,it(grid.cells.h[e]))})}function ot(){let e=grid.cells.h.reduce((e,t)=>t>=20?e+1:e,0);y(`landmassCounter`).innerText=`${e} (${r(e/grid.cells.i.length*100)}%)`,y(`landmassAverage`).innerText=String(r(ae(grid.cells.h)??0))}function J(e,t){let n=(n,r)=>{let i=l(n);i&&(i.disabled=e);let a=l(r);a&&(a.disabled=t)};n(`undo`,`redo`),n(`templateUndo`,`templateRedo`)}function Y(e){let t=edits.n;if(edits=Object.assign(edits.slice(0,t),{n:t+1}),edits[t]=grid.cells.h.slice(),edits.length>Ue){let e=edits.length-Ue;edits.splice(0,e),edits.n-=e}J(edits.n<=1,!0),e||(ot(),st())}function st(){document.getElementById(`preview`)&&$t(),document.getElementById(`canvas3d`)&&fe.View3d.redraw(),W()}function X(e){edits.n=e,J(edits.n<=1,edits.n>=edits.length),edits[edits.n-1]!==void 0&&(grid.cells.h=edits[edits.n-1].slice(),q(),ot(),st())}function ct(){window.edits=Object.assign([],{n:0}),J(!0,!0),Y()}function lt(){document.getElementById(`brushesPanel`)||(ut(),$(`#brushesPanel`).dialog({title:`Paint Brushes`,resizable:!1,position:{my:`right top`,at:`right-10 top+10`,of:`svg`},close:dt}))}function ut(){O(`brushesPanel`);let e=`<div id="brushesPanel" class="dialog stable">
    <div id="brushesButtons" style="display: inline-block">
      <button id="brushRaise" data-tip="Raise brush: increase height of cells in radius by Power value">
        <svg viewBox="15 15 70 70" height="1em" width="1.6em">
          <path d="m20,39 h60 M50,85 v-35 l-12,8 m12,-8 l12,8" fill="none" stroke="#000" stroke-width="5" />
        </svg>
      </button>
      <button id="brushElevate" data-tip="Elevate brush: drag to gradually increase height of cells in radius by Power value">
        <svg viewBox="15 15 70 70" height="1em" width="1.6em">
          <path d="m20,50 q30,-35 60,0 M50,85 v-35 l-12,8 m12,-8 l12,8" fill="none" stroke="#000" stroke-width="5" />
        </svg>
      </button>
      <button id="brushLower" data-tip="Lower brush: drag to decrease height of cells in radius by Power value">
        <svg viewBox="15 15 70 70" height="1em" width="1.6em">
          <path d="M50,30 v35 l-12,-8 m12,8 l12,-8 M20,78 h60" fill="none" stroke="#000" stroke-width="5" />
        </svg>
      </button>
      <button id="brushDepress" data-tip="Depress brush: drag to gradually decrease height of cells in radius by Power value">
        <svg viewBox="15 15 70 70" height="1em" width="1.6em">
          <path d="M50,30 v35 l-12,-8 m12,8 l12,-8 M20,63 q30,35 60,0" fill="none" stroke="#000" stroke-width="5" />
        </svg>
      </button>
      <button id="brushAlign" data-tip="Align brush: drag to set height of cells in radius to height of the cell at mousepoint">
        <svg viewBox="15 15 70 70" height="1em" width="1.6em">
          <path d="m20,50 h56 m0,20 h-56" fill="none" stroke="#000" stroke-width="5" />
        </svg>
      </button>
      <button id="brushSmooth" data-tip="Smooth brush: drag to level height of cells in radius to height of adjacent cells">
        <svg viewBox="15 15 70 70" height="1em" width="1.6em">
          <path d="m15,60 q15,-15 30,0 q15,15 35,0" fill="none" stroke="#000" stroke-width="5" />
        </svg>
      </button>
      <button id="brushDisrupt" data-tip="Disrupt brush: drag to randomize height of cells in radius based on Power value">
        <svg viewBox="15 15 70 70" height="1em" width="1.6em">
          <path d="m15,63 l15,-13 15,20 15,-20 15,19 15,-14" fill="none" stroke="#000" stroke-width="5" />
        </svg>
      </button>
      <button id="brushFill" data-tip="Fill: click enclosed water or same-height land area to create a cone blob">
        <svg viewBox="20 10 60 60" height="1em" width="1.6em">
          <path d="M30,70 h40 M30,70 q0,-20 20,-20 q20,0 20,20" fill="none" stroke="#000" stroke-width="5" />
          <path d="M50,20 v25 M50,20 l-10,8 M50,20 l10,8" fill="none" stroke="#000" stroke-width="5" />
        </svg>
      </button>
      <button id="brushLine" data-tip="Line: select two points to change heights along the line">
        <svg viewBox="0 -5 100 100" height="1em" width="1.6em">
          <path d="M0 90 L100 10" fill="none" stroke="#000" stroke-width="7"></path>
        </svg>
      </button>
    </div>
    <div id="brushesSliders" style="display: none">
      <div data-tip="Change brush size. Shortcut: + to increase; – to decrease">
        <slider-input id="heightmapBrushRadius" data-brush-size min="1" max="100" value="25">
          <div style="width: 3.5em">Radius:</div>
        </slider-input>
      </div>
      <div data-tip="Change brush power">
        <slider-input id="heightmapBrushPower" data-brush-size min="1" max="10" value="5">
          <div style="width: 3.5em">Power:</div>
        </slider-input>
      </div>
    </div>
    <div id="lineSlider" style="display: none">
      <div data-tip="Change tool power. Shortcut: + to increase; – to decrease">
        <slider-input id="heightmapLinePower" data-brush-size min="-100" max="100" value="30">
          <div style="width: 5.5em">Power:</div>
        </slider-input>
      </div>
      <div data-tip="Change line randomness. Zero makes the line as straight as possible">
        <slider-input id="heightmapLineRandomness" min="0" max="100" value="30">
          <div style="width: 5.5em">Randomness:</div>
        </slider-input>
      </div>
    </div>
    <div data-tip="Restrict brush to specific cell types" style="margin-bottom: 0.6em">
      <label for="cellTypeFilter"><i>Cells to change:</i></label>
      <select id="cellTypeFilter">
        <option value="all" ${V.cellType===`all`?`selected`:``}>all cells</option>
        <option value="land" ${V.cellType===`land`?`selected`:``}>only land cells</option>
        <option value="water" ${V.cellType===`water`?`selected`:``}>only water cells</option>
      </select>
    </div>
    <div id="modifyButtons">
      <button id="undo" data-tip="Undo the latest action (Ctrl + Z)" class="icon-ccw" disabled></button>
      <button id="redo" data-tip="Redo the action (Ctrl + Y)" class="icon-cw" disabled></button>
      <button id="rescaleShow" data-tip="Show rescaler slider" class="icon-exchange"></button>
      <button id="rescaleCondShow" data-tip="Rescaler: change height if condition is fulfilled" class="icon-if"></button>
      <button id="smoothHeights" data-tip="Smooth all heights a bit" class="icon-smooth"></button>
      <button id="disruptHeights" data-tip="Disrupt (randomize) heights a bit" class="icon-disrupt"></button>
      <button id="brushClear" data-tip="Set height for all cells to 0 (erase the map)" class="icon-eraser"></button>
    </div>
    <div id="rescaleSection" style="display: none">
      <button id="rescaleHide" data-tip="Hide rescaler slider" class="icon-exchange"></button>
      <input id="rescaler" data-tip="Change height for all cells" type="range" min="-10" max="10" step="1" value="0" />
    </div>
    <div
      id="rescaleCondSection"
      data-tip="If height is greater or equal to X and less or equal to Y, then perform an operation Z with operand V"
      style="display: none"
    >
      <button id="rescaleCondHide" data-tip="Hide rescaler" class="icon-if"></button>
      <label>h ≥</label>
      <input id="rescaleLower" value="20" type="number" min="0" max="100" />
      <label>≤</label>
      <input id="rescaleHigher" value="100" type="number" min="1" max="100" />
      <label>⇒</label>
      <select id="conditionSign">
        <option value="multiply" selected>×</option>
        <option value="divide">÷</option>
        <option value="add">+</option>
        <option value="subtract">-</option>
        <option value="exponent">^</option>
      </select>
      <input id="rescaleModifier" type="number" value="0.9" min="0" max="1.5" step="0.01" />
      <button id="rescaleExecute" data-tip="Click to perform an operation" class="icon-play-circled2"></button>
    </div>
  </div>`;y(`dialogs`).insertAdjacentHTML(`beforeend`,e),ft()}function dt(){pt(),O(`brushesPanel`)}function ft(){y(`brushesButtons`).addEventListener(`click`,mt),y(`cellTypeFilter`).addEventListener(`change`,xt),y(`undo`).addEventListener(`click`,()=>X(edits.n-1)),y(`redo`).addEventListener(`click`,()=>X(edits.n+1)),y(`rescaleShow`).addEventListener(`click`,()=>{y(`modifyButtons`).style.display=`none`,y(`rescaleSection`).style.display=`block`}),y(`rescaleHide`).addEventListener(`click`,()=>{y(`modifyButtons`).style.display=`block`,y(`rescaleSection`).style.display=`none`}),y(`rescaler`).addEventListener(`change`,e=>St(e.target.valueAsNumber)),y(`rescaleCondShow`).addEventListener(`click`,()=>{y(`modifyButtons`).style.display=`none`,y(`rescaleCondSection`).style.display=`block`}),y(`rescaleCondHide`).addEventListener(`click`,()=>{y(`modifyButtons`).style.display=`block`,y(`rescaleCondSection`).style.display=`none`}),y(`rescaleExecute`).addEventListener(`click`,Ct),y(`smoothHeights`).addEventListener(`click`,wt),y(`disruptHeights`).addEventListener(`click`,Tt),y(`brushClear`).addEventListener(`click`,Et)}function pt(){let e=document.querySelector(`#brushesButtons > button.pressed`);e&&e.classList.remove(`pressed`),ge(),v(`#map`).on(`dblclick.zoom`,null),v(`#viewbox`).on(`touchmove mousemove`,Ze),v(`#debug`).selectAll(`#brushCircle, .lineCircle`).remove(),ve(),y(`brushesSliders`).style.display=`none`,y(`lineSlider`).style.display=`none`}function mt(e){let t=e.target.closest(`#brushesButtons > button`);if(!t)return;if(t.classList.contains(`pressed`)){pt();return}pt(),t.classList.add(`pressed`);let n=y(`heightmapBrushRadius`).parentElement;n&&(n.style.display=t.id===`brushFill`?`none`:``),t.id===`brushLine`?(y(`lineSlider`).style.display=`block`,v(`#viewbox`).style(`cursor`,`crosshair`).on(`click`,ht)):t.id===`brushFill`?(y(`brushesSliders`).style.display=`block`,v(`#viewbox`).style(`cursor`,`crosshair`).on(`click`,gt)):(y(`brushesSliders`).style.display=`block`,v(`#viewbox`).style(`cursor`,`crosshair`).call(oe().on(`start`,yt)))}function ht(e){let[t,n]=d(e,this),r=Grid.findCell(t,n),i=v(`#debug`).selectAll(`.lineCircle`);if(!i.size()){v(`#debug`).append(`line`).attr(`id`,`brushCircle`).attr(`x1`,t).attr(`y1`,n).attr(`x2`,t).attr(`y2`,n),v(`#debug`).append(`circle`).attr(`data-cell`,r).attr(`class`,`lineCircle`).attr(`r`,6).attr(`cx`,t).attr(`cy`,n).attr(`fill`,`yellow`).attr(`stroke`,`#333`).attr(`stroke-width`,2);return}let a=+i.attr(`data-cell`);v(`#debug`).selectAll(`*`).remove();let o=y(`heightmapLinePower`).valueAsNumber;if(o===0){E(`Power should not be zero`,!1,`error`);return}let s=y(`heightmapLineRandomness`).valueAsNumber/200,c=grid.cells.h,l=o>0?HeightmapGenerator.addRange.bind(HeightmapGenerator):HeightmapGenerator.addTrough.bind(HeightmapGenerator);HeightmapGenerator.setGraph(grid),l(`1`,String(Math.abs(o)),``,``,a,r,s);let u=HeightmapGenerator.getHeights(),f=y(`cellTypeFilter`).value,p=[];for(let e=0;e<c.length;e++)u[e]!==c[e]&&(f===`land`&&c[e]<20||f===`water`&&c[e]>=20||(c[e]=u[e],p.push(e)));at(p),Y()}function gt(e){let[t,n]=d(e,this),r=Grid.findCell(t,n),i=grid.cells.h[r],a=i<20,o=y(`cellTypeFilter`).value;if(o===`water`){E(`Fill brush is not available with 'only water cells' filter`,!1,`error`);return}if(o===`land`&&a){E(`Land filter is active, water areas cannot be filled`,!1,`error`);return}let{selection:s,reachedBorder:c}=_t(r,a,i);if(s.length<3){E(`No enclosed area found to fill`,!1,`error`);return}if(a&&c){E(`Selected water area is open to map border and is not enclosed`,!1,`error`);return}let l=vt(s,a,i);l.length&&(at(l),K())}function _t(e,t,n){let{h:r,c:i,i:a}=grid.cells,o=new Uint8Array(a.length),s=[e],c=[],l=!1;for(;s.length;){let e=s.pop();o[e]||(o[e]=1,(t?r[e]<20:r[e]===n)&&(c.push(e),grid.cells.b[e]&&(l=!0),i[e].forEach(e=>{o[e]||s.push(e)})))}return{selection:c,reachedBorder:l}}function vt(e,t,n){let r=y(`heightmapBrushPower`).valueAsNumber*10,{h:i,c:a,i:o}=grid.cells,s=new Uint8Array(o.length),c=new Uint16Array(o.length),l=[];e.forEach(e=>{s[e]=1});let u=[],d=0;for(e.forEach(e=>{a[e].some(e=>!s[e])&&(s[e]=2,u.push(e))});d<u.length;){let e=u[d++],t=c[e]+1;a[e].forEach(e=>{s[e]===1&&(s[e]=2,c[e]=t,u.push(e))})}let f=w(e,e=>c[e])||0,p=t?20:n;return e.forEach(e=>{let t=f?c[e]/f:1,n=m(p+Math.max(1,Math.round(r*t)),0,100);n!==i[e]&&(i[e]=n,l.push(e))}),l}function yt(e){let t=y(`heightmapBrushRadius`).valueAsNumber,[n,r]=d(e,this),i=Grid.findCell(n,r),a=Se(t/2,(e,n)=>{let r=Grid.findAll(e,n,t),a=r,o=y(`cellTypeFilter`).value;o===`land`?a=r.filter(e=>grid.cells.h[e]>=20):o===`water`&&(a=r.filter(e=>grid.cells.h[e]<20)),a?.length&&bt(a,i)});a.moveTo(n,r),e.on(`drag`,e=>{let[n,r]=d(e,this);_e(n,r,t),a.moveTo(n,r)}),e.on(`end`,K)}function bt(e,t){let n=y(`heightmapBrushPower`).valueAsNumber,i=o(n,1),a=y(`cellTypeFilter`).value===`land`,s=y(`cellTypeFilter`).value===`water`,c=e=>m(e,a?20:0,s?19:100),l=grid.cells.h,u=document.querySelector(`#brushesButtons > button.pressed`).id;u===`brushRaise`?e.forEach(e=>{l[e]=!s&&l[e]<20?20:c(l[e]+n)}):u===`brushElevate`?e.forEach((t,n)=>{l[t]=c(l[t]+i(n/Math.max(e.length-1,1)))}):u===`brushLower`?e.forEach(e=>{l[e]=c(l[e]-n)}):u===`brushDepress`?e.forEach((t,n)=>{l[t]=c(l[t]-i(n/Math.max(e.length-1,1)))}):u===`brushAlign`?e.forEach(e=>{l[e]=c(l[t])}):u===`brushSmooth`?e.forEach(e=>{l[e]=r(((ae(grid.cells.c[e].filter(e=>a?l[e]>=20:s?l[e]<20:!0).map(e=>l[e]))??0)+l[e]*(10-n)+.6)/(11-n),1)}):u===`brushDisrupt`&&e.forEach(e=>{l[e]=l[e]<15?l[e]:c(l[e]+n/1.6-Math.random()*n)}),at(e)}function xt(){let e=y(`cellTypeFilter`);e.value===`land`&&y(`heightmapEditMode`).innerHTML===`keep`&&(E(`You cannot change the coastline in 'Keep' edit mode`,!1,`error`),e.value=`all`),V.cellType=e.value,D.set(B,`filters`,V)}function St(e){let t=y(`cellTypeFilter`).value===`land`,n=y(`cellTypeFilter`).value===`water`;grid.cells.h=grid.cells.h.map(r=>{if(t&&(r<20||r+e<20)||n&&r>=20)return r;let i=c(r+e);return n?Math.min(i,19):i}),K(),y(`rescaler`).value=`0`}function Ct(){let e=`${y(`rescaleLower`).value}-${y(`rescaleHigher`).value}`,t=y(`conditionSign`).value,n=y(`rescaleModifier`).valueAsNumber;if(Number.isNaN(n)){E(`Operand should be a number`,!1,`error`);return}if((t===`add`||t===`subtract`)&&!Number.isInteger(n)){E(`Operand should be an integer`,!1,`error`);return}HeightmapGenerator.setGraph(grid),t===`multiply`?HeightmapGenerator.modify(e,0,n,0):t===`divide`?HeightmapGenerator.modify(e,0,1/n,0):t===`add`?HeightmapGenerator.modify(e,n,1,0):t===`subtract`?HeightmapGenerator.modify(e,-1*n,1,0):t===`exponent`&&HeightmapGenerator.modify(e,0,1,n),grid.cells.h=HeightmapGenerator.getHeights(),K()}function wt(){HeightmapGenerator.setGraph(grid),HeightmapGenerator.smooth(4,1.5),grid.cells.h=HeightmapGenerator.getHeights(),K()}function Tt(){grid.cells.h=grid.cells.h.map(e=>e<15?e:c(e+2.5-Math.random()*4)),K()}function Et(){let e=y(`cellTypeFilter`).value;if(e===`land`){E(`Not allowed when 'only land cells' filter is set`,!1,`error`);return}if(e===`water`){E(`Not allowed when 'only water cells' filter is set`,!1,`error`);return}if(!grid.cells.h.some(e=>e)){E(`Heightmap is already cleared, please do not click twice if not required`,!1,`error`);return}grid.cells.h=new Uint8Array(grid.cells.i.length),v(`#viewbox`).select(`#heights`).selectAll(`*`).remove(),Y()}function Dt(){document.getElementById(`templateEditor`)||(Ge(),$(`#templateEditor`).dialog({title:`Template Editor`,minHeight:`auto`,width:`fit-content`,resizable:!1,position:{my:`right top`,at:`right-10 top+10`,of:`svg`},close:Ot}))}function Ot(){$(`#templateEditor`).dialog(`destroy`),y(`templateEditor`).remove()}function kt(e){let t=e.target;if(t.tagName!==`BUTTON`)return;let n=t.dataset.type;y(`templateBody`).dataset.changed=`1`,At(n)}function At(e,t,n,r,i){let a=y(`templateBody`);a.insertAdjacentHTML(`beforeend`,jt(e,t,n,r,i));let o=a.querySelector(`div:last-child > span > .templateDist`);if(o&&o.addEventListener(`change`,Mt),n&&o&&o.tagName===`SELECT`){for(let e of Array.from(o.options))e.value===n&&(o.value=n);if(o.value!==n){let e=document.createElement(`option`);e.value=e.innerHTML=n,o.add(e),o.value=n}}}function jt(e,t,n,r,i){let a=`<div data-type="${e}"><div class="icon-check" data-tip="Click to skip the step"></div><div style="width:4em">${e}</div><i class="icon-trash-empty pointer" data-tip="Click to remove the step"></i><i class="icon-resize-vertical" data-tip="Drag to reorder"></i>`,o=`<span>y:
      <input class="templateY" data-tip="Placement range percentage along Y axis (minY-maxY)" value=${i||`20-80`} />
    </span>`,s=`<span>x:
      <input class="templateX" data-tip="Placement range percentage along X axis (minX-maxX)" value=${r||`15-85`} />
    </span>`,c=`<span>h:
      <input class="templateHeight" data-tip="Blob maximum height, use hyphen to get a random number in range" value=${n||`40-50`} />
    </span>`,l=`<span>n:
      <input class="templateCount" data-tip="Blobs to add, use hyphen to get a random number in range" value=${t||`1-2`} />
    </span>`;return e===`Hill`||e===`Pit`||e===`Range`||e===`Trough`?`${a}${o}${s}${c}${l}</div>`:e===`Strait`?`${a}
      <span>d:
        <select class="templateDist" data-tip="Strait direction">
          <option value="vertical" selected>vertical</option>
          <option value="horizontal">horizontal</option>
        </select>
      </span>
      <span>w:
        <input class="templateCount" data-tip="Strait width, use hyphen to get a random number in range" value=${t||`2-7`} />
      </span>
    </div>`:e===`Invert`?`${a}
      <span>by:
        <select class="templateDist" data-tip="Mirror heightmap along axis" style="width: 7.8em">
          <option value="x" selected>x</option>
          <option value="y">y</option>
          <option value="xy">both</option>
        </select>
      </span>
      <span>n:
        <input class="templateCount" data-tip="Probability of inversion, range 0-1" value=${t||`0.5`} />
      </span>
    </div>`:e===`Mask`?`${a}
      <span>f:
        <input class="templateCount"
          data-tip="Set masking fraction. 1 - full insulation (prevent land on map edges), 2 - half-insulation, etc. Negative number to inverse the effect"
          type="number" min=-10 max=10 value=${t||1} />
      </span>
    </div>`:e===`Add`?`${a}
      <span>to:
        <select class="templateDist" data-tip="Change only land or all cells">
          <option value="all" selected>all cells</option>
          <option value="land">land only</option>
          <option value="interval">interval</option>
        </select>
      </span>
      <span>v:
        <input class="templateCount" data-tip="Add value to height of all cells (negative values are allowed)"
        type="number" value=${t||-10} min=-100 max=100 step=1 />
      </span>
    </div>`:e===`Multiply`?`${a}
      <span>to:
        <select class="templateDist" data-tip="Change only land or all cells">
          <option value="all" selected>all cells</option>
          <option value="land">land only</option>
          <option value="interval">interval</option>
        </select>
      </span>
      <span>v:
        <input class="templateCount" data-tip="Multiply all cells Height by the value" type="number"
          value=${t||1.1} min=0 max=10 step=.1 />
      </span>
    </div>`:e===`Smooth`?`${a}
      <span>f:
        <input class="templateCount" data-tip="Set smooth fraction. 1 - full smooth, 2 - half-smooth, etc."
          type="number" min=1 max=10 step=1 value=${t||2} />
      </span>
    </div>`:``}function Mt(e){let t=e.target;t.value===`interval`&&prompt(`Set a height interval. Avoid space, use hyphen as a separator`,{default:`17-20`},e=>{let n=document.createElement(`option`);n.value=n.innerHTML=String(e),t.add(n),t.value=String(e)})}function Nt(e){let t=y(`templateBody`),n=t.querySelectorAll(`div`).length,r=+t.getAttribute(`data-changed`),i=e.target.value;if(!n||!r){Pt(i);return}alertMessage.innerHTML=`Are you sure you want to select a different template? All changes will be lost.`,$(`#alert`).dialog({resizable:!1,title:`Change Template`,buttons:{Change:function(){Pt(i),$(this).dialog(`close`)},Cancel:function(){$(this).dialog(`close`)}}})}function Pt(e){let t=y(`templateBody`);t.setAttribute(`data-changed`,`0`),t.innerHTML=``;let n=me[e]?.template;if(!n)return;let r=n.split(`
`);if(!r.length){E(`Heightmap template: no steps defined`,!1,`error`);return}for(let e of r){let t=e.trim().split(` `);At(t[0],t[1],t[2],t[3],t[4])}}function Ft(){let e=y(`templateBody`).querySelectorAll(`#templateBody > div`);if(!e.length)return;let t=y(`templateSeed`).value;Math.random=aleaPRNG(t||i()),grid.cells.h=new Uint8Array(grid.points.length),HeightmapGenerator.setGraph(grid),ct();for(let t of e){if(t.style.opacity===`0.5`)continue;let e=t.querySelector(`.templateCount`)?.value||``,n=t.querySelector(`.templateHeight`)?.value||``,r=t.querySelector(`.templateDist`)?.value||``,i=t.querySelector(`.templateX`)?.value||``,a=t.querySelector(`.templateY`)?.value||``,o=t.dataset.type;o===`Hill`?HeightmapGenerator.addHill(e,n,i,a):o===`Pit`?HeightmapGenerator.addPit(e,n,i,a):o===`Range`?HeightmapGenerator.addRange(e,n,i,a):o===`Trough`?HeightmapGenerator.addTrough(e,n,i,a):o===`Strait`?HeightmapGenerator.addStrait(e,r):o===`Mask`?HeightmapGenerator.mask(+e):o===`Invert`?HeightmapGenerator.invert(+e,r):o===`Add`?HeightmapGenerator.modify(r,+e,1):o===`Multiply`?HeightmapGenerator.modify(r,0,+e):o===`Smooth`&&HeightmapGenerator.smooth(+e),grid.cells.h=HeightmapGenerator.getHeights(),Y(`noStat`)}grid.cells.h=HeightmapGenerator.getHeights(),ot(),q(),st()}function It(){let e=y(`templateBody`);e.dataset.changed=`0`;let t=e.querySelectorAll(`#templateBody > div`);if(!t.length)return;let n=``;for(let e of Array.from(t)){if(e.style.opacity===`0.5`)continue;let t=e.getAttribute(`data-type`),r=e.querySelector(`.templateCount`)?.value||`0`,i=e.querySelector(`.templateHeight`)?.value||e.querySelector(`.templateDist`)?.value||`0`,a=e.querySelector(`.templateX`)?.value||`0`,o=e.querySelector(`.templateY`)?.value||`0`;n+=`${t} ${r} ${i} ${a} ${o}\r\n`}let r=`template_${Date.now()}.txt`;p(n,r)}function Lt(){H??=s(`.txt`),H.onchange=()=>h(H,Rt),H.click()}function Rt(e){let t=e.split(`\r
`);if(!t.length){E(`Cannot parse the template, please check the file`,!1,`error`);return}y(`templateBody`).innerHTML=``;for(let e of t){let t=e.split(` `);if(t.length!==5){ERROR&&console.error(`Cannot parse step, wrong arguments count`,e);continue}At(t[0],t[1],t[2],t[3],t[4])}}function zt(){U??=s(`image/*`),U.onchange=()=>Ht.call(U),U.click()}function Bt(){if(document.getElementById(`imageConverter`))return;zt(),k(`#imageConverter`),Ke(),$(`#imageConverter`).dialog({title:`Image Converter`,maxHeight:le.height*.8,minHeight:`auto`,width:`20em`,position:{my:`right top`,at:`right-10 top+10`,of:`svg`},beforeClose:Zt});let e=document.createElement(`canvas`);e.id=`canvas`,e.width=options.map.graph.width,e.height=options.map.graph.height,document.body.insertBefore(e,y(`optionsContainer`)),Jt(0),de(),E(`Image Converter is opened. Upload image and assign height value for each color`,!1,`warn`),grid.cells.h=new Uint8Array(grid.cells.i.length),v(`#viewbox`).select(`#heights`).selectAll(`*`).remove(),Y()}function Vt(){let e=+this.getAttribute(`data-color`);y(`colorsSelectValue`).innerHTML=String(e),y(`colorsSelectFriendly`).innerHTML=Qe(e);let t=y(`imageConverterPalette`).querySelector(`.hoveredColor`);t&&(t.className=``),this.className=`hoveredColor`}function Ht(){let e=this.files[0];this.value=``;let t=new FileReader,n=new Image;n.id=`imageToConvert`,n.style.display=`none`,document.body.appendChild(n),n.onload=()=>{y(`canvas`).getContext(`2d`).drawImage(n,0,0,options.map.graph.width,options.map.graph.height),Z(+y(`convertColors`).value),resetZoom()},t.onloadend=()=>{n.src=t.result},t.readAsDataURL(e)}function Z(e){let t=y(`canvas`),n=document.createElement(`canvas`);n.width=grid.cellsX,n.height=grid.cellsY,n.getContext(`2d`).drawImage(t,0,0,grid.cellsX,grid.cellsY);let r=new RgbQuant({colors:e});r.sample(n);let i=r.reduce(n),a=r.palette(!0);v(`#viewbox`).select(`#heights`).selectAll(`*`).remove(),v(`#imageConverter`).selectAll(`div.color-div`).remove(),y(`colorsSelect`).style.display=`block`,y(`colorsUnassigned`).style.display=`block`,y(`colorsAssigned`).style.display=`none`,n.remove(),v(`#viewbox`).select(`#heights`).selectAll(`polygon`).data(Array.from(grid.cells.i)).join(`polygon`).attr(`points`,e=>String(Grid.getPolygon(e))).attr(`id`,e=>`cell${e}`).attr(`fill`,e=>`rgb(${i[e*4]}, ${i[e*4+1]}, ${i[e*4+2]})`).on(`click`,Ut);let o=a.map(e=>`rgb(${e[0]}, ${e[1]}, ${e[2]})`);v(`#colorsUnassignedContainer`).selectAll(`div`).data(o).enter().append(`div`).attr(`data-color`,e=>e).style(`background-color`,e=>e).attr(`class`,`color-div`).on(`click`,Wt),y(`colorsUnassignedNumber`).innerHTML=String(o.length)}function Ut(){let e=this.getAttribute(`fill`);y(`imageConverter`).querySelector(`div[data-color="${e}"]`)?.click()}function Wt(){v(`#viewbox`).select(`#heights`).selectAll(`.selectedCell`).attr(`class`,null);let e=this.classList.contains(`selectedColor`),t=y(`imageConverter`).querySelector(`div.selectedColor`);t&&t.classList.remove(`selectedColor`);let n=y(`imageConverterPalette`).querySelector(`div.hoveredColor`);if(n&&n.classList.remove(`hoveredColor`),y(`colorsSelectValue`).innerHTML=y(`colorsSelectFriendly`).innerHTML=`0`,e)return;if(this.classList.add(`selectedColor`),this.dataset.height){let e=+this.dataset.height;y(`imageConverterPalette`).querySelector(`div[data-color="${e}"]`)?.classList.add(`hoveredColor`),y(`colorsSelectValue`).innerHTML=String(e),y(`colorsSelectFriendly`).innerHTML=Qe(e)}let r=this.getAttribute(`data-color`);v(`#viewbox`).select(`#heights`).selectAll(`polygon.selectedCell`).classed(`selectedCell`,!1),v(`#viewbox`).select(`#heights`).selectAll(`polygon[fill='${r}']`).classed(`selectedCell`,!0)}function Gt(){let e=+this.dataset.color,t=z(1-(e<20?e-5:e)/100),n=y(`imageConverter`).querySelector(`div.selectedColor`);n.style.backgroundColor=t,n.setAttribute(`data-color`,t),n.setAttribute(`data-height`,String(e)),v(`#viewbox`).select(`#heights`).selectAll(`.selectedCell`).each(function(){this.setAttribute(`fill`,t),this.setAttribute(`data-height`,String(e))}),n.parentNode.id===`colorsUnassignedContainer`&&(y(`colorsAssignedContainer`).appendChild(n),y(`colorsAssigned`).style.display=`block`,y(`colorsUnassignedNumber`).innerHTML=String(y(`colorsUnassignedContainer`).childElementCount-2),y(`colorsAssignedNumber`).innerHTML=String(y(`colorsAssignedContainer`).childElementCount-2))}function Kt(e){let t=y(`colorsUnassignedContainer`),n=t.querySelectorAll(`div`);if(!n.length&&(Z(+y(`convertColors`).value),n=t.querySelectorAll(`div`),!n.length)){E(`No unassigned colors. Please load an image and click the button again`,!1,`error`);return}let r=e=>{let t=x(e).h;return t>300&&(t-=360),t>170?Math.abs(t-250)/3|0:Math.abs(t-250+20)/3|0},i=e=>{let t=Ae(e).l;return t<13?t/13*20|0:t|0},a=ee(101).map(e=>it(e)),o=a.map(e=>x(e).h|0),s=e=>{let t=a.indexOf(e);if(t!==-1)return t;let n=x(e).h,r=o.reduce((e,t)=>Math.abs(t-n)<Math.abs(e-n)?t:e);return o.indexOf(r)},c=[],l=y(`colorsAssignedContainer`);n.forEach(t=>{let n=t.dataset.color,a=e===`hue`?r(n):e===`lum`?i(n):s(n),o=z(1-(a<20?(a-5)/100:a/100));if(v(`#viewbox`).select(`#heights`).selectAll(`polygon[fill='${n}']`).attr(`fill`,o).attr(`data-height`,a),c[a]){t.remove();return}t.style.backgroundColor=t.dataset.color=o,t.dataset.height=String(a),l.appendChild(t),c[a]=!0}),Array.from(l.children).sort((e,t)=>e.dataset.height-+t.dataset.height).forEach(e=>{l.appendChild(e)}),y(`colorsAssigned`).style.display=`block`,y(`colorsUnassigned`).style.display=`none`,y(`colorsAssignedNumber`).innerHTML=String(l.childElementCount-2)}function qt(){prompt(`Please set maximum number of colors. <br>An actual number is usually lower and depends on color scheme`,{default:+y(`convertColors`).value,step:1,min:3,max:255},e=>{y(`convertColors`).value=String(e),Z(+e)})}function Jt(e){y(`convertOverlay`).value=y(`convertOverlayNumber`).value=String(e),y(`canvas`).style.opacity=String(e)}function Yt(){if(y(`colorsAssignedContainer`).childElementCount<3){E(`Please assign colors to heights first`,!1,`error`);return}v(`#viewbox`).select(`#heights`).selectAll(`polygon`).each(function(){let e=+(this.dataset.height??`0`)||0,t=+this.id.slice(4);grid.cells.h[t]=e}),v(`#viewbox`).select(`#heights`).selectAll(`polygon`).remove(),K(),Q()}function Xt(){Q(),v(`#viewbox`).select(`#heights`).selectAll(`polygon`).remove(),X(edits.n-1)}function Q(){document.getElementById(`canvas`)?.remove(),document.getElementById(`imageToConvert`)?.remove(),v(`#imageConverter`).selectAll(`div.color-div`).remove(),y(`colorsAssigned`).style.display=`none`,y(`colorsUnassigned`).style.display=`none`,y(`colorsSelectValue`).innerHTML=y(`colorsSelectFriendly`).innerHTML=`0`,v(`#viewbox`).style(`cursor`,`default`).on(`.drag`,null),E(`Heightmap edit mode is active. Click on "Exit Customization" to finalize the heightmap`,!0),$(`#imageConverter`).dialog(`destroy`),y(`imageConverter`).remove(),lt()}function Zt(e){e.preventDefault(),e.stopPropagation(),alertMessage.innerHTML=`Are you sure you want to close the Image Converter? Click "Cancel" to keep editing. Click "Complete" to apply
  the conversion and close the tool. Click "Close" to discard the conversion and restore the previous heightmap.`,$(`#alert`).dialog({resizable:!1,title:`Close Image Converter`,buttons:{Cancel:function(){$(this).dialog(`close`)},Complete:function(){$(this).dialog(`close`),Yt()},Close:function(){$(this).dialog(`close`),Q(),v(`#viewbox`).select(`#heights`).selectAll(`polygon`).remove(),X(edits.n-1)}}})}function Qt(){let e=document.getElementById(`preview`);if(e){e.remove();return}let t=document.createElement(`canvas`);t.id=`preview`,t.width=grid.cellsX,t.height=grid.cellsY,document.body.insertBefore(t,y(`optionsContainer`)),t.addEventListener(`mouseover`,()=>E(`Heightmap preview. Click to download a screen-sized image`)),t.addEventListener(`click`,en),$t()}function $t(){let e=document.getElementById(`preview`).getContext(`2d`),t=e.createImageData(grid.cellsX,grid.cellsY);grid.cells.h.forEach((e,n)=>{let r=(e<20?Math.max(e/1.5,0):e)/100*255,i=n*4;t.data[i]=r,t.data[i+1]=r,t.data[i+2]=r,t.data[i+3]=255}),e.putImageData(t,0,0)}function en(){let e=document.getElementById(`preview`).toDataURL(`image/png`),t=new Image;t.src=e,t.onload=()=>{let e=document.createElement(`canvas`),n=e.getContext(`2d`);e.width=options.map.graph.width,e.height=options.map.graph.height,document.body.insertBefore(e,y(`optionsContainer`)),n.drawImage(t,0,0,options.map.graph.width,options.map.graph.height);let r=e.toDataURL(`image/png`),i=document.createElement(`a`);i.download=`${te(`Heightmap`)}.png`,i.href=r,i.click(),e.remove()}}var tn={open:We,redrawDrainage:W};export{tn as HeightmapEditor};