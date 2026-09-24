import{Bn as e,Et as t,F as n,M as r,On as i,P as a,R as o,Wt as s,Yt as c,_ as l,a as u,dt as d,hn as f,j as p,k as m,nn as h,nt as g,o as _,vt as v,z as y}from"./utils-Cob8vHf9.js";import{J as b,K as x,Z as S,i as C,q as w,r as T,t as E}from"./layers-Bh4OWBXX.js";import{t as ee}from"./sin-DXK16t1M.js";import{i as D,n as te}from"./highlight-Qtqc1_QO.js";import{r as ne,t as re}from"./stratify-CGdiYggi.js";import{n as O,t as k}from"./constant-CUk6ox2a.js";import{i as A,t as ie}from"./tooltips-BTSHGd98.js";import{t as j}from"./state-B2hBYDzv.js";import{t as M}from"./controllers-DnVd8NhQ.js";import{t as N}from"./emblems-generator-C2sA4EpN.js";import{H as ae,V as oe,ct as P,d as se,dt as F,lt as I,st as L,u as ce}from"./index-DsIn6sTp.js";import{t as le}from"./highlighting-BxkDyRR_.js";import{a as ue,i as de,n as fe,r as pe}from"./table-B6G2rlSI.js";import{t as me}from"./annex-mode-DUkjuVOT.js";function he(e){e.x0=Math.round(e.x0),e.y0=Math.round(e.y0),e.x1=Math.round(e.x1),e.y1=Math.round(e.y1)}function ge(e,t,n,r,i){for(var a=e.children,o,s=-1,c=a.length,l=e.value&&(r-t)/e.value;++s<c;)o=a[s],o.y0=n,o.y1=i,o.x0=t,o.x1=t+=o.value*l}function _e(e,t,n,r,i){for(var a=e.children,o,s=-1,c=a.length,l=e.value&&(i-n)/e.value;++s<c;)o=a[s],o.x0=t,o.x1=r,o.y0=n,o.y1=n+=o.value*l}var ve=(1+Math.sqrt(5))/2;function ye(e,t,n,r,i,a){for(var o=[],s=t.children,c,l,u=0,d=0,f=s.length,p,m,h=t.value,g,_,v,y,b,x,S;u<f;){p=i-n,m=a-r;do g=s[d++].value;while(!g&&d<f);for(_=v=g,x=Math.max(m/p,p/m)/(h*e),S=g*g*x,b=Math.max(v/S,S/_);d<f;++d){if(g+=l=s[d].value,l<_&&(_=l),l>v&&(v=l),S=g*g*x,y=Math.max(v/S,S/_),y>b){g-=l;break}b=y}o.push(c={value:g,dice:p<m,children:s.slice(u,d)}),c.dice?ge(c,n,r,i,h?r+=m*g/h:a):_e(c,n,r,h?n+=p*g/h:i,a),h-=g,u=d}return o}var be=(function e(t){function n(e,n,r,i,a){ye(t,e,n,r,i,a)}return n.ratio=function(t){return e((t=+t)>1?t:1)},n})(ve);function xe(){var e=be,t=!1,n=1,r=1,i=[0],a=k,o=k,s=k,c=k,l=k;function u(e){return e.x0=e.y0=0,e.x1=n,e.y1=r,e.eachBefore(d),i=[0],t&&e.eachBefore(he),e}function d(t){var n=i[t.depth],r=t.x0+n,u=t.y0+n,d=t.x1-n,f=t.y1-n;d<r&&(r=d=(r+d)/2),f<u&&(u=f=(u+f)/2),t.x0=r,t.y0=u,t.x1=d,t.y1=f,t.children&&(n=i[t.depth+1]=a(t)/2,r+=l(t)-n,u+=o(t)-n,d-=s(t)-n,f-=c(t)-n,d<r&&(r=d=(r+d)/2),f<u&&(u=f=(u+f)/2),e(t,r,u,d,f))}return u.round=function(e){return arguments.length?(t=!!e,u):t},u.size=function(e){return arguments.length?(n=+e[0],r=+e[1],u):[n,r]},u.tile=function(t){return arguments.length?(e=ne(t),u):e},u.padding=function(e){return arguments.length?u.paddingInner(e).paddingOuter(e):u.paddingInner()},u.paddingInner=function(e){return arguments.length?(a=typeof e==`function`?e:O(+e),u):a},u.paddingOuter=function(e){return arguments.length?u.paddingTop(e).paddingRight(e).paddingBottom(e).paddingLeft(e):u.paddingTop()},u.paddingTop=function(e){return arguments.length?(o=typeof e==`function`?e:O(+e),u):o},u.paddingRight=function(e){return arguments.length?(s=typeof e==`function`?e:O(+e),u):s},u.paddingBottom=function(e){return arguments.length?(c=typeof e==`function`?e:O(+e),u):c},u.paddingLeft=function(e){return arguments.length?(l=typeof e==`function`?e:O(+e),u):l},u}var R=`provincesEditor`,z={my:`right top`,at:`right-10 top+10`,of:`svg`,collision:`fit`},B,V=e=>u(e.area),H=t=>e(t.rural*options.map.units.population.scale+t.urban*options.map.units.population.scale*options.map.units.population.urbanization.rate),U=[{key:`color`,width:`1.2em`,permanent:!0},{key:`name`,label:`Province`,width:`7em`,permanent:!0,sortBy:e=>e.name||``,sortType:`alpha`},{key:`emblem`,width:`1.4em`},{key:`form`,label:`Form`,width:`7em`,mobileHidden:!0,sortBy:e=>e.formName||``,sortType:`alpha`},{key:`capital`,label:`Capital`,width:`7em`,sortBy:e=>e.burg&&pack.burgs[e.burg]?.name||``,sortType:`alpha`},{key:`state`,label:`State`,width:`7em`,permanent:!0,sortBy:e=>pack.states[e.state]?.name||``,sortType:`alpha`},{key:`burgs`,label:`Burgs`,width:`5em`,mobileHidden:!0,sortBy:e=>e.burgs?.length||0},{key:`area`,label:`Area`,width:`7em`,mobileHidden:!0,defaultSort:`desc`,sortBy:V},{key:`population`,label:`Population`,width:`6em`,sortBy:H},{key:`note`,width:`1.1em`},{key:`independence`,width:`1.1em`},{key:`locate`,width:`1.1em`},{key:`focus`,width:`1.1em`},{key:`lock`,width:`1.1em`},{key:`remove`,width:`1.4em`,permanent:!0}],W=pe({getData:J,onUpdate:we});function G(){customization||(B=j.get(R,`filters`,()=>({stateId:1})),L(`#provincesEditor, .stable`),E.show(`provinces`,`borders`),E.hide(`states`,`cultures`),Se(),K(),$(`#provincesEditor`).dialog({title:`Provinces Editor`,resizable:!1,width:`fit-content`,close:$e,position:z}))}function Se(){I(`provincesEditor`);let e=`<div id="provincesEditor" class="dialog stable editorDialog">
      <div id="provincesBodySection" class="table" data-type="absolute">
        ${de({dialogId:R,columns:U})}
      </div>
      <div id="provincesFooter" class="totalLine">
        <div data-tip="Provinces displayed" style="margin-left: 4px">
          Provinces:&nbsp;<span id="provincesFooterNumber">0</span>
        </div>
        <div data-tip="Total burgs number" style="margin-left: 12px" data-col="burgs">
          Burgs:&nbsp;<span id="provincesFooterBurgs">0</span>
        </div>
        <div data-tip="Average area" style="margin-left: 14px" data-col="area">
          Mean area:&nbsp;<span id="provincesFooterArea">0</span>
        </div>
        <div data-tip="Average population" style="margin-left: 14px" data-col="population">
          Mean population:&nbsp;<span id="provincesFooterPopulation">0</span>
        </div>
      </div>
      <div id="provincesBottom" class="editorToolbar">
        <button id="provincesEditorRefresh" data-tip="Refresh the Editor" class="icon-cw"></button>
        <button id="provincesEditStyle" data-tip="Edit provinces style in Style Editor" class="icon-adjust"></button>
        <button
          id="provincesRecolor"
          data-tip="Recolor listed provinces based on state color"
          class="icon-paint-roller"
        ></button>
        <button
          id="provincesPercentage"
          data-tip="Toggle percentage / absolute values views"
          class="icon-percent"
        ></button>
        <button id="provincesChart" data-tip="Show provinces chart" class="icon-chart-area"></button>
        <button
          id="provincesExport"
          data-tip="Save provinces-related data as a text file (.csv)"
          class="icon-download"
        ></button>
        <button id="provincesManually" data-tip="Manually re-assign provinces" class="icon-brush"></button>
        <button
          id="provincesRelease"
          data-tip="Release all provinces. It will make all provinces with burgs independent"
          class="icon-flag"
        ></button>
        <button
          id="provincesAdd"
          data-tip="Add a new province. Hold Shift to add multiple"
          class="icon-plus"
        ></button>
        <button id="provincesMerge" data-tip="Merge several provinces into one" class="icon-layer-group"></button>
        <button
          id="provincesAnnex"
          data-tip="Annex provinces: click the annexing province, then the provinces of the same state it absorbs. Hold Shift to keep annexing"
          class="icon-crown"
        ></button>
        <button
          id="provincesRemoveAll"
          data-tip="Remove all provinces. States will remain as they are"
          class="icon-trash"
        ></button>
        <span>State: </span>
        <select id="provincesFilterState"></select>
      </div>
    </div>`;p(`dialogs`).insertAdjacentHTML(`beforeend`,e),ce(R,W.reset),fe({dialogId:R,columns:U,onUpdate:()=>F(R,{width:`fit-content`,position:z})}),le(`provincesEditor`,({cellId:e})=>pack.cells.province[e]),p(`provincesEditorRefresh`).addEventListener(`click`,K),p(`provincesEditStyle`).addEventListener(`click`,()=>editStyle(`provs`)),p(`provincesFilterState`).addEventListener(`change`,e=>{B.stateId=+e.target.value,j.set(R,`filters`,B),W.reset()}),p(`provincesPercentage`).addEventListener(`click`,Ue),p(`provincesChart`).addEventListener(`click`,We),p(`provincesExport`).addEventListener(`click`,Ze),p(`provincesRemoveAll`).addEventListener(`click`,Qe),p(`provincesManually`).addEventListener(`click`,Ke),p(`provincesRelease`).addEventListener(`click`,Ge),p(`provincesAdd`).addEventListener(`click`,Je),p(`provincesMerge`).addEventListener(`click`,et),p(`provincesAnnex`).addEventListener(`click`,nt.toggle),p(`provincesRecolor`).addEventListener(`click`,Xe),p(`provincesBodySection`).addEventListener(`click`,e=>{if(customization)return;let t=e.target,n=t.classList,r=t.closest(`.states`);if(!r)return;let i=+r.dataset.id,a=pack.provinces[i].state;t.tagName===`FILL-BOX`?Ee(t):n.contains(`name`)?Pe(i):n.contains(`coaIcon`)?M.EmblemsEditor.open(`province`,`provinceCOA${i}`,pack.provinces[i]):n.contains(`icon-star-empty`)?De(i):n.contains(`icon-flag-empty`)?Oe(i):n.contains(`icon-dot-circled`)?M.BurgsOverview.open({stateId:a}):n.contains(`culturePopulation`)?je(i):n.contains(`icon-target`)?te(f(`#provs`).select(`#province${i}`).node(),8):n.contains(`icon-pin`)?Me(i,n):n.contains(`icon-book`)?M.NotesEditor.open({type:`province`,id:i}):n.contains(`icon-trash-empty`)?Ne(i):(n.contains(`icon-lock`)||n.contains(`icon-lock-open`))&&ot(i,n)}),p(`provincesBodySection`).addEventListener(`change`,e=>{let t=e.target,n=t.classList,r=t.closest(`.states`);if(!r)return;let i=+r.dataset.id;n.contains(`cultureBase`)&&He(i,r,t.value)})}function K(){q(),Ce(),W.reset()}function q(){let{cells:e,provinces:t,burgs:n}=pack;t.forEach(e=>{!e.i||e.removed||(e.area=e.rural=e.urban=0,e.burgs=[],(e.burg&&!n[e.burg]||n[e.burg]?.removed)&&(e.burg=0))});for(let r of e.i){let i=e.province[r];i&&(t[i].area+=e.area[r],t[i].rural+=e.pop[r],e.burg[r]&&(t[i].urban+=n[e.burg[r]].population??0,t[i].burgs.push(e.burg[r])))}t.forEach(e=>{!e.i||e.removed||!e.burg&&e.burgs.length&&(e.burg=e.burgs[0])})}function Ce(){let e=p(`provincesFilterState`);B.stateId!==-1&&!pack.states.some(e=>e.i===B.stateId&&!e.removed)&&(B.stateId=-1),e.options.length=0,e.options.add(new Option(`all`,`-1`,!1,B.stateId===-1)),pack.states.filter(e=>e.i&&!e.removed).sort((e,t)=>e.name>t.name?1:-1).forEach(t=>{e.options.add(new Option(t.name,String(t.i),!1,t.i===B.stateId))}),j.set(R,`filters`,B)}function J(){let e=pack.provinces.filter(e=>e.i&&!e.removed);return se(R,B.stateId===-1?e:e.filter(e=>e.state===B.stateId),U)}function we(t){let n=p(`provincesBodySection`),r=` ${_()}`,i=t.all.reduce((e,t)=>({area:e.area+V(t),population:e.population+H(t),burgs:e.burgs+t.burgs.length}),{area:0,population:0,burgs:0}),a=n.dataset.type===`percentage`,o=t.rows.map(t=>{let n=V(t),o=t.rural*options.map.units.population.scale,s=t.urban*options.map.units.population.scale*options.map.units.population.urbanization.rate,c=H(t),u=`Total population: ${l(c)}; Rural population: ${l(o)}; Urban population: ${l(s)}`,d=pack.states[t.state].name,p=t.burg&&t.burg!==pack.states[t.state].capital,m=f(`#deftemp`).select(`#fog #focusProvince${t.i}`).size();return S.trigger(`provinceCOA${t.i}`,t.coa),`<div class="states" data-id=${t.i}>
      <fill-box data-col="color" fill="${t.color}"></fill-box>
      <input data-col="name" data-tip="Province name. Click to change" class="name pointer" value="${t.name}" readonly />
      <svg data-col="emblem" data-tip="Click to show and edit province emblem" class="coaIcon pointer" viewBox="0 0 200 200"><use href="#provinceCOA${t.i}"></use></svg>
      <input data-col="form" data-tip="Province form name. Click to change" class="name pointer" value="${t.formName}" readonly />
      <div data-col="capital">
        <span data-tip="Province capital. Click to zoom into view" class="icon-star-empty pointer ${t.burg?``:`placeholder`}"></span>
        <select data-tip="Province capital. Click to select from burgs within the state. No capital means the province is governed from the state capital" class="cultureBase ${t.burgs.length?``:`placeholder`}">${t.burgs.length?Te(t.burgs,t.burg):``}</select>
      </div>
      <input data-col="state" data-tip="Province owner" class="provinceOwner" value="${d}" disabled>
      <div data-col="burgs">
        <span data-tip="Click to overview province burgs" class="icon-dot-circled pointer"></span>
        <span data-tip="Burgs count" class="provinceBurgs">${a?`${e(i.burgs?t.burgs.length/i.burgs*100:0)}%`:t.burgs.length}</span>
      </div>
      <div data-col="area">
        <span data-tip="Province area" class="icon-map-o" style="padding-right: 4px"></span>
        <span data-tip="Province area" class="biomeArea">${a?`${e(i.area?n/i.area*100:0)}%`:l(n)+r}</span>
      </div>
      <div data-col="population">
        <span data-tip="${u}" class="icon-male"></span>
        <span data-tip="${u}" class="culturePopulation">${a?`${e(i.population?c/i.population*100:0)}%`:l(c)}</span>
      </div>
      ${ae.getIcon(`this province`)}
      <span data-col="independence" data-tip="Declare province independence (turn non-capital province with burgs into a new state)" class="icon-flag-empty ${p?``:`placeholder`}"></span>
      <span data-col="locate" data-tip="Locate the province" class="icon-target"></span>
      <span data-col="focus" data-tip="Toggle province focus" class="icon-pin ${m?``:` inactive`}"></span>
      <span data-col="lock" data-tip="Lock the province" class="icon-lock${t.lock?``:`-open`}"></span>
      <span data-col="remove" data-tip="Remove the province" class="icon-trash-empty"></span>
    </div>`}).join(``);n.querySelectorAll(`:scope > .states`).forEach(e=>{e.remove()}),n.insertAdjacentHTML(`beforeend`,o),p(`provincesFooterNumber`).innerHTML=String(t.all.length),p(`provincesFooterBurgs`).innerHTML=String(i.burgs),p(`provincesFooterArea`).innerHTML=t.all.length?l(i.area/t.all.length)+r:`0${r}`,p(`provincesFooterPopulation`).innerHTML=t.all.length?l(i.population/t.all.length):`0`,p(`provincesFooterArea`).dataset.area=String(i.area),p(`provincesFooterPopulation`).dataset.population=String(i.population),ue(p(`provincesFooter`),t,W.goto),n.querySelectorAll(`div.states`).forEach(e=>{e.addEventListener(`mouseenter`,Y),e.addEventListener(`mouseleave`,X)}),F(R,{width:`fit-content`,position:z})}function Te(e,t){let n=``;return e.forEach(e=>{n+=`<option ${e===t?`selected`:``} value="${e}">${pack.burgs[e].name}</option>`}),n}function Y(e){let t=+e.target.dataset.id,n=p(`provincesBodySection`).querySelector(`div[data-id='${t}']`);if(n&&n.classList.add(`active`),!E.isOn(`provinces`)||customization)return;let r=s().duration(2e3).ease(ee);f(`#provs`).select(`#province${t}`).raise().transition(r).attr(`stroke-width`,2.5).attr(`stroke`,`#d0240f`)}function X(e){let t=e.target?.dataset?.id?+e.target.dataset.id:null;if(t){let e=p(`provincesBodySection`).querySelector(`div[data-id='${t}']`);e&&e.classList.remove(`active`)}if(!E.isOn(`provinces`)||!t){f(`#debug`).selectAll(`.highlight`).remove();return}f(`#provs`).select(`#province${t}`).transition().attr(`stroke-width`,null).attr(`stroke`,null),f(`#debug`).selectAll(`.highlight`).remove()}function Ee(e){let t=e.getAttribute(`fill`),n=+e.closest(`.states`).dataset.id;M.ColorPicker.open(t,t=>{e.fill=t,pack.provinces[n].color=t,E.draw(`provinces`)})}function De(e){let t=pack.provinces[e].burg,{x:n,y:r}=pack.burgs[t];zoomTo(n,r,8,2e3)}function Oe(e){P({title:`Declare independence`,message:`Are you sure you want to declare province independence? <br>It will turn province into a new state`,confirm:`Declare`,onConfirm:()=>{let t=ke(e);if(!t)return;let[n,r]=t;Ae([n],[r])}})}function ke(e){let{states:t,provinces:n,cells:i,burgs:a}=pack,o=n[e],{name:s,burg:c,burgs:l}=o;if(l.some(e=>a[e].capital)){A(`Cannot declare independence of a province having capital burg. Please change capital first`,!1,`error`);return}if(!c){A(`Cannot declare independence of a province without burg`,!1,`error`);return}let u=o.state,f=t.length,p=a[c];p.capital=1,Burgs.changeGroup(p),E.draw(`burgIcons`,`labels`),o.burgs.forEach(e=>{a[e].state=f});let{cell:m,culture:h}=a[c],g=d(),_=o.coa,v=r(`provinceCOA${e}`);v&&(v.id=`stateCOA${f}`),b(`province`,e),i.i.filter(t=>i.province[t]===e).forEach(e=>{i.province[e]=0,i.state[e]=f});let y=t.map(e=>{if(!e.i||e.removed)return`x`;let n=t[u].diplomacy[e.i];return e.i===u?n=`Enemy`:n===`Ally`||n===`Friendly`?n=`Suspicion`:n===`Suspicion`?n=`Neutral`:n===`Enemy`||n===`Rival`?n=`Friendly`:n===`Vassal`?n=`Suspicion`:n===`Suzerain`&&(n=`Enemy`),e.diplomacy.push(n),n});return y.push(`x`),t[0].diplomacy.push([`Independance declaration`,`${s} declared its independance from ${t[u].name}`]),t.push({i:f,name:s,diplomacy:y,provinces:[],color:g,expansionism:.5,capital:c,type:`Generic`,center:m,culture:h,military:[],alert:1,coa:_}),t[u].provinces=t[u].provinces.filter(t=>t!==e),n[e]={i:e,removed:!0},[u,f]}function Ae(e,t){let n=i([...e,...t]);E.hide(`provinces`),E.show(`states`,`borders`),States.getPoles(),States.findNeighbors(),States.collectStatistics(),States.defineStateForms(t),E.draw(`labels`),w(n.map(e=>[`state`,e])),E.hide(`provinces`),E.show(`states`,`borders`),C(),L(),M.StatesEditor.open()}function je(t){let n=pack.provinces[t],r=pack.cells.i.filter(e=>pack.cells.province[e]===t);if(!r.length){A(`Province does not have any cells, cannot change population`,!1,`error`);return}let i=e(n.rural*options.map.units.population.scale),a=e(n.urban*options.map.units.population.scale*options.map.units.population.urbanization.rate),o=i+a,s=e=>Number(e).toLocaleString();alertMessage.innerHTML=` Rural: <input type="number" min="0" step="1" id="ruralPop" value=${i} style="width:6em" /> Urban:
    <input type="number" min="0" step="1" id="urbanPop" value=${a} style="width:6em" ${n.burgs.length?``:`disabled`} />
    <p>Total population: ${s(o)} ⇒ <span id="totalPop">${s(o)}</span> (<span id="totalPopPerc">100</span>%)</p>`;let c=p(`ruralPop`),l=p(`urbanPop`),u=()=>{let t=c.valueAsNumber+l.valueAsNumber;Number.isNaN(t)||(p(`totalPop`).innerHTML=s(t),p(`totalPopPerc`).innerHTML=String(e(t/o*100)))};c.oninput=()=>u(),l.oninput=()=>u(),$(`#alert`).dialog({resizable:!1,title:`Change province population`,width:`24em`,buttons:{Apply:function(){d(),$(this).dialog(`close`)},Cancel:function(){$(this).dialog(`close`)}},position:{my:`center`,at:`center`,of:`svg`}});function d(){let t=+c.value/i;if(Number.isFinite(t)&&t!==1&&r.forEach(e=>{pack.cells.pop[e]*=t}),!Number.isFinite(t)&&+c.value>0){let t=e(+c.value/options.map.units.population.scale/r.length);r.forEach(e=>{pack.cells.pop[e]=t})}let o=+l.value/a;if(Number.isFinite(o)&&o!==1&&n.burgs.forEach(t=>{pack.burgs[t].population=e((pack.burgs[t].population??0)*o,4)}),!Number.isFinite(o)&&+l.value>0){let t=e(+l.value/options.map.units.population.scale/options.map.units.population.urbanization.rate/n.burgs.length,4);n.burgs.forEach(e=>{pack.burgs[e].population=t})}E.draw(`population`),K()}}function Me(e,t){let n=f(`#provs`).select(`#province${e}`).attr(`d`),r=`focusProvince${e}`;t.contains(`inactive`)?T(r,n):C(r),t.toggle(`inactive`)}function Ne(e){alertMessage.innerHTML=`Are you sure you want to remove the province? <br />This action cannot be reverted`,$(`#alert`).dialog({resizable:!1,title:`Remove province`,buttons:{Remove:function(){pack.cells.province.forEach((t,n)=>{t===e&&(pack.cells.province[n]=0)});let t=pack.provinces[e].state,n=pack.states[t];n.provinces.includes(e)&&n.provinces.splice(n.provinces.indexOf(e),1),C(`focusProvince${e}`),b(`province`,e),pack.provinces[e]={i:e,removed:!0};let r=f(`#provs`).select(`#provincesBody`);r.select(`#province${e}`).remove(),r.select(`#province-gap${e}`).remove(),E.draw(`borders`),E.draw(`labels`),K(),$(this).dialog(`close`)},Cancel:function(){$(this).dialog(`close`)}}})}function Pe(e){Fe();let t=pack.provinces[e];p(`provinceNameEditor`).dataset.province=String(e),p(`provinceNameEditorShort`).value=t.name,m(p(`provinceNameEditorSelectForm`),t.formName),p(`provinceNameEditorFull`).value=t.fullName;let n=pack.cells.culture[t.center];p(`provinceCultureDisplay`).innerText=pack.cultures[n].name,$(`#provinceNameEditor`).dialog({resizable:!1,title:`Change province name`,buttons:{Apply:function(){Ve(t),$(this).dialog(`close`)},Cancel:function(){$(this).dialog(`close`)}},position:{my:`center`,at:`center`,of:`svg`},close:Ie})}function Fe(){I(`provinceNameEditor`),p(`dialogs`).insertAdjacentHTML(`beforeend`,`<div id="provinceNameEditor" class="dialog" data-province="0">
      <div>
        <div data-tip="Province short name" class="label">Short name:</div>
        <input
          id="provinceNameEditorShort"
          data-tip="Type to change the short name"
          autocorrect="off"
          spellcheck="false"
          style="width: 11em"
        />
        <span id="provinceNameEditorShortSpeak" data-tip="Speak the name. You can change voice and language in options" class="speaker">🔊</span>
        <span
          id="provinceNameEditorShortCulture"
          data-tip="Generate culture-specific name for the province"
          class="icon-book pointer"
        ></span>
        <span id="provinceNameEditorShortRandom" data-tip="Generate random name" class="icon-globe pointer"></span>
      </div>
      <div data-tip="Select form name">
        <div data-tip="Province form name" class="label">Form name:</div>
        <select id="provinceNameEditorSelectForm" style="display: inline-block; width: 11em; height: 1.645em">
          <option value="">blank</option>
          <option value="Area">Area</option>
          <option value="Autonomy">Autonomy</option>
          <option value="Barony">Barony</option>
          <option value="Canton">Canton</option>
          <option value="Captaincy">Captaincy</option>
          <option value="Chiefdom">Chiefdom</option>
          <option value="Clan">Clan</option>
          <option value="Colony">Colony</option>
          <option value="Council">Council</option>
          <option value="County">County</option>
          <option value="Deanery">Deanery</option>
          <option value="Department">Department</option>
          <option value="Dependency">Dependency</option>
          <option value="Diaconate">Diaconate</option>
          <option value="District">District</option>
          <option value="Earldom">Earldom</option>
          <option value="Governorate">Governorate</option>
          <option value="Island">Island</option>
          <option value="Islands">Islands</option>
          <option value="Land">Land</option>
          <option value="Landgrave">Landgrave</option>
          <option value="Mandate">Mandate</option>
          <option value="Margrave">Margrave</option>
          <option value="Municipality">Municipality</option>
          <option value="Occupation zone">Occupation zone</option>
          <option value="Parish">Parish</option>
          <option value="Prefecture">Prefecture</option>
          <option value="Province">Province</option>
          <option value="Region">Region</option>
          <option value="Republic">Republic</option>
          <option value="Reservation">Reservation</option>
          <option value="Seneschalty">Seneschalty</option>
          <option value="Shire">Shire</option>
          <option value="State">State</option>
          <option value="Territory">Territory</option>
          <option value="Tribe">Tribe</option>
        </select>
        <input
          id="provinceNameEditorCustomForm"
          placeholder="type form name"
          data-tip="Create custom province form name"
          style="display: none; width: 11em"
        />
        <span
          id="provinceNameEditorAddForm"
          data-tip="Click to add custom province form name to the list"
          class="icon-plus pointer"
        ></span>
      </div>
      <div>
        <div data-tip="Province full name" class="label">Full name:</div>
        <input
          id="provinceNameEditorFull"
          data-tip="Type to change the full name"
          autocorrect="off"
          spellcheck="false"
          style="width: 11em"
        />
        <span id="provinceNameEditorFullSpeak" data-tip="Speak the name. You can change voice and language in options" class="speaker">🔊</span>
        <span
          id="provinceNameEditorFullRegenerate"
          data-tip="Click to re-generate full name"
          class="icon-arrows-cw pointer"
        ></span>
      </div>
      <div
        id="provinceCultureName"
        data-tip="Dominant culture in the province. This defines culture-based naming. Can be changed via the Cultures Editor"
        style="margin-top: 0.2em"
      >
        Dominant culture:&nbsp;<span id="provinceCultureDisplay"></span>
      </div>
    </div>`),p(`provinceNameEditorShortCulture`).addEventListener(`click`,Le),p(`provinceNameEditorShortRandom`).addEventListener(`click`,Re),p(`provinceNameEditorShortSpeak`).addEventListener(`click`,()=>g(p(`provinceNameEditorShort`).value)),p(`provinceNameEditorAddForm`).addEventListener(`click`,ze),p(`provinceNameEditorFullRegenerate`).addEventListener(`click`,Be),p(`provinceNameEditorFullSpeak`).addEventListener(`click`,()=>g(p(`provinceNameEditorFull`).value))}function Ie(){$(`#provinceNameEditor`).dialog(`destroy`),p(`provinceNameEditor`).remove()}function Le(){let e=+p(`provinceNameEditor`).dataset.province,t=pack.cells.culture[pack.provinces[e].center],n=Names.getState(Names.getCultureShort(t),t);p(`provinceNameEditorShort`).value=n}function Re(){let e=t(Names.nameBases.length-1),n=Names.getState(Names.getBase(e),void 0,e);p(`provinceNameEditorShort`).value=n}function ze(){let e=p(`provinceNameEditorCustomForm`),t=p(`provinceNameEditorSelectForm`),n=e.value,r=e.style.display===`inline-block`;e.style.display=r?`none`:`inline-block`,t.style.display=r?`inline-block`:`none`,r&&m(t,n)}function Be(){let e=p(`provinceNameEditorShort`).value,t=p(`provinceNameEditorSelectForm`).value,n=()=>t?!e&&t?`The ${t}`:`${e} ${t}`:e;p(`provinceNameEditorFull`).value=n()}function Ve(e){e.name=p(`provinceNameEditorShort`).value,e.formName=p(`provinceNameEditorSelectForm`).value,e.fullName=p(`provinceNameEditorFull`).value,E.draw(`provinces`),E.draw(`labels`),K()}function He(e,t,n){t.dataset.capital=pack.burgs[+n].name,pack.provinces[e].center=pack.burgs[+n].cell,pack.provinces[e].burg=+n}function Ue(){let e=p(`provincesBodySection`);e.dataset.type=e.dataset.type===`absolute`?`percentage`:`absolute`,W.refresh()}function We(){q();let t=e=>!e.i||e.removed||e.color[0]!==`#`?`#666`:String(h(e.color).darker()),n=pack.states.map(e=>({id:e.i,state:e.i?0:null,color:t(e)})),r=pack.provinces.filter(e=>e.i&&!e.removed).map(e=>({id:e.i+n.length-1,i:e.i,state:e.state,color:e.color,name:e.name,fullName:e.fullName,area:e.area,urban:e.urban,rural:e.rural})),i=[...n,...r],a=re().parentId(e=>e.state)(i).sum(e=>e.area),o=+p(`uiSize`).value,s=300+300*o,c=90+90*o,d={top:10,right:10,bottom:0,left:10},m=s-d.left-d.right,g=c-d.top-d.bottom,v=xe().size([m,g]).padding(2);alertMessage.innerHTML=`<select id="provincesTreeType" style="display:block; margin-left:13px; font-size:11px">
    <option value="area" selected>Area</option>
    <option value="population">Total population</option>
    <option value="rural">Rural population</option>
    <option value="urban">Urban population</option>
  </select>`,alertMessage.innerHTML+=`<div id='provinceInfo' class='chartInfo'>&#8205;</div>`;let y=f(`#alertMessage`).insert(`svg`,`#provinceInfo`).attr(`id`,`provincesTree`).attr(`width`,s).attr(`height`,c).attr(`font-size`,`10px`).append(`g`).attr(`transform`,`translate(10, 0)`);p(`provincesTreeType`).addEventListener(`change`,w),v(a);let b=y.selectAll(`g`).data(a.leaves()).enter().append(`g`).attr(`data-id`,e=>e.data.i).on(`mouseenter`,(e,t)=>x(e,t)).on(`mouseleave`,e=>S(e));function x(t,n){f(t.currentTarget).select(`rect`).classed(`selected`,!0);let r=n.data.fullName,i=pack.states[n.data.state].fullName,a=`${u(n.data.area)} ${_()}`,o=e(n.data.rural*options.map.units.population.scale),s=e(n.data.urban*options.map.units.population.scale*options.map.units.population.urbanization.rate),c=p(`provincesTreeType`).value,d=c===`area`?`Area: ${a}`:c===`rural`?`Rural population: ${l(o)}`:c===`urban`?`Urban population: ${l(s)}`:`Population: ${l(o+s)}`;p(`provinceInfo`).innerHTML=`${r}. ${i}. ${d}`,Y(t)}function S(e){X(e),document.getElementById(`provinceInfo`)&&(p(`provinceInfo`).innerHTML=`&#8205;`,f(e.currentTarget).select(`rect`).classed(`selected`,!1))}b.append(`rect`).attr(`stroke`,e=>e.parent.data.color).attr(`stroke-width`,1).attr(`fill`,e=>e.data.color).attr(`x`,e=>e.x0).attr(`y`,e=>e.y0).attr(`width`,e=>e.x1-e.x0).attr(`height`,e=>e.y1-e.y0),b.append(`text`).attr(`text-rendering`,`optimizeSpeed`).attr(`dx`,`.2em`).attr(`dy`,`1em`).attr(`x`,e=>e.x0).attr(`y`,e=>e.y0);function C(){b.select(`text`).each(function(e){this.innerHTML=e.data.name;let t=this.getBBox();t.y+t.height>e.y1+1&&(this.innerHTML=``);for(let n=0;n<15&&t.width>0&&t.x+t.width>e.x1;n++){if(this.innerHTML.length<3){this.innerHTML=``;break}this.innerHTML=`${this.innerHTML.slice(0,-2)}…`,t=this.getBBox()}})}function w(){let e=this.value===`area`?e=>e.area:this.value===`rural`?e=>e.rural:this.value===`urban`?e=>e.urban:e=>e.rural+e.urban;a.sum(e),b.data(v(a).leaves()),b.select(`rect`).transition().duration(1500).attr(`x`,e=>e.x0).attr(`y`,e=>e.y0).attr(`width`,e=>e.x1-e.x0).attr(`height`,e=>e.y1-e.y0),b.select(`text`).transition().duration(1500).attr(`x`,e=>e.x0).attr(`y`,e=>e.y0),setTimeout(C,2e3)}$(`#alert`).dialog({title:`Provinces chart`,width:`fit-content`,position:{my:`left bottom`,at:`left+10 bottom-10`,of:`svg`},buttons:{},close:()=>{alertMessage.innerHTML=``}}),C()}function Ge(){P({title:`Release provinces`,message:`Are you sure you want to release all provinces?
        </br>It will turn all separable provinces into independent states.
        </br>Capital province and provinces without any burgs will state as they are`,confirm:`Release`,onConfirm:()=>{let e=[],t=[];J().forEach(n=>{if(!n.burg||n.burg===pack.states[n.state].capital||n.burgs.some(e=>pack.burgs[e].capital))return;let r=ke(n.i);r&&(e.push(r[0]),t.push(r[1]))}),Ae(i(e),t)}})}function Ke(){E.show(`provinces`,`borders`),M.PaintEditor.open({title:`Paint Provinces`,parentDialogId:R,onClose:G,items:J().map(e=>({id:e.i,name:e.name,color:e.color||`#ffffff`})),getValue:e=>pack.cells.province[e],filterCell:(e,t,r)=>!n(e,pack)||!pack.cells.state[e]||pack.cells.state[e]!==pack.provinces[r].state?!1:!t||e!==pack.provinces[t].center?!0:(A(`Province center cannot be assigned to a different region. Please remove the province first`,!1,`error`),!1),dontOverrideControl:!0,onApply:qe})}function qe(e){for(let[t,n]of e)pack.cells.province[t]=n;Provinces.getPoles(),E.draw(`borders`,`provinces`),E.draw(`labels`),document.getElementById(R)&&K()}function Je(){if(this.classList.contains(`pressed`)){Z();return}customization=12,this.classList.add(`pressed`),A(`Click on the map to place a new province center`,!0),f(`#viewbox`).style(`cursor`,`crosshair`).on(`click`,Ye),p(`provincesBodySection`).querySelectorAll(`div > input, select, span, svg`).forEach(e=>{e.style.pointerEvents=`none`})}function Ye(e){let{cells:t,provinces:n}=pack,r=a(e,this),i=Pack.findCell(r[0],r[1]);if(t.h[i]<20){A(`You cannot place province into the water. Please click on a land cell`,!1,`error`);return}let o=t.province[i];if(o&&n[o].center===i){A(`The cell is already a center of a different province. Select other cell`,!1,`error`);return}let s=t.state[i];if(!s){A(`You cannot create a province in neutral lands. Please assign this land to a state first`,!1,`error`);return}e.shiftKey===!1&&Z();let l=n.length;pack.states[s].provinces.push(l);let u=t.burg[i],f=t.culture[i],m=u?pack.burgs[u].name:Names.getState(Names.getCultureShort(f),f),g=o?n[o].formName:`Province`,_=`${m} ${g}`,y=pack.states[s].color,b=d(),S=y[0]===`#`?h(c(y,b)(.2)).hex():b,C=u?.8:.4,w=u?pack.burgs[u].coa:pack.states[s].coa,T=u?pack.burgs[u].port:void 0,ee=Burgs.getType(i,T),D=N.generate(w,C,+v(.1),ee);D.shield=N.getShield(f,s),n.push({i:l,state:s,center:i,burg:u,name:m,formName:g,fullName:_,color:S,coa:D}),x(`province`,l),t.province[i]=l,t.c[i].forEach(e=>{t.h[e]<20||t.state[e]!==s||n.find(t=>!t.removed&&t.center===e)||(t.province[e]=l)}),E.draw(`borders`,`provinces`),E.draw(`labels`),q(),B.stateId=s,j.set(R,`filters`,B),p(`provincesFilterState`).value=String(B.stateId),W.reset()}function Z(){customization=0,oe(),ie(),p(`provincesBodySection`).querySelectorAll(`div > input, select, span, svg`).forEach(e=>{e.style.removeProperty(`pointer-events`)});let e=p(`provincesAdd`);e.classList.contains(`pressed`)&&e.classList.remove(`pressed`)}function Xe(){let e=B.stateId;pack.provinces.forEach(t=>{if(!t||t.removed||e!==-1&&t.state!==e)return;let n=pack.states[t.state].color,r=d();t.color=n[0]===`#`?h(c(n,r)(.2)).hex():r}),E.draw(`provinces`),W.refresh()}function Ze(){let e=`Id,Province,Full Name,Form,State,Color,Capital,Area ${options.map.units.area.unit===`square`?`${options.map.units.distance.unit}2`:options.map.units.area.unit},Total Population,Rural Population,Urban Population,Burgs\n`;for(let t of J()){let n=t.burg?pack.burgs[t.burg].name:``;e+=`${t.i},${t.name},${t.fullName},${t.formName},${pack.states[t.state].name},${t.color},${n},${V(t)},${H(t)},${Math.round(t.rural*options.map.units.population.scale)},${Math.round(t.urban*options.map.units.population.scale*options.map.units.population.urbanization.rate)},${t.burgs.length}\n`}let t=`${y(`Provinces`)}.csv`;o(e,t)}function Qe(){alertMessage.innerHTML=`Are you sure you want to remove all provinces? <br />This action cannot be reverted`,$(`#alert`).dialog({resizable:!1,title:`Remove all provinces`,buttons:{Remove:function(){$(this).dialog(`close`),pack.provinces.forEach(e=>{e.i&&b(`province`,e.i)}),pack.provinces=[0],pack.cells.province=new Uint16Array(pack.cells.i.length),pack.states.forEach(e=>{e.provinces=[]}),C(),E.draw(`borders`),f(`#provs`).select(`#provincesBody`).remove(),E.hide(`provinces`),E.draw(`labels`),W.reset()},Cancel:function(){$(this).dialog(`close`)}}})}function $e(){customization===12&&Z(),nt.exit(),M.ColorPicker.close();let e=W.view();e.rows=[],e.all=[],$(`#provincesEditor`).dialog(`destroy`),p(`provincesEditor`).remove()}function et(){let e=B.stateId;if(e===-1){alertMessage.innerHTML=`Please select a specific state from the filter to merge provinces within that state.`,$(`#alert`).dialog({title:`Merge Provinces`,buttons:{OK:function(){$(this).dialog(`close`)}}});return}let t=pack.provinces.filter(t=>t.i&&!t.removed&&t.state===e);if(t.length<2){alertMessage.innerHTML=`Not enough provinces in the selected state to merge.`,$(`#alert`).dialog({title:`Merge Provinces`,buttons:{OK:function(){$(this).dialog(`close`)}}});return}let n=t.map(e=>`
    <div data-id="${e.i}" data-tip="${e.fullName||e.name}" style="cursor:default">
      <input type="radio" name="rulingProvince" value="${e.i}" />
      <input id="selectProvince${e.i}" class="checkbox" type="checkbox" name="provincesToMerge" value="${e.i}" />
      <label for="selectProvince${e.i}" class="checkbox-label"><fill-box fill="${e.color}" disabled></fill-box>${Q(e.i)}${e.name}</label>
    </div>
  `).join(``);alertMessage.innerHTML=`
    <form id='mergeProvincesForm' style="overflow: hidden; display: flex; flex-direction: column; gap: 1em;">
      <p style="margin:0">
        Check the <b>checkbox</b> next to each province you want to merge.
        Use the <b>radio button</b> to pick the <em>primary province</em> that will absorb all others.
        Hover over a row to highlight the province on the map.
      </p>
      <main style='display: grid; grid-template-columns: 1fr 1fr; gap: .3em;'>
        ${n}
      </main>
    </form>
  `,p(`mergeProvincesForm`).querySelectorAll(`div[data-id]`).forEach(e=>{e.addEventListener(`mouseenter`,rt),e.addEventListener(`mouseleave`,X)}),$(`#alert`).dialog({width:600,title:`Merge provinces`,close:X,buttons:{Merge:function(){let e=new FormData(p(`mergeProvincesForm`)),t=Number(e.get(`rulingProvince`));if(!t){A(`Please select a province to merge into`,!1,`error`);return}let n=e.getAll(`provincesToMerge`).map(Number).filter(e=>e!==t);if(!n.length){A(`Please select several provinces to merge`,!1,`error`);return}tt(n,t,()=>$(this).dialog(`close`))},Cancel:function(){$(this).dialog(`close`)}}})}var Q=e=>`<svg class="coaIcon" viewBox="0 0 200 200"><use href="#provinceCOA${e}"></use></svg>`;function tt(e,t,n){P({title:`Merge provinces`,message:`
      <p>The following provinces will be <strong>removed</strong>: ${e.map(e=>`${Q(e)}${pack.provinces[e].name}`).join(`, `)}.</p>
      <p>Removed provinces data (burgs and cells) will be assigned to ${Q(t)}${pack.provinces[t].name}.</p>
      <p>Are you sure you want to merge provinces? This action cannot be reverted.</p>`,confirm:`Merge`,onConfirm:()=>{at(e,t),n?.()}})}var nt=me({buttonId:`provincesAnnex`,bodySectionId:`provincesBodySection`,noun:`province`,ownerOf:e=>pack.cells.province[e],colorOf:e=>pack.provinces[e].color,nameOf:e=>pack.provinces[e].name,rejectReason:(e,t)=>pack.provinces[t].state===pack.provinces[e].state?void 0:`${pack.provinces[t].name} belongs to another state. Merge states first, or pick a province of ${pack.states[pack.provinces[e].state].name}`,commit:(e,t)=>tt(t,e)});function rt(e){if(!E.isOn(`provinces`))return;let t=+e.currentTarget.dataset.id;if(!t)return;let n=f(`#provs`).select(`#province${t}`).attr(`d`);n&&(X(e),D(n))}function it(e){C(`focusProvince${e}`),b(`province`,e)}function at(e,t){let n=pack.provinces[t],r=new Map;e.forEach(e=>{if(e===t)return;let i=pack.provinces[e];i.burgs.forEach(e=>{pack.burgs[e].province=t,n.burgs.includes(e)||n.burgs.push(e)}),!n.burg&&i.burg&&(n.burg=i.burg),r.set(e,t),it(e),pack.provinces[e]={i:e,removed:!0}}),pack.cells.province.forEach((e,t)=>{let n=r.get(e);n!==void 0&&(pack.cells.province[t]=n)});let i=pack.states[n.state];i.provinces=i.provinces.filter(e=>!pack.provinces[e].removed),q(),Provinces.getPoles(),E.draw(`provinces`,`borders`),E.draw(`labels`),C(),f(`#debug`).selectAll(`.highlight`).remove(),K()}function ot(e,t){let n=pack.provinces[e];n.lock=!n.lock,t.toggle(`icon-lock-open`),t.toggle(`icon-lock`)}var st={open:G,showChart:We};export{st as ProvincesEditor};