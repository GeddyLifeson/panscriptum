import{Bn as e,Et as t,F as n,P as r,R as i,Tt as a,_ as o,a as s,dt as c,hn as l,j as u,k as d,nt as f,o as p,pt as m,r as h,ut as g,vt as _,xn as v,z as y}from"./utils-Cob8vHf9.js";import{I as b,J as x,K as S,P as C,R as ee,Z as te,i as w,q as ne,r as re,t as T}from"./layers-Bh4OWBXX.js";import{i as E,n as ie}from"./highlight-Qtqc1_QO.js";import{t as ae}from"./stratify-CGdiYggi.js";import{t as oe}from"./pack-CyBKcrr4.js";import{i as D,t as se}from"./tooltips-BTSHGd98.js";import{t as O}from"./controllers-DnVd8NhQ.js";import{t as k}from"./emblems-generator-C2sA4EpN.js";import{H as ce,V as le,ct as A,d as ue,dt as j,lt as M,st as de,u as fe}from"./index-DsIn6sTp.js";import{t as N}from"./highlighting-BxkDyRR_.js";import{a as pe,i as me,n as he,r as ge}from"./table-B6G2rlSI.js";import{t as _e}from"./annex-mode-DUkjuVOT.js";var P=`statesEditor`,F=`States`,I={my:`right top`,at:`right-10 top+10`,of:`svg`,collision:`fit`},L=[{key:`color`,width:`1.2em`,permanent:!0},{key:`name`,label:`State`,width:`7em`,permanent:!0,sortBy:e=>e.name||``,sortType:`alpha`},{key:`emblem`,width:`1.4em`},{key:`form`,label:`Form`,width:`8em`,mobileHidden:!0,sortBy:e=>e.i&&e.formName||``,sortType:`alpha`},{key:`capital`,label:`Capital`,width:`7em`,sortBy:e=>e.i&&pack.burgs[e.capital]?.name||``,sortType:`alpha`},{key:`culture`,label:`Culture`,width:`10em`,mobileHidden:!0,sortBy:e=>e.i&&pack.cultures[e.culture]?.name||``,sortType:`alpha`},{key:`burgs`,label:`Burgs`,width:`5em`,mobileHidden:!0,sortBy:e=>e.burgs||0},{key:`cells`,label:`Cells`,width:`5em`,hidden:!0,mobileHidden:!0,sortBy:e=>e.cells||0},{key:`area`,label:`Area`,width:`7em`,mobileHidden:!0,defaultSort:`desc`,sortBy:e=>s(e.area||0)},{key:`population`,label:`Population`,width:`6em`,sortBy:t=>e((t.rural||0)*options.map.units.population.scale+(t.urban||0)*options.map.units.population.scale*options.map.units.population.urbanization.rate)},{key:`treasury`,label:`Treasury`,width:`6em`,mobileHidden:!0,tip:`Click to sort by state treasury. Click on a value to view and edit taxes`,sortBy:e=>e.treasury||0},{key:`type`,label:`Type`,width:`5em`,hidden:!0,sortBy:e=>e.i&&e.type||``,sortType:`alpha`},{key:`expansionism`,label:`Expansion`,width:`5em`,hidden:!0,sortBy:e=>e.i&&e.expansionism||0},{key:`note`,width:`1.1em`},{key:`locate`,width:`1.1em`},{key:`focus`,width:`1.1em`},{key:`lock`,width:`1.1em`},{key:`remove`,width:`1.4em`,permanent:!0}],R=ge({getData:()=>ue(P,pack.states.filter(e=>!e.removed),L),onUpdate:be});function z(){customization||(de(`#${P}, .stable`),T.show(`states`,`borders`),T.hide(`cultures`,`biomes`,`religions`),ve(),States.collectStatistics(),R.reset(),$(`#${P}`).dialog({title:`States Editor`,resizable:!1,position:I,close:ye}))}function ve(){M(P);let e=`<div id="${P}" class="dialog stable editorDialog">
    <div id="statesBodySection" class="table" data-type="absolute">
      ${me({dialogId:P,columns:L})}
    </div>

    <div id="statesFooter" class="totalLine">
      <div data-tip="States number" style="margin-left: 5px">States:&nbsp;<span id="statesFooterStates">0</span></div>
      <div data-tip="Total burgs number" style="margin-left: 12px" data-col="burgs">Burgs:&nbsp;<span id="statesFooterBurgs">0</span></div>
      <div data-tip="Total land area" style="margin-left: 12px" data-col="area">Land Area:&nbsp;<span id="statesFooterArea">0</span></div>
      <div data-tip="Total population" style="margin-left: 12px" data-col="population">Population:&nbsp;<span id="statesFooterPopulation">0</span></div>
    </div>

    <div id="statesBottom" class="editorToolbar">
      <button id="statesEditorRefresh" data-tip="Refresh the Editor" class="icon-cw"></button>
      <button id="statesEditStyle" data-tip="Edit states style in Style Editor" class="icon-adjust"></button>
      <button id="statesLegend" data-tip="Toggle Legend box" class="icon-list-bullet"></button>
      <button id="statesPercentage" data-tip="Toggle percentage / absolute values views" class="icon-percent"></button>
      <button id="statesChart" data-tip="Show states bubble chart" class="icon-chart-area"></button>

      <button id="statesRegenerate" data-tip="Show the regeneration menu and more data" class="icon-cog-alt"></button>
      <div id="statesRegenerateButtons" style="display: none">
        <button id="statesRegenerateBack" data-tip="Hide the regeneration menu" class="icon-cog-alt"></button>
        <button id="statesRandomize" data-tip="Randomize states Expansion value and re-calculate states and provinces" class="icon-shuffle"></button>
        <button id="statesRecalculate" data-tip="Recalculate states based on current values of growth-related attributes" class="icon-retweet"></button>
        <div data-tip="Allow states neutral distance, expansion and type changes to take an immediate effect" style="display: inline-block">
          <input id="statesAutoChange" class="checkbox" type="checkbox" />
          <label for="statesAutoChange" class="checkbox-label"><i>auto-apply changes</i></label>
        </div>
        <div data-tip="Allow system to change state labels when states data is change" style="display: inline-block">
          <input id="adjustLabels" class="checkbox" type="checkbox" />
          <label for="adjustLabels" class="checkbox-label"><i>auto-change labels</i></label>
        </div>
      </div>

      <button id="statesManually" data-tip="Manually re-assign states" class="icon-brush"></button>

      <button id="statesAdd" data-tip="Add a new state. Hold Shift to add multiple" class="icon-plus"></button>
      <button id="statesMerge" data-tip="Merge several states into one" class="icon-layer-group"></button>
      <button id="statesAnnex" data-tip="Annex states: click the annexing state, then the states it absorbs. Hold Shift to keep annexing" class="icon-crown"></button>
      <button id="statesExport" data-tip="Save state-related data as a text file (.csv)" class="icon-download"></button>
    </div>
  </div>`;u(`dialogs`).insertAdjacentHTML(`beforeend`,e),fe(P,R.reset),N(P,({cellId:e})=>pack.cells.h[e]<20?void 0:pack.cells.state[e]),he({dialogId:P,columns:L,onUpdate:()=>j(P,{width:`fit-content`,position:I})}),u(`statesEditorRefresh`).addEventListener(`click`,B),u(`statesEditStyle`).addEventListener(`click`,()=>editStyle(`regions`)),u(`statesLegend`).addEventListener(`click`,Pe),u(`statesPercentage`).addEventListener(`click`,G),u(`statesChart`).addEventListener(`click`,K),u(`statesRegenerate`).addEventListener(`click`,Fe),u(`statesRegenerateBack`).addEventListener(`click`,Le),u(`statesRecalculate`).addEventListener(`click`,()=>q(!0)),u(`statesRandomize`).addEventListener(`click`,Ie),u(`statesManually`).addEventListener(`click`,Re),u(`statesAdd`).addEventListener(`click`,Be),u(`statesMerge`).addEventListener(`click`,He),u(`statesAnnex`).addEventListener(`click`,Q.toggle),u(`statesExport`).addEventListener(`click`,Ge),u(`statesBodySection`).addEventListener(`click`,e=>{let t=e.target,n=t.classList,r=t.closest(`.states`);if(!r)return;let i=Number(r.dataset.id);t.tagName===`FILL-BOX`?xe(t):n.contains(`name`)?Se(i):n.contains(`coaIcon`)?O.EmblemsEditor.open(`state`,`stateCOA${i}`,pack.states[i]):n.contains(`icon-star-empty`)?De(i):n.contains(`icon-dot-circled`)?O.BurgsOverview.open({stateId:i}):n.contains(`statePopulation`)?Te(i):n.contains(`stateTreasury`)?Ee(i):n.contains(`icon-book`)?O.NotesEditor.open({type:`state`,id:i}):n.contains(`icon-pin`)?je(i,n):n.contains(`icon-target`)?ie(l(`#regions`).select(`#state${i}`).node(),4):n.contains(`icon-trash-empty`)?Me(i):(n.contains(`icon-lock`)||n.contains(`icon-lock-open`))&&Ke(i,n)}),u(`statesBodySection`).addEventListener(`change`,e=>{let t=e.target,n=t.classList,r=t.closest(`.states`);if(!r)return;let i=+r.dataset.id;n.contains(`stateCulture`)?Oe(i,r,t.value):n.contains(`cultureType`)?ke(i,r,t.value):n.contains(`statePower`)&&Ae(i,r,t.value)})}function ye(){customization===3&&Y(),Q.exit(),O.ColorPicker.close(),l(`#debug`).selectAll(`.highlight`).remove();let e=R.view();e.rows=[],e.all=[],M(P)}function B(){States.collectStatistics(),R.refresh()}function be(t){let n=p(),r=0,i=0,a=0;for(let n of t.all){r+=s(n.area||0);let t=(n.rural||0)*options.map.units.population.scale,o=(n.urban||0)*options.map.units.population.scale*options.map.units.population.urbanization.rate;i+=e(t+o),a+=n.burgs||0}let c=``;for(let r of t.rows){let t=s(r.area||0),i=(r.rural||0)*options.map.units.population.scale,a=(r.urban||0)*options.map.units.population.scale*options.map.units.population.urbanization.rate,u=e(i+a),d=`Total population: ${o(u)}; Rural population: ${o(i)}; Urban population: ${o(a)}. Click to change`,f=l(`#deftemp`).select(`#fog #focusState${r.i}`).size(),p=`Current treasury: 🟡 ${o(r.treasury)}. Sales Tax: ${e((r.salesTax||0)*100,1)}%. Poll Tax: ${e((r.pollTax||0)*100,1)}%. Click to view and edit taxes`;if(!r.i){c+=`<div
        class="states"
        data-id=${r.i}
        data-name="${r.name}"
        data-cells=${r.cells}
        data-area=${t}
        data-population=${u}
        data-burgs=${r.burgs}
        data-treasury="0"
        data-color=""
        data-form=""
        data-capital=""
        data-culture=""
        data-type=""
        data-expansionism=""
      >
        <svg width="1em" height="1em" class="placeholder" data-col="color"></svg>
        <input data-tip="Neutral lands name. Click to change" class="stateName name pointer italic" value="${r.name}" readonly data-col="name" />
        <svg class="coaIcon placeholder" viewBox="0 0 200 200" data-col="emblem"></svg>
        <input class="stateForm placeholder" value="none" data-col="form" />
        <div data-col="capital">
          <span class="icon-star-empty placeholder"></span>
          <div class="stateCapital placeholder"></div>
        </div>
        <select class="stateCulture placeholder" data-col="culture">${V(0)}</select>
        <div data-col="burgs">
          <span data-tip="Click to overview neutral burgs" class="icon-dot-circled pointer" style="padding-right: 1px"></span>
          <div data-tip="Burgs count" class="stateBurgs">${r.burgs}</div>
        </div>
        <div data-col="cells">
          <span data-tip="Cells count" class="icon-check-empty"></span>
          <div data-tip="Cells count" class="stateCells">${r.cells}</div>
        </div>
        <div data-col="area">
          <span data-tip="Neutral lands area" style="padding-right: 4px" class="icon-map-o"></span>
          <div data-tip="Neutral lands area" class="stateArea">${o(t)} ${n}</div>
        </div>
        <div data-col="population">
          <span data-tip="${d}" class="icon-male"></span>
          <div data-tip="${d}" class="statePopulation pointer">${o(u)}</div>
        </div>
        <div data-tip="Neutrals collect no taxes" class="stateTreasury placeholder" data-col="treasury"></div>
        <select class="cultureType placeholder" data-col="type">${H(0)}</select>
        <div data-col="expansionism">
          <span class="icon-resize-full placeholder"></span>
          <input class="statePower placeholder" type="number" value="0" />
        </div>
        <div data-col="note"></div>
        <div data-col="locate"></div>
        <div data-col="focus"></div>
        <div data-col="lock"></div>
        <div data-col="remove"></div>
      </div>`;continue}let m=pack.burgs[r.capital].name;te.trigger(`stateCOA${r.i}`,r.coa),c+=`<div
      class="states"
      data-id=${r.i}
      data-name="${r.name}"
      data-form="${r.formName}"
      data-capital="${m}"
      data-color="${r.color}"
      data-cells=${r.cells}
      data-area=${t}
      data-population=${u}
      data-burgs=${r.burgs}
      data-treasury="${r.treasury}"
      data-culture=${pack.cultures[r.culture].name}
      data-type=${r.type}
      data-expansionism=${r.expansionism}
    >
      <fill-box fill="${r.color}" data-col="color"></fill-box>
      <input data-tip="State name. Click to change" class="stateName name pointer" value="${r.name}" readonly data-col="name" />
      <svg data-tip="Click to show and edit state emblem" class="coaIcon pointer" viewBox="0 0 200 200" data-col="emblem"><use href="#stateCOA${r.i}"></use></svg>
      <input data-tip="State form name. Click to change" class="stateForm name pointer" value="${r.formName}" readonly data-col="form" />
      <div data-col="capital">
        <span data-tip="State capital. Click to zoom into view" class="icon-star-empty pointer"></span>
        <div data-tip="Capital name" class="stateCapital">${m}</div>
      </div>
      <select data-tip="Dominant culture. Click to change" class="stateCulture" data-col="culture">${V(r.culture)}</select>
      <div data-col="burgs">
        <span data-tip="Click to overview state burgs" style="padding-right: 1px" class="icon-dot-circled pointer"></span>
        <div data-tip="Burgs count" class="stateBurgs">${r.burgs}</div>
      </div>
      <div data-col="cells">
        <span data-tip="Cells count" class="icon-check-empty"></span>
        <div data-tip="Cells count" class="stateCells">${r.cells}</div>
      </div>
      <div data-col="area">
        <span data-tip="State area" style="padding-right: 4px" class="icon-map-o"></span>
        <div data-tip="State area" class="stateArea">${o(t)} ${n}</div>
      </div>
      <div data-col="population">
        <span data-tip="${d}" class="icon-male"></span>
        <div data-tip="${d}" class="statePopulation pointer">${o(u)}</div>
      </div>
      <div data-tip="${p}" class="stateTreasury pointer" data-col="treasury">🟡 ${o(r.treasury)}</div>
      <select data-tip="State type. Defines growth model. Click to change" class="cultureType" data-col="type">${H(r.type)}</select>
      <div data-col="expansionism">
        <span data-tip="State expansionism" class="icon-resize-full"></span>
        <input data-tip="Expansionism (defines competitive size). Change to re-calculate states based on new value"
          class="statePower" type="number" min="0" max="99" step=".1" value=${r.expansionism} />
      </div>
      ${ce.getIcon(`this state`)}
      <span data-col="locate" data-tip="Locate the state" class="icon-target"></span>
      <span data-col="focus" data-tip="Toggle state focus" class="icon-pin ${f?``:` inactive`}"></span>
      <span data-col="lock" data-tip="Lock the state to protect it from re-generation" class="icon-lock${r.lock?``:`-open`}"></span>
      <span data-col="remove" data-tip="Remove the state" class="icon-trash-empty"></span>
    </div>`}let d=u(`statesBodySection`);d.querySelectorAll(`:scope > .states`).forEach(e=>{e.remove()}),d.insertAdjacentHTML(`beforeend`,c),u(`statesFooterStates`).innerHTML=String(pack.states.filter(e=>e.i&&!e.removed).length),u(`statesFooterBurgs`).innerHTML=String(a),u(`statesFooterArea`).innerHTML=o(r)+n,u(`statesFooterArea`).dataset.area=String(r),u(`statesFooterPopulation`).innerHTML=o(i),u(`statesFooterPopulation`).dataset.population=String(i),pe(u(`statesFooter`),t,R.goto),u(`statesBodySection`).querySelectorAll(`:scope > .states`).forEach(e=>{e.addEventListener(`mouseenter`,U),e.addEventListener(`mouseleave`,W)}),u(`statesBodySection`).dataset.type===`percentage`&&(u(`statesBodySection`).dataset.type=`absolute`,G()),j(P,{width:`fit-content`,position:I})}function V(e){let t=``;return pack.cultures.forEach(n=>{n.removed||(t+=`<option ${n.i===e?`selected`:``} value="${n.i}">${n.name}</option>`)}),t}function H(e){let t=``;return[`Generic`,`River`,`Lake`,`Naval`,`Nomadic`,`Hunting`,`Highland`].forEach(n=>{t+=`<option ${e===n?`selected`:``} value="${n}">${n}</option>`}),t}function U(e){if(!T.isOn(`states`)||l(`#deftemp`).select(`#fog path`).size())return;let t=+e.target.dataset.id;customization||!t||E(l(`#regions`).select(`#state${t}`).attr(`d`))}function W(){l(`#debug`).selectAll(`.highlight`).each(function(){l(this).transition().duration(1e3).attr(`opacity`,0).remove()})}function xe(e){let t=e.getAttribute(`fill`)||`#ffffff`,n=+e.closest(`.states`).dataset.id;O.ColorPicker.open(t,t=>{e.fill=t,pack.states[n].color=t,T.draw(`states`),T.draw(`military`)})}function Se(e){Ce();let n=u(`stateNameEditorCustomForm`),r=u(`stateNameEditorSelectForm`);n.value=``,n.style.display===`inline-block`&&(n.style.display=`none`,r.style.display=`inline-block`);let i=pack.states[e];u(`stateNameEditor`).dataset.state=String(e),u(`stateNameEditorShort`).value=i.name||``,d(r,i.formName||``),u(`stateNameEditorFull`).value=i.fullName||``,$(`#stateNameEditor`).dialog({resizable:!1,title:`Change state name`,buttons:{Apply:function(){l(i),$(this).dialog(`close`)},Cancel:function(){$(this).dialog(`close`)}},position:{my:`center`,at:`center`,of:`svg`},close:we}),u(`stateNameEditorShortCulture`).addEventListener(`click`,a),u(`stateNameEditorShortRandom`).addEventListener(`click`,o),u(`stateNameEditorShortSpeak`).addEventListener(`click`,()=>f(u(`stateNameEditorShort`).value)),u(`stateNameEditorAddForm`).addEventListener(`click`,s),u(`stateNameEditorCustomForm`).addEventListener(`change`,s),u(`stateNameEditorFullRegenerate`).addEventListener(`click`,c),u(`stateNameEditorFullSpeak`).addEventListener(`click`,()=>f(u(`stateNameEditorFull`).value));function a(){let e=+u(`stateNameEditor`).dataset.state,t=pack.states[e].culture,n=Names.getState(Names.getCultureShort(t),t);u(`stateNameEditorShort`).value=n}function o(){let e=t(Names.nameBases.length-1),n=Names.getState(Names.getBase(e),void 0,e);u(`stateNameEditorShort`).value=n}function s(){let e=n.value,t=n.style.display===`inline-block`;n.style.display=t?`none`:`inline-block`,r.style.display=t?`inline-block`:`none`,e&&t&&d(r,e),n.value=``}function c(){let e=u(`stateNameEditorShort`).value,t=u(`stateNameEditorSelectForm`).value;u(`stateNameEditorFull`).value=n();function n(){if(!t)return e;if(!e&&t)return`The ${t}`;let n=u(`stateNameEditorFullRegenerate`),r=+n.dataset.tick;return n.dataset.tick=String(r+1),r%2?`${m(e)} ${t}`:`${t} of ${e}`}}function l(e){let t=u(`stateNameEditorShort`),n=u(`stateNameEditorSelectForm`),r=u(`stateNameEditorFull`),i=t.value!==e.name,a=n.value!==e.formName,o=r.value!==e.fullName,s=i||a||o;if(a){let t=n.selectedOptions[0].parentElement?.getAttribute(`label`)||null;t&&(e.form=t)}e.name=t.value,e.formName=n.value,e.fullName=r.value,s&&u(`stateNameEditorUpdateLabel`).checked&&(e.label?.text&&delete e.label.text,T.draw(`labels`)),B()}}function Ce(){M(`stateNameEditor`),u(`dialogs`).insertAdjacentHTML(`beforeend`,`<div id="stateNameEditor" class="dialog" data-state="0">
      <div>
        <div data-tip="State short name" class="label">Short name:</div>
        <input
          id="stateNameEditorShort"
          data-tip="Type to change the short name"
          autocorrect="off"
          spellcheck="false"
          style="width: 11em"
        />
        <span id="stateNameEditorShortSpeak" data-tip="Speak the name. You can change voice and language in options" class="speaker">🔊</span>
        <span
          id="stateNameEditorShortCulture"
          data-tip="Generate culture-specific name"
          class="icon-book pointer"
        ></span>
        <span id="stateNameEditorShortRandom" data-tip="Generate random name" class="icon-globe pointer"></span>
      </div>
      <div data-tip="Select form name">
        <div data-tip="State form name" class="label">Form name:</div>
        <select id="stateNameEditorSelectForm" style="width: 11em">
          <option value="">blank</option>
          <optgroup label="Monarchy">
            <option value="Beylik">Beylik</option>
            <option value="Despotate">Despotate</option>
            <option value="Dominion">Dominion</option>
            <option value="Duchy">Duchy</option>
            <option value="Emirate">Emirate</option>
            <option value="Empire">Empire</option>
            <option value="Horde">Horde</option>
            <option value="Grand Duchy">Grand Duchy</option>
            <option value="Heptarchy">Heptarchy</option>
            <option value="Khaganate">Khaganate</option>
            <option value="Khanate">Khanate</option>
            <option value="Kingdom">Kingdom</option>
            <option value="Marches">Marches</option>
            <option value="Principality">Principality</option>
            <option value="Satrapy">Satrapy</option>
            <option value="Shogunate">Shogunate</option>
            <option value="Sultanate">Sultanate</option>
            <option value="Tsardom">Tsardom</option>
            <option value="Ulus">Ulus</option>
            <option value="Viceroyalty">Viceroyalty</option>
          </optgroup>
          <optgroup label="Republic">
            <option value="Chancellery">Chancellery</option>
            <option value="City-state">City-state</option>
            <option value="Diarchy">Diarchy</option>
            <option value="Federation">Federation</option>
            <option value="Free City">Free City</option>
            <option value="Most Serene Republic">Most Serene Republic</option>
            <option value="Oligarchy">Oligarchy</option>
            <option value="Protectorate">Protectorate</option>
            <option value="Republic">Republic</option>
            <option value="Tetrarchy">Tetrarchy</option>
            <option value="Trade Company">Trade Company</option>
            <option value="Triumvirate">Triumvirate</option>
          </optgroup>
          <optgroup label="Union">
            <option value="Confederacy">Confederacy</option>
            <option value="Confederation">Confederation</option>
            <option value="Conglomerate">Conglomerate</option>
            <option value="Commonwealth">Commonwealth</option>
            <option value="League">League</option>
            <option value="Union">Union</option>
            <option value="United Hordes">United Hordes</option>
            <option value="United Kingdom">United Kingdom</option>
            <option value="United Provinces">United Provinces</option>
            <option value="United Republic">United Republic</option>
            <option value="United States">United States</option>
            <option value="United Tribes">United Tribes</option>
          </optgroup>
          <optgroup label="Theocracy">
            <option value="Bishopric">Bishopric</option>
            <option value="Brotherhood">Brotherhood</option>
            <option value="Caliphate">Caliphate</option>
            <option value="Diocese">Diocese</option>
            <option value="Divine Duchy">Divine Duchy</option>
            <option value="Divine Grand Duchy">Divine Grand Duchy</option>
            <option value="Divine Principality">Divine Principality</option>
            <option value="Divine Kingdom">Divine Kingdom</option>
            <option value="Divine Empire">Divine Empire</option>
            <option value="Eparchy">Eparchy</option>
            <option value="Exarchate">Exarchate</option>
            <option value="Holy State">Holy State</option>
            <option value="Imamah">Imamah</option>
            <option value="Patriarchate">Patriarchate</option>
            <option value="Theocracy">Theocracy</option>
          </optgroup>
          <optgroup label="Anarchy">
            <option value="Commune">Commune</option>
            <option value="Community">Community</option>
            <option value="Council">Council</option>
            <option value="Free Territory">Free Territory</option>
            <option value="Tribes">Tribes</option>
          </optgroup>
        </select>
        <input
          id="stateNameEditorCustomForm"
          placeholder="type form name"
          data-tip="Enter custom form name"
          style="display: none; width: 11em"
        />
        <span
          id="stateNameEditorAddForm"
          data-tip="Click to add custom state form name to the list"
          class="icon-plus pointer"
        ></span>
      </div>
      <div>
        <div data-tip="State full name" class="label">Full name:</div>
        <input
          id="stateNameEditorFull"
          data-tip="Type to change the full name"
          autocorrect="off"
          spellcheck="false"
          style="width: 11em"
        />
        <span id="stateNameEditorFullSpeak" data-tip="Speak the name. You can change voice and language in options" class="speaker">🔊</span>
        <span
          id="stateNameEditorFullRegenerate"
          data-tip="Click to re-generate full name"
          data-tick="0"
          class="icon-arrows-cw pointer"
        ></span>
      </div>
      <div data-tip="Uncheck to not update state label on name change" style="padding-block: 0.2em">
        <input id="stateNameEditorUpdateLabel" class="checkbox" type="checkbox" checked />
        <label for="stateNameEditorUpdateLabel" class="checkbox-label"><i>Update label on Apply</i></label>
      </div>
    </div>`)}function we(){$(`#stateNameEditor`).dialog(`destroy`),u(`stateNameEditor`).remove()}function Te(t){let n=pack.states[t];if(!n.cells){D(`State does not have any cells, cannot change population`,!1,`error`);return}let r=e((n.rural||0)*options.map.units.population.scale),i=e((n.urban||0)*options.map.units.population.scale*options.map.units.population.urbanization.rate),a=r+i,o=e=>Number(e).toLocaleString();alertMessage.innerHTML=`<div>
    <i>Change population of all cells assigned to the state</i>
    <div style="margin: 0.5em 0">
      Rural: <input type="number" min="0" step="1" id="ruralPop" value=${r} style="width:6em" />
      Urban: <input type="number" min="0" step="1" id="urbanPop" value=${i} style="width:6em" />
    </div>
    <div>Total population: ${o(a)} ⇒ <span id="totalPop">${o(a)}</span>
      (<span id="totalPopPerc">100</span>%)
    </div>
  </div>`;let s=u(`ruralPop`),c=u(`urbanPop`),l=u(`totalPop`),d=u(`totalPopPerc`),f=()=>{let t=s.valueAsNumber+c.valueAsNumber;Number.isNaN(t)||(l.innerHTML=o(t),d.innerHTML=String(e(t/a*100)))};s.oninput=()=>f(),c.oninput=()=>f(),$(`#alert`).dialog({resizable:!1,title:`Change state population`,width:`24em`,buttons:{Apply:function(){p(),$(this).dialog(`close`)},Cancel:function(){$(this).dialog(`close`)}},position:{my:`center`,at:`center`,of:`svg`}});function p(){let n=+s.value/r;if(Number.isFinite(n)&&n!==1&&pack.cells.i.filter(e=>pack.cells.state[e]===t).forEach(e=>{pack.cells.pop[e]*=n}),!Number.isFinite(n)&&+s.value>0){let e=+s.value/options.map.units.population.scale,n=pack.cells.i.filter(e=>pack.cells.state[e]===t),r=e/n.length;n.forEach(e=>{pack.cells.pop[e]=r})}let a=+c.value/i;if(Number.isFinite(a)&&a!==1&&pack.burgs.filter(e=>!e.removed&&e.state===t).forEach(t=>{t.population=e((t.population||0)*a,4)}),!Number.isFinite(a)&&+c.value>0){let n=+c.value/options.map.units.population.scale/options.map.units.population.urbanization.rate,r=pack.burgs.filter(e=>!e.removed&&e.state===t),i=e(n/r.length,4);r.forEach(e=>{e.population=i})}T.draw(`population`),B()}}function Ee(t){let n=pack.states[t];if(!t||!n||n.removed)return;let r=e(n.pollTax*((n.rural||0)+(n.urban||0)),2),i=pack.deals.reduce((e,n)=>{if(!n.tax)return e;let r=0;if(n.sellerType===`burg`)r=pack.burgs[n.seller]?.state||0;else if(n.sellerType===`market`){let e=Markets.get(n.seller)?.centerBurgId;r=e&&pack.burgs[e]?.state||0}return r===t?e+n.tax:e},0);alertMessage.innerHTML=`<div data-tip="Sales tax is applied to deals with a seller from the state. Poll tax is applied to all population of the state. Tax changes take effect on Production regeneration" style="margin: 0.6em 0; display: grid; grid-template-columns: 7em auto auto; row-gap: 0.4em; align-items: center">
      <label for="stateSalesTaxInput">Sales Tax:</label>
      <input id="stateSalesTaxInput" type="number" min="0" max="1" step="0.01" value="${n.salesTax}" style="width: 6em"/> = ${h(i)}
      <label for="statePollTaxInput">Poll Tax:</label>
      <input id="statePollTaxInput" type="number" min="0" max="10" step="0.01" value="${n.pollTax}" style="width: 6em"/> = ${h(r)}
      <label for="stateTreasuryInput">Treasury:</label>
      <input id="stateTreasuryInput" type="number" step="1" value="${n.treasury}" style="width: 6em" />
    </div>`,$(`#alert`).dialog({resizable:!1,title:`Taxes and Treasury: ${n.name}`,width:`26em`,buttons:{Apply:function(){let t=u(`stateSalesTaxInput`),r=u(`statePollTaxInput`),i=u(`stateTreasuryInput`),a=Math.max(0,Math.min(1,+t.value)),o=Math.max(0,+r.value),s=+i.value;Number.isFinite(a)&&(n.salesTax=e(a,4)),Number.isFinite(o)&&(n.pollTax=e(o,4)),Number.isFinite(s)&&(n.treasury=e(s,2)),B(),$(this).dialog(`close`)},Cancel:function(){$(this).dialog(`close`)}},position:{my:`center`,at:`center`,of:`svg`}})}function De(e){let t=pack.states[e].capital,{x:n,y:r}=pack.burgs[t];zoomTo(n,r,8,2e3)}function Oe(e,t,n){pack.states[e].culture=+n,t.dataset.base=String(+n)}function ke(e,t,n){pack.states[e].type=n,t.dataset.type=n,q()}function Ae(e,t,n){pack.states[e].expansionism=Number(n),t.dataset.expansionism=n,q()}function je(e,t){if(customization)return;let n=l(`#statesBody`).select(`#state${e}`).attr(`d`),r=`focusState${e}`;t.contains(`inactive`)?re(r,n):w(r),t.toggle(`inactive`)}function Me(e){customization||A({title:`Remove state`,message:`Are you sure you want to remove the state? <br>This action cannot be reverted`,confirm:`Remove`,onConfirm:()=>Ne(e)})}function Ne(e){w(`focusState${e}`),pack.burgs.forEach(t=>{t.state===e&&(t.state=0,t.capital&&(t.capital=0,Burgs.changeGroup(t,null)))}),pack.cells.state.forEach((t,n)=>{t===e&&(pack.cells.state[n]=0)}),x(`state`,e),(pack.states[e].provinces||[]).forEach(e=>{pack.provinces[e]={i:e,removed:!0},pack.cells.province.forEach((t,n)=>{t===e&&(pack.cells.province[n]=0)}),x(`province`,e)}),pack.states.forEach(t=>{!t.i||t.removed||!t.neighbors||(t.neighbors=t.neighbors.filter(t=>t!==e))}),delete pack.states[e].label,pack.states[e]={i:e,removed:!0},l(`#debug`).selectAll(`.highlight`).remove(),T.draw(`burgIcons`,`labels`,`military`,`borders`,`provinces`,`states`),B()}function Pe(){if(ee(F)){C(F);return}let e=pack.states.filter(e=>e.i&&!e.removed&&e.cells).sort((e,t)=>(t.area??0)-(e.area??0)).map(e=>[e.i,e.color,e.name]);if(!e.length)return void D(`No states to show`,!1,`error`);b(F,e)}function G(){if(u(`statesBodySection`).dataset.type===`absolute`){u(`statesBodySection`).dataset.type=`percentage`;let t=+u(`statesFooterBurgs`).innerText,n=+u(`statesFooterArea`).dataset.area,r=+u(`statesFooterPopulation`).dataset.population,i=pack.states.reduce((e,t)=>e+(t.treasury||0),0),a=pack.states.reduce((e,t)=>e+(t.i&&!t.removed&&t.cells||0),0);u(`statesBodySection`).querySelectorAll(`:scope > .states`).forEach(o=>{let{burgs:s,area:c,population:l,treasury:u,cells:d}=o.dataset;o.querySelector(`.stateBurgs`).innerText=`${e(+s/t*100)}%`,o.querySelector(`.stateCells`).innerText=`${e(+d/a*100)}%`,o.querySelector(`.stateArea`).innerText=`${e(+c/n*100)}%`,o.querySelector(`.statePopulation`).innerText=`${e(+l/r*100)}%`,o.querySelector(`.stateTreasury`).innerText=`${e(+u/i*100,2)}%`})}else u(`statesBodySection`).dataset.type=`absolute`,R.refresh()}function K(){let t=pack.states.filter(e=>!e.removed);if(t.length<2){D(`There are no states to show`,!1,`error`);return}let n=ae().id(e=>String(e.i)).parentId(e=>e.i?`0`:null)(t).sum(e=>e.area).sort((e,t)=>t.value-e.value),r=150+200*u(`uiSize`).valueAsNumber,i={top:0,right:-50,bottom:0,left:-50},a=r-i.left-i.right,c=r-i.top-i.bottom,d=oe().size([a,c]).padding(3);alertMessage.innerHTML=`<select id="statesTreeType" style="display:block; margin-left:13px; font-size:11px">
    <option value="area" selected>Area</option>
    <option value="population">Total population</option>
    <option value="rural">Rural population</option>
    <option value="urban">Urban population</option>
    <option value="burgs">Burgs number</option>
  </select>`,alertMessage.innerHTML+=`<div id='statesInfo' class='chartInfo'>&#8205;</div>`;let f=l(`#alertMessage`).insert(`svg`,`#statesInfo`).attr(`id`,`statesTree`).attr(`width`,r).attr(`height`,r).style(`font-family`,`Almendra SC`).attr(`text-anchor`,`middle`).attr(`dominant-baseline`,`central`).append(`g`).attr(`transform`,`translate(-50, 0)`);u(`statesTreeType`).addEventListener(`change`,b),d(n);let m=f.selectAll(`g`).data(n.leaves()).enter().append(`g`).attr(`transform`,e=>`translate(${e.x},${e.y})`).attr(`data-id`,e=>e.data.i).on(`mouseenter`,(e,t)=>_(e,t)).on(`mouseleave`,e=>y(e));m.append(`circle`).attr(`fill`,e=>e.data.color).attr(`r`,e=>e.r);let h=/(?=[A-Z][^A-Z])/g,g=e=>(v(e.split(h).map(e=>e.length))??0)+1;m.append(`text`).attr(`text-rendering`,`optimizeSpeed`).style(`font-size`,t=>`${e(t.r**.97*4/g(t.data.name),2)}px`).selectAll(`tspan`).data(e=>e.data.name.split(h)).join(`tspan`).attr(`x`,0).text(e=>e).attr(`dy`,(e,t,n)=>`${t?1:(n.length-1)/-2}em`);function _(t,n){l(t.target).select(`circle`).classed(`selected`,!0);let r=n.data.fullName,i=`${s(n.data.area)} ${p()}`,a=e(n.data.rural*options.map.units.population.scale),c=e(n.data.urban*options.map.units.population.scale*options.map.units.population.urbanization.rate),d=u(`statesTreeType`).value,f=d===`area`?`Area: ${i}`:d===`rural`?`Rural population: ${o(a)}`:d===`urban`?`Urban population: ${o(c)}`:d===`burgs`?`Burgs number: ${n.data.burgs}`:`Population: ${o(a+c)}`;u(`statesInfo`).innerHTML=`${r}. ${f}`,U(t)}function y(e){W(),document.getElementById(`statesInfo`)&&(u(`statesInfo`).innerHTML=`&#8205;`,l(e.target).select(`circle`).classed(`selected`,!1))}function b(){let t=this.value===`area`?e=>e.area:this.value===`rural`?e=>e.rural:this.value===`urban`?e=>e.urban:this.value===`burgs`?e=>e.burgs:e=>e.rural+e.urban;n.sum(t),m.data(d(n).leaves()),m.transition().duration(1500).attr(`transform`,e=>`translate(${e.x},${e.y})`),m.select(`circle`).transition().duration(1500).attr(`r`,e=>e.r),m.select(`text`).transition().duration(1500).style(`font-size`,t=>`${e(t.r**.97*4/g(t.data.name),2)}px`)}$(`#alert`).dialog({title:`States bubble chart`,width:`fit-content`,position:{my:`left bottom`,at:`left+10 bottom-10`,of:`svg`},buttons:{},close:()=>{alertMessage.innerHTML=``}})}function Fe(){u(`statesBottom`).querySelectorAll(`:scope > button`).forEach(e=>{e.style.display=`none`}),u(`statesRegenerateButtons`).style.display=`block`}function q(e){if(!(!e&&!u(`statesAutoChange`).checked)){if(States.expandStates(),Provinces.generate(),Provinces.getPoles(),States.getPoles(),T.draw(`states`,`borders`,`provinces`,`goods`,`emblems`),u(`adjustLabels`).checked){for(let e of pack.states)e.label&&(e.label.pathPoints=void 0);T.draw(`labels`)}B()}}function Ie(){pack.states.forEach(t=>{if(!t.i||t.removed)return;let n=e(Math.random()*4+1,1);t.expansionism=n,u(`statesBodySection`).querySelector(`div.states[data-id='${t.i}'] input.statePower`).value=String(n)}),q(!0)}function Le(){u(`statesBottom`).querySelectorAll(`:scope > button`).forEach(e=>{e.style.display=`inline-block`}),u(`statesRegenerateButtons`).style.display=`none`}function Re(){T.show(`states`);let e=u(`adjustLabels`).checked;O.PaintEditor.open({title:`Paint States`,parentDialogId:P,onClose:z,items:pack.states.filter(e=>!e.removed).map(e=>({id:e.i,name:e.name,color:e.color||`#ffffff`})),dontOverrideControl:!0,getValue:e=>pack.cells.state[e],filterCell:(e,t)=>n(e,pack)&&e!==pack.states[t].center,onApply:t=>ze(t,e)})}function ze(e,t){let{cells:n}=pack,r=[],i=[];for(let[t,a]of e)r.push(n.state[t],a),i.push(n.province[t]),n.state[t]=a,n.burg[t]&&(pack.burgs[n.burg[t]].state=a);if(r.length){if(States.getPoles(),J([...new Set(i)]),T.draw(`states`,`borders`,`provinces`),t){let e=[...new Set(r)];for(let t of e)pack.states[t].label&&delete pack.states[t].label;T.draw(`labels`)}document.getElementById(P)&&B()}}function J(e){let{cells:t,provinces:n,states:r,burgs:i}=pack,o=[];e.forEach(e=>{if(!n[e])return;let r=t.i.filter(n=>t.province[n]===e),i=[...new Set(r.map(e=>t.state[e]))];if(e&&i.length===1){s(e,i[0],r);return}c(e,i,r)}),ne(o.map(e=>[`province`,e]));function s(e,i,a){let o=n[e],s=r[o.state];s.provinces=s.provinces.filter(t=>t!==e),i?(o.state=i,r[i].provinces.push(e)):(n[e]={i:e,removed:!0},x(`province`,e),a.forEach(e=>{t.province[e]=0}))}function c(e,i,a){let o=n[e],s=r[o.state],c=t.state[o.center];i.forEach(i=>{let d=a.filter(e=>t.state[e]===i);if(i===c){if(i===s.i)return;if(!i){n[e]={i:e,removed:!0},x(`province`,e),d.forEach(e=>{t.province[e]=0});return}s.provinces=s.provinces.filter(t=>t!==e),o.state=i,o.color=g(r[i].color),r[i].provinces.push(e);return}if(!i){d.forEach(e=>{t.province[e]=0});return}if(d.length<20){let n=u(e,i,d);if(n){d.forEach(e=>{t.province[e]=n});return}}l(o,i,d)})}function l(e,s,c){let l=n.length,u=c.find(e=>t.burg[e]),d=u||c[0],f=u?t.burg[u]:0,p=f?i[f]:null,m=t.culture[d],h=u&&_(.5),v=h?p.name:e.name||Names.getState(Names.getCultureShort(m),m),y=u&&e.formName?e.formName:a([`Zone`,`Area`,`Territory`,`Province`]),b=g(r[s].color),x=h?.8:.4,S=Burgs.getType(d,p?.port),C=k.generate(p?.coa||r[s].coa,x,p?null:.9,S);C.shield=k.getShield(m,s),n.push({i:l,state:s,center:d,burg:f,name:v,formName:y,fullName:`${v} ${y}`,color:b,coa:C}),c.forEach(e=>{t.province[e]=l}),r[s].provinces.push(l),o.push(l)}function u(e,n,r){let i=r.find(r=>t.c[r].some(r=>t.state[r]===n&&t.province[r]&&t.province[r]!==e));return i&&t.c[i].map(e=>t.province[e]).find(t=>t&&t!==e)}}function Be(){if(this.classList.contains(`pressed`)){Y();return}customization=3,this.classList.add(`pressed`),D(`Click on the map to create a new capital or promote an existing burg`,!0),l(`#viewbox`).style(`cursor`,`crosshair`).on(`click`,Ve),u(`statesBodySection`).querySelectorAll(`div > input, select, span, svg`).forEach(e=>{e.style.pointerEvents=`none`})}function Ve(e){let{cells:t,states:n,burgs:i}=pack,a=r(e,this),o=Pack.findCell(a[0],a[1]);if(t.h[o]<20){D(`You cannot place state into the water. Please click on a land cell`,!1,`error`);return}let s=t.burg[o];if(s&&i[s].capital){D(`Existing capital cannot be selected as a new state capital! Select other cell`,!1,`error`);return}s||(s=Burgs.add(a),S(`burg`,s));let l=t.state[o],u=n.length;i[s].capital=1,i[s].state=u,Burgs.changeGroup(i[s],null),T.draw(`burgIcons`,`labels`,`routes`),e.shiftKey===!1&&Y();let d=t.culture[o],f=o%5==0?i[s].name:Names.getCulture(d),p=Names.getState(f,d),m=c(),h=pack.cultures[d].type,g=k.generate(i[s].coa,.4,null,h);g.shield=k.getShield(d,void 0);let _=n.map(e=>{if(!e.i||e.removed)return`x`;if(!l)return e.diplomacy.push(`Neutral`),`Neutral`;let t=n[l].diplomacy[e.i];return e.i===l?t=`Enemy`:t===`Ally`||t===`Friendly`?t=`Suspicion`:t===`Suspicion`?t=`Neutral`:t===`Enemy`||t===`Rival`?t=`Friendly`:t===`Vassal`?t=`Suspicion`:t===`Suzerain`&&(t=`Enemy`),e.diplomacy.push(t),t});_.push(`x`),n[0].diplomacy.push([`Independance declaration`,`${p} declared its independance from ${n[l].name}`]),t.state[o]=u,t.province[o]=0,n.push({i:u,name:p,diplomacy:_,provinces:[],color:m,expansionism:.5,capital:s,type:`Generic`,center:o,culture:d,military:[],alert:1,coa:g}),States.getPoles(),States.findNeighbors(),States.collectStatistics(),States.defineStateForms([u]),J([t.province[o]]),T.draw(`labels`),S(`state`,u),T.hide(`provinces`),T.draw(`states`,`borders`),R.refresh()}function Y(){customization=0,le(),se(),u(`statesBodySection`).querySelectorAll(`div > input, select, span, svg`).forEach(e=>{e.style.removeProperty(`pointer-events`)});let e=u(`statesAdd`);e.classList.contains(`pressed`)&&e.classList.remove(`pressed`)}var X=e=>`<svg class="coaIcon" viewBox="0 0 200 200"><use href="#stateCOA${e}"></use></svg>`;function He(){let e=pack.states.filter(e=>e.i&&!e.removed).map(e=>`
      <div data-id="${e.i}" data-tip="${e.fullName}" style="cursor:default">
        <input type="radio" name="rulingState" value="${e.i}" />
        <input id="selectState${e.i}" class="checkbox" type="checkbox" name="statesToMerge" value="${e.i}" />
        <label for="selectState${e.i}" class="checkbox-label"><fill-box fill="${e.color}" disabled></fill-box>${X(e.i)}${e.fullName}</label>
      </div>
    `).join(``);alertMessage.innerHTML=`
    <form id='mergeStatesForm' style="overflow: hidden; display: flex; flex-direction: column; gap: 1em;">
      <p style="margin:0">
        Check the <b>checkbox</b> next to each state you want to merge.
        Use the <b>radio button</b> to pick the <em>ruling state</em> that will absorb all others (its name, color, and capital will be kept).
        Hover over a row to highlight the state on the map.
      </p>
      <main style='display: grid; grid-template-columns: 1fr 1fr; gap: .3em;'>
        ${e}
      </main>
    </form>
  `,u(`mergeStatesForm`).querySelectorAll(`div[data-id]`).forEach(e=>{e.addEventListener(`mouseenter`,t),e.addEventListener(`mouseleave`,W)}),N(`alert`,({cellId:e})=>pack.cells.state[e]);function t(e){if(!T.isOn(`states`))return;let t=+e.currentTarget.dataset.id;if(!t)return;let n=l(`#regions`).select(`#state${t}`).attr(`d`);n&&(W(),E(n))}$(`#alert`).dialog({width:600,title:`Merge states`,close:W,buttons:{Merge:function(){let e=new FormData(u(`mergeStatesForm`)),t=Number(e.get(`rulingState`));if(!t){D(`Please select a state to merge into`,!1,`error`);return}let n=e.getAll(`statesToMerge`).map(Number).filter(e=>e!==t);if(!n.length){D(`Please select several states to merge`,!1,`error`);return}Z(n,t,()=>$(this).dialog(`close`))},Cancel:function(){$(this).dialog(`close`)}}})}function Z(e,t,n){let r=pack.states[t],i=`${X(r.i)}${r.name}`;A({title:`Merge states`,message:`
      <p>The following states will be <strong>removed</strong>: ${e.map(e=>`${X(e)}${pack.states[e].name}`).join(`, `)}.</p>
      <p>Removed states data (burgs, provinces, regiments) will be assigned to ${i}.</p>
      <label style="display: flex; align-items: center"><input id="mergeStatesAsProvinces" class="checkbox native" type="checkbox"> Keep each removed state as a province of ${i}, replacing its own provinces</label>
      <p>Are you sure you want to merge states? This action cannot be reverted.</p>`,confirm:`Merge`,onConfirm:()=>{Ue(e,t,u(`mergeStatesAsProvinces`).checked),n?.()}})}var Q=_e({buttonId:`statesAnnex`,bodySectionId:`statesBodySection`,noun:`state`,ownerOf:e=>pack.cells.state[e],colorOf:e=>pack.states[e].color??`#999999`,nameOf:e=>pack.states[e].name,commit:(e,t)=>Z(t,e)});function Ue(e,t,n=!1){let r=pack.states[t],i=u(`army${t}`);e.forEach(e=>{let a=pack.states[e];a.removed=!0,delete pack.states[e].label,x(`state`,e),(a.military||[]).forEach(n=>{let a=`regiment${e}-${n.i}`,o=(r.military||[]).length;(r.military||[]).push({...n,i:o});let s=`regiment${t}-${o}`,c=document.getElementById(a);c&&(c.id=s,c.dataset.state=String(t),c.dataset.id=String(o),i.appendChild(c))}),l(`#armies g#army${e}`).remove(),n&&We(a,r)}),pack.burgs.forEach(n=>{e.includes(n.state??0)&&(n.capital&&(n.capital=0,Burgs.changeGroup(n,null)),n.state=t)}),pack.provinces.forEach(n=>{e.includes(n.state)&&(n.state=t)}),pack.cells.state.forEach((n,r)=>{e.includes(n)&&(pack.cells.state[r]=t)}),w(),l(`#debug`).selectAll(`.highlight`).remove(),States.getPoles(),n&&Provinces.getPoles(),pack.states[t].label||delete pack.states[t].label,T.draw(`states`,`borders`,`burgIcons`,`labels`,`provinces`),n&&T.show(`provinces`),B()}function We(e,t){let{cells:n,provinces:r,burgs:i}=pack,a=r.length;r.forEach(t=>{t.state!==e.i||t.removed||(x(`province`,t.i),r[t.i]={i:t.i,removed:!0})}),n.state.forEach((t,r)=>{t===e.i&&(n.province[r]=a)});let o=e.capital,s=e.formName||`Province`;r.push({i:a,state:t.i,center:o?i[o].cell:e.center,burg:o,name:e.name,formName:s,fullName:`${e.name} ${s}`,color:g(e.color),coa:e.coa}),t.provinces.push(a),S(`province`,a)}function Ge(){let t=`Id,State,Full Name,Form,Color,Capital,Culture,Type,Expansionism,Cells,Burgs,Area ${p(`2`)},Total Population,Rural Population,Urban Population`,n=R.view().all.map(t=>{let n=t.rural||0,r=t.urban||0,i=e(n*options.map.units.population.scale+r*options.map.units.population.scale*options.map.units.population.urbanization.rate);return[t.i,t.name,t.fullName||``,t.i?t.formName:``,t.i?t.color:``,t.i?pack.burgs[t.capital].name:``,t.i?pack.cultures[t.culture].name:``,t.i?t.type:``,t.i?t.expansionism:``,t.cells,t.burgs,s(t.area||0),i,Math.round(n*options.map.units.population.scale),Math.round(r*options.map.units.population.scale*options.map.units.population.urbanization.rate)].join(`,`)});i([t].concat(n).join(`
`),`${y(`States`)}.csv`)}function Ke(e,t){let n=pack.states[e];n.lock=!n.lock,t.toggle(`icon-lock-open`),t.toggle(`icon-lock`)}var qe={open:z,showChart:K};export{qe as StatesEditor};