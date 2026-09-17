function filterCustomers(){
  const q = document.getElementById('cust-search').value.toLowerCase();
  const rows = document.querySelectorAll('#cust-list tr');
  rows.forEach(r=>{r.style.display = (r.innerText.toLowerCase().includes(q)) ? '' : 'none'});
}

// Invoice builder helpers
let rowCount = 1;
function addRow(){
  const container = document.getElementById('items');
  const idx = rowCount++;
  const div = document.createElement('div'); div.className='item-row form-row align-items-center mb-2';
   div.innerHTML = `
    <div class="form-group col-md-4">
      <select name="item_product_${idx}" class="product-pick form-control" onchange="onProductChange(this,${idx})">
        <option value="">-- product --</option>
      </select>
    </div>
    <div class="form-group col-md-1">
      <input name="item_qty_${idx}" value="1" type="number" min="1" onchange="recalc()" class="form-control">
    </div>
    <div class="col-md-2 col-amount unit">₹0.00</div>
    <div class="col-md-2 amount">₹0.00</div>
    <div class="col-md-1">
      <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeRow(this)">Delete</button>
    </div>
  `;
  container.appendChild(div);
  // copy product options
  const template = document.querySelector('.item-row select');
  const opts = template.innerHTML;
  div.querySelector('select').innerHTML = opts;
}

function onProductChange(sel, idx){
  recalc();
}

function recalc(){
  let total = 0;
  document.querySelectorAll('#items .item-row').forEach((row, i)=>{
    const qtyInput = row.querySelector('input[type="number"]');
    const qty = parseFloat(qtyInput?.value||1);
    const sel = row.querySelector('select');
    const price = parseFloat(sel?.selectedOptions[0]?.dataset?.price || 0);
    const amt = qty * price;
    total += amt;
    const amtEl = row.querySelector('.amount');
    const unitEl = row.querySelector('.col-amount.unit');
    if(unitEl) unitEl.innerText = '₹' + price.toFixed(2);
    if(amtEl) amtEl.innerText = '₹' + amt.toFixed(2);
  });
  const totalEl = document.getElementById('total'); if(totalEl) totalEl.innerText = total.toFixed(2);
}

function removeRow(btn){
  const row = btn.closest('.item-row');
  if(row) row.remove();
  recalc();
}

// copy product options from server-provided select
window.addEventListener('DOMContentLoaded', ()=>{
  const templates = document.querySelectorAll('.product-pick');
  if(templates.length>0){
    fetch('/api/products_active').then(r=>r.json()).then(data=>{
      const opts = data.map(p=>`<option value="${p.id}" data-price="${p.price}">${p.name}</option>`).join('');
      templates.forEach(t=>{ t.innerHTML = `<option value="">-- product --</option>` + opts });
    }).finally(()=>recalc());
  }
  // initialize cart count badge
  fetch('/api/cart_count').then(r=>r.json()).then(data=>{
    if(data && typeof data.count !== 'undefined') updateCartCount(data.count);
  }).catch(()=>{});
});

// Cart helpers
function addToCart(productId, qty=1){
  fetch('/cart/add', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({product_id: productId, quantity: qty})})
    .then(r=>r.json()).then(data=>{
      if(data && data.ok){
        updateCartCount(data.count || 0);
      } else {
        console.error('Could not add to cart', data);
      }
    }).catch(()=>alert('Error adding to cart'));
}

function removeFromCart(productId){
  fetch('/cart/remove', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({product_id: productId})})
    .then(r=>r.json()).then(data=>{ if(data && data.ok){ updateCartCount(data.count || 0); location.reload(); } else { console.error('Could not remove', data); } })
    .catch(()=>alert('Error'));
}

function updateCartCount(n){
  const el = document.getElementById('cart-count');
  if(!el) return;
  if(n && n>0){
    el.style.display = 'inline-block';
    el.innerText = n;
  } else {
    el.style.display = 'none';
    el.innerText = '0';
  }
}

// wire up add-to-cart buttons if present
document.addEventListener('click', function(e){
  const btn = e.target.closest('.add-to-cart');
  if(btn){
    const id = btn.dataset.id;
    addToCart(id, 1);
  }
});
