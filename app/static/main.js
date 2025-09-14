async function loadReviews(itemId){
  const res = await fetch(`/reviews/for/${itemId}`);
  const js = await res.json();
  const list = js.success ? js.data : [];
  document.getElementById('revCount').textContent = list.length;

  const wrap = document.getElementById('reviewsWrap');
  if(!list.length){
    wrap.innerHTML = `<div class="alert alert-info">No reviews yet.</div>`;
    return;
  }
  wrap.innerHTML = list.map((r,idx)=>`
    <div class="card mb-2">
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-start">
          <h6 class="mb-1">${escapeHtml(r.title)}</h6>
          <span class="badge ${r.recommended? 'bg-success':'bg-secondary'}">
            ${r.recommended? 'Recommended':'Not Recommended'}
          </span>
        </div>
        <div class="text-warning small mb-1">${"★".repeat(r.rating)}${"☆".repeat(5-r.rating)}</div>
        <p class="mb-2">${escapeHtml(r.review_text)}</p>
        <div class="d-flex justify-content-between text-muted small">
          <span>Age: ${r.age||'-'}</span>
          <span>
            Helpful: <b>${r.positive_feedback||0}</b>
            <button class="btn btn-sm btn-link" onclick="thumbUp(${itemId},${idx})">+1</button>
          </span>
        </div>
      </div>
    </div>`).join('');
}

async function thumbUp(itemId, idx){
  await fetch(`/reviews/thumb-up`, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({item_id:itemId, index:idx})
  });
  loadReviews(itemId);
}

function wireNewReview(itemId){
  const form = document.getElementById('reviewForm');
  const btnSuggest = document.getElementById('btnSuggest');
  const aiHint = document.getElementById('aiHint');
  const aiLabel = document.getElementById('aiLabel');
  const aiProb = document.getElementById('aiProb');

  btnSuggest.addEventListener('click', async ()=>{
    const data = formToJSON(form);
    const r = await fetch('/reviews/ai', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ title:data.title, review_text:data.review_text })
    });
    const js = await r.json();
    if(js.success){
      aiHint.classList.remove('d-none');
      aiLabel.textContent = js.recommendation ? 'Positive' : 'Negative';
      aiProb.textContent = Math.round(js.confidence*100)+'%';
    }
  });

  form.addEventListener('submit', async (e)=>{
    e.preventDefault();
    const data = formToJSON(form);
    data.item_id = itemId;
    const r = await fetch('/reviews', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify(data)
    });
    const js = await r.json();
    if(js.success){
      const modal = bootstrap.Modal.getInstance(document.getElementById('newReviewModal'));
      modal.hide();
      form.reset(); aiHint.classList.add('d-none');
      loadReviews(itemId);
    }else{
      alert(js.error||'Failed');
    }
  });
}

function formToJSON(form){
  const fd = new FormData(form); const o={};
  for(const [k,v] of fd.entries()) o[k]=v;
  o.rating = Number(o.rating||0);
  o.age = Number(o.age||0);
  return o;
}
function escapeHtml(s){ return (s||'').replace(/[&<>"']/g, m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[m])); }