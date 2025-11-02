import csv
import requests
import cloudscraper
import time
import random
from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from perfumes.models import Perfume


class Command(BaseCommand):
    help = "Import perfumes from CSV into database with image & description from perfume page. Designed to stop and resume cleanly on 429 rate limit errors."

    # Define a list of User Agents for rotation
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0',
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize the cloudscraper client
        self.scraper = cloudscraper.create_scraper() 
        self.base_headers = {
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/",
        }

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to the CSV file")

    def handle(self, *args, **options):
        file_path = options["csv_file"]
        self.stdout.write(f"📖 Reading CSV file: {file_path}")

        imported = 0
        row_count = 0

        with open(file_path, mode="r", encoding="utf-8", errors="ignore") as csvfile:
            reader = csv.DictReader(csvfile, delimiter=";")
            for row in reader:
                row_count += 1
                try:
                    name = (row.get("Perfume") or "").strip()
                    brand = (row.get("Brand") or "").strip()
                    url = (row.get("url") or "").strip()

                    if not name or not brand:
                        continue

                    # --- RESUME LOGIC: Check if it exists and is complete before proceeding ---
                    
                    # 1. Attempt to find an existing entry
                    existing_perfumes = Perfume.objects.filter(name=name, brand=brand)
                    
                    if existing_perfumes.exists():
                        perfume = existing_perfumes.first()
                        
                        # If the description AND image are present, this row is COMPLETE. Skip it.
                        if perfume.description and perfume.image: 
                            self.stdout.write(f"➡️ Skipping row {row_count}: {name} ({brand}) already complete.")
                            continue
                        
                        # If it exists but is incomplete (missing data), we treat it as not 'created' 
                        # so the scraping logic runs to fill in the gaps.
                        created = False 
                    
                    else:
                        # 2. If it does not exist, create the entry from the CSV data
                        perfume = Perfume.objects.create(
                            name=name,
                            brand=brand,
                            url=url,
                            country=(row.get("Country") or "").strip(),
                            gender=(row.get("Gender") or "").strip(),
                            rating_value=(row.get("Rating Value") or "").replace(",", ".") or None,
                            rating_count=row.get("Rating Count") or None,
                            year=(row.get("Year") or "").strip(),
                            top_notes=(row.get("Top") or "").strip(),
                            middle_notes=(row.get("Middle") or "").strip(),
                            base_notes=(row.get("Base") or "").strip(),
                            perfumer1=(row.get("Perfumer1") or "").strip(),
                            perfumer2=(row.get("Perfumer2") or "").strip(),
                            mainaccord1=(row.get("mainaccord1") or "").strip(),
                            mainaccord2=(row.get("mainaccord2") or "").strip(),
                            mainaccord3=(row.get("mainaccord3") or "").strip(),
                            mainaccord4=(row.get("mainaccord4") or "").strip(),
                            mainaccord5=(row.get("mainaccord5") or "").strip(),
                        )
                        created = True
                    
                    # --- Scraping Logic: Runs if newly created OR if existing but incomplete ---
                    if url:
                        # Pass row_count for better error tracking
                        image_url, description = self.scrape_fragrantica(url, name, row_count)
                        
                        update_fields = []

                        # Only update if the field is currently missing AND we found data
                        if image_url and not perfume.image: 
                            perfume.image_url = image_url
                            self.download_and_attach_image(perfume, image_url)
                            self.stdout.write(f"🖼️ Added image for {name}")
                            update_fields.append("image_url")

                        if description and not perfume.description:
                            perfume.description = description
                            self.stdout.write(f"📝 Added description for {name}")
                            update_fields.append("description")
                        
                        if update_fields:
                            perfume.save(update_fields=update_fields)
                            if created:
                                imported += 1
                    
                    # --- MODIFIED: LONGER RANDOM DELAY AFTER A SUCCESSFUL/ATTEMPTED SCRAPE (8-15s) ---
                    time.sleep(random.uniform(8, 15))

                except Exception as e:
                    self.stderr.write(f"⚠️ Error importing row {row_count} ({row.get('Perfume')}): {e}")

        self.stdout.write(self.style.SUCCESS(f"✅ Imported {imported} new perfumes with images & descriptions"))

    # --- UPDATED SCRAPING METHOD WITH INCREASED RETRY LOGIC AND EXIT ---
    def scrape_fragrantica(self, url, name, row_num, max_retries=10): # <-- MODIFIED: max_retries=10
        """Scrape perfume with retry logic for 429 errors and image URL correction. Exits script on max failure."""
        
        for attempt in range(max_retries):
            try:
                # Prepare Headers and Request
                headers = self.base_headers.copy()
                headers["User-Agent"] = random.choice(self.USER_AGENTS)
                res = self.scraper.get(url, headers=headers, timeout=15, allow_redirects=True) 
                
                # Check for 429 error and implement exponential backoff
                if res.status_code == 429:
                    # --- CRITICAL EXIT LOGIC ---
                    if attempt == max_retries - 1:
                        self.stderr.write(f"⛔ CRITICAL 429 at row {row_num}: Max retries hit for {name}. Stopping execution to allow manual cooldown.")
                        self.stderr.write(self.style.ERROR(f"Script stopped due to persistent rate limiting (429). Last uncompleted row: {row_num}. Wait 30 minutes and run the script again to resume."))
                        exit(1) # Stop the script execution
                        
                    wait_time = (2 ** attempt) + random.uniform(1, 3) 
                    self.stdout.write(f"⏳ Attempt {attempt+1}/{max_retries}: 429 Rate Limit hit for {name}. Waiting {wait_time:.2f}s...")
                    time.sleep(wait_time)
                    continue 
                
                if res.status_code != 200:
                    self.stderr.write(f"🚫 Request failed for {url}. Status code: {res.status_code}")
                    return None, None

                # Success, proceed to scraping
                soup = BeautifulSoup(res.text, "html.parser")

                # --- Image URL Correction ---
                image_url = None
                img_tag = soup.select_one('img[itemprop="image"]')
                if img_tag:
                    image_url = img_tag.get('src') or img_tag.get('data-src')
                
                # Fallback to Open Graph/Metadata (if primary selector failed)
                if not image_url:
                    og_image = soup.select_one("meta[property='og:image']")
                    image_url = og_image.get("content") if og_image else None
                
                # If the image URL is a low-res thumbnail, correct it
                if image_url and 'perfume-thumbs' in image_url:
                    image_url = image_url.replace('perfume-thumbs', 'perfume')

                # --- Description Extraction ---
                og_desc = soup.select_one("meta[property='og:description']")
                description = og_desc.get("content").strip() if og_desc else None
                
                if description:
                    description = description.replace("&amp;", "&").replace("&quot;", '"') 
                
                if not description:
                    desc_div = soup.select_one("div[itemprop='description']")
                    if not desc_div:
                        desc_div = soup.select_one(".pgridCell p")
                    description = desc_div.get_text(strip=True) if desc_div else None
                
                return image_url, description

            except Exception as e:
                self.stderr.write(f"⚠️ Scrape error for {url}: {e}")
                time.sleep(5) 
                continue

        return None, None

    # --- DOWNLOAD METHOD ---
    def download_and_attach_image(self, perfume, image_url):
        """Download image and attach to Perfume model"""
        try:
            # Prepare Headers with Rotating User-Agent
            headers = self.base_headers.copy()
            headers["User-Agent"] = random.choice(self.USER_AGENTS)

            # Use the instance scraper for the download request too
            res = self.scraper.get(image_url, headers=headers, timeout=15)
            
            if res.status_code == 200:
                file_name = image_url.split("/")[-1].split("?")[0]
                if '.' not in file_name:
                    file_name += '.jpg' 
                
                perfume.image.save(file_name, ContentFile(res.content), save=True)
            else:
                self.stderr.write(f"⚠️ Image download failed for {perfume.name}. Status code: {res.status_code} for URL: {image_url}")

        except Exception as e:
            self.stderr.write(f"⚠️ Download error for {perfume.name}: {e}")