const {test} = require('node:test');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');

test('Render build generates public configuration and rejects non-HTTPS API',()=>{
  const output = fs.mkdtempSync(path.join(os.tmpdir(), 'fiap-render-'));
  const script = path.resolve('scripts/build-render-frontend.py');
  try {
    execFileSync('python3', [script, '--output', output], {env:{...process.env, API_BASE_URL:'https://api.example.com/', DEMO_MODE:'1'}});
    const window = {};
    vm.runInNewContext(fs.readFileSync(path.join(output,'assets/js/runtime-config.js'),'utf8'), {window});
    assert.equal(window.APP_CONFIG.apiBaseUrl, 'https://api.example.com');
    assert.equal(window.APP_CONFIG.demoMode,true);
    for (const file of ['index.html','pages/sinais-vitais.html','pages/fisioterapia.html']) {
      const html=fs.readFileSync(path.join(output,file),'utf8');
      assert.ok(html.indexOf('runtime-config.js') < html.indexOf('config.js"'));
      assert.match(html,/demo-notice/);
    }
    assert.throws(()=>execFileSync('python3',[script,'--output',output],{env:{...process.env,API_BASE_URL:'http://example.com',DEMO_MODE:'1'},stdio:'pipe'}));
  } finally { fs.rmSync(output,{recursive:true,force:true}); }
});
