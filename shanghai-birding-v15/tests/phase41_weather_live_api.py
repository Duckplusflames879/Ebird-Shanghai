import asyncio
import json
import os
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]

def js(rel):
    return (ROOT / rel).read_text(encoding='utf8')

def make_payload():
    dates = [f'2026-09-{i:02d}' for i in range(3, 10)]
    return {
        'latitude': 31.2304,
        'longitude': 121.4737,
        'timezone': 'Asia/Shanghai',
        'current': {
            'time': '2026-09-03T08:20',
            'temperature_2m': 29.4,
            'relative_humidity_2m': 78,
            'apparent_temperature': 34.1,
            'is_day': 1,
            'weather_code': 2,
            'wind_speed_10m': 13.2,
            'wind_direction_10m': 120,
        },
        'daily': {
            'time': dates,
            'weather_code': [2, 3, 61, 63, 1, 0, 2],
            'temperature_2m_max': [32, 31, 29, 28, 33, 34, 32],
            'temperature_2m_min': [27, 26, 25, 24, 26, 27, 27],
            'wind_direction_10m_dominant': [135, 90, 45, 0, 90, 135, 180],
            'wind_speed_10m_max': [16, 20, 22, 18, 12, 10, 14],
            'precipitation_probability_max': [20, 45, 80, 70, 15, 5, 20],
            'precipitation_sum': [0, 1.2, 6.4, 9.1, 0, 0, 0.3],
            'sunrise': [f'2026-09-{i:02d}T05:25' for i in range(3, 10)],
            'sunset': [f'2026-09-{i:02d}T18:10' for i in range(3, 10)],
        },
    }

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox', '--disable-gpu'])
        page = await browser.new_page()
        await page.set_content('<div id="app"></div>')
        await page.add_script_tag(content=js('js/constants.js'))
        await page.add_script_tag(content=js('js/utils.js'))
        await page.add_script_tag(content="window.AppState={externalData:{weather:null,hotspots:[],updatedAt:null,sourceStatus:'unknown'}};")

        payload = make_payload()
        await page.add_script_tag(content=js('js/modules/weather.js'))
        await page.evaluate("window.__weatherFetchCount=0; window.fetch=async()=>{window.__weatherFetchCount++; return {ok:true, json:async()=>JSON.parse(%s)};}" % json.dumps(json.dumps(payload)))

        await page.evaluate("(async()=>{await WeatherPage.render();})()")
        assert await page.locator('.weather-day').count() == 7
        assert 'Open-Meteo' in await page.locator('.card').first.inner_text()
        assert '29°C' in await page.locator('.weather-live').inner_text()
        assert '湿度 78%' in await page.locator('.weather-live').inner_text()
        assert (await page.locator('.weather-day').nth(0).inner_text()).count('降水') == 1
        initial_fetch_count = await page.evaluate('window.__weatherFetchCount')
        assert initial_fetch_count >= 1

        await page.locator('.weather-day').nth(2).click()
        assert '2026-09-05' in await page.locator('.card').filter(has_text='2026-09-05').last.inner_text()
        assert await page.evaluate('window.__weatherFetchCount') == initial_fetch_count

        await page.locator('#refresh-weather').click()
        await page.wait_for_timeout(50)
        assert await page.evaluate('window.__weatherFetchCount') == initial_fetch_count + 1

        await browser.close()
    print('PHASE 41 WEATHER LIVE API PASS', flush=True)
    os._exit(0)

asyncio.run(main())
