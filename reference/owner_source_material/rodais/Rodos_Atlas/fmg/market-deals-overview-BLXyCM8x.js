import{Bn as e,R as t,j as n,r,z as i}from"./utils-Cob8vHf9.js";import{i as a}from"./tooltips-BTSHGd98.js";import{t as o}from"./state-B2hBYDzv.js";import{d as s,dt as c,lt as l,u}from"./index-DsIn6sTp.js";import{a as d,i as f,n as p,r as m}from"./table-B6G2rlSI.js";var h=0,g,_=`marketDeals`,v={my:`right top`,at:`right bottom+10`,of:`#marketOverview`,collision:`fit`},y=[{key:`icon`,width:`2em`,permanent:!0},{key:`good`,label:`Good`,width:`6.8em`,permanent:!0,sortBy:e=>Goods.get(e.good)?.name??``,sortType:`alpha`},{key:`direction`,label:`Type`,width:`5em`,sortBy:e=>O(e,h),sortType:`alpha`},{key:`counterparty`,label:`Counterparty`,width:`8em`,sortBy:e=>j(e)?.name??``,sortType:`alpha`},{key:`units`,label:`Units`,width:`5em`,sortBy:e=>e.units},{key:`income`,label:`Income`,width:`5em`,permanent:!0,sortBy:e=>M(e,h)}],b=m({getData:w,onUpdate:T});function x(e){let t=Markets.get(e);if(!t){a(`Invalid market. The selected market does not exist`,!0,`error`,5e3);return}g=o.get(_,`filters`,()=>({scope:`all`})),[`all`,`local`,`global`].includes(g.scope)||(g.scope=`all`),o.set(_,`filters`,g),h=e,S(),n(`marketDealsFilter`).value=g.scope,b.reset(),$(`#${_}`).dialog({title:`${Markets.getName(t)} Market Deals`,position:v,close:C})}function S(){l(_);let e=`<div id="${_}" class="dialog stable editorDialog">
      <div>
        ${f({dialogId:_,columns:y})}
        <div id="marketDealsBody" class="table" style="max-height:30em"></div>

        <div id="marketDealsFooter" class="totalLine">
          <div style="margin-left: 5px" data-tip="Deals count">Deals: <span id="marketDealsFooterDeals">0</span></div>
          <div data-col="income" style="margin-left: 12px" data-tip="Net flow for this market">Net Flow: <span id="marketDealsFooterNet">🟡 0</span></div>
        </div>

        <div id="marketDealsBottom">
          <button id="marketDealsRefresh" data-tip="Refresh the Deals screen" class="icon-cw"></button>
          <button id="marketDealsExport" data-tip="Save market deals data as a text file (.csv)" class="icon-download"></button>
          <select id="marketDealsFilter" data-tip="Filter deals by scope" style="margin-left: 8px">
            <option value="all">All</option>
            <option value="local">Local</option>
            <option value="global">Global</option>
          </select>
        </div>
      </div>
  </div>`;n(`dialogs`).insertAdjacentHTML(`beforeend`,e),u(_,b.reset),p({dialogId:_,columns:y,onUpdate:()=>c(_,{width:`fit-content`,position:v})}),n(`marketDealsRefresh`).addEventListener(`click`,b.refresh),n(`marketDealsExport`).addEventListener(`click`,N),n(`marketDealsBody`).addEventListener(`click`,e=>{let t=e.target.closest(`.marketDealParty`)?.closest(`.marketDeal`)?.dataset.id,n=pack.deals.find(e=>e.i===Number(t));if(!n)return;let r=j(n);r&&zoomTo(r.x,r.y,8,2e3)}),n(`marketDealsFilter`).addEventListener(`change`,e=>{g.scope=e.target.value,o.set(_,`filters`,g),b.reset()})}function C(){$(`#${_}`).dialog(`destroy`),n(_).remove()}function w(){return Markets.get(h)?s(_,E(pack.deals,h).filter(e=>{if(g.scope===`all`)return!0;let t=k(e,h);return g.scope===`local`?t.type===`burg`:t.type===`market`}),y):(a(`Invalid market. The selected market does not exist`,!0,`error`,5e3),[])}function T(e){let t=e.rows.map(A).join(``),i=e.all.reduce((e,t)=>e+M(t,h),0);n(`marketDealsBody`).innerHTML=t||`No market deals recorded`,n(`marketDealsFooterDeals`).innerHTML=String(e.all.length),n(`marketDealsFooterNet`).innerHTML=r(i),d(n(`marketDealsFooter`),e,b.goto),c(_,{width:`fit-content`,position:v})}function E(e,t){return e.filter(e=>e.sellerType===`market`&&e.seller===t||e.buyerType===`market`&&e.buyer===t)}function D(e,t){return e.sellerType===`market`&&e.seller===t}function O(e,t){return D(e,t)?`out`:`in`}function k(e,t){return D(e,t)?{id:e.buyer,type:e.buyerType}:{id:e.seller,type:e.sellerType}}function A(t){let n=Goods.get(t.good);if(!n)return``;let i=M(t,h),a=j(t),o=k(t,h),s=O(t,h),c=i>=0?`#2a6`:`#c44`,l=i>=0?`#dff0d8`:`#f2dede`;return`<div class="states marketDeal" data-id="${t.i}" data-good="${n.name}" data-direction="${s}" data-units="${e(t.units,2)}" data-counterparty="${o.type}_${a?.name}" data-income="${i}">
      <svg data-col="icon" data-tip="Good icon" width="1.3em" height="1.3em" class="goodIcon">
        <circle cx="50%" cy="50%" r="42%" fill="${n.color}" stroke="${Goods.getStroke(n.color)}"/>
        <use href="#${n.icon}" x="10%" y="10%" width="80%" height="80%"/>
      </svg>
      <div data-col="good" data-tip="Good name" class="goodName">${n.name}</div>
      <div data-col="direction"><span class="marketBadge" style="background:${l}; color:${c}">${s.toUpperCase()}</span></div>
      <div data-col="counterparty" class="marketDealParty pointer" data-tip="Click to zoom">
        <div class="${o.type===`burg`?`icon-dot-circled`:`icon-store`}" style="display:inline-block; width: 0.8em; ${o.type===`market`?`font-size: 0.85em;`:``}"></div>
        <div style="display:inline-block; width: 6.8em;">${a?.name}</div>
      </div>
      <div data-col="units" class="marketDealUnits">${e(t.units,2)}</div>
      <div data-col="income" class="marketDealIncome" style="color:${c}">${r(i)}</div>
    </div>`}function j(e){let t=k(e,h),n=t.type===`burg`?t.id:Markets.get(t.id)?.centerBurgId;return n&&pack.burgs[n]||null}function M(t,n){let r=e(t.units*t.price,2);return D(t,n)?r:-r}function N(){if(!Markets.get(h))return;let n=E(pack.deals,h),r=`Id,Good,Type,Client,Units,Price,Net
`;for(let t of n){let n=Goods.get(t.good);n&&(r+=[t.i,n.name,O(t,h),j(t)?.name??``,e(t.units,2),e(t.price,2),e(M(t,h),2)].join(`,`),r+=`
`)}t(r,`${i(`Market_${h}_Deals`)}.csv`)}var P={open:x};export{P as MarketDealsOverview};