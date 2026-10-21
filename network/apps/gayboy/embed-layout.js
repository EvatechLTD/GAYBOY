/* Let the homepage follow the complete app height, including tutorial and beats. */
(() => {
 if(parent===window)return;
 let pending=false;
 function report(){pending=false;parent.postMessage({type:'y2k-app-layout',app:'gayboy',height:Math.ceil(document.body.getBoundingClientRect().height),expanded:document.body.classList.contains('demo-open')},location.origin);}
 function schedule(){if(!pending){pending=true;requestAnimationFrame(report);}}
 new ResizeObserver(schedule).observe(document.body);
 new MutationObserver(schedule).observe(document.body,{attributes:true,attributeFilter:['class']});
 window.addEventListener('load',schedule);schedule();
})();
