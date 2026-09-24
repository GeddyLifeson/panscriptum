import{Bn as e,Rn as t,j as n}from"./utils-Cob8vHf9.js";import{r}from"./viewport-CRAO29Z3.js";import{lt as i,st as a}from"./index-DsIn6sTp.js";function o(){a(`#minimap, .stable`),s(),u(),$(`#minimap`).dialog({title:`Minimap`,resizable:!1,width:`auto`,position:{my:`left bottom`,at:`left+10 bottom-25`,of:`svg`,collision:`fit`},open:function(){$(this).parent().addClass(`minimap-dialog`)},close:c})}function s(){i(`minimap`),n(`dialogs`).insertAdjacentHTML(`beforeend`,`<div id="minimap" class="dialog stable">
      <div id="minimapViewportWrap">
        <svg id="minimapSurface" preserveAspectRatio="xMidYMid meet" aria-label="Map minimap">
          <use id="minimapMapUse" href="#viewbox"></use>
          <rect id="minimapViewport"></rect>
        </svg>
      </div>
    </div>`),n(`minimapSurface`).addEventListener(`click`,l),document.getElementById(`minimapStyles`)?.remove();let e=document.createElement(`style`);e.id=`minimapStyles`,e.textContent=`
    .minimap-dialog .ui-dialog-content {
      padding: 0 !important;
      overflow: hidden;
    }

    #minimap {
      padding: 0 !important;
      background: transparent;
    }

    #minimapViewportWrap {
      position: relative;
      width: 20em;
      border: 0;
    }

    #minimapSurface {
      display: block;
      width: 100%;
      height: auto;
      cursor: crosshair;
    }

    #minimapMapUse {
      pointer-events: none;
    }

    #minimapViewport {
      fill: rgba(190, 255, 137, 0.1);
      stroke: #624954;
      stroke-width: 1;
      stroke-dasharray: 4;
      vector-effect: non-scaling-stroke;
      pointer-events: none;
    }
  `,document.head.append(e)}function c(){$(`#minimap`).dialog(`destroy`),n(`minimap`).remove(),document.getElementById(`minimapStyles`)?.remove()}function l(e){let n=document.getElementById(`minimapSurface`);if(!n)return;let i=n.createSVGPoint();i.x=e.clientX,i.y=e.clientY;let a=n.getScreenCTM();if(!a)return;let o=i.matrixTransform(a.inverse()),s=t(o.x,0,options.map.graph.width),c=t(o.y,0,options.map.graph.height);zoomTo(s,c,r.scale,450)}function u(){let t=document.getElementById(`minimapSurface`),n=document.getElementById(`minimapViewport`),i=document.getElementById(`minimapMapUse`);if(!t||!n||!i)return;t.setAttribute(`viewBox`,`0 0 ${options.map.graph.width} ${options.map.graph.height}`);let a=r.scale?1/r.scale:1;i.setAttribute(`transform`,`translate(${e(-r.x*a,3)} ${e(-r.y*a,3)}) scale(${e(a,6)})`);let o=Math.max(0,-r.x*a),s=Math.max(0,-r.y*a),c=Math.min(options.map.graph.width,o+r.width*a),l=Math.min(options.map.graph.height,s+r.height*a);n.setAttribute(`x`,String(e(o,3))),n.setAttribute(`y`,String(e(s,3))),n.setAttribute(`width`,String(e(Math.max(0,c-o),3))),n.setAttribute(`height`,String(e(Math.max(0,l-s),3)))}window.updateMinimap=u;var d={open:o};export{d as Minimap};