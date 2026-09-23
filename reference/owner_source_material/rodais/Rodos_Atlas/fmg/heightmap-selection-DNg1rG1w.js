import{Ct as e,j as t}from"./utils-Cob8vHf9.js";import{G as n}from"./layers-Bh4OWBXX.js";import{o as r,t as i}from"./pins-D6mEpUZC.js";import{Ct as a,P as o,at as s,ct as c,st as l}from"./index-DsIn6sTp.js";var u=e(),d=x(),f=S();h(),g(),_();function p(){l(`.stable`),y(options.generation.template),d=x(),f=S(),t(`heightmapSelection`).style.setProperty(`--preview-aspect-ratio`,`${d.width}/${d.height}`),E(),$(`#heightmapSelection`).dialog({title:`Select Heightmap`,resizable:!1,position:{my:`center`,at:`center`,of:`svg`},close:m,buttons:{Cancel:function(){$(this).dialog(`close`)},Select:function(){let e=v();e&&(Options.set(t=>t.generation.template=e),o(),i.set(`template`,options.generation.template),$(this).dialog(`close`))},"New Map":function(){let e=v();if(!e)return;Options.set(t=>t.generation.template=e),o(),i.set(`template`,options.generation.template);let t=b(),n=f,r=d;n&&r&&regeneratePrompt({seed:t,graph:n,...r}),$(this).dialog(`close`)}}})}function m(){f=null,d=null,HeightmapGenerator.clearData()}function h(){let e=document.createElement(`style`);e.textContent=`
    div.dialog > div.heightmap-selection {
      width: 70vw;
      height: 70vh;
    }

    .heightmap-selection_container {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
      grid-gap: 6px;
    }

    @media (max-width: 600px) {
      .heightmap-selection_container {
        grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
        grid-gap: 4px;
      }
    }

    @media (min-width: 2000px) {
      .heightmap-selection_container {
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        grid-gap: 8px;
      }
    }

    .heightmap-selection_options {
      display: grid;
      grid-template-columns: 2fr 1fr;
    }

    .heightmap-selection_options > div:first-child {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      align-items: center;
      justify-self: start;
      justify-items: start;
    }

    @media (max-width: 600px) {
      .heightmap-selection_options {
        grid-template-columns: 3fr 1fr;
      }

      .heightmap-selection_options > div:first-child {
        display: block;
      }
    }

    .heightmap-selection_options > div:last-child {
      justify-self: end;
    }

    .heightmap-selection article {
      padding: 4px;
      border-radius: 8px;
      transition: all 0.1s ease-in-out;
      filter: drop-shadow(1px 1px 4px #999);
    }

    .heightmap-selection article:hover {
      background-color: #ddd;
      filter: drop-shadow(1px 1px 8px #999);
      cursor: pointer;
    }

    .heightmap-selection article.selected {
      background-color: #ccc;
      outline: 1px solid var(--dark-solid);
      filter: drop-shadow(1px 1px 8px #999);
    }

    .heightmap-selection article > div {
      display: flex;
      justify-content: space-between;
      padding: 2px 1px;
    }

    .heightmap-selection article > img {
      width: 100%;
      aspect-ratio: var(--preview-aspect-ratio);
      border-radius: 8px;
      object-fit: fill;
    }

    .heightmap-selection article .regeneratePreview {
      outline: 1px solid #bbb;
      padding: 1px 3px;
      border-radius: 4px;
      transition: all 0.1s ease-in-out;
    }

    .heightmap-selection article .regeneratePreview:hover {
      outline: 1px solid #666;
    }

    .heightmap-selection article .regeneratePreview:active {
      outline: 1px solid #333;
      color: #000;
      transform: rotate(45deg);
    }
  `,document.head.appendChild(e)}function g(){let e=f,n=d;if(!e||!n)return;let r=`<div id="heightmapSelection" class="dialog stable">
    <div class="heightmap-selection">
      <section data-tip="Select heightmap template – template provides unique, but similar-looking maps on generation">
        <header><h1>Heightmap templates</h1></header>
        <div class="heightmap-selection_container"></div>
      </section>
      <section data-tip="Select precreated heightmap – it will be the same for each map">
        <header><h1>Precreated heightmaps</h1></header>
        <div class="heightmap-selection_container"></div>
      </section>
      <section>
        <header><h1>Options</h1></header>
        <div class="heightmap-selection_options">
          <div>
            <label data-tip="Rerender all preview images" class="checkbox-label" id="heightmapSelectionRedrawPreview">
              <i class="icon-cw"></i>
              Redraw preview
            </label>
            <div>
              <input id="heightmapSelectionRenderOcean" class="checkbox" type="checkbox" />
              <label data-tip="Draw heights of water cells" for="heightmapSelectionRenderOcean" class="checkbox-label">Render ocean heights</label>
            </div>
            <div data-tip="Color scheme used for heightmap preview">
              Color scheme
              <select id="heightmapSelectionColorScheme">${Object.keys(heightmapColorSchemes).map(e=>`<option value="${e}">${e}</option>`).join(``)}</select>
            </div>
          </div>
          <div>
            <button data-tip="Open Template Editor" data-tool="templateEditor" id="heightmapSelectionEditTemplates">Edit Templates</button>
            <button data-tip="Open Image Converter" data-tool="imageConverter" id="heightmapSelectionImportHeightmap">Import Heightmap</button>
          </div>
        </div>
      </section>
    </div>
  </div>`;t(`dialogs`).insertAdjacentHTML(`beforeend`,r);let i=document.getElementsByClassName(`heightmap-selection_container`);i[0].innerHTML=Object.keys(a).map(t=>{let r=a[t].name;return Math.random=aleaPRNG(u),`<article data-id="${t}" data-seed="${u}">
        <img src="${O(HeightmapGenerator.fromTemplate(e,t,n))}" alt="${r}" />
        <div>
          ${r}
          <span data-tip="Regenerate preview" class="icon-cw regeneratePreview"></span>
        </div>
      </article>`}).join(``),i[1].innerHTML=Object.keys(s).map(e=>{let t=s[e].name;return w(e),`<article data-id="${e}" data-seed="${u}">
        <img alt="${t}" />
        <div>${t}</div>
      </article>`}).join(``)}function _(){t(`heightmapSelection`).addEventListener(`click`,e=>{let t=e.target,n=t.closest(`#heightmapSelection article`);if(!n)return;let r=n.dataset.id;r&&(t.matches(`span.icon-cw`)&&T(n,r),y(r))}),t(`heightmapSelectionRenderOcean`).addEventListener(`change`,E),t(`heightmapSelectionColorScheme`).addEventListener(`change`,E),t(`heightmapSelectionRedrawPreview`).addEventListener(`click`,E),t(`heightmapSelectionEditTemplates`).addEventListener(`click`,e=>D(e.currentTarget)),t(`heightmapSelectionImportHeightmap`).addEventListener(`click`,e=>D(e.currentTarget))}function v(){return t(`heightmapSelection`).querySelector(`.selected`)?.dataset?.id}function y(e){let n=t(`heightmapSelection`);n.querySelector(`.selected`)?.classList?.remove(`selected`),n.querySelector(`[data-id="${e}"]`)?.classList?.add(`selected`)}function b(){return t(`heightmapSelection`).querySelector(`.selected`)?.dataset?.seed}function x(){let{width:e,height:t,density:n}=options.generation.graph;return{width:e,height:t,points:r(n)}}function S(){let{width:e,height:t,points:n}=d??x(),r=options.map.graph;if(r.width!==e||r.height!==t||r.points!==n)return Grid.generate(u,e,t,n);let i=structuredClone(grid);return Grid.resetHeights(i),i}function C(e){let n=f,r=d;if(!n||!r)return;let i=O(HeightmapGenerator.fromTemplate(n,e,r));t(`heightmapSelection`).querySelector(`[data-id="${e}"]`)?.querySelector(`img`)?.setAttribute(`src`,i)}async function w(e){let n=f,r=d;if(!n||!r)return;let i=await HeightmapGenerator.fromPrecreated(n,e,r);if(n!==f)return;let a=O(i);t(`heightmapSelection`).querySelector(`[data-id="${e}"]`)?.querySelector(`img`)?.setAttribute(`src`,a)}function T(t,n){if(!f)return;Grid.resetHeights(f);let r=e();t.dataset.seed=r,Math.random=aleaPRNG(r),C(n)}function E(){if(!f)return;Grid.resetHeights(f);let e=t(`heightmapSelection`).querySelectorAll(`article`);for(let t of e){let{id:e,seed:n}=t.dataset;!e||!n||(Math.random=aleaPRNG(n),e in a?C(e):w(e))}}function D(e){let t=e.dataset.tool;t&&c({title:e.dataset.tip??``,message:`Opening the tool will erase the current map. Are you sure you want to proceed?`,confirm:`Continue`,onConfirm:()=>window.Controllers.HeightmapEditor.open({mode:`erase`,tool:t})})}function O(e){if(!f)return``;let r=getColorScheme(t(`heightmapSelectionColorScheme`).value),i=t(`heightmapSelectionRenderOcean`).checked;return n({heights:e,width:f.cellsX,height:f.cellsY,scheme:r,renderOcean:i})}var k={open:p};export{k as HeightmapSelection};