document.addEventListener('DOMContentLoaded', () => {
 const header=document.getElementById('fyeHeader');
 const onScroll=()=>header?.classList.toggle('is-scrolled',window.scrollY>24);
 onScroll();window.addEventListener('scroll',onScroll,{passive:true});
 const nav=document.getElementById('mainNav');
 if(nav&&window.bootstrap){nav.querySelectorAll('a.nav-link:not(.dropdown-toggle)').forEach(a=>a.addEventListener('click',()=>{if(window.innerWidth<992&&nav.classList.contains('show'))window.bootstrap.Collapse.getOrCreateInstance(nav,{toggle:false}).hide()}));}
 const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
 if(reduced||!window.gsap)return;
 const gsap=window.gsap;
 gsap.fromTo('.fye-header',{y:-30,opacity:0},{y:0,opacity:1,duration:.75,ease:'power3.out',clearProps:'transform,opacity'});
 if(!document.querySelector('.fye-home'))return;
 gsap.fromTo('.fye-animate-in',{y:30,opacity:0},{y:0,opacity:1,duration:.8,stagger:.13,ease:'power3.out',delay:.12,clearProps:'opacity'});
 gsap.fromTo('.fye-art-stage',{y:30,scale:.92,opacity:0},{y:0,scale:1,opacity:1,duration:1.1,ease:'power3.out',delay:.15,onComplete:()=>{gsap.to('.fye-art-stage',{y:-10,duration:3,ease:'sine.inOut',yoyo:true,repeat:-1})}});
 gsap.fromTo('.fye-floating-card',{y:20,opacity:0},{y:0,opacity:1,duration:.8,stagger:.18,delay:.75,onComplete:()=>{gsap.to('.fye-floating-top',{y:-9,duration:2.7,yoyo:true,repeat:-1,ease:'sine.inOut'});gsap.to('.fye-floating-bottom',{y:9,duration:3.1,yoyo:true,repeat:-1,ease:'sine.inOut'})}});
 const art=document.getElementById('fyeHeroArt'),stage=document.getElementById('fyeArtStage');
 if(art&&stage&&window.matchMedia('(hover:hover) and (pointer:fine)').matches){
  art.addEventListener('pointermove',e=>{const r=art.getBoundingClientRect(),x=(e.clientX-r.left)/r.width-.5,y=(e.clientY-r.top)/r.height-.5;gsap.to(stage,{rotateY:x*7,rotateX:-y*5,duration:.55,overwrite:'auto',ease:'power2.out'})});
  art.addEventListener('pointerleave',()=>gsap.to(stage,{rotateY:0,rotateX:0,duration:.7,ease:'power2.out'}));
 }
 if(window.ScrollTrigger){gsap.registerPlugin(window.ScrollTrigger);gsap.utils.toArray('.fye-reveal').forEach(el=>gsap.fromTo(el,{opacity:0,y:35},{opacity:1,y:0,duration:.8,ease:'power2.out',scrollTrigger:{trigger:el,start:'top 90%',once:true}}));
 gsap.utils.toArray('.fye-count').forEach(el=>{const end=Number(el.dataset.count);if(!Number.isFinite(end)||end<0)return;const obj={v:0};gsap.to(obj,{v:end,duration:1.5,ease:'power2.out',scrollTrigger:{trigger:el,start:'top 95%',once:true},onUpdate:()=>{el.textContent=Math.round(obj.v).toLocaleString()}})})}
});
