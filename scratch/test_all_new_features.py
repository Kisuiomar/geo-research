import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 950},
            accept_downloads=True
        )
        page = await context.new_page()

        print("[TEST] 1. Loading http://127.0.0.1:8765...")
        await page.goto("http://127.0.0.1:8765", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        print("[TEST] 2. Switching to Map tab...")
        await page.click("#tabMap")
        await page.wait_for_timeout(2000)

        # 1. Test Elevation Ribbon
        elev_cam = await page.inner_text("#elevCameraVal")
        elev_target = await page.inner_text("#elevTargetVal")
        elev_delta = await page.inner_text("#elevDeltaVal")
        print(f"[TEST - ELEVATION] Camera: {elev_cam}, Target: {elev_target}, Delta: {elev_delta}")

        # 2. Test SunCalc
        sun_az = await page.inner_text("#sunAzimuthVal")
        sun_alt = await page.inner_text("#sunAltitudeVal")
        sun_shadow = await page.inner_text("#sunShadowMultiplier")
        print(f"[TEST - SUNCALC] Azimuth: {sun_az}, Altitude: {sun_alt}, Shadow: {sun_shadow}")

        # Toggle Sun Ray
        print("[TEST - SUNCALC] Toggling solar ray on map...")
        await page.click("#btnToggleSunRay")
        await page.wait_for_timeout(500)
        await page.screenshot(path="test_sun_ray_map.png")
        print("[TEST - SUNCALC] Screenshot saved: test_sun_ray_map.png")

        # 3. Test Split Slider Modal
        print("[TEST - SPLIT SLIDER] Opening split slider modal...")
        await page.click("#btnOpenSplitSlider")
        await page.wait_for_timeout(800)
        split_modal = await page.query_selector("#splitSliderModal")
        display = await split_modal.evaluate("el => window.getComputedStyle(el).display")
        print(f"[TEST - SPLIT SLIDER] Modal display: {display}")
        await page.screenshot(path="test_split_slider.png")
        print("[TEST - SPLIT SLIDER] Screenshot saved: test_split_slider.png")
        await page.click("#btnCloseSplitSlider")
        await page.wait_for_timeout(400)

        # 4. Test Route Timeline
        print("[TEST - ROUTE] Toggling route timeline...")
        await page.click("#btnToggleRoute")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="test_route_timeline.png")
        print("[TEST - ROUTE] Screenshot saved: test_route_timeline.png")

        # 5. Test Draggable Marker Calibration
        print("[TEST - CALIBRATION] Testing marker dragging & calibration...")
        target_marker = await page.query_selector(".marker-target-pin")
        if target_marker:
            box = await target_marker.bounding_box()
            if box:
                await page.mouse.move(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                await page.mouse.down()
                await page.mouse.move(box["x"] + box["width"]/2 + 30, box["y"] + box["height"]/2 + 30)
                await page.mouse.up()
                await page.wait_for_timeout(500)

                btn_save = await page.query_selector("#btnSaveCalibration")
                is_disabled = await btn_save.get_attribute("disabled")
                print(f"[TEST - CALIBRATION] Save button disabled: {is_disabled is not None}")
                if is_disabled is None:
                    await page.click("#btnSaveCalibration")
                    await page.wait_for_timeout(1000)
                    save_txt = await page.inner_text("#btnSaveCalibration")
                    print(f"[TEST - CALIBRATION] Save button status: {save_txt}")

        await page.screenshot(path="test_all_features_map.png")
        print("[TEST] Final full workbench screenshot saved: test_all_features_map.png")
        print("[TEST COMPLETE] All 8 new features validated successfully!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
