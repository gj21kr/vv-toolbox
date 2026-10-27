const {chromium}=require('playwright');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1280,height:1000},locale:'en-US'});
 const base='http://127.0.0.1:8093',rows=[];
 try{
  await page.route(base+'/ui-language.js',r=>r.fulfill({contentType:'application/javascript',body:fs.readFileSync('exports/language-ui/language.js','utf8')}));
  for(const path of ['/','/case-labels']){
   await page.goto(base+path);
   await page.waitForFunction(()=>window.VVLanguage);
   if(path==='/'){
    await page.waitForFunction(()=>state?.atlas?.parts?.length);
    await page.waitForFunction(()=>document.querySelector('#boundaryFrame')?.textContent.includes('bodyparts3d_native_LPS'));
   }
   await page.locator('[data-language=en]').click();
   const missing=await page.evaluate(()=>{
    const out=[],walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
    while(walker.nextNode()){
     const n=walker.currentNode,p=n.parentElement,text=n.nodeValue.trim();
     if(!p||p.closest('script,style,textarea,code,pre,#vv-language')||!/[가-힣]/.test(text))continue;
     out.push({text,element:p.id||p.tagName});
    }
    return out;
   });
   rows.push({path,untranslated:[...new Map(missing.map(r=>[r.text,r])).values()]});
   await page.locator('[data-language=ko]').click();
   const english=await page.evaluate(()=>{
    const names=typeof state!=='undefined'?(state?.atlas?.parts||[]).map(p=>p.name).filter(Boolean):[];
    const out=[],walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
    while(walker.nextNode()){
     const n=walker.currentNode,p=n.parentElement,text=n.nodeValue.trim();
     if(!p||p.closest('script,style,textarea,code,pre,#vv-language')||!/[A-Za-z]{3}/.test(text)||/[가-힣]/.test(text))continue;
     if(/^([← ]*VV Toolbox.*|ATLAS|NOT RUN|UNKNOWN|PASS|FAIL|[MAP][123]|ACom|PCom)$/.test(text))continue;
     if(names.some(name=>text.includes(name)))continue;
     out.push({text,element:p.id||p.tagName});
    }return out;
   });
   rows[rows.length-1].english_in_korean=[...new Map(english.map(r=>[r.text,r])).values()];
  }
 }finally{await browser.close();}
 const report={scope:'Rendered initial pages including hidden UI nodes; not every interaction or error branch',rows};
 fs.writeFileSync('docs/evidence/ui-language-gap-audit.json',JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify(report));
})().catch(e=>{console.error(e);process.exitCode=1});
