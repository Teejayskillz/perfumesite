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

    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0',
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        start_line = 5200  # 👈 Start importing from this line

        with open(file_path, mode="r", encoding="utf-8", errors="ignore") as csvfile:
            reader = csv.DictReader(csvfile, delimiter=";")
            for row in reader:
                row_count += 1

                # Skip lines before the specified start line
                if row_count < start_line:
                    continue

                try:
                    name = (row.get("Perfume") or "").strip()
                    brand = (row.get("Brand") or "").strip()
                    url = (row.get("url") or "").strip()

                    if not name or not brand:
                        continue

                    existing_perfumes = Perfume.objects.filter(name=name, brand=brand)

                    if existing_perfumes.exists():
                        perfume = existing_perfumes.first()

                        # Skip if this perfume already has both description and image
                        if perfume.description and perfume.image:
                            self.stdout.write(f"➡️ Skipping row {row_count}: {name} ({brand}) already complete.")
                            continue

                        created = False
                    else:
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

                    if url:
                        image_url, description = self.scrape_fragrantica(url, name, row_count)
                        update_fields = []

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

                    time.sleep(random.uniform(8, 15))

                except Exception as e:
                    self.stderr.write(f"⚠️ Error importing row {row_count} ({row.get('Perfume')}): {e}")

        self.stdout.write(
            self.style.SUCCESS(f"✅ Imported {imported} new perfumes (starting from line {start_line})")
        )

    def scrape_fragrantica(self, url, name, row_num, max_retries=10):
        for attempt in range(max_retries):
            try:
                headers = self.base_headers.copy()
                headers["User-Agent"] = random.choice(self.USER_AGENTS)
                res = self.scraper.get(url, headers=headers, timeout=15, allow_redirects=True)

                if res.status_code == 429:
                    if attempt == max_retries - 1:
                        self.stderr.write(f"⛔ CRITICAL 429 at row {row_num}: Max retries hit for {name}.")
                        self.stderr.write(
                            self.style.ERROR(
                                f"Script stopped due to persistent rate limiting. Last uncompleted row: {row_num}."
                            )
                        )
                        exit(1)

                    wait_time = (2 ** attempt) + random.uniform(1, 3)
                    self.stdout.write(
                        f"⏳ Attempt {attempt+1}/{max_retries}: 429 Rate Limit hit for {name}. Waiting {wait_time:.2f}s..."
                    )
                    time.sleep(wait_time)
                    continue

                if res.status_code != 200:
                    self.stderr.write(f"🚫 Request failed for {url}. Status code: {res.status_code}")
                    return None, None

                soup = BeautifulSoup(res.text, "html.parser")

                image_url = None
                img_tag = soup.select_one('img[itemprop="image"]')
                if img_tag:
                    image_url = img_tag.get("src") or img_tag.get("data-src")

                if not image_url:
                    og_image = soup.select_one("meta[property='og:image']")
                    image_url = og_image.get("content") if og_image else None

                if image_url and "perfume-thumbs" in image_url:
                    image_url = image_url.replace("perfume-thumbs", "perfume")

                og_desc = soup.select_one("meta[property='og:description']")
                description = og_desc.get("content").strip() if og_desc else None

                if description:
                    description = description.replace("&amp;", "&").replace("&quot;", '"')

                if not description:
                    desc_div = soup.select_one("div[itemprop='description']") or soup.select_one(".pgridCell p")
                    description = desc_div.get_text(strip=True) if desc_div else None

                return image_url, description

            except Exception as e:
                self.stderr.write(f"⚠️ Scrape error for {url}: {e}")
                time.sleep(5)
                continue

        return None, None

    def download_and_attach_image(self, perfume, image_url):
        try:
            headers = self.base_headers.copy()
            headers["User-Agent"] = random.choice(self.USER_AGENTS)
            res = self.scraper.get(image_url, headers=headers, timeout=15)

            if res.status_code == 200:
                file_name = image_url.split("/")[-1].split("?")[0]
                if "." not in file_name:
                    file_name += ".jpg"

                perfume.image.save(file_name, ContentFile(res.content), save=True)
            else:
                self.stderr.write(
                    f"⚠️ Image download failed for {perfume.name}. Status code: {res.status_code} for URL: {image_url}"
                )

        except Exception as e:
            self.stderr.write(f"⚠️ Download error for {perfume.name}: {e}")
