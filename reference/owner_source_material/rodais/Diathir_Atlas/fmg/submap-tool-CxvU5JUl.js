import{Bn as e,Rn as t,X as n,Y as r,j as i}from"./utils-Cob8vHf9.js";import{t as a}from"./layers-Bh4OWBXX.js";import{r as o}from"./viewport-CRAO29Z3.js";import{a as s}from"./pins-D6mEpUZC.js";import{Et as c,F as l,G as u,M as d,Mt as f,N as p,Tt as m,lt as h,m as g}from"./index-DsIn6sTp.js";function _(){v(),y(),$(`#submapTool`).dialog({title:`Create a submap`,resizable:!1,width:`32em`,position:{my:`center`,at:`center`,of:`svg`},close:b,buttons:{Submap:function(){S(),$(this).dialog(`close`)},Cancel:function(){$(this).dialog(`close`)}}})}function v(){h(`submapTool`);let e=String(options.generation.graph.density),t=s[+e],n=`<div id="submapTool" class="dialog">
    <p style="font-weight: bold">
      This operation is destructive and irreversible. It will create a completely new map based on the current one.
      Don't forget to save the .map file to your machine first!
    </p>
    <div style="display: flex; flex-direction: column; gap: 0.5em">
      <div data-tip="Set points (cells) number of the submap" style="display: flex; gap: 1em">
        <div>Points number</div>
        <div>
          <input id="submapPointsInput" type="range" min="1" max="13" value="${e}" />
          <output id="submapPointsFormatted" style="color: ${d(t)}">${t/1e3}K</output>
        </div>
      </div>
      <div data-tip="Check to fit burg styles (icon and label size) to the submap scale">
        <input type="checkbox" class="checkbox" id="submapRescaleBurgStyles" checked />
        <label for="submapRescaleBurgStyles" class="checkbox-label">Rescale burg styles</label>
      </div>
    </div>
  </div>`;i(`dialogs`).insertAdjacentHTML(`beforeend`,n)}function y(){i(`submapPointsInput`).oninput=x}function b(){h(`submapTool`)}function x(e){let t=s[+e.target.value],n=i(`submapPointsFormatted`);n.value=`${t/1e3}K`,n.style.color=d(t)}function S(){INFO&&console.group(`generateSubmap`);let{scale:e,x:t,y:n}=o,[r,s]=[Math.abs(t/e),Math.abs(n/e)];C(r,s,e);let d=i(`submapPointsInput`).value;d!==String(options.generation.graph.density)&&p(+d),m(),c(),resetZoom(0),u(),g.process({projection:(t,n)=>[(t-r)*e,(n-s)*e],inverse:(t,n)=>[t/e+r,n/e+s],scale:e}),i(`submapRescaleBurgStyles`).checked&&w(e),a.drawAll(),l(),f(),INFO&&console.groupEnd()}function C(t,i,a){let{geography:o,graph:s,units:c}=options.map,{coordinates:l}=o;o.mapSize=e(o.mapSize/a,2);let u=l.latT/a;o.latitude=e((90-r(i,l,s.height))/(180-u)*100,2);let d=l.lonT/a;o.longitude=e((180-n(t+s.width/a,l,s.width))/(360-d)*100,2),c.distance.scale=e(c.distance.scale/a,2),c.population.scale=e(c.population.scale/a,2),Options.save()}function w(n){window.Burgs.ensureBurgGroupStyles();for(let r of i(`burgIcons`).querySelectorAll(`:scope > g`)){let i=styles.burgIcons.burgIcons.groups[r.id];i&&(i.options.size=e(t(i.options.size*n,.2,10),2)),r.remove()}let r=new Set(pack.burgs.filter(e=>e.i&&!e.removed).map(e=>e.label?.group||e.group||`burg`));for(let t of r){let r=styles.labels.groups[t];if(!r)continue;let i=Number.parseFloat(r.attrs[`font-size`])||0,a=Math.max(e((i+i/n)/2,2),1)*n;r.attrs[`font-size`]=`${e(a,2)}%`}}var T={open:_};export{T as SubmapTool};