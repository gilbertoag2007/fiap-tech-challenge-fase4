const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

let browser, server, base;
const frontend = path.resolve(__dirname, '../../analise-medica-frontend');
const videoId = 'a'.repeat(20);
const jobId = 'b'.repeat(32);
const report = {
  exercise: 'Abdução do braço direito',
  video: { id:videoId, person_id:1, camera:17, fps:30 },
  summary: {total:2, correct:1, incorrect:0, nonconclusive:1, mean_pose_coverage:.7},
  repetitions: [
    {repetition_number:1, start_seconds:2, end_seconds:4, first_frame:60, status:'Correto', prediction:1, reference_label:1, agreement:true, coverage:1, series:[{ombro_direito:90},{ombro_direito:100}]},
    {repetition_number:2, start_seconds:5, end_seconds:7, first_frame:150, status:'Não conclusivo', prediction:null, reference_label:0, agreement:null, coverage:.4, reason:'Postura insuficiente', series:[]}
  ], limitations:['Avaliação acadêmica binária.']
};

before(async () => {
  server = http.createServer((req,res) => {
    const relative = decodeURIComponent(new URL(req.url,'http://localhost').pathname);
    const target = path.resolve(frontend,'.'+relative);
    if(!target.startsWith(frontend+path.sep)) { res.writeHead(403).end(); return; }
    fs.readFile(target,(error,body) => {
      if(error) {res.writeHead(404).end();return;}
      const types={'.html':'text/html','.js':'text/javascript','.css':'text/css'};
      res.setHeader('Content-Type',types[path.extname(target)]||'application/octet-stream');
      res.end(body);
    });
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  base='http://127.0.0.1:'+server.address().port;
  browser=await chromium.launch({headless:true});
});
after(async()=>{if(browser) await browser.close(); if(server) await new Promise(resolve=>server.close(resolve));});

async function fixture(page,{failure=false}={}) {
  await page.route('**/v1/fisioterapia/**',async route=>{
    const url=new URL(route.request().url());
    const headers={'access-control-allow-origin':'*','content-type':'application/json'};
    if(failure) return route.fulfill({status:503,headers,body:JSON.stringify({detail:'Dataset não preparado.'})});
    if(route.request().method()==='OPTIONS') return route.fulfill({status:204,headers:{...headers,'access-control-allow-methods':'GET,POST','access-control-allow-headers':'Content-Type'}});
    let data;
    if(url.pathname.endsWith('/catalogo')) data={exercises:[{id:1,name:'Abdução do braço direito'}],videos:[{id:videoId,recording_id:'PM_001',exercise_id:1,person_id:1,camera:17,fps:30,width:64,height:48,frame_count:300}]};
    else if(url.pathname.includes('/videos/')) return route.fulfill({status:200,contentType:'video/mp4',body:Buffer.alloc(0)});
    else if(url.pathname.endsWith('/relatorio')) data=report;
    else if(url.pathname.endsWith('/pose')) data={fps:30,points:[]};
    else data={id:jobId,video_id:videoId,status:'concluido',progress:1,report_url:`/v1/fisioterapia/analises/${jobId}/relatorio`,pose_url:`/v1/fisioterapia/analises/${jobId}/pose`};
    return route.fulfill({status:route.request().method()==='POST'?202:200,headers,body:JSON.stringify(data)});
  });
}

test('análise apresenta repetições, resultado não conclusivo e relatório para download',async()=>{
  const page=await browser.newPage();
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await fixture(page);
  await page.goto(base+'/pages/fisioterapia.html');
  await page.getByLabel('Exercício', {exact:true}).selectOption('1');
  await page.getByLabel('Câmera', {exact:true}).selectOption('17');
  await page.getByRole('button',{name:'Analisar vídeo',exact:true}).click();
  await page.getByRole('heading',{name:'Resultado da análise'}).waitFor();
  assert.equal(await page.locator('#repetitions-body tr').count(),2);
  assert.match(await page.locator('#repetitions-body').innerText(),/Não conclusivo/);
  await page.getByRole('button',{name:'Ver repetição 1',exact:true}).click();
  assert.match(await page.locator('#selected-repetition').innerText(),/1/);
  const downloadPromise=page.waitForEvent('download');
  await page.getByRole('button',{name:'Baixar relatório JSON'}).click();
  const download=await downloadPromise;
  assert.match(download.suggestedFilename(),/fisioterapia.*\.json$/);
  assert.deepEqual(errors,[]);
  await page.setViewportSize({width:390,height:844});
  const fitsViewport = await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth);
  if(!fitsViewport) {
    console.log('Mobile overflow',await page.evaluate(()=>[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>({tag:e.tagName,id:e.id,class:e.className,width:e.getBoundingClientRect().width,right:e.getBoundingClientRect().right})).slice(0,15)));
    fs.mkdirSync('playwright-output',{recursive:true});
    await page.screenshot({path:'playwright-output/mobile-overflow.png',fullPage:true});
  }
  assert.equal(fitsViewport,true);
  await page.close();
});

test('configuração ausente mostra mensagem e bloqueia iniciar análise',async()=>{
  const page=await browser.newPage();
  await fixture(page,{failure:true});
  await page.goto(base+'/pages/fisioterapia.html');
  await page.getByRole('alert').filter({hasText:'Dataset não preparado'}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Analisar vídeo',exact:true}).isDisabled(),true);
  await page.close();
});

test('menu principal mantém acesso a sinais vitais e oferece fisioterapia',async()=>{
  const page=await browser.newPage();
  await page.goto(base+'/index.html');
  assert.ok(await page.getByRole('link',{name:'Sinais Vitais',exact:true}).count());
  await page.getByRole('link',{name:'Fisioterapia',exact:true}).click();
  assert.match(page.url(),/fisioterapia\.html$/);
  await page.close();
});

test('quatro exercícios com API, vídeos, modelos e relatório reais', {skip:!process.env.FIAP_REAL_API}, async()=>{
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto(base+'/pages/fisioterapia.html');
  await page.waitForFunction(()=>document.querySelector('#exercise-select').options.length===4);
  fs.mkdirSync('playwright-output',{recursive:true});
  for(const exercise of ['1','2','3','4']) {
    await page.getByLabel('Exercício',{exact:true}).selectOption(exercise);
    await page.getByLabel('Câmera',{exact:true}).selectOption('17');
    if(exercise==='1') {
      const mixed=await page.locator('#video-select option').evaluateAll(options=>options.find(option=>option.textContent.startsWith('PM_001 '))?.value);
      assert.ok(mixed,'Gravação PM_001 com repetições das duas classes deve estar presente.');
      await page.getByLabel('Vídeo',{exact:true}).selectOption(mixed);
    }
    await page.waitForFunction(()=>document.querySelector('video').readyState>=1);
    const selected=await page.locator('#video-select').inputValue();
    await page.getByRole('button',{name:'Analisar vídeo',exact:true}).click();
    await page.getByRole('heading',{name:'Resultado da análise'}).waitFor({timeout:90000});
    const count=await page.locator('#repetitions-body tr').count();
    assert.ok(count>0,'Deve haver repetições reais no relatório.');
    await page.getByRole('button',{name:'Ver repetição 1',exact:true}).click();
    const promise=page.waitForEvent('download');
    await page.getByRole('button',{name:'Baixar relatório JSON'}).click();
    const download=await promise;
    const result=JSON.parse(fs.readFileSync(await download.path(),'utf8'));
    assert.equal(result.video.id,selected);
    assert.equal(result.video.exercise_id,Number(exercise));
    assert.equal(result.summary.total,count);
    assert.equal(result.summary.correct+result.summary.incorrect+result.summary.nonconclusive,count);
    assert.ok(result.repetitions.every(rep=>!rep.training_participants.includes(result.video.person_id)));
    if(exercise==='1') {
      assert.equal(result.repetitions[0].reference_label,1);
      assert.equal(result.repetitions[5].reference_label,0);
    }
    await page.waitForFunction(expected=>Math.abs(document.querySelector('video').currentTime-expected)<.2,result.repetitions[0].start_seconds);
    await page.waitForFunction(()=>document.querySelector('video').readyState>=2);
    await page.screenshot({path:`playwright-output/real-ex${exercise}.png`,fullPage:true});
  }
  assert.deepEqual(errors,[]);
  await page.close();
});
