const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const folder='exports/candidate-language',descriptions=JSON.parse(fs.readFileSync(folder+'/descriptions.json'));
 const browser=await chromium.launch({headless:true});const page=await browser.newPage({locale:'ko-KR'});
 const report={status:'RUNNING',scope:'Nine production candidate description branches with synthetic audit values; no geometry acceptance'};
 try{
  await page.goto('http://127.0.0.1:8093/case-labels');
  // Use a separate blank document to isolate the current language asset.
  await page.goto('about:blank');await page.setContent('<html><head></head><body><main id="descriptions"></main></body></html>');
  await page.addScriptTag({content:fs.readFileSync(folder+'/language.js','utf8')});
  await page.evaluate(values=>{for(const [i,description]of values.entries()){
   const section=document.createElement('section');section.dataset.index=i;
   for(const text of description.split('\n\n')){const p=document.createElement('p');p.textContent=text.replaceAll('**','');section.append(p);}
   document.querySelector('#descriptions').append(section);
  }},descriptions);
  await page.locator('[data-language=en]').click();
  const english=await page.locator('#descriptions section').allTextContents();
  for(let i=0;i<english.length;i++){
   assert(!/[가-힣]/.test(english[i]),`Untranslated candidate ${i}: ${english[i]}`);
   for(const code of descriptions[i].match(/NOT RUN|UNKNOWN|FAIL|PASS|NO_CONTACT_DETECTED/g)||[])assert(english[i].includes(code));
  }
  assert(english[0].includes('50188'));assert(english[2].includes('1.05')&&english[2].includes('65'));
  assert(english[7].includes('5/8'));
  await page.locator('[data-language=ko]').click();
  for(let i=0;i<descriptions.length;i++)assert.equal(await page.locator(`[data-index="${i}"]`).textContent(),descriptions[i].replaceAll('**','').split('\n\n').join(''));
  await page.screenshot({path:folder+'/korean.png'});
  Object.assign(report,{status:'PASS',description_branches:descriptions.length,english_no_untranslated_korean:true,korean_roundtrip_exact:true,measurement_and_status_codes_preserved:true});
 }catch(e){report.status='FAIL';report.error=String(e);process.exitCode=1;}
 finally{await browser.close();fs.writeFileSync('docs/evidence/candidate-language.json',JSON.stringify(report,null,2)+'\n');}
 console.log(JSON.stringify(report));
})().catch(e=>{console.error(e);process.exitCode=1});
