import{Bn as e,Bt as t,I as n,It as r,Lt as i,R as a,Ut as o,_ as s,a as c,bn as l,f as u,gn as d,hn as f,j as p,kn as m,m as h,n as g,o as _,r as v,xn as y,yn as b,z as x}from"./utils-Cob8vHf9.js";import{t as S}from"./mean-4Awewi9R.js";import{n as ee,r as C}from"./axis-I8_pxNLd.js";import{i as w}from"./tooltips-BTSHGd98.js";import{At as T,dt as E,jt as D,lt as O,st as k}from"./index-DsIn6sTp.js";var A=class extends Map{constructor(e,t=P){if(super(),Object.defineProperties(this,{_intern:{value:new Map},_key:{value:t}}),e!=null)for(let[t,n]of e)this.set(t,n)}get(e){return super.get(j(this,e))}has(e){return super.has(j(this,e))}set(e,t){return super.set(M(this,e),t)}delete(e){return super.delete(N(this,e))}};function j({_intern:e,_key:t},n){let r=t(n);return e.has(r)?e.get(r):n}function M({_intern:e,_key:t},n){let r=t(n);return e.has(r)?e.get(r):(e.set(r,n),n)}function N({_intern:e,_key:t},n){let r=t(n);return e.has(r)&&(n=e.get(r),e.delete(r)),n}function P(e){return typeof e==`object`&&e?e.valueOf():e}function F(e,t,...n){return I(e,Array.from,t,n)}function I(e,t,n,r){return(function e(i,a){if(a>=r.length)return n(i);let o=new A,s=r[a++],c=-1;for(let e of i){let t=s(e,++c,i),n=o.get(t);n?n.push(e):o.set(t,[e])}for(let[t,n]of o)o.set(t,e(n,a));return t(o)})(e,0)}function te(e){return f(d(e).call(document.documentElement))}var L=Symbol(`implicit`);function R(){var e=new A,t=[],n=[],r=L;function i(i){let a=e.get(i);if(a===void 0){if(r!==L)return r;e.set(i,a=t.push(i)-1)}return n[a%n.length]}return i.domain=function(n){if(!arguments.length)return t.slice();t=[],e=new A;for(let r of n)e.has(r)||e.set(r,t.push(r)-1);return i},i.range=function(e){return arguments.length?(n=Array.from(e),i):n.slice()},i.unknown=function(e){return arguments.length?(r=e,i):r},i.copy=function(){return R(t,n).unknown(r)},o.apply(i,arguments),i}function ne(){var e=R().unknown(void 0),t=e.domain,n=e.range,r=0,i=1,a,s,c=!1,l=0,u=0,d=.5;delete e.unknown;function f(){var e=t().length,o=i<r,f=o?i:r,p=o?r:i;a=(p-f)/Math.max(1,e-l+u*2),c&&(a=Math.floor(a)),f+=(p-f-a*(e-l))*d,s=a*(1-l),c&&(f=Math.round(f),s=Math.round(s));var m=b(e).map(function(e){return f+a*e});return n(o?m.reverse():m)}return e.domain=function(e){return arguments.length?(t(e),f()):t()},e.range=function(e){return arguments.length?([r,i]=e,r=+r,i=+i,f()):[r,i]},e.rangeRound=function(e){return[r,i]=e,r=+r,i=+i,c=!0,f()},e.bandwidth=function(){return s},e.step=function(){return a},e.round=function(e){return arguments.length?(c=!!e,f()):c},e.padding=function(e){return arguments.length?(l=Math.min(1,u=+e),f()):l},e.paddingInner=function(e){return arguments.length?(l=Math.min(1,e),f()):l},e.paddingOuter=function(e){return arguments.length?(u=+e,f()):u},e.align=function(e){return arguments.length?(d=Math.max(0,Math.min(1,e)),f()):d},e.copy=function(){return ne(t(),[r,i]).round(c).paddingInner(l).paddingOuter(u).align(d)},o.apply(f(),arguments)}function z(e,t){if((o=e.length)>1)for(var n=1,r,i,a=e[t[0]],o,s=a.length;n<o;++n)for(i=a,a=e[t[n]],r=0;r<s;++r)a[r][1]+=a[r][0]=isNaN(i[r][1])?i[r][0]:i[r][1]}function B(e){for(var t=e.length,n=Array(t);--t>=0;)n[t]=t;return n}function V(e,t){return e[t]}function H(e){let t=[];return t.key=e,t}function re(){var e=i([]),t=B,n=z,a=V;function o(i){var o=Array.from(e.apply(this,arguments),H),s,c=o.length,l=-1,u;for(let e of i)for(s=0,++l;s<c;++s)(o[s][l]=[0,+a(e,o[s].key,l,i)]).data=e;for(s=0,u=r(t(o));s<c;++s)o[u[s]].index=s;return n(o,u),o}return o.keys=function(t){return arguments.length?(e=typeof t==`function`?t:i(Array.from(t)),o):e},o.value=function(e){return arguments.length?(a=typeof e==`function`?e:i(+e),o):a},o.order=function(e){return arguments.length?(t=e==null?B:typeof e==`function`?e:i(Array.from(e)),o):t},o.offset=function(e){return arguments.length?(n=e??z,o):n},o}function ie(e,t){if((r=e.length)>0){for(var n,r,i=0,a=e[0].length,o;i<a;++i){for(o=n=0;n<r;++n)o+=e[n][i][1]||0;if(o)for(n=0;n<r;++n)e[n][i][1]/=o}z(e,t)}}function ae(e,t){if((c=e.length)>0)for(var n,r=0,i,a,o,s,c,l=e[t[0]].length;r<l;++r)for(o=s=0,n=0;n<c;++n)(a=(i=e[t[n]][r])[1]-i[0])>0?(i[0]=o,i[1]=o+=a):a<0?(i[1]=s,i[0]=s+=a):(i[0]=0,i[1]=a)}var U={states:{label:`State`,getId:e=>pack.cells.state[e],getName:Z(`states`),getColors:Q(`states`),landOnly:!0},cultures:{label:`Culture`,getId:e=>pack.cells.culture[e],getName:Z(`cultures`),getColors:Q(`cultures`),landOnly:!0},religions:{label:`Religion`,getId:e=>pack.cells.religion[e],getName:Z(`religions`),getColors:Q(`religions`),landOnly:!0},provinces:{label:`Province`,getId:e=>pack.cells.province[e],getName:Z(`provinces`),getColors:Q(`provinces`),landOnly:!0},biomes:{label:`Biome`,getId:e=>pack.cells.biome[e],getName:xe,getColors:Se,landOnly:!1},markets:{label:`Market`,getId:e=>pack.cells.market[e],getName:Ce,getColors:we,landOnly:!1},goods:{label:`Good`,requires:`good`,getId:(e,t)=>t.good,getName:Te,getColors:Ee,landOnly:!1}},W={total_population:{label:`Total population`,quantize:e=>Oe(e)+ke(e),aggregate:t=>e(T(t)),formatTicks:e=>s(e),stringify:e=>e.toLocaleString(),stackable:!0,landOnly:!0},urban_population:{label:`Urban population`,quantize:Oe,aggregate:t=>e(T(t)),formatTicks:e=>s(e),stringify:e=>e.toLocaleString(),stackable:!0,landOnly:!0},rural_population:{label:`Rural population`,quantize:ke,aggregate:t=>e(T(t)),formatTicks:e=>s(e),stringify:e=>e.toLocaleString(),stackable:!0,landOnly:!0},area:{label:`Land area`,quantize:e=>c(pack.cells.area[e]),aggregate:t=>e(T(t)),formatTicks:e=>`${s(e)} ${_()}`,stringify:e=>`${e.toLocaleString()} ${_()}`,stackable:!0,landOnly:!0},cells:{label:`Cells`,hint:`Number of land cells`,quantize:()=>1,aggregate:e=>T(e),formatTicks:e=>e,stringify:e=>e.toLocaleString(),stackable:!0,landOnly:!0},burgs_number:{label:`Burgs`,hint:`Number of burgs`,quantize:e=>+!!pack.cells.burg[e],aggregate:e=>T(e),formatTicks:e=>e,stringify:e=>e.toLocaleString(),stackable:!0,landOnly:!0},average_elevation:{label:`Average elevation`,quantize:e=>pack.cells.h[e],aggregate:e=>S(e),formatTicks:e=>u(e),stringify:e=>u(e),stackable:!1,landOnly:!1},max_elevation:{label:`Maximum mean elevation`,quantize:e=>pack.cells.h[e],aggregate:e=>y(e),formatTicks:e=>u(e),stringify:e=>u(e),stackable:!1,landOnly:!1},min_elevation:{label:`Minimum mean elevation`,quantize:e=>pack.cells.h[e],aggregate:e=>l(e),formatTicks:e=>u(e),stringify:e=>u(e),stackable:!1,landOnly:!1},average_temperature:{label:`Annual mean temperature`,quantize:e=>grid.cells.temp[pack.cells.g[e]],aggregate:e=>S(e),formatTicks:e=>g(e),stringify:e=>g(e),stackable:!1,landOnly:!1},max_temperature:{label:`Annual max temperature`,hint:`Highest mean temperature of the year`,quantize:e=>grid.cells.temp[pack.cells.g[e]],aggregate:e=>y(e),formatTicks:e=>g(e),stringify:e=>g(e),stackable:!1,landOnly:!1},min_temperature:{label:`Annual min temperature`,hint:`Lowest mean temperature of the year`,quantize:e=>grid.cells.temp[pack.cells.g[e]],aggregate:e=>l(e),formatTicks:e=>g(e),stringify:e=>g(e),stackable:!1,landOnly:!1},average_precipitation:{label:`Annual mean precipitation`,quantize:e=>grid.cells.prec[pack.cells.g[e]],aggregate:t=>e(S(t)),formatTicks:t=>h(e(t)),stringify:t=>h(e(t)),stackable:!1,landOnly:!0},max_precipitation:{label:`Annual max precipitation`,hint:`Highest mean precipitation of the year`,quantize:e=>grid.cells.prec[pack.cells.g[e]],aggregate:t=>e(y(t)),formatTicks:t=>h(e(t)),stringify:t=>h(e(t)),stackable:!1,landOnly:!0},min_precipitation:{label:`Annual min precipitation`,hint:`Lowest mean precipitation of the year`,quantize:e=>grid.cells.prec[pack.cells.g[e]],aggregate:t=>e(l(t)),formatTicks:t=>h(e(t)),stringify:t=>h(e(t)),stackable:!1,landOnly:!0},coastal_cells:{label:`Number of coastal cells`,quantize:e=>+(pack.cells.t[e]===1),aggregate:e=>T(e),formatTicks:e=>e,stringify:e=>e.toLocaleString(),stackable:!0,landOnly:!0},river_cells:{label:`Number of river cells`,quantize:e=>+!!pack.cells.r[e],aggregate:e=>T(e),formatTicks:e=>e,stringify:e=>e.toLocaleString(),stackable:!0,landOnly:!0},production_value:{label:`Production value`,hint:`Worth of produced goods`,provides:[`good`],prepare:()=>({biomeProduction:Goods.getBiomesProduction()}),getContributions:(e,{biomeProduction:t})=>{let n=De(e,t),r=[];for(let[e,t]of Object.entries(n)){let n=Goods.get(+e);n&&r.push({good:+e,value:t*n.value})}return r},aggregate:t=>e(T(t)),formatTicks:e=>s(e),stringify:e=>v(e),stackable:!0,landOnly:!0},production_units:{label:`Production volume`,hint:`Units of goods produced`,provides:[`good`],prepare:()=>({biomeProduction:Goods.getBiomesProduction()}),getContributions:(e,{biomeProduction:t})=>{let n=De(e,t),r=[];for(let[e,t]of Object.entries(n))r.push({good:+e,value:t});return r},aggregate:t=>e(T(t)),formatTicks:e=>s(e),stringify:e=>`${e.toLocaleString()} units`,stackable:!0,landOnly:!0},burgs_profit:{label:`Burgs profit`,hint:`Burgs profit from trade and manufacturing`,quantize:e=>{let t=pack.cells.burg[e];return t&&pack.burgs[t].product||0},aggregate:t=>e(T(t)),formatTicks:e=>s(e),stringify:e=>v(e),stackable:!0,landOnly:!0}},oe={stackedBar:{offset:ae},normalizedStackedBar:{offset:ie,formatX:t=>`${e(t*100)}%`}},G=[],K;function se(){ce(),me(),le(),k(`#chartsOverview, .stable`);let e=mapHistory.at(-1)?.created;if(K!==e&&(G=[],K=e),!G.length)ue();else for(let e of G)de(e);$(`#chartsOverview`).dialog({title:`Data Charts`,width:`60vw`,height:`auto`,position:{my:`center`,at:`center`,of:`svg`},close:he})}function ce(){O(`chartsOverview`);let e=Object.entries(U).map(([e,{label:t}])=>[e,t]),t=Object.entries(W).map(([e,{label:t}])=>[e,t]),n=([e,t])=>`<option value="${e}">${t}</option>`,r=e=>e.map(n).join(``),i=`<div id="chartsOverview" class="dialog stable">
    <form id="chartsOverview__form">
      <div>
        <button data-tip="Add a chart" type="submit">Plot</button>

        <select data-tip="Select entity (y axis)" id="chartsOverview__entitiesSelect">
          ${r(e)}
        </select>

        <label for="chartsOverview__plotBySelect" data-tip="Select metric to plot (x axis)">
          <span>by</span>
          <select id="chartsOverview__plotBySelect">
            ${r(t)}
          </select>
          <i id="chartsOverview__plotByInfo" class="icon-info-circled" style="display: none"></i>
        </label>

        <label for="chartsOverview__groupBySelect" data-tip="Select entity to group by. If you don't need grouping, set it the same as the entity">
          <span>grouped by</span>
          <select id="chartsOverview__groupBySelect">
            ${r(e)}
          </select>
        </label>

        <label data-tip="Sorting type" for="chartsOverview__sortingSelect">
          <span>sorted</span>
          <select id="chartsOverview__sortingSelect">
            <option value="value">by value</option>
            <option value="name">by name</option>
            <option value="natural">naturally</option>
          </select>
        </label>
      </div>

      <div>
        <label data-tip="Select chart type" for="chartsOverview__chartType">
          <span>Type</span>
          <select id="chartsOverview__chartType">
            <option value="stackedBar" selected>Stacked Bar</option>
            <option value="normalizedStackedBar">Normalized Bar</option>
          </select>
        </label>

        <label data-tip="Show the charts in 1, 2, 3 or 4 columns" for="chartsOverview__viewColumns">
          <span>Columns</span>
          <select id="chartsOverview__viewColumns">
            <option value="1" selected>1</option>
            <option value="2">2</option>
            <option value="3">3</option>
            <option value="4">4</option>
          </select>
        </label>

        <label data-tip="Exclude zero element from the results (id 0, e.g. the neutral state)" for="chartsOverview__excludeNeutral">
          <input id="chartsOverview__excludeNeutral" type="checkbox" class="native" />
          <span>Exclude neutral</span>
        </label>
      </div>
    </form>

    <section id="chartsOverview__charts"></section>
  </div>`;p(`dialogs`).insertAdjacentHTML(`beforeend`,i),p(`chartsOverview__entitiesSelect`).value=`states`,p(`chartsOverview__plotBySelect`).value=`total_population`,p(`chartsOverview__groupBySelect`).value=`cultures`,p(`chartsOverview__form`).addEventListener(`submit`,ue),p(`chartsOverview__viewColumns`).addEventListener(`change`,me),p(`chartsOverview__plotBySelect`).addEventListener(`change`,le),document.getElementById(`chartsOverviewStyle`)?.remove();let a=document.createElement(`style`);a.id=`chartsOverviewStyle`,a.textContent=`
    #chartsOverview {
      max-width: 90vw !important;
      max-height: 90vh !important;
      overflow: hidden;
      display: grid;
      grid-template-rows: auto 1fr;
    }

    #chartsOverview__form {
      display: grid;
      font-size: 1.1em;
      margin: 0.3em 0;
    }

    #chartsOverview__form > div:first-child {
      display: flex;
      align-items: center;
      gap: 0.2em;
    }

    #chartsOverview__form > div:nth-child(2) {
      display: flex;
      align-items: center;
      gap: 1em;
    }

    #chartsOverview__form label {
      display: inline-flex;
      align-items: center;
    }

    #chartsOverview__charts {
      overflow: auto;
      scroll-behavior: smooth;
      display: grid;
    }

    #chartsOverview__charts figure {
      margin: 0;
      padding: 0.6em 0 1em;
      border-top: 1px solid rgba(128, 128, 128, 0.4);
    }

    #chartsOverview__charts figcaption {
      font-size: 1.2em;
      margin: 0 1% 0.4em 4%;
      display: grid;
      align-items: center;
      grid-template-columns: 1fr auto;
    }

    #chartsOverview__plotByInfo {
      margin-left: 0.3em;
      cursor: help;
      opacity: 0.6;
    }
  `,document.head.appendChild(a)}function le(){let e=p(`chartsOverview__plotBySelect`).value,t=p(`chartsOverview__plotByInfo`),{hint:n}=W[e];n?(t.dataset.tip=n,t.style.display=``):t.style.display=`none`}function ue(e){e&&e.preventDefault();let t=p(`chartsOverview__entitiesSelect`).value,n=p(`chartsOverview__plotBySelect`).value,r=p(`chartsOverview__groupBySelect`).value,i=p(`chartsOverview__sortingSelect`).value,a=p(`chartsOverview__chartType`).value,o=p(`chartsOverview__excludeNeutral`).checked,{label:s,stackable:c,provides:l=[]}=W[n],u=[t,r].find(e=>{let t=U[e].requires;return t?!l.includes(t):!1});if(u){w(`${s} cannot be broken down by ${U[u].label.toLowerCase()}`,!1,`error`,4e3);return}!c&&r!==t&&(w(`Grouping is not supported for ${n}`,!1,`warn`,4e3),r=t);let d={id:Date.now(),entity:t,plotBy:n,groupBy:r,sorting:i,type:a,excludeNeutral:o};G.push(d),de(d),q()}function de({id:t,entity:r,plotBy:i,groupBy:a,sorting:o,type:s,excludeNeutral:c}){let{label:l,stringify:u,quantize:d,getContributions:f,prepare:h,aggregate:g,formatTicks:_,landOnly:v}=W[i],y=a===r,{label:b,getName:x,getId:S,landOnly:ee}=U[r],{label:C,getName:w,getId:T,getColors:E}=U[a],D=h?h():void 0,O=f?e=>f(e,D):e=>[{value:d(e)}],k=`${m(r)} by ${l}${y?``:` grouped by ${C}`}`,A=(t,n,r,i)=>{let a=`${b}: ${t}`,o=y?``:`${C}: ${n}`,s=`${l}: ${u(r)}`;return y||(s+=` (${e(i*100)}%)`),[a,o,s].filter(Boolean)},j={},M=new Set;for(let e of pack.cells.i)if(!((ee||v)&&n(e,pack)))for(let t of O(e)){let n=S(e,t),r=T(e,t);if(c&&(n===0||r===0))continue;let{value:i}=t;j[n]?j[n][r]?j[n][r].push(i):j[n][r]=[i]:j[n]={[r]:[i]},M.add(r)}let N=Ae(Object.entries(j).flatMap(([e,t])=>{let n=x(e);return Object.entries(t).map(([e,t])=>({name:n,group:w(e),value:g(t)}))}),o),P=E(),{offset:F,formatX:I=_}=oe[s];pe(t,N,fe(N,{colors:P,tooltip:A,offset:F,formatX:I}),k),p(`chartsOverview__charts`).lastElementChild?.scrollIntoView()}function fe(e,{colors:n,tooltip:r,offset:i,formatX:a}){let o=e.map(e=>e.value),s=e.map(e=>e.name),c=e.map(e=>e.group),l=new Set(s),u=new Set(c),d=b(o.length).filter(e=>l.has(s[e])&&u.has(c[e])),f=Array.from(l),p=Array.from(u),m=ye(f),h=be(p,X-m-15),g={top:30,right:15,bottom:h*20+10,left:m},_=[g.left,X-g.right],v=l.size*25+g.top+g.bottom,y=[v-g.bottom,g.top],x=F(d,([e])=>e,e=>s[e],e=>c[e]),S=re().keys(p).value(([,e],t)=>o[new Map(e).get(t)]).order(B).offset(i)(x).map(e=>{let t=e.filter(e=>!Number.isNaN(e[1])).map(t=>Object.assign(t,{i:new Map(t.data[1]).get(e.key)}));return{key:e.key,data:t}}),E=t(D(S.flatMap(e=>e.data.flatMap(e=>[e[0],e[1]]))),_),O=ne(f,y).paddingInner(ge),k=C(E).ticks(X/80,null),A=ee(O).tickSizeOuter(0),j=te(`svg`).attr(`version`,`1.1`).attr(`xmlns`,`http://www.w3.org/2000/svg`).attr(`viewBox`,`0 0 ${X} ${v}`).attr(`style`,`max-width: 100%; height: auto; height: intrinsic;`);j.append(`g`).attr(`transform`,`translate(0,${g.top})`).call(k).call(e=>e.select(`.domain`).remove()).call(e=>e.selectAll(`text`).text(e=>a(e))).call(e=>e.selectAll(`.tick line`).clone().attr(`y2`,v-g.top-g.bottom).attr(`stroke-opacity`,.1));let M=j.append(`g`).attr(`stroke`,`#666`).attr(`stroke-width`,.5).selectAll(`g`).data(S).join(`g`).attr(`fill`,e=>n[e.key]).selectAll(`rect`).data(e=>e.data.filter(([e,t])=>e!==t)).join(`rect`).attr(`x`,([e,t])=>Math.min(E(e),E(t))).attr(`y`,({i:e})=>O(s[e])).attr(`width`,([e,t])=>Math.abs(E(e)-E(t))).attr(`height`,O.bandwidth()),N=Object.fromEntries(F(d,e=>T(e,e=>o[e]),e=>s[e])),P=({i:e})=>r(s[e],c[e],o[e],o[e]/N[s[e]]);M.append(`title`).text(e=>P(e).join(`\r
`)),M.on(`mouseover`,(e,t)=>w(P(t).join(`. `))),j.append(`g`).attr(`transform`,`translate(${E(0)},0)`).call(A);let I=Math.ceil(p.length/h),L=X/(I+.5),R=(e,t)=>t%I*L,z=(e,t)=>R(e,t)+ve,V=(e,t)=>Math.floor(t/I)*20,H=j.append(`g`).attr(`stroke`,`#666`).attr(`stroke-width`,.5).attr(`dominant-baseline`,`central`).attr(`transform`,`translate(${g.left},${v-g.bottom+15})`);return H.selectAll(`circle`).data(p).join(`rect`).attr(`x`,R).attr(`y`,V).attr(`width`,10).attr(`height`,10).attr(`transform`,`translate(-5, -5)`).attr(`fill`,e=>n[e]),H.selectAll(`text`).data(p).join(`text`).attr(`x`,z).attr(`y`,V).text(e=>e),j.node()}function pe(e,t,n,r){let i=p(`chartsOverview__charts`),o=document.createElement(`figure`),s=document.createElement(`figcaption`);s.innerHTML=`
    <div>
      <strong>Figure ${i.childElementCount+1}</strong>. ${r}
    </div>
    <div>
      <button data-tip="Download chart data as a text file (.csv)" class="icon-download"></button>
      <button data-tip="Download the chart as a PNG image" class="icon-export"></button>
      <button data-tip="Download the chart in SVG format (vector, opens in a browser or Inkscape)" class="icon-chart-bar"></button>
      <button data-tip="Remove the chart" class="icon-trash"></button>
    </div>
  `,o.appendChild(s),o.appendChild(n),i.appendChild(o),o.querySelector(`button.icon-download`)?.addEventListener(`click`,()=>{let e=`${x(r)}.csv`;a(`Name,Group,Value
`+t.map(({name:e,group:t,value:n})=>`${e},${t},${n}`).join(`
`),e)}),o.querySelector(`button.icon-export`)?.addEventListener(`click`,()=>{let{width:e,height:t}=n.viewBox.baseVal,i=n.cloneNode(!0);i.setAttribute(`width`,String(e)),i.setAttribute(`height`,String(t));let o=new XMLSerializer().serializeToString(i),s=URL.createObjectURL(new Blob([o],{type:`image/svg+xml;charset=utf-8`})),c=new Image;c.onload=()=>{let n=document.createElement(`canvas`);n.width=e*2,n.height=t*2;let i=n.getContext(`2d`);i&&(i.fillStyle=`#fff`,i.fillRect(0,0,n.width,n.height),i.drawImage(c,0,0,n.width,n.height),n.toBlob(e=>e&&a(e,`${x(r)}.png`,`image/png`))),URL.revokeObjectURL(s)},c.src=s}),o.querySelector(`button.icon-chart-bar`)?.addEventListener(`click`,()=>{let e=`${x(r)}.svg`;a(n.outerHTML,e)}),o.querySelector(`button.icon-trash`)?.addEventListener(`click`,()=>{o.remove(),G=G.filter(t=>t.id!==e),q()})}function me(){let e=p(`chartsOverview__viewColumns`).value,t=p(`chartsOverview__charts`);t.style.gridTemplateColumns=`repeat(${e}, 1fr)`,q()}function q(){E(`chartsOverview`,{position:{my:`center`,at:`center`,of:`svg`,collision:`fit`}})}function he(){$(`#chartsOverview`).dialog(`destroy`),p(`chartsOverview`).remove(),document.getElementById(`chartsOverviewStyle`)?.remove()}var J=`#ccc`,Y=`no`,X=800,ge=.2,_e=7,ve=10;function ye(e){return y(e.map(e=>e.length))*_e}function be(e,t){if(!e.length)return 0;let n=ve+ye(e),r=Math.max(1,Math.floor(t/n));return Math.ceil(e.length/r)}function Z(e){return t=>pack[e][+t]?.name||Y}function Q(e){return()=>Object.fromEntries(pack[e].map(e=>[e.name||Y,e.color||J]))}function xe(e){return pack.biomes[+e]?.name||Y}function Se(){return Object.fromEntries(pack.biomes.map(({name:e,color:t})=>[e,t]))}function Ce(e){let t=Markets.get(+e);return t?t.name||pack.burgs[t.centerBurgId]?.name||`Market ${t.i}`:Y}function we(){return Object.fromEntries((pack.markets||[]).map(e=>[Ce(e.i),e.color||J]))}function Te(e){return Goods.get(+e)?.name||Y}function Ee(){return Object.fromEntries((pack.goods||[]).map(e=>[e.name||Y,e.color||J]))}function De(e,t){let n=Production.getCellProduction(e,t),r=pack.cells.burg[e];if(r){let e=Production.getBurgProduction(pack.burgs[r]);for(let[t,r]of Object.entries(e))n[+t]=(n[+t]||0)+r}return n}function Oe(e){let t=pack.cells.burg[e];return t?(pack.burgs[t].population||0)*options.map.units.population.scale*options.map.units.population.urbanization.rate:0}function ke(e){return pack.cells.pop[e]*options.map.units.population.scale}function Ae(e,t){if(t===`natural`)return e;if(t===`name`)return e.sort((e,t)=>e.name===t.name?e.group.localeCompare(t.group):t.name.localeCompare(e.name));if(t===`value`){let t={},n={};for(let{name:r,group:i,value:a}of e)t[r]=(t[r]||0)+a,n[i]=(n[i]||0)+a;return e.sort((e,r)=>e.name===r.name?n[r.group]-n[e.group]:t[e.name]-t[r.name])}return e}var je={open:se};export{je as ChartsOverview};