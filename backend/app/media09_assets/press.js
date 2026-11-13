'use strict';
const form=document.querySelector('#inquiry'), result=document.querySelector('#result'), submit=document.querySelector('#submit');
let key=crypto.randomUUID();
form.addEventListener('submit',async event=>{
 event.preventDefault(); submit.disabled=true; result.classList.remove('error'); result.textContent='Submitting…';
 const data=new FormData(form); const payload={synthetic:form.dataset.mode!=='real',idempotency_key:key,name:data.get('name'),email:data.get('email'),subject:data.get('subject'),message:data.get('message'),kind:data.get('kind'),company:data.get('company'),privacy_notice_version:form.dataset.notice||'MEDIA-09.1-SYNTHETIC-NOTICE-V1',privacy_notice_acknowledged:true};
 try{
  const response=await fetch('/press/inquiries',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-SC-Form':document.querySelector('#form-token').value},body:JSON.stringify(payload)});
  const body=await response.json();
  if(!response.ok) throw new Error(response.status===429?'Too many test inquiries. Please wait a minute and try again.':typeof body.detail==='string'?body.detail:'The service is unavailable. Please try again later.');
  result.textContent='Inquiry received. Reference: '+body.inquiry_id+(form.dataset.mode==='real'?'. Our team will review your request.':'. This is a staging test; no email will be sent.');
  form.reset(); key=crypto.randomUUID();
 }catch(error){result.classList.add('error'); result.textContent=error instanceof TypeError?'Connection interrupted. Retry without changing the form to safely check receipt.':error.message;}
 finally{submit.disabled=false;}
});
