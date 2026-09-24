import{j as e,k as t}from"./utils-Cob8vHf9.js";import{t as n}from"./layers-Bh4OWBXX.js";import{t as r}from"./pins-D6mEpUZC.js";import{lt as i,st as a}from"./index-DsIn6sTp.js";var o=`unitsEditor`,s=`
    <div id="unitsBody" style="margin-left: 1.1em">
      <div class="unitsHeader" style="margin-top: 0.4em">
        <span class="icon-map-signs"></span>
        <label>Distance:</label>
      </div>
      <div data-tip="Select a distance unit or provide a custom name">
        <label>Distance unit:</label>
        <select id="distanceUnitInput">
          <option value="mi" selected>Mile (mi)</option>
          <option value="km">Kilometer (km)</option>
          <option value="lg">League (lg)</option>
          <option value="vr">Versta (vr)</option>
          <option value="nmi">Nautical mile (nmi)</option>
          <option value="nlg">Nautical league (nlg)</option>
          <option value="custom_name">Custom name</option>
        </select>
      </div>
      <div data-tip="Select how many distance units are in one pixel">
        <i data-locked="0" id="lock_distanceScale" class="icon-lock-open"></i>
        <slider-input id="distanceScaleInput" min=".01" max="20" step=".1" value="3">
          <label>1 map pixel:</label>
        </slider-input>
      </div>
      <div data-tip='Area unit name, type "square" to add ² to the distance unit'>
        <label>Area unit:</label>
        <input id="areaUnit" type="text" value="square" />
      </div>
      <div class="unitsHeader">
        <span class="icon-signal"></span>
        <label>Altitude:</label>
      </div>
      <div data-tip="Select an altitude unit or provide a custom name">
        <label>Height unit:</label>
        <select id="heightUnit">
          <option value="ft" selected>Feet (ft)</option>
          <option value="m">Meters (m)</option>
          <option value="f">Fathoms (f)</option>
          <option value="custom_name">Custom name</option>
        </select>
      </div>
      <div
        data-tip="Set height exponent, i.e. a value for altitude change sharpness. Altitude affects temperature and hence biomes"
      >
        <slider-input
          id="heightExponentInput"
         
          min="1.5"
          max="2.2"
          step=".01"
          value="2"
        >
          <label>Exponent:</label>
        </slider-input>
      </div>
      <div class="unitsHeader" data-tip="Select Temperature scale">
        <span class="icon-temperature-high"></span>
        <label>Temperature:</label>
      </div>
      <div>
        <label>Temperature scale:</label>
        <select id="temperatureScale">
          <option value="°C" selected>degree Celsius (°C)</option>
          <option value="°F">degree Fahrenheit (°F)</option>
          <option value="K">Kelvin (K)</option>
          <option value="°R">degree Rankine (°R)</option>
          <option value="°De">degree Delisle (°De)</option>
          <option value="°N">degree Newton (°N)</option>
          <option value="°Ré">degree Réaumur (°Ré)</option>
          <option value="°Rø">degree Rømer (°Rø)</option>
        </select>
      </div>
      <div class="unitsHeader">
        <span class="icon-male"></span>
        <label>Population:</label>
      </div>
      <div data-tip="Set how many people are in one population point">
        <slider-input
          id="populationRateInput"
         
          min="10"
          max="10000"
          step="10"
          value="1000"
        >
          <label>1 population point:</label>
        </slider-input>
      </div>
      <div data-tip="Set urban population modifier. Change to increase or descrese burgs population">
        <slider-input id="urbanizationInput" min=".01" max="5" step=".01" value="1">
          <label>Urbanization rate:</label>
        </slider-input>
      </div>
      <div data-tip="Set urban density: average population per building in Medieval Fantasy City Generator">
        <slider-input id="urbanDensityInput" min="1" max="200" step="1" value="10">
          <label>Urban density:</label>
        </slider-input>
      </div>
    </div>
    <div id="unitsBottom">
      <button id="unitsRestore" data-tip="Restore default units settings" class="icon-ccw"></button>
    </div>
`;function c(){a(`#unitsEditor, .stable`),l(),$(`#unitsEditor`).dialog({title:`Units Editor`,position:{my:`right top`,at:`right-10 top+10`,of:`svg`,collision:`fit`},close:()=>i(o)})}function l(){i(o),e(`dialogs`).insertAdjacentHTML(`beforeend`,`<div id="${o}" class="dialog stable">${s}</div>`),m(),h(),r.bindIcons(e(o),d)}var u=[`distanceUnit`,`distanceScale`,`areaUnit`,`heightUnit`,`heightExponent`,`temperatureScale`,`populationRate`,`urbanization`,`urbanDensity`];function d(e){let{distance:t,area:n,height:r,temperature:i,population:a}=options.map.units;if(e===`distanceUnit`)return t.unit;if(e===`distanceScale`)return t.scale;if(e===`areaUnit`)return n.unit;if(e===`heightUnit`)return r.unit;if(e===`heightExponent`)return r.exponent;if(e===`temperatureScale`)return i.unit;if(e===`populationRate`)return a.scale;if(e===`urbanization`)return a.urbanization.rate;if(e===`urbanDensity`)return a.urbanization.density}var f=[`areaUnit`,`heightUnit`,`temperatureScale`],p=t=>e(f.includes(t)?t:`${t}Input`);function m(){t(e(`distanceUnitInput`),options.map.units.distance.unit),t(e(`heightUnit`),options.map.units.height.unit);for(let e of u)p(e).value=String(d(e))}function h(){e(o).addEventListener(`change`,g),e(`unitsRestore`).addEventListener(`click`,y)}function g(e){let t=e.target,i=t.value,{units:a}=options.map;switch(t.id){case`distanceUnitInput`:if(i===`custom_name`){_(t,`distance`);return}a.distance.unit=i,r.set(`distanceUnit`,i),v();break;case`distanceScaleInput`:a.distance.scale=+i,r.set(`distanceScale`,+i),v();break;case`areaUnit`:a.area.unit=i,r.set(`areaUnit`,i);break;case`heightUnit`:if(i===`custom_name`){_(t,`height`);return}a.height.unit=i,r.set(`heightUnit`,i);break;case`heightExponentInput`:a.height.exponent=+i,r.set(`heightExponent`,+i),Temperature.generate(),n.draw(`temperature`);break;case`temperatureScale`:a.temperature.unit=i,r.set(`temperatureScale`,i),n.draw(`temperature`);break;case`populationRateInput`:a.population.scale=+i,r.set(`populationRate`,+i);break;case`urbanizationInput`:a.population.urbanization.rate=+i,r.set(`urbanization`,+i);break;case`urbanDensityInput`:a.population.urbanization.density=+i,r.set(`urbanDensity`,+i);break;default:return}Options.save()}function _(e,t){m(),prompt(`Provide a custom name for a ${t} unit`,{default:``},n=>{let i=String(n);i&&(e.options.add(new Option(i,i,!1,!0)),t===`distance`?(options.map.units.distance.unit=i,r.set(`distanceUnit`,i),v()):(options.map.units.height.unit=i,r.set(`heightUnit`,i)),Options.save())})}function v(){n.draw(`scaleBar`),calculateFriendlyGridSize()}function y(){options.map.units=Options.getDefaultOptions().map.units;for(let e of u)r.clear(e);Options.save(),m(),Temperature.generate(),v()}var b={open:c};export{b as UnitsEditor};