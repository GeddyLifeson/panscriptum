import{Bn as e,Et as t,M as n,P as r,Z as i,hn as a,j as o,nt as s}from"./utils-Cob8vHf9.js";import{C as c,S as l,t as u}from"./layers-Bh4OWBXX.js";import{t as d}from"./drag-hfHVCxdY.js";import{i as f,t as p}from"./tooltips-BTSHGd98.js";import{t as m}from"./controllers-DnVd8NhQ.js";import{H as h,lt as g,st as _}from"./index-DsIn6sTp.js";var v,y=!1;function b(e){if(customization||n(`riverEditor`)&&e===v.attr(`id`))return;_(`.stable`),u.show(`rivers`),y=!u.isOn(`cells`),u.show(`cells`),c(Number(e.slice(5))),v=a(`#${e}`).on(`click`,M),f(`Drag control points to change the river course. Click on point to remove it. Click on river to add additional control point. For major changes please create a new river instead`,!0),a(`#debug`).append(`g`).attr(`id`,`controlCells`),a(`#debug`).append(`g`).attr(`id`,`controlPoints`),x(),T();let{cells:t,points:r}=w();O(Rivers.getRiverPoints(t,r??null)),k(t),$(`#riverEditor`).dialog({title:`Edit River`,resizable:!1,position:{my:`left top`,at:`left+10 top+10`,of:`#map`},close:W})}function x(){g(`riverEditor`);let e=`<div id="riverEditor" class="dialog">
    <div id="riverBody" style="padding-bottom: 0.3em">
      <div>
        <div class="label" style="width: 4.8em">Name:</div>
        <span id="riverNameCulture" data-tip="Generate culture-specific name for the river" class="icon-book pointer"></span>
        <span id="riverNameRandom" data-tip="Generate random name for the river" class="icon-globe pointer"></span>
        <input id="riverName" data-tip="Type to rename the river" autocorrect="off" spellcheck="false" />
        <span id="riverNameSpeak" data-tip="Speak the name. You can change voice and language in options" class="speaker">🔊</span>
      </div>
      <div data-tip="Type to change river type (e.g. fork, creek, river, brook, stream)">
        <div class="label">Type:</div>
        <input id="riverType" autocorrect="off" spellcheck="false" />
      </div>
      <div data-tip="Select parent river">
        <div class="label">Mainstem:</div>
        <select id="riverMainstem"></select>
      </div>
      <div data-tip="River drainage basin (watershed)">
        <div class="label">Basin:</div>
        <input id="riverBasin" disabled />
      </div>
      <div data-tip="River discharge (flux power)">
        <div class="label">Discharge:</div>
        <input id="riverDischarge" disabled />
      </div>
      <div data-tip="River length in selected units">
        <div class="label">Length:</div>
        <input id="riverLength" disabled />
      </div>
      <div data-tip="River mouth width in selected units">
        <div class="label">Mouth width:</div>
        <input id="riverWidth" disabled />
      </div>
      <div data-tip="River source additional width. Default value is 0">
        <div class="label">Source width:</div>
        <input id="riverSourceWidth" type="number" min="0" max="3" step=".01" />
      </div>
      <div data-tip="River width multiplier. Default value is 1">
        <div class="label">Width modifier:</div>
        <input id="riverWidthFactor" type="number" min=".1" max="4" step=".1" />
      </div>
    </div>
    <div id="riverBottom">
      <button id="riverCreateSelectingCells" data-tip="Create a new river selecting river cells" class="icon-map-pin"></button>
      <button id="riverEditStyle" data-tip="Edit style for all rivers in Style Editor" class="icon-brush"></button>
      <button id="riverElevationProfile" data-tip="Show the elevation profile for the river" class="icon-chart-area"></button>
      ${h.getButton(`riverLegend`,`this river`)}
      <button id="riverRemove" data-tip="Remove river" data-shortcut="Delete" class="icon-trash fastDelete"></button>
    </div>
  </div>`;o(`dialogs`).insertAdjacentHTML(`beforeend`,e),o(`riverCreateSelectingCells`).addEventListener(`click`,S),o(`riverEditStyle`).addEventListener(`click`,C),o(`riverElevationProfile`).addEventListener(`click`,V),o(`riverLegend`).addEventListener(`click`,H),o(`riverRemove`).addEventListener(`click`,U),o(`riverName`).addEventListener(`input`,P),o(`riverNameSpeak`).addEventListener(`click`,()=>s(o(`riverName`).value)),o(`riverType`).addEventListener(`input`,F),o(`riverNameCulture`).addEventListener(`click`,I),o(`riverNameRandom`).addEventListener(`click`,L),o(`riverMainstem`).addEventListener(`change`,R),o(`riverSourceWidth`).addEventListener(`input`,z),o(`riverWidthFactor`).addEventListener(`input`,B)}function S(){m.RiverCreator.open()}function C(){editStyle(`rivers`)}function w(){let e=+v.attr(`id`).slice(5);return pack.rivers.find(t=>t.i===e)}function T(){let e=w();o(`riverName`).value=e.name,o(`riverType`).value=e.type;let t=o(`riverMainstem`);t.options.length=0;let n=e.parent||e.i;pack.rivers.slice().sort((e,t)=>e.name>t.name?1:-1).forEach(e=>{let r=new Option(e.name,String(e.i),!1,e.i===n);t.options.add(r)}),o(`riverBasin`).value=pack.rivers.find(t=>t.i===e.basin).name,o(`riverDischarge`).value=`${e.discharge} m³/s`,o(`riverSourceWidth`).value=String(e.sourceWidth),o(`riverWidthFactor`).value=String(e.widthFactor),E(e),D(e)}function E(t){t.length=e(v.node().getTotalLength()/2,2);let n=`${e(t.length*options.map.units.distance.scale)} ${options.map.units.distance.unit}`;o(`riverLength`).value=n}function D(t){let{cells:n,discharge:r,widthFactor:i,sourceWidth:a}=t,s=Rivers.addMeandering(n);t.width=Rivers.getWidth(Rivers.getOffset({flux:r,pointIndex:s.length,widthFactor:i,startingWidth:a}));let c=`${e(t.width*options.map.units.distance.scale,3)} ${options.map.units.distance.unit}`;o(`riverWidth`).value=c}function O(e){a(`#controlPoints`).selectAll(`circle`).data(e).join(`circle`).attr(`cx`,e=>e[0]).attr(`cy`,e=>e[1]).attr(`r`,.6).call(d().on(`start`,A)).on(`click`,N)}function k(e){let t=[...new Set(e)].filter(e=>pack.cells.i[e]);a(`#controlCells`).selectAll(`polygon`).data(t).join(`polygon`).attr(`points`,e=>String(Pack.getPolygon(e)))}function A(t){let{r:n,fl:r}=pack.cells,i=w(),{x:a,y:o}=t,s=Pack.findCell(a,o),c=null;t.on(`drag`,function(t){let{x:n,y:r}=t,a=Pack.findCell(n,r);c=s===a?null:a,this.setAttribute(`cx`,n),this.setAttribute(`cy`,r),this.__data__=[e(n,1),e(r,1)],j(),k(i.cells)}),t.on(`end`,()=>{if(c&&!n[c]){n[s]=0,n[c]=i.i;let e=r[s];r[s]=r[c],r[c]=e,j()}})}function j(){let e=w();e.points=a(`#controlPoints`).selectAll(`*`).data(),e.cells=e.points.map(([e,t])=>Pack.findCell(e,t)),l(e),E(e),u.draw(`labels`),n(`elevationProfile`)&&V()}function M(t){let[n,o]=r(t,this),s=[e(n,1),e(o,1)],c=w();c.points||=a(`#controlPoints`).selectAll(`*`).data();let l=i(c.points,s,2);c.points.splice(l,0,s),O(c.points),j()}function N(){this.remove(),j();let{cells:e}=w();k(e)}function P(){w().name=this.value}function F(){w().type=this.value}function I(){let e=w();e.name=o(`riverName`).value=Rivers.getName(e.mouth)}function L(){let e=w();e&&(e.name=o(`riverName`).value=Names.getBase(t(Names.nameBases.length-1)))}function R(){let e=w();e.parent=+this.value,e.basin=pack.rivers.find(t=>t.i===e.parent).basin,o(`riverBasin`).value=pack.rivers.find(t=>t.i===e.basin).name}function z(){let e=w();e.sourceWidth=+this.value,D(e),j()}function B(){let e=w();e.widthFactor=+this.value,D(e),j()}function V(){let t=a(`#controlPoints`).selectAll(`*`).data().map(([e,t])=>Pack.findCell(e,t)),n=e(w().length*options.map.units.distance.scale);m.ElevationProfile.open(t,n,!0)}function H(){m.NotesEditor.open({type:`river`,id:w().i})}function U(){alertMessage.innerHTML=`Are you sure you want to remove the river and all its tributaries`,$(`#alert`).dialog({resizable:!1,width:`22em`,title:`Remove river and tributaries`,buttons:{Remove:function(){$(this).dialog(`close`);let e=+v.attr(`id`).slice(5);Rivers.remove(e),$(`#riverEditor`).dialog(`close`),u.draw(`rivers`,`labels`)},Cancel:function(){$(this).dialog(`close`)}}})}function W(){a(`#controlPoints`).remove(),a(`#controlCells`).remove(),v.on(`click`,null),c(null),p(),y&&u.hide(`cells`),y=!1,g(`riverEditor`),v=null}var G={open:b};export{G as RiverEditor};