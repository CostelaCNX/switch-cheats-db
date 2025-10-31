#!/usr/bin/env python3

import rarfile
import zipfile
import cloudscraper
import json
import shutil
import time
from pathlib import Path
from datetime import date, datetime, timedelta
from bs4 import BeautifulSoup
import os

import process_cheats


def version_parser(version):
    year = int(version[4:8])
    month = int(version[0:2])
    day = int(version[2:4])
    return date(year, month, day)


class DatabaseInfo:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper()
        self.database_version_url = "https://github.com/CostelaCNX/switch-cheats-db/releases/latest/download/VERSION"
        self.database_version = self.fetch_database_version()

    def fetch_database_version(self):
        try:
            response = self.scraper.get(self.database_version_url)
            if response.status_code == 200 and not response.text.strip().startswith('<!DOCTYPE'):
                # Valid response with actual version data
                return date.fromisoformat(response.text.strip())
            else:
                # File doesn't exist or returned HTML (404 page)
                print("No existing VERSION file found, using epoch date to force initial update")
                return date(2020, 1, 1)  # Return old date to force update
        except Exception as e:
            print(f"Error fetching database version: {e}")
            print("Using epoch date to force initial update")
            return date(2020, 1, 1)  # Return old date to force update

    def get_database_version(self):
        return self.database_version


class GbatempCheatsInfo:
    def __init__(self):
        # Create scraper with more realistic browser headers and session management
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            },
            delay=10  # Add delay between requests
        )
        # Enhanced headers to look more like a real browser session
        self.scraper.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        })
        self.page_url = "https://gbatemp.net/download/cheat-codes-sxos-and-ams-main-cheat-file-updated.36311/"
        self.gbatemp_version = self.fetch_gbatemp_version()

    def fetch_gbatemp_version(self):
        try:
            page = self.scraper.get(f"{self.page_url}/updates")
            soup = BeautifulSoup(page.content, "html.parser")
            
            # Try the original selector first
            block_container = soup.find("div", {"class": "block-container"})
            if block_container:
                dates = block_container.find_all("time", {"class": "u-dt"})
            else:
                # Fallback: try to find any time elements with datetime attribute
                dates = soup.find_all("time")
            
            if not dates:
                print("Warning: Could not find date elements on GBATemp page, using fallback date")
                # Return a date that will force an update (yesterday)
                return date.today() - timedelta(days=1)
            
            # Extract datetime from all found time elements
            valid_dates = []
            for date_elem in dates:
                datetime_attr = date_elem.get("datetime")
                if datetime_attr:
                    try:
                        valid_dates.append(datetime.fromisoformat(datetime_attr.replace('Z', '+00:00')))
                    except ValueError:
                        continue
            
            if not valid_dates:
                print("Warning: No valid dates found on GBATemp page, using fallback date")
                return date.today() - timedelta(days=1)
            
            version = max(valid_dates)
            return version.date()
            
        except Exception as e:
            print(f"Error fetching GBATemp version: {e}")
            print("Using fallback date to force update")
            # Return a date that will force an update (yesterday)
            return date.today() - timedelta(days=1)

    def has_new_cheats(self, database_version):
        return self.gbatemp_version > database_version

    def get_gbatemp_version(self):
        return self.gbatemp_version

    def establish_session(self):
        """Establish session with advanced cloudscraper techniques"""
        try:
            print("  Establishing session with advanced bypass...")
            
            # Create a fresh cloudscraper with more aggressive settings
            fresh_scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'desktop': True
                },
                delay=5,  # Slower requests to avoid triggering limits
                debug=False
            )
            
            # More comprehensive headers
            fresh_scraper.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            })
            
            # Test multiple approaches to find working method
            test_strategies = [
                ("Direct HTTPS", "https://gbatemp.net/"),
                ("WWW subdomain", "https://www.gbatemp.net/"),
                ("Mobile subdomain", "https://m.gbatemp.net/"),
            ]
            
            for strategy_name, base_url in test_strategies:
                try:
                    print(f"  Trying {strategy_name}: {base_url}")
                    time.sleep(3)  # Be extra respectful
                    
                    response = fresh_scraper.get(base_url, timeout=20, allow_redirects=True)
                    
                    if response.status_code == 200 and b'gbatemp' in response.content.lower():
                        print(f"  SUCCESS with {strategy_name}")
                        # Update our main scraper
                        self.scraper = fresh_scraper
                        self.working_base = base_url.rstrip('/')
                        return True
                    else:
                        print(f"  {strategy_name} returned {response.status_code}")
                        
                except Exception as e:
                    print(f"  {strategy_name} failed: {type(e).__name__}: {e}")
                    continue
            
            print("  All session strategies failed")
            return False
            
        except Exception as e:
            print(f"  Session establishment error: {e}")
            return False

    def get_download_url(self):
        return f"{self.page_url.rstrip('/')}/download"


class HighFPSCheatsInfo:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper()
        self.download_url = "https://github.com/ChanseyIsTheBest/NX-60FPS-RES-GFX-Cheats/archive/refs/heads/main.zip"
        self.api_url = "https://api.github.com/repos/ChanseyIsTheBest/NX-60FPS-RES-GFX-Cheats/branches/main"
        self.highfps_version = self.fetch_high_FPS_cheats_version()

    def fetch_high_FPS_cheats_version(self):
        try:
            token = os.getenv('GITHUB_TOKEN')
            headers = {'Authorization': f'token {token}'} if token else {}
            repo_info = self.scraper.get(self.api_url, headers=headers).json()
            
            if 'commit' not in repo_info:
                print("Warning: Could not fetch GitHub API data for high FPS cheats, using fallback date")
                return date.today() - timedelta(days=1)
            
            last_commit_date = repo_info.get("commit").get("commit").get("author").get("date")
            return date.fromisoformat(last_commit_date.split("T")[0])
        except Exception as e:
            print(f"Error fetching high FPS cheats version: {e}")
            print("Using fallback date to force update")
            return date.today() - timedelta(days=1)

    def has_new_cheats(self, database_version):
        return self.highfps_version > database_version

    def get_high_FPS_version(self):
        return self.highfps_version

    def get_download_url(self):
        return self.download_url


class ArchiveWorker():
    def __init__(self):
        # Use the same improved scraper configuration with enhanced headers
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            },
            delay=10
        )
        self.scraper.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        })

    def download_gbatemp_archive(self, gbatemp_info, url, path):
        """Specialized download method for GBATemp with multiple strategies"""
        print(f"  Attempting GBATemp download from: {url}")
        
        # Strategy 1: Session establishment with realistic browser behavior
        try:
            return self._download_with_session(gbatemp_info, url, path)
        except Exception as e:
            print(f"  Session strategy failed: {e}")
        
        # Strategy 2: Direct download with alternative headers
        try:
            return self._download_with_alternative_headers(url, path)
        except Exception as e:
            print(f"  Alternative headers strategy failed: {e}")
        
        # Strategy 3: Try alternative download URLs
        try:
            return self._download_with_alternative_urls(gbatemp_info, path)
        except Exception as e:
            print(f"  Alternative URLs strategy failed: {e}")
        
        raise Exception("All download strategies failed")
    
    def _download_with_session(self, gbatemp_info, url, path):
        """Primary download strategy with session establishment"""
        # Establish session first
        gbatemp_info.establish_session()
        
        # Use the established session from gbatemp_info
        scraper = gbatemp_info.scraper
        
        # Add download-specific headers
        scraper.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Referer': gbatemp_info.page_url,
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
        })
        
        # Add respectful delay
        time.sleep(5)
        
        # Try the download with the established session
        dl = scraper.get(url, allow_redirects=True, timeout=60)
        
        # Check response
        if dl.status_code != 200:
            raise Exception(f"HTTP {dl.status_code}: {dl.reason}")
        
        # Validate content
        self._validate_and_save_archive(dl, path)
        
    def _download_with_alternative_headers(self, url, path):
        """Alternative download strategy with different headers"""
        print("  Trying alternative headers strategy...")
        
        # Create a new scraper with different configuration
        alt_scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'firefox',
                'platform': 'linux',
                'desktop': True
            }
        )
        
        alt_scraper.headers.update({
            'Accept': 'application/octet-stream,*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0',
        })
        
        time.sleep(3)
        dl = alt_scraper.get(url, allow_redirects=True, timeout=60)
        
        if dl.status_code != 200:
            raise Exception(f"HTTP {dl.status_code}: {dl.reason}")
            
        self._validate_and_save_archive(dl, path)
        
    def _download_with_alternative_urls(self, gbatemp_info, path):
        """Try alternative GBATemp URLs and mirror sources"""
        print("  Trying alternative sources...")
        
        # Alternative GBATemp URLs (older versions that might still work)
        gbatemp_alternatives = [
            "https://gbatemp.net/download/cheat-codes-sxos-and-ams-main-cheat-file-updated.36311/version/1633847520/download",
            "https://gbatemp.net/attachments/titles-rar.467812/",
            "https://gbatemp.net/attachments/titles-rar.392156/",
        ]
        
        # Try GBATemp alternatives first
        for alt_url in gbatemp_alternatives:
            try:
                print(f"  Trying GBATemp: {alt_url}")
                time.sleep(2)
                dl = gbatemp_info.scraper.get(alt_url, allow_redirects=True, timeout=60)
                
                if dl.status_code == 200 and len(dl.content) > 1000000:  # At least 1MB
                    self._validate_and_save_archive(dl, path)
                    print(f"  Success with GBATemp alternative")
                    return
                else:
                    print(f"  GBATemp alt failed: {dl.status_code}")
                    
            except Exception as e:
                print(f"  GBATemp alt failed: {e}")
                continue
        
        # Try GitHub mirror sources as ultimate fallback
        mirror_sources = [
            # These are common Nintendo Switch cheat repositories that might have the same database
            "https://github.com/HamletDuFromage/switch-cheats-db/releases/latest/download/titles.zip",
            "https://github.com/tomvita/EdiZon-SE/releases/latest/download/cheats.zip",
        ]
        
        print("  Trying mirror sources as fallback...")
        for mirror_url in mirror_sources:
            try:
                print(f"  Trying mirror: {mirror_url}")
                time.sleep(2)
                
                # Use a fresh scraper for GitHub
                github_scraper = cloudscraper.create_scraper()
                dl = github_scraper.get(mirror_url, allow_redirects=True, timeout=60)
                
                if dl.status_code == 200 and len(dl.content) > 100000:  # At least 100KB
                    # Convert ZIP to expected RAR name for compatibility
                    if mirror_url.endswith('.zip'):
                        zip_path = path.replace('.rar', '.zip')
                        with open(zip_path, 'wb') as f:
                            f.write(dl.content)
                        print(f"  Mirror success: downloaded {len(dl.content)} bytes as ZIP")
                        # Create a symlink or copy with RAR name for compatibility
                        import shutil
                        shutil.copy2(zip_path, path)
                    else:
                        with open(path, 'wb') as f:
                            f.write(dl.content)
                        
                    print(f"  Mirror source worked: {len(dl.content)} bytes")
                    return
                else:
                    print(f"  Mirror failed: {dl.status_code}")
                    
            except Exception as e:
                print(f"  Mirror failed: {e}")
                continue
                
        raise Exception("All alternative sources failed - GBATemp protection too strong")
        
    def _validate_and_save_archive(self, response, path):
        """Validate and save archive content"""
        content_type = response.headers.get('content-type', '').lower()
        content_length = len(response.content)
        
        print(f"  Response: {response.status_code}, Content-Type: {content_type}, Size: {content_length} bytes")
        
        # Detect if we got HTML instead of an archive
        if 'text/html' in content_type or content_length < 1000:
            if b'<html' in response.content[:500].lower() or b'captcha' in response.content.lower():
                # Save HTML for debugging
                with open(path + '.html', 'wb') as f:
                    f.write(response.content)
                raise Exception("Bot protection detected - received HTML page instead of archive")

        # Write the archive
        with open(path, 'wb') as f:
            f.write(response.content)
        
        print(f"  Successfully downloaded {content_length} bytes to {path}")

    def download_archive(self, url, path):
        print(f"  Attempting download from: {url}")
        
        # Add a small delay to be respectful to servers
        time.sleep(2)
        
        # Try the download with timeout
        try:
            dl = self.scraper.get(url, allow_redirects=True, timeout=30)
        except Exception as e:
            raise Exception(f"Download failed: {e}")
        
        # Check if we got a valid response
        if dl.status_code != 200:
            raise Exception(f"HTTP {dl.status_code}: {dl.reason}")
        
        # Check content type and size
        content_type = dl.headers.get('content-type', '').lower()
        content_length = len(dl.content)
        
        print(f"  Response: {dl.status_code}, Content-Type: {content_type}, Size: {content_length} bytes")
        
        # Detect if we got HTML instead of an archive (likely captcha/bot protection)
        if 'text/html' in content_type or content_length < 1000:
            print(f"  Warning: Received HTML response (likely bot protection)")
            if b'<html' in dl.content[:500].lower() or b'captcha' in dl.content.lower():
                print(f"  Detected HTML/captcha page instead of archive")
                # Still write the file for debugging
                with open(path + '.html', 'wb') as f:
                    f.write(dl.content)
                raise Exception("Bot protection detected - received HTML page instead of archive")
        
        # Check if content looks like an archive and detect format
        archive_info = {
            b'PK': ('ZIP', '.zip'),
            b'Rar!': ('RAR', '.rar'), 
            b'\x1f\x8b': ('GZIP', '.gz'),
        }
        
        detected_format = None
        detected_extension = None
        for signature, (format_name, extension) in archive_info.items():
            if dl.content.startswith(signature):
                detected_format = format_name
                detected_extension = extension
                break
        
        if detected_format:
            print(f"  Detected {detected_format} archive")
            # If the path has wrong extension, suggest the correct one
            if not path.endswith(detected_extension):
                correct_path = path.rsplit('.', 1)[0] + detected_extension
                print(f"  Note: Archive is {detected_format} but path suggests different format")
                print(f"  Consider using: {correct_path}")
        else:
            if content_length > 100:
                print(f"  Warning: Content doesn't appear to be a valid archive")
                print(f"  First 100 bytes: {dl.content[:100]}")
        
        with open(path, "wb") as f:
            f.write(dl.content)
        
        print(f"  ✓ Downloaded {content_length} bytes to {path}")

    def extract_archive(self, path, extract_path=None):
        if rarfile.is_rarfile(path):
            rf = rarfile.RarFile(path)
            rf.extractall(path=extract_path)
        elif zipfile.is_zipfile(path):
            zf = zipfile.ZipFile(path)
            zf.extractall(path=extract_path)
        else:
            return False
        return True

    def build_cheat_files(self, cheats_path, out_path):
        cheats_path = Path(cheats_path)
        titles_path = Path(out_path).joinpath("titles")
        if not(titles_path.exists()):
            titles_path.mkdir(parents=True)
        for tid in cheats_path.iterdir():
            tid_path = titles_path.joinpath(tid.stem)
            tid_path.mkdir(exist_ok=True)
            with open(tid, "r", encoding="utf-8", errors="ignore") as cheats_file:
                cheats_dict = json.load(cheats_file)
            for key, value in cheats_dict.items():
                if key == "attribution":
                    for author, content in value.items():
                        with open(tid_path.joinpath(author), "w", encoding="utf-8") as attribution_file:
                            attribution_file.write(content)
                else:
                    cheats_folder = tid_path.joinpath("cheats")
                    cheats_folder.mkdir(exist_ok=True)
                    cheats = ""
                    for _, content in value.items():
                        cheats += content
                    if cheats:
                        with open(cheats_folder.joinpath(f"{key}.txt"), "w", encoding="utf-8") as bid_file:
                            bid_file.write(cheats)

    def touch_all(self, path):
        for path in path.rglob("*"):
            if path.is_file():
                path.touch()

    def create_archives(self, out_path):
        out_path = Path(out_path)
        titles_path = out_path.joinpath("titles")
        
        if not titles_path.exists():
            print(f"Warning: {titles_path} does not exist, cannot create archives")
            return False
            
        self.touch_all(titles_path)
        titles_zip = f"{titles_path.resolve()}.zip"
        shutil.make_archive(str(titles_path.resolve()), "zip", root_dir=out_path, base_dir="titles")
        print(f"Created: {titles_zip}")
        
        # Handle the rename more carefully - remove existing contents dir first
        contents_path = titles_path.parent.joinpath("contents")
        if contents_path.exists():
            shutil.rmtree(contents_path)
        
        contents_path = titles_path.rename(contents_path)
        self.touch_all(contents_path)
        contents_zip = f"{contents_path.resolve()}.zip"
        shutil.make_archive(str(contents_path.resolve()), "zip", root_dir=out_path, base_dir="contents")
        print(f"Created: {contents_zip}")
        
        return True

    def create_version_file(self, out_path="."):
        with open(f"{out_path}/VERSION", "w") as version_file:
            version_file.write(str(date.today()))

def count_cheats(cheats_directory):
    n_games = 0
    n_updates = 0
    n_cheats = 0
    for json_file in Path(cheats_directory).glob('*.json'):
        with open(json_file, 'r', encoding="utf-8", errors="ignore") as file:
            cheats = json.load(file)
            for bid in cheats.values():
                n_cheats += len(bid)
                n_updates += 1
        n_games += 1

    readme_file = Path('README.md')
    with readme_file.open('r', encoding="utf-8", errors="ignore") as file:
        lines = file.readlines()
    lines[-1] = f"{n_cheats} cheats in {n_games} titles/{n_updates} updates"
    with readme_file.open('w', encoding="utf-8") as file:
        file.writelines(lines)

if __name__ == '__main__':
    try:
        cheats_path = "cheats"
        cheats_gba_path = "cheats_gbatemp"
        cheats_gfx_path = "cheats_gfx"
        gbatemp_archive_path = "gbatemp_titles.rar"
        highfps_archive_path = "highfps_titles.zip"
        
        print("Initializing database info...")
        database = DatabaseInfo()
        database_version = database.get_database_version()
        
        print("Initializing cheat sources...")
        highfps = HighFPSCheatsInfo()
        gbatemp = GbatempCheatsInfo()
    except Exception as e:
        print(f"Error during initialization: {e}")
        print("Continuing with fallback behavior...")
        database_version = date.today() - timedelta(days=2)  # Force update
        highfps = None
        gbatemp = None
    # Check if we should update (with fallback logic)
    should_update = True  # Default to always update if we can't determine versions
    try:
        if gbatemp and highfps:
            should_update = gbatemp.has_new_cheats(database_version) or highfps.has_new_cheats(database_version)
    except Exception as e:
        print(f"Error checking for updates: {e}. Will proceed with update anyway.")
        should_update = True
    
    if should_update:
        archive_worker = ArchiveWorker()
        print(f"Downloading cheats")
        
        # Download GBATemp cheats (with enhanced session handling)
        gbatemp_success = False
        try:
            print("Downloading GBATemp cheats...")
            if gbatemp:
                print(f"Using GBATemp URL: {gbatemp.get_download_url()}")
                archive_worker.download_gbatemp_archive(gbatemp, gbatemp.get_download_url(), gbatemp_archive_path)
            else:
                # Create temporary gbatemp info for fallback
                gbatemp = GbatempCheatsInfo()
                fallback_url = "https://gbatemp.net/download/cheat-codes-sxos-and-ams-main-cheat-file-updated.36311/download"
                print(f"Using fallback GBATemp URL: {fallback_url}")
                archive_worker.download_gbatemp_archive(gbatemp, fallback_url, gbatemp_archive_path)
            
            print(f"Extracting GBATemp archive to 'gbatemp' directory...")
            extraction_success = archive_worker.extract_archive(gbatemp_archive_path, "gbatemp")
            if extraction_success:
                print("✓ GBATemp archive extracted successfully")
                gbatemp_success = True
            else:
                print("✗ GBATemp archive extraction failed")
                
        except Exception as e:
            print(f"✗ Error downloading/extracting GBATemp cheats: {e}")
            print("  Note: GBATemp has very strict bot protection - this may be temporary")
            print("  Continuing with HighFPS source only...")
        
        # Download HighFPS cheats (with error handling)
        highfps_success = False
        try:
            print("Downloading HighFPS cheats...")
            if highfps:
                print(f"Using HighFPS URL: {highfps.get_download_url()}")
                archive_worker.download_archive(highfps.get_download_url(), highfps_archive_path)
            else:
                fallback_url = "https://github.com/ChanseyIsTheBest/NX-60FPS-RES-GFX-Cheats/archive/refs/heads/main.zip"
                print(f"Using fallback HighFPS URL: {fallback_url}")
                archive_worker.download_archive(fallback_url, highfps_archive_path)
                
            print(f"Extracting HighFPS archive...")
            extraction_success = archive_worker.extract_archive(highfps_archive_path)
            if extraction_success:
                print("✓ HighFPS archive extracted successfully")
                highfps_success = True
            else:
                print("✗ HighFPS archive extraction failed")
                
        except Exception as e:
            print(f"✗ Error downloading/extracting HighFPS cheats: {e}")
        
        # Debug: List what was actually extracted
        print("\nDebug: Checking extracted directories...")
        for check_path in ["gbatemp", "gbatemp/titles", "NX-60FPS-RES-GFX-Cheats-main", "NX-60FPS-RES-GFX-Cheats-main/titles"]:
            path_obj = Path(check_path)
            if path_obj.exists():
                print(f"✓ {check_path} exists")
                if path_obj.is_dir():
                    try:
                        contents = list(path_obj.iterdir())
                        print(f"  Contains {len(contents)} items")
                    except Exception as e:
                        print(f"  Error reading directory: {e}")
            else:
                print(f"✗ {check_path} does not exist")

        print("Processing the cheat sheets")
        
        # Process GBATemp cheats (with directory existence check)
        gbatemp_titles_path = Path("gbatemp/titles")
        if gbatemp_titles_path.exists():
            try:
                print("Processing GBATemp cheats...")
                process_cheats.ProcessCheats("gbatemp/titles", cheats_gba_path)
                process_cheats.ProcessCheats("gbatemp/titles", cheats_path)
                print("✓ GBATemp cheats processed successfully")
            except Exception as e:
                print(f"Error processing GBATemp cheats: {e}")
        else:
            print(f"Warning: GBATemp titles directory not found at {gbatemp_titles_path}")
        
        # Process HighFPS cheats (with directory existence check)
        highfps_titles_path = Path("NX-60FPS-RES-GFX-Cheats-main/titles")
        if highfps_titles_path.exists():
            try:
                print("Processing HighFPS cheats...")
                process_cheats.ProcessCheats("NX-60FPS-RES-GFX-Cheats-main/titles", cheats_gfx_path)
                process_cheats.ProcessCheats("NX-60FPS-RES-GFX-Cheats-main/titles", cheats_path)
                print("✓ HighFPS cheats processed successfully")
            except Exception as e:
                print(f"Error processing HighFPS cheats: {e}")
        else:
            print(f"Warning: HighFPS titles directory not found at {highfps_titles_path}")

        # Build complete cheat sheets (only if we have processed cheats)
        cheats_path_obj = Path(cheats_path)
        if cheats_path_obj.exists() and any(cheats_path_obj.iterdir()):
            try:
                print("Building complete cheat sheets...")
                out_path = Path("complete")
                out_path.mkdir(exist_ok=True)
                archive_worker.build_cheat_files(cheats_path, out_path)
                print("✓ Complete cheat sheets built successfully")
            except Exception as e:
                print(f"Error building complete cheat sheets: {e}")
        else:
            print("Warning: No processed cheats found, skipping complete cheat sheets")

        print("Creating the archives")
        
        # Create archives with error handling
        archive_paths = [
            ("complete", "Complete cheats"),
            ("NX-60FPS-RES-GFX-Cheats-main", "HighFPS cheats"),
            ("gbatemp", "GBATemp cheats")
        ]
        
        for archive_path, description in archive_paths:
            if Path(archive_path).exists():
                try:
                    print(f"Creating {description} archive...")
                    success = archive_worker.create_archives(archive_path)
                    if success:
                        print(f"✓ {description} archive created successfully")
                    else:
                        print(f"✗ {description} archive creation failed")
                except Exception as e:
                    print(f"Error creating {description} archive: {e}")
            else:
                print(f"Warning: {description} directory not found, skipping archive creation")

        try:
            archive_worker.create_version_file()
            print("✓ Version file created successfully")
        except Exception as e:
            print(f"Error creating version file: {e}")

        try:
            if cheats_path_obj.exists():
                count_cheats(cheats_path)
                print("✓ README updated with cheat counts")
            else:
                print("Warning: No cheats directory found, skipping count update")
        except Exception as e:
            print(f"Error updating cheat counts: {e}")

    else:
        print("Everything is already up to date!")
