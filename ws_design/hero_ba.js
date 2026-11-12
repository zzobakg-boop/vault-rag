/* 표지 전/후 비교 (frontmatter hero_before, 2026-11-12 사회 8-7~8) — 경계 막대(키보드 화살표)·전/후 단추·그림 끌기/누르기로 경계를 옮긴다.
   입력칸이 아니라 저장·제출·점수에 잡히지 않는다. 움직임 줄이기 설정이면 단추도 바로 바뀐다. */
(function(){
  var reduce=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
  [].forEach.call(document.querySelectorAll('.hero-ba'),function(fig){
    var fr=fig.querySelector('.hba-frame'),rg=fig.querySelector('.hba-range'),aft=fig.querySelector('.hba-after'),
        bB=fig.querySelector('.hba-go-b'),bA=fig.querySelector('.hba-go-a'),
        tB=fig.querySelector('.hba-tag-b'),tA=fig.querySelector('.hba-tag-a');
    if(!fr||!rg)return;
    var lb=tB?tB.textContent:'전',la=tA?tA.textContent:'후',tm=null;
    function ratio(){if(aft&&aft.naturalWidth)fig.style.setProperty('--hba-r',(aft.naturalWidth/aft.naturalHeight).toFixed(4));}
    if(aft){if(aft.complete)ratio();else aft.addEventListener('load',ratio);}
    function set(v,anim){
      v=Math.max(0,Math.min(100,Math.round(+v)));
      clearTimeout(tm);
      if(anim&&!reduce){fig.classList.add('hba-anim');tm=setTimeout(function(){fig.classList.remove('hba-anim');},500);}
      else fig.classList.remove('hba-anim');
      fig.style.setProperty('--v',v+'%');
      if(+rg.value!==v)rg.value=v;
      rg.setAttribute('aria-valuetext',v>=100?lb+'만 보임':v<=0?la+'만 보임':'왼쪽 '+v+'퍼센트는 '+lb+', 나머지는 '+la);
      if(bB)bB.setAttribute('aria-pressed',v>=100?'true':'false');
      if(bA)bA.setAttribute('aria-pressed',v<=0?'true':'false');
      if(tB)tB.style.opacity=v<14?'0':'';
      if(tA)tA.style.opacity=v>86?'0':'';
    }
    rg.addEventListener('input',function(){set(rg.value);});
    if(bB)bB.addEventListener('click',function(){set(100,true);});
    if(bA)bA.addEventListener('click',function(){set(0,true);});
    /* 그림 위: 옆으로 끌면 경계가 따라오고, 끌지 않고 누르면 그 자리로 옮긴다. 세로로 밀면 화면이 그대로 내려간다(touch-action:pan-y). */
    var down=null,moved=false;
    function at(e){var r=fr.getBoundingClientRect();return r.width?(e.clientX-r.left)/r.width*100:50;}
    fr.addEventListener('pointerdown',function(e){
      if(e.button>0)return;
      down={x:e.clientX,id:e.pointerId};moved=false;
      try{fr.setPointerCapture(e.pointerId);}catch(_){}
    });
    fr.addEventListener('pointermove',function(e){
      if(!down||e.pointerId!==down.id)return;
      if(!moved&&Math.abs(e.clientX-down.x)<4)return;
      moved=true;set(at(e));
    });
    function end(e,ok){
      if(!down||e.pointerId!==down.id)return;
      if(ok&&!moved)set(at(e),true);
      down=null;
    }
    fr.addEventListener('pointerup',function(e){end(e,true);});
    fr.addEventListener('pointercancel',function(e){end(e,false);});
    set(rg.value||50);
  });
})();
