import{j as e}from"./utils-Cob8vHf9.js";import{t}from"./pins-D6mEpUZC.js";import{lt as n,pt as r,st as i}from"./index-DsIn6sTp.js";var a=`loreEditor`,o=`
  <style>
    #${a} .le { display: grid; grid-template-columns: 1em 5.6em minmax(0, 1fr) 1.2em; gap: .3em; align-items: center; width: 23em; }
    #${a} .le > label[for="loreDescription"] { align-self: start; padding-top: .35em; }
    #${a} .le-era { display: flex; align-items: center; gap: .4em; min-width: 0; }
    #${a} .le-era > input:first-child { flex: 1; min-width: 0; }
    #${a} .le-era > input:last-child { flex: 0 0 3.4em; }
    #${a} input, #${a} textarea { width: 100%; box-sizing: border-box; font: inherit; }
    #${a} textarea { resize: vertical; }
    #${a} .le > i { cursor: pointer; justify-self: center; }
    #${a} .le > i[data-locked] { font-size: .8em; color: #626573; }
  </style>

  <div class="le">
    <i data-locked="0" id="lock_mapName" class="icon-lock-open"></i>
    <label for="loreMapName">Map name:</label>
    <input
      id="loreMapName"
      data-tip="Name of the map. Used to name the files it is downloaded as"
      autocorrect="off"
      spellcheck="false"
      type="text"
    />
    <i data-tip="Generate a new map name" id="loreMapNameRegenerate" class="icon-arrows-cw"></i>

    <i data-locked="0" id="lock_year" class="icon-lock-open"></i>
    <label for="loreYear">Year:</label>
    <input
      id="loreYear"
      data-tip="Current year. Dates state history and battle reports"
      type="number"
      step="1"
    />
    <span></span>

    <i data-locked="0" id="lock_era" data-ids="era,eraShort" class="icon-lock-open"></i>
    <label for="loreEra">Era:</label>
    <span class="le-era" data-tip="Name of the era the current year belongs to, and its abbreviation">
      <input id="loreEra" autocorrect="off" spellcheck="false" type="text" placeholder="Winter Era" />
      <input id="loreEraShort" autocorrect="off" spellcheck="false" type="text" placeholder="WE" />
    </span>
    <i data-tip="Generate a new era" id="loreEraRegenerate" class="icon-arrows-cw"></i>

    <span></span>
    <label for="loreDescription">Description:</label>
    <textarea
      id="loreDescription"
      rows="5"
      data-tip="Your own description of this world. Free text, carried in the map file"
      placeholder="Describe the map, its age, its peoples – whatever the map should carry with it."
    ></textarea>
    <span></span>
  </div>
`;function s(){i(`#loreEditor, .stable`),c(),$(`#${a}`).dialog({title:`Setup Lore`,width:`auto`,minWidth:340,position:{my:`right top`,at:`right-10 top+10`,of:`svg`,collision:`fit`},close:()=>n(a)})}function c(){n(a),e(`dialogs`).insertAdjacentHTML(`beforeend`,`<div id="${a}" class="dialog stable">${o}</div>`),u(),d(),t.bindIcons(e(a),l)}function l(e){let{name:t,calendar:n}=options.map.lore;if(e===`mapName`)return t;if(e===`year`)return n.year;if(e===`era`)return n.era;if(e===`eraShort`)return n.eraShort}function u(){let{name:t,description:n,calendar:r}=options.map.lore;e(`loreMapName`).value=t,e(`loreYear`).value=String(r.year),e(`loreEra`).value=r.era,e(`loreEraShort`).value=r.eraShort,e(`loreDescription`).value=n}function d(){e(a).addEventListener(`change`,f),e(`loreMapNameRegenerate`).addEventListener(`click`,p),e(`loreEraRegenerate`).addEventListener(`click`,m)}function f(n){let i=n.target,a=i.value,{lore:o}=options.map;switch(i.id){case`loreMapName`:o.name=a,t.set(`mapName`,a);break;case`loreYear`:if(!a||Number.isNaN(+a))return;o.calendar.year=+a,t.set(`year`,+a);break;case`loreEra`:if(!a)return;o.calendar.era=a,o.calendar.eraShort=r.getEraShort(a),t.set(`era`,a),t.set(`eraShort`,o.calendar.eraShort),e(`loreEraShort`).value=o.calendar.eraShort;break;case`loreEraShort`:if(!a)return;o.calendar.eraShort=a,t.set(`eraShort`,a);break;case`loreDescription`:o.description=a;break;default:return}Options.save()}function p(){t.clear(`mapName`),options.map.lore.name=r.getMapName(),Options.save(),u()}function m(){t.clear(`era`),t.clear(`eraShort`);let{calendar:e}=options.map.lore;e.era=r.getEra(),e.eraShort=r.getEraShort(e.era),Options.save(),u()}var h={open:s};export{h as LoreEditor};