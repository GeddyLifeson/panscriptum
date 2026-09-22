import{Bn as e,P as t,R as n,hn as r,j as i,r as a,z as o}from"./utils-Cob8vHf9.js";import{Z as s,t as c}from"./layers-Bh4OWBXX.js";import{i as l,t as u}from"./tooltips-BTSHGd98.js";import{t as d}from"./controllers-DnVd8NhQ.js";import{H as f,V as p,d as m,dt as h,lt as g,st as _,u as v}from"./index-DsIn6sTp.js";import{a as y,i as b,n as x,r as S}from"./table-B6G2rlSI.js";var C=0,w=`marketOverview`,T={my:`right top`,at:`right-10 top+10`,of:`svg`,collision:`fit`},E=[{key:`icon`,width:`2.5em`,permanent:!0},{key:`good`,label:`Good`,width:`8em`,permanent:!0,sortBy:e=>e.good,sortType:`alpha`},{key:`stock`,label:`Stock`,width:`5em`,sortBy:e=>e.stock,defaultSort:`desc`},{key:`price`,label:`Price`,width:`5em`,permanent:!0,sortBy:e=>e.price}],D=S({getData:P,onUpdate:F});function O(e){if(customization)return;let t=Markets.get(e);if(!t){l(`Invalid market. The selected market does not exist`,!0,`error`,5e3);return}C=e,_(`#${w}, .stable`),k(),D.reset(),A(t),$(`#${w}`).dialog({title:`Market Stock: ${Markets.getName(t)}`,width:`auto`,close:z,position:T})}function k(){g(w);let e=`<div id="${w}" class="dialog stable editorDialog">
      ${b({dialogId:w,columns:E})}
      <div id="marketOverviewGoodsBody" class="table" style="max-height:40em"></div>
      <div id="marketOverviewSummary" class="totalLine"></div>
      <div id="marketOverviewNameLine" style="display: flex; align-items: center; margin-bottom: 0.4em">
        <div class="label">Name:</div>
        <input
          id="marketOverviewName"
          data-tip="Type to rename the market. Clear the field to reset to the default name"
          autocorrect="off"
          spellcheck="false"
          style="width: 11em; margin-left: 0.3em;"
        />
        <span
          id="marketOverviewNameReset"
          data-tip="Reset to the default name (center burg name)"
          class="icon-ccw pointer"
          style="margin-left: 0.3em"
        ></span>
      </div>
      <div id="marketOverviewInfo" style="margin-bottom: 0.3em"></div>
      <div id="marketOverviewBottom">
        <button id="marketOverviewRefresh" data-tip="Refresh the Overview screen" class="icon-cw"></button>
        <button id="marketOverviewOpenDeals" data-tip="View market deals" class="icon-list-bullet"></button>
        ${f.getButton(`marketOverviewLegend`,`this market`)}
        <button
          id="marketOverviewRelocate"
          data-tip="Relocate market. Click on a burg on the map to move the market center"
          class="icon-map-pin"
        ></button>
        <button id="marketOverviewExport" data-tip="Save market deals data as a text file (.csv)" class="icon-download"></button>
      </div>
  </div>`;i(`dialogs`).insertAdjacentHTML(`beforeend`,e),v(w,D.reset),x({dialogId:w,columns:E,onUpdate:()=>h(w,{width:`fit-content`,position:T})}),i(`marketOverviewRefresh`).addEventListener(`click`,D.refresh),i(`marketOverviewExport`).addEventListener(`click`,R),i(`marketOverviewOpenDeals`).addEventListener(`click`,()=>d.MarketDealsOverview.open(C)),i(`marketOverviewRelocate`).addEventListener(`click`,I),i(`marketOverviewLegend`).addEventListener(`click`,j),i(`marketOverviewName`).addEventListener(`input`,M),i(`marketOverviewNameReset`).addEventListener(`click`,N)}function A(e){let t=i(`marketOverviewName`);t.value=e.name||``,t.placeholder=pack.burgs[e.centerBurgId]?.name||`Market ${e.i}`}function j(){d.NotesEditor.open({type:`market`,id:C})}function M(){let e=Markets.get(C);e&&(e.name=this.value.trim()||void 0,$(`#marketOverview`).dialog(`option`,`title`,`Market Stock: ${Markets.getName(e)}`))}function N(){let e=Markets.get(C);e&&(e.name=void 0,i(`marketOverviewName`).value=``,$(`#marketOverview`).dialog(`option`,`title`,`Market Stock: ${Markets.getName(e)}`))}function P(){let e=Markets.get(C);if(!e)return l(`Invalid market. The selected market does not exist`,!0,`error`,5e3),[];let t=pack.burgs[e.centerBurgId];return!t||t.removed?(l(`Invalid market. The selected market has no center burg`,!0,`error`,5e3),[]):m(w,Object.entries(e.goods).flatMap(([e,t])=>{let n=Goods.get(+e);return n?[{goodId:+e,good:n.name,stock:t.stock,price:t.price}]:[]}),E)}function F(t){let n=Markets.get(C);if(!n)return;let r=t.rows.map(t=>{let n=Goods.get(t.goodId),r=Goods.getStroke(n.color);return`<div class="states marketGood"
      data-good="${n.name}"
      data-stock="${e(t.stock,2)}"
      data-price="${e(t.price,2)}">
      <svg data-col="icon" data-tip="Good icon" width="2em" height="2em" class="goodIcon">
        <circle cx="50%" cy="50%" r="42%" fill="${n.color}" stroke="${r}"/>
        <use href="#${n.icon}" x="10%" y="10%" width="80%" height="80%"/>
      </svg>
      <div data-col="good" data-tip="Good name" class="goodName">${n.name}</div>
      <div data-col="stock" data-tip="Good stock" class="marketGoodStock">${e(t.stock,2)}</div>
      <div data-col="price" data-tip="Good price" class="marketGoodPrice">${a(t.price)}</div>
    </div>`});i(`marketOverviewGoodsBody`).innerHTML=r.join(``)||`No market goods available`;let o=pack.burgs[n.centerBurgId],c=pack.states[o?.state||0],l=`stateCOA${c.i}`;c&&s.trigger(l,c.coa),i(`marketOverviewInfo`).innerHTML=`<svg class="coaIcon" viewBox="0 0 200 200"><use href="#${l}"></use></svg><b>Owner:</b> ${c.fullName||c.name}`;let u=pack.burgs.filter(e=>!e.removed&&e.market===n.i),d=t.all.reduce((e,t)=>e+t.stock,0);i(`marketOverviewSummary`).innerHTML=`
    <div style="margin-left:5px">Cells: ${pack.cells.market.reduce((e,t)=>e+ +(t===n.i),0)}</div>
    <div style="margin-left:12px">Burgs: ${u.length}</div>
    <div data-col="stock" style="margin-left:12px">Stock: ${e(d,2)}</div>`,y(i(`marketOverviewSummary`),t,D.goto),h(w,{width:`fit-content`,position:T})}function I(){let e=i(`marketOverviewRelocate`);e.classList.toggle(`pressed`),e.classList.contains(`pressed`)?(r(`#viewbox`).style(`cursor`,`crosshair`).on(`click`,L),l(`Click on a burg on the map to relocate the market center`,!0)):(u(),p())}function L(e){let n=Markets.get(C);if(!n)return;let[r,i]=t(e,this),a=Pack.findCell(r,i);if(a===void 0)return;let o=pack.cells.burg[a],s=pack.burgs[o];if(!o||!s||s.removed){l(`No valid burg in this cell. Click on a cell with a burg`,!1,`error`);return}if(o===n.centerBurgId){l(`This burg is already the center of this market`,!1,`error`);return}if(pack.markets.some(e=>e.centerBurgId===o)){l(`This burg is already a center of another market`,!1,`error`);return}Markets.relocateMarket(C,o)&&(I(),c.draw(`markets`),A(n),$(`#marketOverview`).dialog(`option`,`title`,`Market Stock: ${Markets.getName(n)}`),D.refresh())}function R(){let t=Markets.get(C);if(!t)return;let r=`Good,Stock,Buy Price,Sell Price
`;for(let[n,i]of Object.entries(t.goods)){let t=Goods.get(Number(n));if(!t)continue;let a=e(Markets.customerBuyPrice(i.price),2),o=e(Markets.customerSellPrice(i.price),2);r+=`${[t.name,e(i.stock,2),a,o].join(`,`)}\n`}n(r,`${o(`Market`)}.csv`)}function z(){i(`marketOverviewRelocate`).classList.contains(`pressed`)&&I(),$(`#${w}`).dialog(`destroy`),i(w).remove()}var B={open:O};export{B as MarketOverview};