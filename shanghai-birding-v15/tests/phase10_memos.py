import os
import asyncio, json, tempfile
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
def js(rel): return (ROOT/rel).read_text(encoding='utf8')
SHELL='''<!doctype html><html><body><div id="app"></div><div id="modal-root"></div><div id="toast-root"></div></body></html>'''
ALL=['data/birds.js','data/latest_data.js','js/constants.js','js/utils.js','js/storage.js','js/state.js','js/components/modal.js','js/components/toast.js','js/modules/home.js','js/modules/settings.js']

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox','--disable-gpu'])
        page=await browser.new_page()
        await page.set_content(SHELL)
        await page.evaluate('window.indexedDB=undefined')
        for rel in ALL: await page.add_script_tag(content=js(rel))
        await page.evaluate("AppState={records:[],memos:[],memo:'',externalData:window.EXTERNAL_DATA}; AppStateActions={refreshPersonal:async()=>{AppState.memos=await Storage.getMemos();AppState.records=await Storage.getRecords();AppState.memo=AppState.memos[0]?.text||''},discoveredCount:()=>0,progressTotal:()=>BIRD_LEXICON.length,notify:()=>{}};")
        await page.evaluate("Storage.clearAll()")
        await page.evaluate("Storage.addMemo('第一条备忘').then(()=>Storage.addMemo('第二条备忘'))")
        await page.evaluate("AppStateActions.refreshPersonal().then(()=>HomePage.render())")
        assert await page.locator('[data-memo-input]').count()==2
        assert await page.locator('[data-delete-memo]').count()==2
        texts=await page.locator('[data-memo-input]').all_text_contents()
        assert texts==['第一条备忘','第二条备忘']

        # Each memo autosaves independently on blur.
        first=page.locator('[data-memo-input]').nth(0)
        await first.fill('第一条已修改')
        await first.blur()
        assert await page.evaluate("Storage.getMemos().then(xs=>xs.find(x=>x.text==='第一条已修改')?.text || '')")== '第一条已修改'

        # Add another memo through the real UI.
        await page.get_by_role('button', name='＋ 添加备忘').click()
        await page.locator('#modal-root textarea[name=text]').fill('第三条备忘')
        await page.get_by_role('button', name='保存').click()
        await page.wait_for_function("AppState.memos.length === 3")
        await page.wait_for_function("document.querySelectorAll('[data-memo-input]').length === 3")
        assert await page.locator('[data-memo-input]').count()==3

        # Delete one memo and verify the other two remain.
        await page.locator('[data-delete-memo]').nth(1).click()
        await page.get_by_role('button', name='确认').click()
        await page.wait_for_function("AppState.memos.length === 2")
        await page.wait_for_function("document.querySelectorAll('[data-memo-input]').length === 2")
        remaining=await page.locator('[data-memo-input]').all_text_contents()
        assert remaining==['第一条已修改','第三条备忘']

        # Export includes the new multi-memo payload.
        await page.evaluate("AppStateActions.refreshPersonal()")
        payload=await page.evaluate("SettingsPage.exportPayload()")
        assert len(payload['memos'])==2
        assert payload['quickMemo']=='第一条已修改'

        # Legacy single quickMemo backups remain importable.
        legacy=json.dumps({'version':1,'app':'shanghai-birding','exportedAt':'x','records':[],'quickMemo':'旧备忘'},ensure_ascii=False)
        with tempfile.NamedTemporaryFile('w',suffix='.json',delete=False,encoding='utf8') as f:
            f.write(legacy); path=f.name
        try:
            result=await page.evaluate("""(path)=>fetch(path).then(r=>r.text()).then(t=>SettingsPage.importBackup(new File([t],'legacy.json',{type:'application/json'})))""", path)
        except Exception:
            # Browser fetch cannot access a local temp file; construct the file in-page instead.
            result=await page.evaluate("SettingsPage.importBackup(new File([%s],'legacy.json',{type:'application/json'}))" % json.dumps(legacy,ensure_ascii=False))
        assert result['ok'] is True
        assert await page.evaluate("Storage.getMemos().then(xs=>xs.length)")==1
        assert await page.evaluate("Storage.getMemos().then(xs=>xs[0].text)")== '旧备忘'
        await browser.close()
    print('PHASE 10 MEMOS PASS', flush=True)
    os._exit(0)

asyncio.run(main())
