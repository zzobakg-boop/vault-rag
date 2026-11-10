// 답이 하나라도 있을 때 초기화를 누르면 한 번 묻는다. 채점·저장·제출 동작은 그대로다.
function askReset(){
  var has = (typeof _anyAnswer === 'function') ? _anyAnswer()
    : Array.prototype.some.call(document.querySelectorAll('.blank-input,.ox-input,.essay-input'), function(el){ return el.value && el.value.trim(); });
  if (has && !confirm("적은 답이 모두 지워져요. 정말 초기화할까요?\n\n저장하려던 거라면 '취소'를 누르고 💾 저장을 누르세요.")) return;
  reset();
}
