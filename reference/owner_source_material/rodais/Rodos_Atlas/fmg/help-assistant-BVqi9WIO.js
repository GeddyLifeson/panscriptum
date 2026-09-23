import{j as e}from"./utils-Cob8vHf9.js";import{I as t,L as n,R as r,lt as i}from"./index-DsIn6sTp.js";var a=`fmg-help-conversation`;function o(){try{return sessionStorage.getItem(a)}catch{return null}}var s=/^[A-Za-z0-9_-]{16,64}$/;function c(e){if(s.test(e))try{sessionStorage.setItem(a,e)}catch{}}function l(){try{sessionStorage.removeItem(a)}catch{}}function u(e,t){return e!==null&&e!==t}var d=`https://ask.azgaarsfmg.com`,f=`https://azgaar.github.io`,p=class extends Error{code;retryAfter;constructor(e,t,n){super(t),this.name=`HelpApiError`,this.code=e,this.retryAfter=n}};function m(){return d}async function h(e,t){let i=r(),a={...t.headers,...i?{Authorization:`Bearer ${i}`}:{}},o;try{o=await fetch(`${m()}${e}`,{...t,headers:a})}catch{throw new p(`unreachable`,`The assistant is unreachable. Check your connection and try again.`)}if(o.ok){if(o.status===204)return;try{return await o.json()}catch{throw new p(`provider_error`,`The assistant returned an unreadable response.`)}}if(o.status===401)throw n(),l(),new p(`unauthorized`,`Your sign-in has expired. Sign in with Discord again for more questions.`);let s=`provider_error`,c=`The assistant returned an error (${o.status}).`,u;try{let e=await o.json();e?.error&&(s=e.error.code??s,c=e.error.message??c,u=e.error.retryAfter)}catch{}throw new p(s,c,u)}var g=async(e,t)=>{let n=await h(`/v1/ask`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify(t?{question:e,conversationId:t}:{question:e})});if(!n)throw new p(`provider_error`,`The assistant returned an unreadable response.`);return n},ee=(e,t)=>h(`/v1/feedback`,{method:`POST`,headers:{"Content-Type":`application/json`},body:JSON.stringify({requestId:e,rating:t})}),te=()=>h(`/v1/limits`,{method:`GET`});function ne(){try{sessionStorage.setItem(t,`1`)}catch{}location.assign(`${m()}/v1/auth/discord`)}async function _(){try{await h(`/v1/auth/logout`,{method:`POST`})}catch{}n()}var v=/^ {0,3}```(\S*)\s*$/,y=/^ {0,3}(#{1,6})\s+(.*)$/,b=/^ {0,3}([-*_])(?:\s*\1){2,}\s*$/,x=/^ {0,3}>\s?(.*)$/,S=/^(\s*)([-*+]|\d{1,9}[.)])\s+(.*)$/,re=/^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$/,C=`\0`,ie=RegExp(`${C}(\\d+)${C}`,`g`);function w(e){let t=e.replace(/\r\n?/g,`
`).split(`
`),n=[],r=0;for(;r<t.length;){let e=t[r];if(!e.trim()){r++;continue}if(v.test(e)){let e=[];for(r++;r<t.length&&!v.test(t[r]);)e.push(t[r++]);r++,n.push(`<pre><code>${A(e.join(`
`))}</code></pre>`);continue}let i=e.match(y);if(i){let e=Math.min(i[1].length+2,6);n.push(`<h${e}>${k(i[2])}</h${e}>`),r++;continue}if(b.test(e)){n.push(`<hr />`),r++;continue}if(x.test(e)){let e=[];for(;r<t.length&&x.test(t[r]);)e.push(t[r++].match(x)?.[1]??``);n.push(`<blockquote>${w(e.join(`
`))}</blockquote>`);continue}if(S.test(e)){let e=[];for(;r<t.length;){let n=t[r].match(S);if(!n)break;e.push({indent:n[1].length,ordered:/\d/.test(n[2]),text:n[3]}),r++}n.push(E(e,0).html);continue}if(e.includes(`|`)&&r+1<t.length&&re.test(t[r+1])){r=D(t,r,n);continue}let a=[];for(;r<t.length&&t[r].trim()&&!T(t[r]);)a.push(t[r++]);n.push(`<p>${a.map(k).join(`<br />`)}</p>`)}return n.join(``)}function T(e){return v.test(e)||y.test(e)||b.test(e)||x.test(e)||S.test(e)}function E(e,t){let{indent:n,ordered:r}=e[t],i=[],a=t;for(;a<e.length&&e[a].indent>=n;){if(e[a].indent>n&&i.length){let t=E(e,a);i[i.length-1]+=t.html,a=t.next;continue}i.push(k(e[a].text)),a++}let o=r?`ol`:`ul`;return{html:`<${o}>${i.map(e=>`<li>${e}</li>`).join(``)}</${o}>`,next:a}}function D(e,t,n){let r=O(e[t]),i=O(e[t+1]).map(e=>e.startsWith(`:`)&&e.endsWith(`:`)?` style="text-align: center"`:e.endsWith(`:`)?` style="text-align: right"`:``),a=(e,t,n)=>`<${n}${i[t]??``}>${k(e)}</${n}>`,o=[],s=t+2;for(;s<e.length&&e[s].includes(`|`);){let t=O(e[s]);o.push(`<tr>${t.map((e,t)=>a(e,t,`td`)).join(``)}</tr>`),s++}let c=r.map((e,t)=>a(e,t,`th`)).join(``);return n.push(`<table><thead><tr>${c}</tr></thead><tbody>${o.join(``)}</tbody></table>`),s}var O=e=>e.trim().replace(/^\|/,``).replace(/\|$/,``).split(`|`).map(e=>e.trim());function k(e){let t=[];return A(e.replace(/`([^`]+)`/g,(e,n)=>(t.push(`<code>${A(n)}</code>`),`${C}${t.length-1}${C}`))).replace(/\[([^\]\n]+)\]\(([^)\s]+)\)/g,(e,t,n)=>/^https?:\/\//i.test(n)?`<a href="${n}" target="_blank" rel="noopener noreferrer">${t}</a>`:e).replace(/(\*\*|__)(?=\S)([\s\S]*?\S)\1/g,`<strong>$2</strong>`).replace(/\*(?=\S)([^*\n]*\S)\*/g,`<em>$1</em>`).replace(/~~(?=\S)([\s\S]*?\S)~~/g,`<del>$1</del>`).replace(ie,(e,n)=>t[Number(n)])}var A=e=>e.replace(/&/g,`&amp;`).replace(/</g,`&lt;`).replace(/>/g,`&gt;`).replace(/"/g,`&quot;`),ae=30,oe=1e3,j=108,se=`Hi! Ask anything about the Fantasy Map Generator. I cannot change maps, but I can teach you how to do it.`,M=()=>location.origin===`https://azgaar.github.io`||!1;function N(){return document.getElementById(`helpAssistant`)!==null}function P(e){let t=document.getElementById(`helpAssistantBubble`);t&&(t.classList.toggle(`open`,e),t.setAttribute(`aria-expanded`,String(e)))}function ce(){N()?$(`#helpAssistant`).dialog(`close`):F()}function F(){L();let e=Math.min(400,window.innerWidth-24),t=Math.min(560,window.innerHeight-140);$(`#helpAssistant`).dialog({title:`Azgaar Assistant`,position:{my:`right bottom`,at:`right-16 bottom-44`,of:window},width:e,height:M()?t:`auto`,minWidth:300,minHeight:M()?320:0,resizable:M(),close:()=>{J(),q=!1,P(!1),i(`helpAssistant`)}}),P(!0),M()&&(I(),Z())}function I(){let e=document.getElementById(`helpAssistant`)?.closest(`.ui-dialog`)?.querySelector(`.ui-dialog-titlebar`);if(!e||e.querySelector(`#helpAssistantNewChat`))return;let t=document.createElement(`button`);t.type=`button`,t.id=`helpAssistantNewChat`,t.className=`helpAssistantNewChat icon-plus`,t.dataset.tip=`Start a new chat`,t.setAttribute(`aria-label`,`Start a new chat`),t.addEventListener(`click`,z),e.insertBefore(t,e.querySelector(`.ui-dialog-titlebar-reset, .ui-dialog-titlebar-collapse`))}function L(){i(`helpAssistant`);let t=`<div id="helpAssistant" class="dialog stable">
    ${`
    <style>
      #helpAssistant.ui-dialog-content { display: flex; flex-direction: column; gap: .5em; overflow: hidden; padding: .6em .7em .5em; font-family: var(--sans-serif); }
      #helpAssistant > div          { width: auto; }
      .ui-dialog-titlebar .helpAssistantNewChat { font-size: .62em; }

      #helpAssistant .helpAssistantLog   { flex: 1; min-height: 0; overflow: hidden auto; padding-right: .2em; line-height: 1.4; }
      #helpAssistant .helpAssistantMsg   { display: flex; margin-bottom: .55em; }
      #helpAssistant .helpAssistantMsg.user { justify-content: flex-end; }
      #helpAssistant .helpAssistantStack { display: flex; flex-direction: column; min-width: 0; max-width: 88%; }
      #helpAssistant .helpAssistantBubble { padding: .45em .65em; border-radius: .4em; background: rgb(0 0 0 / 6%); overflow-wrap: anywhere; }
      #helpAssistant .helpAssistantMsg.user .helpAssistantBubble   { background: var(--header); color: #ffffff; }
      #helpAssistant .helpAssistantMsg.user .helpAssistantBubble a { color: #ffffff; }

      /* answers are rendered markdown: keep block spacing tight enough to read as one message */
      #helpAssistant .helpAssistantBubble > :first-child { margin-top: 0; }
      #helpAssistant .helpAssistantBubble > :last-child  { margin-bottom: 0; }
      #helpAssistant .helpAssistantBubble p              { margin: .4em 0; }
      #helpAssistant .helpAssistantBubble :is(h3, h4, h5, h6) { margin: .6em 0 .3em; font-size: 1em; }
      #helpAssistant .helpAssistantBubble :is(ol, ul)    { margin: .4em 0; padding-left: 1.3em; }
      #helpAssistant .helpAssistantBubble pre            { overflow-x: auto; margin: .4em 0; padding: .4em .5em; border-radius: .3em; background: rgb(0 0 0 / 6%); font-size: .9em; }
      #helpAssistant .helpAssistantBubble code           { font-family: var(--monospace); }
      #helpAssistant .helpAssistantBubble table          { display: block; overflow-x: auto; border-collapse: collapse; }
      #helpAssistant .helpAssistantBubble :is(td, th)    { padding: .15em .4em; border: 1px solid rgb(0 0 0 / 12%); }

      /* three dots standing in for the answer while the gateway is thinking */
      #helpAssistant .helpAssistantTyping   { display: flex; align-items: center; gap: .28em; padding: .65em; }
      #helpAssistant .helpAssistantTyping i { width: .4em; height: .4em; border-radius: 50%; background: currentcolor; opacity: .35; animation: helpAssistantTyping 1.2s infinite ease-in-out; }
      #helpAssistant .helpAssistantTyping i:nth-child(2) { animation-delay: .15s; }
      #helpAssistant .helpAssistantTyping i:nth-child(3) { animation-delay: .3s; }
      @keyframes helpAssistantTyping { 0%, 60%, 100% { opacity: .25; transform: none; } 30% { opacity: .8; transform: translateY(-.18em); } }
      @media (prefers-reduced-motion: reduce) { #helpAssistant .helpAssistantTyping i { animation: none; } }

      #helpAssistant .helpAssistantDivider { display: flex; align-items: center; gap: .6em; margin: .6em 0; opacity: .5; font-size: .82em; text-transform: uppercase; letter-spacing: .06em; }
      #helpAssistant .helpAssistantDivider::before,
      #helpAssistant .helpAssistantDivider::after { content: ""; flex: 1; height: 1px; background: currentcolor; }

      #helpAssistant .helpAssistantFeedback        { display: flex; gap: .2em; margin-top: .15em; }
      #helpAssistant .helpAssistantFeedback button { padding: 0 .15em; border: none; background: none; opacity: .35; font-size: .9em; transition: .15s; }
      #helpAssistant .helpAssistantFeedback button:hover    { opacity: .75; }
      #helpAssistant .helpAssistantFeedback button.selected { opacity: 1; }

      /* server refusals and countdowns: loud enough to notice, quiet enough to stay out of the way */
      #helpAssistant .helpAssistantNotice { flex: none; max-height: 30%; overflow-y: auto; padding: .45em .6em; border-left: 3px solid var(--header); border-radius: .25em; background: rgb(0 0 0 / 5%); font-size: .9em; }
      #helpAssistant .helpAssistantNotice > :first-child { margin-top: 0; }
      #helpAssistant .helpAssistantNotice > :last-child  { margin-bottom: 0; }
      #helpAssistant .helpAssistantCountdown { margin-top: .3em; opacity: .7; font-variant-numeric: tabular-nums; }

      #helpAssistant .helpAssistantComposer          { flex: none; display: flex; align-items: flex-end; gap: .4em; padding: .3em .3em .3em .5em; border: 1px solid rgb(0 0 0 / 18%); border-radius: .5em; background: rgb(255 255 255 / 55%); transition: border-color .15s; }
      #helpAssistant .helpAssistantComposer:focus-within { border-color: var(--header); }
      #helpAssistant .helpAssistantComposer textarea { flex: 1; min-width: 0; height: 1.7em; max-height: ${j}px; padding: .2em 0; border: 0; background: none; resize: none; font: inherit; line-height: 1.4; }
      #helpAssistant .helpAssistantSend              { flex: none; display: flex; align-items: center; justify-content: center; width: 1.9em; height: 1.9em; border: 0; border-radius: .4em; background: var(--header); color: #ffffff; font-size: 1em; transition: .15s; }
      #helpAssistant .helpAssistantSend::before      { margin: 0; }
      #helpAssistant .helpAssistantSend:hover        { background: var(--header-active); }
      #helpAssistant .helpAssistantSend:disabled     { opacity: .4; cursor: default; }

      /* quick links and the account state: present, but plainly secondary to the transcript */
      #helpAssistant .helpAssistantBar     { flex: none; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: .2em .8em; padding-top: .4em; border-top: 1px solid rgb(0 0 0 / 10%); font-size: .9em; }
      #helpAssistant .helpAssistantLinks   { display: flex; gap: .8em; }
      #helpAssistant .helpAssistantAccount { display: flex; align-items: center; gap: .5em; opacity: .85; }
      #helpAssistant .helpAssistantLink        { padding: 0; border: 0; background: none; color: inherit; font: inherit; text-decoration: underline; }
      #helpAssistant .helpAssistantLink:hover  { color: var(--header-active); }

      #helpAssistant .helpAssistantUnlisted { flex: none; line-height: 1.4; }
    </style>`}
    ${M()?`
    <div id="helpAssistantLog" class="helpAssistantLog" role="log" aria-live="polite"></div>
    <div id="helpAssistantNotice" class="helpAssistantNotice" hidden></div>
    <div class="helpAssistantComposer">
      <textarea id="helpAssistantQuestion" rows="1" maxlength="1000" aria-label="Your question"
        placeholder="Ask a question…"></textarea>
      <button id="helpAssistantAsk" type="button" class="helpAssistantSend icon-right-big"
        title="Send (Enter)" aria-label="Send"></button>
    </div>`:`
    <div class="helpAssistantUnlisted">
      <div class="helpAssistantMsg bot">
        <div class="helpAssistantStack">
          <div class="helpAssistantBubble">
            <p>The free assistant is only available on the official site: <a href="https://azgaar.github.io/Fantasy-Map-Generator/" target="_blank" rel="noopener noreferrer"> azgaar.github.io/Fantasy-Map-Generator</a>. On a self-hosted copy, the <a href="https://github.com/Azgaar/Fantasy-Map-Generator/wiki" target="_blank" rel="noopener noreferrer">documentation</a> covers most questions.</p>
          </div>
        </div>
      </div>
    </div>`}
    
    <div class="helpAssistantBar">
      <div class="helpAssistantLinks">
        <a href="https://github.com/Azgaar/Fantasy-Map-Generator/wiki" target="_blank" rel="noopener noreferrer">Wiki</a>
        <a href="https://discordapp.com/invite/X7E84HU" target="_blank" rel="noopener noreferrer">Discord</a>
        <a href="https://www.reddit.com/r/FantasyMapGenerator/" target="_blank" rel="noopener noreferrer">Reddit</a>
        <a href="https://www.patreon.com/azgaar" target="_blank" rel="noopener noreferrer">Patreon</a>
        <a href="https://github.com/Azgaar/Fantasy-Map-Generator/wiki/Policy" target="_blank" rel="noopener noreferrer"
          title="What is sent, how long questions are kept, and the rest of the small print">Policy</a>
      </div>
      <div class="helpAssistantAccount">
        <span id="helpAssistantLimits"></span>
        <span id="helpAssistantAuth"></span>
      </div>
    </div>
  </div>`;if(e(`dialogs`).insertAdjacentHTML(`beforeend`,t),!M())return;z(),e(`helpAssistantAsk`).addEventListener(`click`,()=>void V(Q(B())));let n=e(`helpAssistantQuestion`);n.addEventListener(`keydown`,e=>{let t=e;t.key!==`Enter`||t.shiftKey||t.isComposing||(t.preventDefault(),V(Q(B())))}),n.addEventListener(`input`,()=>R(n))}function R(e){e.style.height=`auto`,e.style.height=`${Math.min(e.scrollHeight,j)}px`}function z(){l();let t=e(`helpAssistantLog`);t.textContent=``;let{row:n,stack:r}=H(`bot`),i=document.createElement(`div`);i.className=`helpAssistantBubble`,i.textContent=se,r.appendChild(i),t.appendChild(n),G(null)}function B(){return e(`helpAssistantQuestion`).value}async function V(t,n=!1){if(!t)return;let r=e(`helpAssistantAsk`);if(r.disabled)return;r.disabled=!0,n||U(t);let i=le(),a=o();try{let{answer:n,conversationId:r,requestId:o}=await g(t,a??void 0),s=u(a,r);if(c(r),!N())return;i.remove(),s&&ue(),de(w(n),o);let l=e(`helpAssistantQuestion`);l.value=``,R(l),G(null),q=!1}catch(e){if(!N())return;i.remove(),e instanceof p?(e.code===`invalid_request`&&l(),pe(me(e),e,t)):console.error(e)}finally{N()&&(r.dataset.locked||(r.disabled=!1),Z())}}function H(e){let t=document.createElement(`div`);t.className=`helpAssistantMsg ${e}`;let n=document.createElement(`div`);return n.className=`helpAssistantStack`,t.appendChild(n),{row:t,stack:n}}function U(e){let{row:t,stack:n}=H(`user`),r=document.createElement(`div`);r.className=`helpAssistantBubble`,r.textContent=e,n.appendChild(r),W(t)}function le(){let{row:e,stack:t}=H(`bot`),n=document.createElement(`div`);return n.className=`helpAssistantBubble helpAssistantTyping`,n.setAttribute(`aria-label`,`Thinking…`),n.innerHTML=`<i></i><i></i><i></i>`,t.appendChild(n),W(e),e}function ue(){let e=document.createElement(`div`);e.className=`helpAssistantDivider`,e.textContent=`new conversation`,W(e)}function de(e,t){let{row:n,stack:r}=H(`bot`),i=document.createElement(`div`);i.className=`helpAssistantBubble`,i.innerHTML=e,r.appendChild(i),t!==null&&r.appendChild(fe(t)),W(n)}function fe(e){let t=document.createElement(`div`);t.className=`helpAssistantFeedback`;for(let n of[`up`,`down`]){let r=document.createElement(`button`);r.type=`button`,r.textContent=n===`up`?`👍`:`👎`,r.setAttribute(`aria-label`,n===`up`?`Good answer`:`Bad answer`),r.setAttribute(`aria-pressed`,`false`),r.addEventListener(`click`,()=>{let i=t.querySelector(`.selected`);i?.classList.remove(`selected`),i?.setAttribute(`aria-pressed`,`false`),r.classList.add(`selected`),r.setAttribute(`aria-pressed`,`true`),ee(e,n).catch(e=>{r.classList.remove(`selected`),r.setAttribute(`aria-pressed`,`false`),i?.classList.add(`selected`),i?.setAttribute(`aria-pressed`,`true`),e instanceof p&&e.code===`unauthorized`&&Z()})}),t.appendChild(r)}return t}function W(t){let n=e(`helpAssistantLog`);n.appendChild(t),n.scrollTop=n.scrollHeight}function G(t){let n=e(`helpAssistantNotice`);n.hidden=t===null,n.innerHTML=t??``}var K=null,q=!1;function J(){K&&=(clearInterval(K),null)}function pe(t,n,r){G(t.html);let i=e(`helpAssistantAsk`);if(J(),!t.askDisabled||(i.disabled=!0,i.dataset.locked=`true`,t.retryCountdown===void 0))return;let a=document.createElement(`div`);a.className=`helpAssistantCountdown`,e(`helpAssistantNotice`).appendChild(a);let o=he(n,q),s=t.retryCountdown;a.textContent=`Ready again in ${s}s`,K=setInterval(()=>{if(--s,s>0){a.textContent=`Ready again in ${s}s`;return}J(),delete i.dataset.locked,i.disabled=!1,G(null),o&&N()&&(q=!0,V(r,!0))},1e3)}var Y=()=>location.origin===f;function X(e){let t=document.getElementById(`helpAssistantAuth`);if(!t)return;if(t.textContent=``,e===`anonymous`){if(!Y())return;let e=document.createElement(`button`);e.type=`button`,e.className=`helpAssistantLink`,e.textContent=`Sign in`,e.title=`Sign in with Discord for more questions a day`,e.addEventListener(`click`,()=>{l(),ne()}),t.appendChild(e);return}let n=document.createElement(`button`);n.type=`button`,n.className=`helpAssistantLink`,n.textContent=`Sign out`,n.addEventListener(`click`,()=>{_().then(()=>{z(),Z()})}),t.appendChild(n)}async function Z(){try{let t=await te();e(`helpAssistantLimits`).textContent=ge(t),X(t.tier)}catch{X(r()?`member`:`anonymous`)}}function me(e){let t=w(e.message);switch(e.code){case`cap_reached`:case`quota`:case`blocked`:return{html:t,askDisabled:!0};case`rate_limited`:return{html:t,askDisabled:!0,retryCountdown:e.retryAfter??ae};default:return{html:t,askDisabled:!1}}}function he(e,t){return e.code===`rate_limited`&&e.retryAfter!==void 0&&!t}function ge(e){return e.remaining<=0?`No questions left today`:`${e.remaining} question${e.remaining===1?``:`s`} left today`}function Q(e){let t=e.trim();return!t.length||t.length>oe?null:t}var _e={open:F,toggle:ce};export{_e as HelpAssistant};