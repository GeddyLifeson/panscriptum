import{Bn as e,F as t,R as n,Wt as r,_ as i,a,dt as o,et as s,hn as c,j as l,o as u,z as d}from"./utils-Cob8vHf9.js";import{I as f,P as p,R as m,t as h}from"./layers-Bh4OWBXX.js";import{t as g}from"./sin-DXK16t1M.js";import{i as _}from"./tooltips-BTSHGd98.js";import{t as v}from"./controllers-DnVd8NhQ.js";import{At as y,H as b,d as x,dt as S,gt as ee,lt as te,st as C,u as w}from"./index-DsIn6sTp.js";import{t as T}from"./highlighting-BxkDyRR_.js";import{a as E,i as D,n as O,r as k}from"./table-B6G2rlSI.js";var A=`biomesEditor`,j=`Biomes`,M={my:`right top`,at:`right-10 top+10`,of:`svg`,collision:`fit`},N=[],P=[{key:`name`,label:`Biome`,width:`15em`,permanent:!0,sortBy:e=>e.name,sortType:`alpha`},{key:`habitability`,label:`Habitability`,width:`6.5em`,sortBy:e=>e.habitability},{key:`cells`,label:`Cells`,width:`5em`,sortBy:e=>N[e.i]?.cells??0,defaultSort:`desc`},{key:`area`,label:`Area`,width:`7em`,mobileHidden:!0,sortBy:e=>N[e.i]?.area??0},{key:`population`,label:`Population`,width:`6.2em`,mobileHidden:!0,sortBy:e=>{let t=N[e.i];return t?t.rural+t.urban:0}},{key:`note`,width:`1.1em`},{key:`wiki`,width:`1.1em`},{key:`remove`,width:`1.4em`,permanent:!0}],F=k({getData:()=>x(A,pack.biomes.filter(e=>e.i&&!e.removed),P),onUpdate:e=>V(e,N)});function I(){customization||(C(`#${A}, .stable`),h.show(`biomes`),h.hide(`states`,`cultures`),h.hide(`religions`,`provinces`),L(),N=B(),F.reset(),$(`#${A}`).dialog({title:`Biomes Editor`,resizable:!1,close:le,position:M}))}function L(){te(A);let e=`<div id="${A}" class="dialog stable editorDialog">
      ${D({dialogId:A,columns:P})}
      <div id="biomesBody" class="table" data-type="absolute"></div>
      <div id="biomesFooter" class="totalLine">
        <div data-tip="Number of land biomes" style="margin-left: 12px">
          Biomes:&nbsp;<span id="biomesFooterBiomes">0</span>
        </div>
        <div data-col="cells" data-tip="Total land cells number" style="margin-left: 12px">
          Cells:&nbsp;<span id="biomesFooterCells">0</span>
        </div>
        <div data-col="area" data-tip="Total land area" style="margin-left: 12px">
          Land Area:&nbsp;<span id="biomesFooterArea">0</span>
        </div>
        <div data-col="population" data-tip="Total population" style="margin-left: 12px">
          Population:&nbsp;<span id="biomesFooterPopulation">0</span>
        </div>
      </div>
      <div id="biomesBottom">
        <button id="biomesEditorRefresh" data-tip="Refresh the Editor" class="icon-cw"></button>
        <button id="biomesEditStyle" data-tip="Edit biomes style in Style Editor" class="icon-adjust"></button>
        <button id="biomesLegend" data-tip="Toggle Legend box" class="icon-list-bullet"></button>
        <button
          id="biomesPercentage"
          data-tip="Toggle percentage / absolute values views"
          class="icon-percent"
        ></button>
        <button
          id="biomesManually"
          data-tip="Manually re-assign biomes to not follow the default moisture/temperature pattern"
          class="icon-brush"
        ></button>
        <button id="biomesAdd" data-tip="Add a custom biome" class="icon-plus"></button>
        <button
          id="biomesRestore"
          data-tip="Restore the defaults and re-define biomes based on current moisture and temperature"
          class="icon-history"
        ></button>
        <button
          id="biomesExport"
          data-tip="Save biomes-related data as a text file (.csv)"
          class="icon-download"
        ></button>
      </div>
    </div>`;l(`dialogs`).insertAdjacentHTML(`beforeend`,e),O({dialogId:A,columns:P,onUpdate:()=>S(A,{width:`fit-content`,position:M})}),l(`biomesEditorRefresh`).addEventListener(`click`,R),l(`biomesEditStyle`).addEventListener(`click`,()=>editStyle(`biomes`)),l(`biomesLegend`).addEventListener(`click`,Y),l(`biomesPercentage`).addEventListener(`click`,X),l(`biomesManually`).addEventListener(`click`,oe),l(`biomesRestore`).addEventListener(`click`,ce),l(`biomesAdd`).addEventListener(`click`,ie),l(`biomesExport`).addEventListener(`click`,Z),w(A,F.reset),T(A,({cellId:e})=>e&&pack.cells.biome[e]),l(`biomesBody`).addEventListener(`click`,e=>{let t=e.target,n=t.classList;t.tagName===`FILL-BOX`?W(t):n.contains(`icon-book`)?q(t):n.contains(`icon-info-circled`)?J(t):n.contains(`icon-trash-empty`)&&ae(t)}),l(`biomesBody`).addEventListener(`change`,e=>{let t=e.target,n=t.classList;n.contains(`biomeName`)?G(t):n.contains(`biomeHabitability`)&&K(t)})}function R(){N=B(),F.refresh()}function z(e=pack){let{cells:t}=e,n=e.biomes.map(()=>({cells:0,area:0,rural:0,urban:0}));for(let r of t.i){if(t.h[r]<20)continue;let i=n[t.biome[r]];i.cells++,i.area+=t.area[r],i.rural+=t.pop[r];let a=t.burg[r]?e.burgs[t.burg[r]]:null;a&&(i.urban+=a.population??0)}return n}function B(){return z(pack)}function V(t,n){let r=` ${u()}`,o=``,s=0,c=0;for(let s of t.rows){let{i:t,name:c,color:l,habitability:u}=s,{cells:d,area:f,rural:p,urban:m}=n[t],h=a(f),g=p*options.map.units.population.scale,_=m*options.map.units.population.scale*options.map.units.population.urbanization.rate,v=e(g+_),y=`Total population: ${i(v)}; Rural population: ${i(g)}; Urban population: ${i(_)}`;o+=`
      <div
        class="states biomes"
        data-id="${t}"
        data-name="${c}"
        data-habitability="${u}"
        data-cells=${d}
        data-area=${h}
        data-population=${v}
        data-color=${l}
      >
        <div data-col="name">
          <fill-box fill="${l}"></fill-box>
          <input data-tip="Biome name. Click and type to change" class="biomeName" value="${c}" autocorrect="off" spellcheck="false" />
        </div>
        <div data-col="habitability" class="hide">
          <span data-tip="Biome habitability percent">%</span>
          <input data-tip="Biome habitability percent. Click and set new value to change" type="number" min="0" max="9999" class="biomeHabitability" value=${u} />
        </div>
        <div data-col="cells" class="hide"><span data-tip="Cells count" class="icon-check-empty"></span><span data-tip="Cells count" class="biomeCells">${d}</span></div>
        <div data-col="area" class="hide"><span data-tip="Biome area" class="icon-map-o" style="padding-right: 2px"></span><span data-tip="Biome area" class="biomeArea">${i(h)+r}</span></div>
        <div data-col="population" class="hide"><span data-tip="${y}" class="icon-male"></span><span data-tip="${y}" class="biomePopulation">${i(v)}</span></div>
        ${b.getIcon(`this biome`)}
        <span data-col="wiki" data-tip="Open Wikipedia article about the biome" class="icon-info-circled pointer"></span>
        <span data-col="remove" ${t>12&&!d?`data-tip="Remove the custom biome" class="icon-trash-empty"`:``}></span>
      </div>
    `}let d=l(`biomesBody`);d.innerHTML=o;for(let r of t.all){let t=n[r.i];s+=a(t.area),c+=e(t.rural*options.map.units.population.scale+t.urban*options.map.units.population.scale*options.map.units.population.urbanization.rate)}let f=a(y(pack.cells.area));l(`biomesFooterBiomes`).innerHTML=String(t.all.length),l(`biomesFooterCells`).innerHTML=String(pack.cells.h.filter(e=>e>=20).length);let p=l(`biomesFooterArea`);p.innerHTML=i(s)+r,l(`biomesFooterPopulation`).innerHTML=i(c),p.dataset.area=String(s),p.dataset.mapArea=String(f),l(`biomesFooterPopulation`).dataset.population=String(c),E(l(`biomesFooter`),t,F.goto),d.querySelectorAll(`div.biomes`).forEach(e=>{e.addEventListener(`mouseenter`,H)}),d.querySelectorAll(`div.biomes`).forEach(e=>{e.addEventListener(`mouseleave`,U)}),d.dataset.type===`percentage`&&(d.dataset.type=`absolute`,X()),S(A,{width:`fit-content`,position:M})}function H(e){if(customization===6)return;let t=+e.target.dataset.id,n=r().duration(2e3).ease(g);c(`#biomes > #biome${t}`).raise().transition(n).attr(`stroke-width`,2).attr(`stroke`,`#cd4c11`)}function U(e){if(customization===6)return;let t=+e.target.dataset.id,n=pack.biomes[t].color;c(`#biomes > #biome${t}`).transition().attr(`stroke-width`,.7).attr(`stroke`,n)}function W(e){let t=e.getAttribute(`fill`),n=+e.closest(`.biomes`).dataset.id;v.ColorPicker.open(t,t=>{e.fill=t,pack.biomes[n].color=t,h.draw(`biomes`)})}function G(e){let t=e.closest(`.biomes`),n=+t.dataset.id;t.dataset.name=e.value,pack.biomes[n].name=e.value}function K(e){let t=e.closest(`.biomes`),n=+t.dataset.id;if(Number.isNaN(+e.value)||+e.value<0||+e.value>9999){e.value=String(pack.biomes[n].habitability),_(`Please provide a valid number in range 0-9999`,!1,`error`);return}pack.biomes[n].habitability=+e.value,t.dataset.habitability=e.value,Q(),R()}function q(e){let t=+(e.closest(`.biomes`)?.dataset.id||0);v.NotesEditor.open({type:`biome`,id:t})}function J(e){let t=e.closest(`.biomes`)?.dataset.name;if(t===`Custom`||!t){_(`Please fill in the biome name`,!1,`error`);return}let n={"Hot desert":`Desert_climate#Hot_desert_climates`,"Cold desert":`Desert_climate#Cold_desert_climates`,Savanna:`Tropical_and_subtropical_grasslands,_savannas,_and_shrublands`,Grassland:`Temperate_grasslands,_savannas,_and_shrublands`,"Tropical seasonal forest":`Seasonal_tropical_forest`,"Temperate deciduous forest":`Temperate_deciduous_forest`,"Tropical rainforest":`Tropical_rainforest`,"Temperate rainforest":`Temperate_rainforest`,Taiga:`Taiga`,Tundra:`Tundra`,Glacier:`Glacier`,Wetland:`Wetland`},r=`https://en.wikipedia.org/w/index.php?search=${t}`;s(n[t]?`https://en.wikipedia.org/wiki/`+n[t]:r)}function Y(){if(m(j)){p(j);return}let e=B(),t=pack.biomes.filter(({i:t})=>e[t].cells).sort((t,n)=>e[n.i].area-e[t.i].area).map(({i:e,color:t,name:n})=>[e,t,n]);if(!t.length)return void _(`No biomes to show`,!1,`error`);f(j,t)}function X(){let t=l(`biomesBody`);if(t.dataset.type===`absolute`){t.dataset.type=`percentage`;let n=+l(`biomesFooterCells`).innerHTML,r=l(`biomesFooterArea`),i=+r.dataset.area,a=+r.dataset.mapArea,o=+l(`biomesFooterPopulation`).dataset.population;t.querySelectorAll(`:scope > div`).forEach(t=>{t.querySelector(`.biomeCells`).innerHTML=`${e(+t.dataset.cells/n*100)}%`,t.querySelector(`.biomeArea`).innerHTML=`${e(+t.dataset.area/i*100)}%`,t.querySelector(`.biomePopulation`).innerHTML=`${e(+t.dataset.population/o*100)}%`}),r.innerHTML=`${e(i/a*100)}%`}else t.dataset.type=`absolute`,F.refresh()}function ne(e,t){let n=e.length;if(n>254)return null;let r={i:n,name:`Custom`,color:t,habitability:50,iconsDensity:0,icons:[],cost:50};return e.push(r),r}function re(e,t,n){let r=e[n];if(n<=12||!r||r.removed)return!1;for(let e=0;e<t.length;e++)if(t[e]===n)return!1;return r.removed=!0,!0}function ie(){if(!ne(pack.biomes,o())){_(`Maximum number of biomes reached (255), data cleansing is required`,!1,`error`);return}N=B(),F.refresh()}function ae(e){let t=+e.closest(`.biomes`).dataset.id;re(pack.biomes,pack.cells.biome,t)&&(N=B(),F.refresh())}function Z(){let t=`Id,Biome,Color,Habitability,Cells,Area ${options.map.units.area.unit===`square`?`${options.map.units.distance.unit}2`:options.map.units.area.unit},Population\n`,r=B();for(let n of pack.biomes){if(!n.i||n.removed)continue;let{cells:i,area:o,rural:s,urban:c}=r[n.i],l=e(s*options.map.units.population.scale+c*options.map.units.population.scale*options.map.units.population.urbanization.rate);t+=`${n.i},${n.name},${n.color},${n.habitability}%,${i},${a(o)},${l}\n`}let i=`${d(`Biomes`)}.csv`;n(t,i)}function oe(){h.show(`biomes`),v.PaintEditor.open({title:`Paint Biomes`,parentDialogId:A,onClose:I,items:pack.biomes.filter(e=>e.i&&!e.removed).map(e=>({id:e.i,name:e.name,color:e.color})),getValue:e=>pack.cells.biome[e],filterCell:e=>t(e,pack),onApply:se})}function se(e){for(let[t,n]of e)pack.cells.biome[t]=n;e.size&&(h.draw(`biomes`),document.getElementById(A)&&R())}function ce(){pack.biomes=Biomes.getDefault(),Biomes.define(),h.draw(`biomes`),Q(),R()}function le(){$(`#biomesEditor`).dialog(`destroy`),l(`biomesEditor`).remove()}function Q(){ee.regenerate(),h.draw(`population`,`goods`)}var ue={open:I,exportCsv:Z};export{ue as BiomesEditor};