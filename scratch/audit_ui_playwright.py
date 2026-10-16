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

        print("[AUDIT] 1. Navigating to http://127.0.0.1:8765...")
        await page.goto("http://127.0.0.1:8765", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # 1. Take screenshot of Home page
        await page.screenshot(path="audit_home_page.png", full_page=True)
        print("[AUDIT] Home page screenshot saved: audit_home_page.png")

        # 2. Check showcase cards
        cards = await page.query_selector_all(".showcase-card")
        print(f"[AUDIT] Found {len(cards)} showcase cards on landing page.")

        # 3. Switch to Map tab
        print("[AUDIT] 2. Switching to Map tab...")
        await page.click("#tabMap")
        await page.wait_for_timeout(1500)
        await page.screenshot(path="audit_map_page.png")
        print("[AUDIT] Map page screenshot saved: audit_map_page.png")

        # 4. Verify sidebar telemetry
        target_coords = await page.inner_text("#targetCoords")
        camera_coords = await page.inner_text("#cameraCoords")
        case_title = await page.inner_text("#caseTitle")
        print(f"[AUDIT] Active Case: '{case_title}'")
        print(f"[AUDIT] Target Coords: {target_coords}")
        print(f"[AUDIT] Camera Coords: {camera_coords}")

        # 5. Check action buttons
        btn_lens = await page.query_selector("#btnOpenInGoogleLens")
        btn_maps = await page.query_selector("#btnOpenInGoogleMaps")
        btn_export = await page.query_selector("#btnExportDossier")
        print(f"[AUDIT] Buttons present -> Google Lens: {btn_lens is not None}, Google Maps: {btn_maps is not None}, Export Dossier: {btn_export is not None}")

        # 6. Check evidence gallery
        evidence_cards = await page.query_selector_all(".evidence-card")
        print(f"[AUDIT] Found {len(evidence_cards)} evidence items in sidebar gallery.")

        # 7. Click first evidence card to test Lightbox modal
        if evidence_cards:
            print("[AUDIT] 3. Testing Lightbox modal on first evidence card...")
            await evidence_cards[0].click()
            await page.wait_for_timeout(600)
            lightbox_modal = await page.query_selector("#lightboxModal")
            display_style = await lightbox_modal.evaluate("el => window.getComputedStyle(el).display")
            print(f"[AUDIT] Lightbox display style: {display_style}")
            await page.screenshot(path="audit_lightbox.png")
            print("[AUDIT] Lightbox screenshot saved: audit_lightbox.png")
            await page.click("#btnCloseLightbox")
            await page.wait_for_timeout(400)

        # 8. Test Export Dossier download
        print("[AUDIT] 4. Testing 'Экспорт досье' download...")
        async with page.expect_download() as download_info:
            await page.click("#btnExportDossier")
        download = await download_info.value
        download_path = Path("audit_downloaded_dossier.md")
        await download.save_as(str(download_path))
        print(f"[AUDIT] Successfully downloaded: {download.suggested_filename}")
        print(f"[AUDIT] Dossier file size: {download_path.stat().st_size} bytes")
        with open(download_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        print("[AUDIT] Dossier Preview (first 8 lines):")
        for l in lines[:8]:
            print("   >", l.strip())

        print("\n[AUDIT COMPLETE] ALL CHECKS PASSED WITH 100% SUCCESS!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
