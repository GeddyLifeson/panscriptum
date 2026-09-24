import{Bn as e,L as t,On as n,V as r,dt as i,j as a,kn as o}from"./utils-Cob8vHf9.js";import{t as s}from"./layers-Bh4OWBXX.js";import{i as c}from"./tooltips-BTSHGd98.js";import{t as l}from"./controllers-DnVd8NhQ.js";import{n as u}from"./cultures-generator-B9VhtNU6.js";import{b as d,lt as f,ut as p,x as m}from"./index-DsIn6sTp.js";var h=null,g=null;function _(t,r){let i=Array.from(a(`good-icons`).querySelectorAll(`symbol`)).map(e=>e.id),u={...t?.demandCoverage||{}},h={...t?.biomeOutput||{}},g=()=>{let e=m.map(e=>[e,u[e]??0]).filter(([,e])=>e>0);return e.length?e.map(([e,t])=>`${d[e]} ${o(e)}: ${t}`).join(`, `):`none`},_=()=>{let e=Object.entries(h).filter(([,e])=>(e??0)>0);return e.length?e.map(([e,t])=>`${pack.biomes[Number(e)].name}: ${t}`).join(`, `):`none`},w={cultureType:{...t?.multipliers?.cultureType??{}},culture:{...t?.multipliers?.culture??{}},state:{...t?.multipliers?.state??{}},religion:{...t?.multipliers?.religion??{}},biome:{...t?.multipliers?.biome??{}},zone:{...t?.multipliers?.zone??{}}},T=t=>{let n=w[t]??{},r=Object.entries(n).filter(([,e])=>e!==1);return r.length?r.map(([n,r])=>`${v(t,n)} ×${e(r,2)}`).join(`, `):`none`},E=(e,t)=>`
      <label data-tip="Production multiplier by ${t.toLowerCase()}. 1 = no effect, 0 = fully suppressed.">${t}</label>
      <div class="ge-edit-row">
        <span id="mSummary_${e}">${T(e)}</span>
        <button class="mEdit icon-pencil ge-edit" data-dim="${e}" data-tip="Edit ${t} multipliers"></button>
      </div>`,D=t?.recipes||[],O;k(),$(O).dialog({width:`30em`,resizable:!1,title:t?`Edit good`:`Add new good`,open:function(){t&&(this.parentElement?.querySelector(`.ui-dialog-buttonpane`))?.insertAdjacentHTML(`afterbegin`,`<div class="dontAsk" data-tip="Re-place this good and recompute production, trade and taxes. Uncheck to update the good only, without disturbing the current economy.">
          <input id="goodRegenerateEconomy" class="checkbox" type="checkbox" checked />
          <label for="goodRegenerateEconomy" class="checkbox-label"><i>regenerate economy on apply</i></label>
        </div>`)},close:()=>{f(`goodEditor`)},buttons:{Cancel:function(){$(this).dialog(`close`)},[t?`Apply`:`Add`]:()=>{let e=[],i=a(`newGoodName`).value.trim(),o=n(a(`newGoodTags`).value.trim().split(`,`).map(e=>e.trim().toLocaleLowerCase())),l=+a(`newGoodValue`).value,d=+a(`newGoodChance`).value,f=a(`newGoodUnit`).value.trim(),m=a(`newGoodIcon`).value,g=a(`newGoodColor`).value,_=a(`newGoodDistribution`).textContent?.trim()??``;if(i||e.push(`Name is required`),(!Number.isFinite(l)||l<0)&&e.push(`Value must be a valid non-negative number`),(!Number.isFinite(d)||d<0||d>100)&&e.push(`Chance must be between 0 and 100`),_)try{let e=Goods.getMethods(),t=`{${Object.keys(e).join(`, `)}}`;Function(t,`return ${_}`)(e)}catch(t){e.push(`Distribution function is invalid: ${t.message||t}`)}for(let t of D){for(let[n,r]of Object.entries(t)){let t=Number(n),i=Goods.get(t);i||e.push(`Recipe references unknown good id: ${t}`);let a=Number(r);(Number.isNaN(a)||!Number.isFinite(a)||a<=0)&&e.push(`Invalid recipe amount for good ${i?.name}`)}Object.keys(t).length||e.push(`Each recipe must have at least one ingredient`)}if(a(`newGoodError`).textContent=e.join(`. `),e.length)return;function v(){let e={};for(let[t,n]of Object.entries(w)){let r=Object.fromEntries(Object.entries(n??{}).filter(([,e])=>e!==void 0&&e!==1));Object.keys(r).length&&(e[t]=r)}return Object.keys(e).length?e:void 0}t?(t.name=i,t.tags=o,t.icon=m,t.color=g,t.value=l,t.chance=d,t.unit=f,t.demandCoverage=u,t.multipliers=v(),t.distribution=_||void 0,t.biomeOutput=Object.keys(h).length?h:void 0,t.recipes=D.length?D:void 0,a(`goodRegenerateEconomy`).checked?(Goods.regeneratePlacement(t.i),Production.regenerateEconomy(),s.draw(`markets`,`goods`),s.draw(`trade`),p()):Goods.sync()):(pack.goods.push({i:(()=>{let e=pack.goods?.at(-1)?.i??1;for(;Goods.get(e);)e++;return e})(),name:i,tags:o,icon:m,color:g,value:l,chance:d,unit:f,demandCoverage:u,multipliers:v(),distribution:_||void 0,biomeOutput:Object.keys(h).length?h:void 0,recipes:D.length?D:void 0}),Goods.sync()),c(t?`Good is updated`:`Good is added`,!1,`success`,5e3),r?.(),$(O).dialog(`close`)}}});function k(){f(`goodEditor`),a(`dialogs`).insertAdjacentHTML(`beforeend`,`<div id="goodEditor" class="dialog">
    <style>
      .ge                 { display:flex; width: auto !important; flex-direction:column; gap:9px; max-height:72vh; overflow-y:auto; padding-right:2px; }
      .ge-section-title   { display:flex; align-items:center; justify-content:space-between; font-weight:bold; text-transform:uppercase; font-size:.8em; letter-spacing:.06em; margin-bottom:7px; padding-bottom:4px; border-bottom:1px solid #666; }
      .ge-grid            { display:grid; grid-template-columns:9em minmax(0, 1fr); gap:.2em; align-items:center; }
      .ge-grid--top       { align-items:start; }
      .ge-grid > *        { min-width:0; }
      .ge-grid > label    { color:#555; }
      .ge-field           { width:100%; }
      input.ge-num        { width:6em; }
      .ge-inline          { display:flex; align-items:center; gap:.4em; }
      .ge-icon-select     { flex:1; min-width:0; }
      .ge-icon-preview    { flex-shrink:0; }
      .ge-color           { width:2.4em; height:1.4em; padding:0; border:none; flex-shrink:0; }
      .ge-edit-row        { display:flex; align-items:flex-start; justify-content:space-between; gap:6px; }
      .ge-edit-row > span { flex:1; min-width:0; }
      .ge-edit            { flex-shrink:0; }
      .ge-dist            { flex:1; min-width:0; color:#555; font-size:.9em; font-family:var(--monospace); word-break:break-all; }
      .ge-note            { color:#777; font-style:italic; font-size:.9em; }
      .ge-error           { color:#b20000; min-height:1.2em; }
      .ge-recipe-list     { display:flex; flex-direction:column; gap:.45em; }
      .ge-recipe          { border:1px solid #ccc; border-radius:3px; }
      .ge-recipe-head     { display:flex; align-items:center; justify-content:space-between; padding:.2em .3em; }
      .ge-recipe-actions  { display:flex; gap:.3em; }
      .ge-recipe-ings     { display:flex; flex-direction:column; gap:.2em; padding:.3em .4em; }
      .ge-recipe-ing      { display:grid; grid-template-columns:1fr 5em 1.5em; gap:.25em; align-items:center; }
    </style>

    <div class="ge">
      <div>
        <div class="ge-section-title">General</div>
        <div class="ge-grid">
          <label for="newGoodName">Name*</label>
          <input id="newGoodName" class="ge-field" value="${t?.name||``}" />

          <label for="newGoodTags">Tags</label>
          <input id="newGoodTags" class="ge-field" value="${t?.tags.join(`, `)||``}" placeholder="comma separated" />

          <label for="newGoodValue">Base Price*</label>
          <span class="ge-inline"><input id="newGoodValue" class="ge-num" type="number" min="0" step="1" value="${t?.value??1}" /> 🟡</span>

          <label for="newGoodChance">Chance</label>
          <input id="newGoodChance" class="ge-num" type="number" min="0" max="100" step="0.1" value="${t?.chance??1}" />

          <label for="newGoodUnit">Unit</label>
          <input id="newGoodUnit" class="ge-field" placeholder="e.g. wagon, barrel" value="${t?.unit||``}" />

          <label for="newGoodIcon">Icon*</label>
          <div class="ge-inline">
            <select id="newGoodIcon" class="ge-icon-select">${i.map(e=>`<option value="${e}" ${t?.icon===e?`selected`:``}>${e}</option>`).join(``)}</select>
            <svg class="ge-icon-preview" width="2em" height="2em">
              <circle id="newGoodIconCircle" cx="50%" cy="50%" r="42%" fill="${t?.color||`#ff5959`}" stroke="${Goods.getStroke(t?.color||`#ff5959`)}"/>
              <use id="newGoodIconPreview" href="#${t?.icon||`good-unknown`}" x="10%" y="10%" width="80%" height="80%"/>
            </svg>
            <button id="newGoodUploadIconRaster" class="icon-upload" data-tip="Upload raster icon"></button>
            <button id="newGoodUploadIconVector" class="icon-upload-cloud" data-tip="Upload vector (SVG) icon"></button>
            <input id="newGoodColor" class="ge-color" type="color" data-tip="Set a stroke color" value="${t?.color||`#ff5959`}" />
          </div>

          <label data-tip="How much of each demand category this good satisfies. Click the pencil icon to edit.">Demand Coverage</label>
          <div class="ge-edit-row">
            <span id="demandCoverageSummary" >${g()}</span>
            <button class="dcEdit icon-pencil ge-edit" data-tip="Edit demand coverage"></button>
          </div>
        </div>
      </div>

      <div>
        <div class="ge-section-title">Raw Production</div>
        <div class="ge-grid ge-grid--top">
          <label data-tip="For raw resources: sets the baseline production per biome">Rural production</label>
          <div class="ge-edit-row">
            <span id="biomeProductionSummary">${_()}</span>
            <button class="bpEdit icon-pencil ge-edit" data-tip="Edit biome baseline production"></button>
          </div>

          <label data-tip="For raw resources: controls where and how this good is produced directly from the environment (e.g. biome, elevation, temperature)">Bonus distribution</label>
          <div class="ge-edit-row">
            <div id="newGoodDistribution" class="ge-dist">${t?.distribution||``}</div>
            <button id="newGoodDistributionEditor" class="icon-pencil ge-edit" data-tip="Open the Distribution visual editor"></button>
          </div>
        </div>
        <div id="newGoodRawNote" class="ge-note"></div>
      </div>

      <div>
        <div class="ge-section-title">
          <span data-tip="For manufactured goods: recipes define which other goods are required to produce this good">Recipes</span>
          <button id="newGoodAddRecipe" class="icon-plus" data-tip="Add a recipe"></button>
        </div>
        <div id="newGoodRecipeList" class="ge-recipe-list"></div>
        <div id="newGoodRecipeNote" class="ge-note"></div>
      </div>

      <div>
        <div class="ge-section-title">
          <span data-tip="Per-dimension production multipliers. 1 = no effect, 0 = fully suppressed.">Multipliers</span>
        </div>
        <div class="ge-grid ge-grid--top">
          ${E(`cultureType`,`Culture Type`)}
          ${E(`culture`,`Culture`)}
          ${E(`state`,`State`)}
          ${E(`religion`,`Religion`)}
          ${E(`biome`,`Biome`)}
          ${E(`zone`,`Zone`)}
        </div>
      </div>

      <div id="newGoodError" class="ge-error"></div>
    </div>
  </div>`),O=a(`goodEditor`);let e=a(`newGoodRecipeList`),n=pack.goods[0]?.i??0,r=[...pack.goods].sort((e,t)=>e.name.localeCompare(t.name)),o=()=>!Object.values(h).some(e=>(e??0)>0)&&!document.getElementById(`newGoodDistribution`)?.textContent?.trim(),s=()=>{let e=o(),t=D.length===0,n=a(`newGoodRecipeNote`);n.textContent=`This good is raw-only: gathered from the environment.`,n.style.display=t&&!e?``:`none`;let r=a(`newGoodRawNote`);r.textContent=`This good is manufactured-only: made from recipes in burgs.`,r.style.display=e&&!t?``:`none`},c=()=>{e.innerHTML=D.map((e,t)=>`
          <div class="recipeOption ge-recipe" data-recipe-index="${t}" >
            <div class="ge-recipe-head">
              <span>Recipe ${t+1}</span>
              <div class="ge-recipe-actions">
                <span class="recipeAddIngredient icon-plus pointer" data-recipe-index="${t}" data-tip="Add ingredient"></span>
                <span class="recipeRemoveOption icon-trash-empty pointer" data-recipe-index="${t}" data-tip="Remove recipe"></span>
              </div>
            </div>
            <div class="recipeIngredients ge-recipe-ings">
              ${Object.entries(e).map(([e,n],i)=>`
                    <div class="ge-recipe-ing" data-recipe-index="${t}" data-ingredient-index="${i}">
                      <select class="recipeGoodSelect" data-recipe-index="${t}" data-ingredient-index="${i}">${r.map(t=>`<option value="${t.i}" ${t.i===Number(e)?`selected`:``}>${t.name}</option>`).join(``)}</select>
                      <input class="recipeAmountInput" data-recipe-index="${t}" data-ingredient-index="${i}" type="number" min="1" step="1" value="${n}" />
                      <span class="recipeRemoveIngredient icon-trash-empty pointer" data-recipe-index="${t}" data-ingredient-index="${i}" data-tip="Remove ingredient" />
                    </div>`).join(``)}
            </div>
          </div>
        `).join(``),e.querySelectorAll(`.recipeGoodSelect`).forEach(e=>{e.onchange=()=>{let t=+e.value,n=+e.dataset.recipeIndex,r=+e.dataset.ingredientIndex,i=D[n],a=i[r]||0;delete i[r],i[t]=a,c()}}),e.querySelectorAll(`.recipeAmountInput`).forEach(e=>{e.onchange=()=>{let t=+e.dataset.recipeIndex,n=+e.dataset.ingredientIndex,r=D[t],i=Number(Object.keys(r)[n]);r[i]=+e.value}}),e.querySelectorAll(`.recipeAddIngredient`).forEach(e=>{e.onclick=t=>{t.preventDefault();let r=D[+e.dataset.recipeIndex],i=Object.keys(r).length?Math.max(...Object.keys(r).map(e=>+e))+1:n;r[i]=1,c()}}),e.querySelectorAll(`.recipeRemoveIngredient`).forEach(e=>{e.onclick=t=>{t.preventDefault();let n=+e.dataset.recipeIndex,r=+e.dataset.ingredientIndex,i=D[n];if(Object.keys(i).length>1){let e=Number(Object.keys(i)[r]);delete i[e],c()}}}),e.querySelectorAll(`.recipeRemoveOption`).forEach(e=>{e.onclick=t=>{t.preventDefault();let n=+e.dataset.recipeIndex;D.splice(n,1),c()}}),s()};c(),O.querySelectorAll(`.mEdit`).forEach(e=>{e.addEventListener(`click`,()=>{let t=e.dataset.dim;x(t,w[t]??{},e=>{w[t]=e;let n=document.getElementById(`mSummary_${t}`);n&&(n.textContent=T(t))})})}),O.querySelector(`.dcEdit`).addEventListener(`click`,()=>{S({...u},e=>{Object.keys(u).forEach(e=>void delete u[e]),Object.assign(u,e);let t=document.getElementById(`demandCoverageSummary`);t&&(t.textContent=g())})}),O.querySelector(`.bpEdit`).addEventListener(`click`,()=>{C({...h},e=>{Object.keys(h).forEach(e=>void delete h[+e]),Object.assign(h,e);let t=document.getElementById(`biomeProductionSummary`);t&&(t.textContent=_()),s()})}),a(`newGoodAddRecipe`).addEventListener(`click`,e=>{e.preventDefault(),D.push({[n]:1}),c()}),a(`newGoodDistributionEditor`).addEventListener(`click`,()=>{let e=a(`newGoodDistribution`);l.DistributionEditor.open(t=>{e.textContent=t,s()},e.textContent?.trim()??``)});let d=a(`newGoodIcon`);d.onchange=()=>a(`newGoodIconPreview`).setAttribute(`href`,`#${d.value}`);let p=a(`newGoodColor`);p.oninput=()=>{let e=a(`newGoodIconCircle`);e.setAttribute(`fill`,p.value),e.setAttribute(`stroke`,Goods.getStroke(p.value))};let m=(e,t)=>{a(`newGoodIconPreview`).setAttribute(`href`,`#${t}`),d.innerHTML+=`<option value="${t}">${t}</option>`,d.value=t},v=e=>{let t=y(e);t.onchange=()=>b(e,m),t.click()};a(`newGoodUploadIconRaster`).onclick=()=>v(`image`),a(`newGoodUploadIconVector`).onclick=()=>v(`svg`)}}function v(e,t){return e===`cultureType`?t:e===`culture`?pack.cultures[+t]?.name??`Culture ${t}`:e===`state`?pack.states[+t]?.name??`State ${t}`:e===`religion`?pack.religions[+t]?.name??`Religion ${t}`:e===`zone`?pack.zones.find(e=>e.i===+t)?.name??`Zone ${t}`:pack.biomes[+t]?.name??`Biome ${t}`}function y(e){return e===`image`?(h??=t(`image/*`),h):(g??=t(`.svg`),g)}function b(e,t){let n=y(e),i=n.files[0];if(n.value=``,i.size>2e5){c(`File is too big, please optimize file size up to 200kB and re-upload. Recommended size is 48x48 px and up to 10kB`,!0,`error`,5e3);return}let o=new FileReader;o.onload=n=>{let i=n.target;if(!i)return;let o=i.result,s=`good-custom-${Math.random().toString(36).slice(-6)}`,l=a(`good-icons`);if(e===`image`){let e=`<svg id="${s}" xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200"><image x="0" y="0" width="200" height="200" href="${o}"/></svg>`;l.insertAdjacentHTML(`beforeend`,e)}else{let e=r(o);if(!e)return void c(`The file should be prepared for load to FMG. If you don't know why it's happening, try to upload raster image`,!1,`error`);let t=l.appendChild(e);t.id=s,t.setAttribute(`width`,`200`),t.setAttribute(`height`,`200`)}t(e,s)},e===`image`?o.readAsDataURL(i):o.readAsText(i)}function x(e,t,n){let r,a;switch(e){case`cultureType`:r=u.map(e=>({id:e,name:e})),a=`Culture Type`;break;case`culture`:r=pack.cultures.filter(e=>e.i&&!e.removed).map(e=>({id:String(e.i),name:e.name,color:e.color})),a=`Culture`;break;case`state`:r=pack.states.filter(e=>e.i&&!e.removed).map(e=>({id:String(e.i),name:e.fullName||e.name,color:e.color})),a=`State`;break;case`religion`:r=pack.religions.filter(e=>e.i&&!e.removed).map(e=>({id:String(e.i),name:e.name,color:e.color})),a=`Religion`;break;case`biome`:r=pack.biomes.filter(e=>!e.removed).map(({i:e,name:t,color:n})=>({id:String(e),name:t,color:n})),a=`Biome`;break;case`zone`:r=pack.zones.map(e=>({id:String(e.i),name:e.name,color:e.color})),a=`Zone`;break}let o=r.map(e=>{let n=t[e.id]??1;return`${`<fill-box fill="${e.color||i()}" size="1em" disabled data-tip="${e.name}"></fill-box>`}<span>${e.name}</span><input type="number" class="mPopupInput" data-id="${e.id}" min="0" step="0.1" style="width:5em;" value="${n}" />`}),s=document.createElement(`div`);document.body.appendChild(s),s.innerHTML=`<div style="max-height:320px; overflow-y:auto; padding:.2em;">${o.length?`<div style="display:grid; grid-template-columns:auto 1fr 5em; gap:.3em .5em; align-items:center;">${o.join(``)}</div>`:`<div style="color:#777; font-style:italic;">No ${a.toLowerCase()}s available</div>`}</div>`,$(s).dialog({title:`${a} multipliers`,width:`22em`,resizable:!1,buttons:{Cancel:function(){$(this).dialog(`close`)},Apply:function(){let e=Array.from(s.querySelectorAll(`.mPopupInput`)),t={};for(let n of e){let e=n.dataset.id,r=Number(n.value);Number.isFinite(r)&&r>=0&&r!==1&&(t[e]=r)}n(t),$(this).dialog(`close`)}},close:()=>{$(s).dialog(`destroy`),s.remove()}})}function S(e,t){let n=m.map(t=>{let n=e[t]??0;return`<span>${d[t]} ${o(t)}</span><input type="number" class="dcPopupInput" data-cat="${t}" min="0" step="0.05" style="width:5em;" value="${n}" />`}).join(``),r=document.createElement(`div`);document.body.appendChild(r),r.innerHTML=`<div style="display:grid;grid-template-columns:1fr 5em;gap:.3em .5em;align-items:center;padding:.2em;">${n}</div>`,$(r).dialog({title:`Demand Coverage`,width:`18em`,resizable:!1,buttons:{Cancel:function(){$(this).dialog(`close`)},Apply:function(){let e={};r.querySelectorAll(`.dcPopupInput`).forEach(t=>{let n=t.dataset.cat,r=Number(t.value);Number.isFinite(r)&&r>0&&(e[n]=r)}),t(e),$(this).dialog(`close`)}},close:()=>{$(r).dialog(`destroy`),r.remove()}})}function C(e,t){let n=pack.biomes.filter(e=>!e.removed).map(({i:t,name:n})=>`<span>${n}</span><input type="number" class="bpPopupInput" data-id="${t}" min="0" step="0.01" style="width:5em;" value="${e[t]??0}" />`).join(``),r=document.createElement(`div`);document.body.appendChild(r),r.innerHTML=`<div style="max-height:320px;overflow-y:auto;padding:.2em;"><div style="display:grid;grid-template-columns:1fr 5em;gap:.3em .5em;align-items:center;">${n}</div></div>`,$(r).dialog({title:`Biome Baseline Production`,width:`22em`,resizable:!1,buttons:{Cancel:function(){$(this).dialog(`close`)},Apply:function(){let e={};r.querySelectorAll(`.bpPopupInput`).forEach(t=>{let n=Number(t.dataset.id),r=Number(t.value);Number.isFinite(r)&&r>0&&(e[n]=r)}),t(e),$(this).dialog(`close`)}},close:()=>{$(r).dialog(`destroy`),r.remove()}})}var w={open:_};export{w as GoodEditor};