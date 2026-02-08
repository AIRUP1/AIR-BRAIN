"""
StormBuster Browserless.io Integration
Unified scraping service using Browserless.io headless browser API
Integrates with all existing scrapers for enhanced JavaScript rendering

Features:
- Headless Chrome browser automation via API
- JavaScript rendering for dynamic pages
- Screenshot and PDF generation
- Multi-platform job scraping
- Property data enrichment
- Instagram profile scraping
- Unified API for all scraping operations

Get your API key at: https://browserless.io
"""

import os
import json
import time
import requests
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
from datetime import datetime
import base64
import re

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

print("=" * 70)
print("STORMBUSTER BROWSERLESS.IO INTEGRATION")
print("=" * 70)
print("\nFeatures Available:")
print("  ✓ Headless Chrome Browser Automation")
print("  ✓ JavaScript Page Rendering")
print("  ✓ Multi-Platform Job Scraping")
print("  ✓ Property Data Enrichment")
print("  ✓ Instagram Profile Scraping")
print("  ✓ Screenshot & PDF Generation")
print("  ✓ Unified Scraper API")


# ============================================
# BROWSERLESS.IO CLIENT
# ============================================

class BrowserlessClient:
    """
    Browserless.io API Client
    Provides headless Chrome browser automation via API
    
    Endpoints:
    - /content - Get rendered HTML
    - /screenshot - Capture screenshots
    - /pdf - Generate PDFs
    - /scrape - Extract data with selectors
    - /function - Execute custom scripts
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('BROWSERLESS_API_KEY', '')
        self.base_url = os.environ.get('BROWSERLESS_URL', 'https://chrome.browserless.io')
        
        if not self.api_key:
            print("\n⚠️  BROWSERLESS_API_KEY not set!")
            print("   Get your API key at: https://browserless.io")
            print("   Set it in environment: BROWSERLESS_API_KEY=your_key")
        else:
            print(f"\n✓ Browserless API configured: {self.base_url}")
        
        self.headers = {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache'
        }
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # seconds
    
    @property
    def api_url(self) -> str:
        """Get base API URL"""
        return f"{self.base_url}"
    
    def _get_auth_params(self) -> Dict:
        """Get authentication parameters"""
        return {'token': self.api_key}
    
    def _rate_limit(self):
        """Implement rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    # ============================================
    # CORE BROWSERLESS METHODS
    # ============================================
    
    def get_content(self, url: str, wait_for: str = None, timeout: int = 30000) -> Optional[str]:
        """
        Get rendered HTML content from a URL
        Uses Browserless /content endpoint
        
        Args:
            url: Page URL to render
            wait_for: CSS selector to wait for before returning
            timeout: Maximum time to wait in milliseconds
        
        Returns:
            Rendered HTML content or None on error
        """
        self._rate_limit()
        
        try:
            endpoint = f"{self.api_url}/content"
            
            payload = {
                'url': url,
                'gotoOptions': {
                    'waitUntil': 'networkidle2',
                    'timeout': timeout
                }
            }
            
            if wait_for:
                payload['waitForSelector'] = {
                    'selector': wait_for,
                    'timeout': timeout
                }
            
            print(f"  📄 Fetching content: {url[:60]}...")
            
            response = requests.post(
                endpoint,
                params=self._get_auth_params(),
                headers=self.headers,
                json=payload,
                timeout=timeout // 1000 + 10
            )
            response.raise_for_status()
            
            print(f"  ✓ Content received: {len(response.text)} bytes")
            return response.text
            
        except requests.exceptions.Timeout:
            print(f"  ❌ Timeout fetching: {url}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Browserless content error: {e}")
            return None
    
    def get_screenshot(self, url: str, full_page: bool = False, 
                       width: int = 1920, height: int = 1080) -> Optional[bytes]:
        """
        Take screenshot of a page
        Uses Browserless /screenshot endpoint
        
        Args:
            url: Page URL to capture
            full_page: Capture entire page height
            width: Viewport width
            height: Viewport height
        
        Returns:
            PNG image bytes or None on error
        """
        self._rate_limit()
        
        try:
            endpoint = f"{self.api_url}/screenshot"
            
            payload = {
                'url': url,
                'options': {
                    'fullPage': full_page,
                    'type': 'png'
                },
                'gotoOptions': {
                    'waitUntil': 'networkidle2'
                },
                'viewport': {
                    'width': width,
                    'height': height
                }
            }
            
            print(f"  📷 Taking screenshot: {url[:60]}...")
            
            response = requests.post(
                endpoint,
                params=self._get_auth_params(),
                headers=self.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            print(f"  ✓ Screenshot captured: {len(response.content)} bytes")
            return response.content
            
        except Exception as e:
            print(f"  ❌ Browserless screenshot error: {e}")
            return None
    
    def get_pdf(self, url: str, format: str = 'A4') -> Optional[bytes]:
        """
        Generate PDF from a URL
        Uses Browserless /pdf endpoint
        
        Args:
            url: Page URL to convert
            format: Paper format (A4, Letter, etc.)
        
        Returns:
            PDF bytes or None on error
        """
        self._rate_limit()
        
        try:
            endpoint = f"{self.api_url}/pdf"
            
            payload = {
                'url': url,
                'options': {
                    'format': format,
                    'printBackground': True,
                    'margin': {
                        'top': '1cm',
                        'right': '1cm',
                        'bottom': '1cm',
                        'left': '1cm'
                    }
                },
                'gotoOptions': {
                    'waitUntil': 'networkidle2'
                }
            }
            
            print(f"  📑 Generating PDF: {url[:60]}...")
            
            response = requests.post(
                endpoint,
                params=self._get_auth_params(),
                headers=self.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            print(f"  ✓ PDF generated: {len(response.content)} bytes")
            return response.content
            
        except Exception as e:
            print(f"  ❌ Browserless PDF error: {e}")
            return None
    
    def scrape(self, url: str, selectors: Dict[str, str], wait_for: str = None) -> Dict:
        """
        Scrape data using CSS selectors
        Uses Browserless /scrape endpoint
        
        Args:
            url: Page URL to scrape
            selectors: Dict mapping names to CSS selectors
            wait_for: CSS selector to wait for
        
        Returns:
            Dict of scraped data
        """
        self._rate_limit()
        
        try:
            endpoint = f"{self.api_url}/scrape"
            
            elements = [
                {'selector': selector, 'name': name}
                for name, selector in selectors.items()
            ]
            
            payload = {
                'url': url,
                'elements': elements,
                'gotoOptions': {
                    'waitUntil': 'networkidle2'
                }
            }
            
            if wait_for:
                payload['waitForSelector'] = {'selector': wait_for}
            
            print(f"  🔍 Scraping: {url[:60]}...")
            
            response = requests.post(
                endpoint,
                params=self._get_auth_params(),
                headers=self.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            print(f"  ✓ Scraped {len(result.get('data', []))} elements")
            return result
            
        except Exception as e:
            print(f"  ❌ Browserless scrape error: {e}")
            return {}
    
    def execute_function(self, code: str, context: Dict = None) -> Optional[Any]:
        """
        Execute custom JavaScript function
        Uses Browserless /function endpoint
        
        Args:
            code: JavaScript function code
            context: Optional context data
        
        Returns:
            Function result or None on error
        """
        self._rate_limit()
        
        try:
            endpoint = f"{self.api_url}/function"
            
            payload = {
                'code': code
            }
            
            if context:
                payload['context'] = context
            
            response = requests.post(
                endpoint,
                params=self._get_auth_params(),
                headers=self.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"  ❌ Browserless function error: {e}")
            return None


# ============================================
# INTEGRATED SCRAPER SERVICES
# ============================================

class BrowserlessLinkedInScraper:
    """LinkedIn scraper using Browserless.io"""
    
    def __init__(self, browserless: BrowserlessClient):
        self.client = browserless
    
    def search_profiles(self, keywords: str, location: str = "") -> List[Dict]:
        """Search LinkedIn profiles (public search only)"""
        print(f"\n🔗 LinkedIn Search: {keywords}")
        
        # URL encode keywords
        from urllib.parse import quote
        search_url = f"https://www.linkedin.com/search/results/people/?keywords={quote(keywords)}"
        if location:
            search_url += f"&location={quote(location)}"
        
        html = self.client.get_content(search_url, wait_for='.search-results-container', timeout=45000)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        profiles = []
        
        # Try multiple selector patterns
        cards = soup.select('.entity-result__item, .reusable-search__result-container, .search-result')
        
        for card in cards[:20]:
            try:
                name_elem = card.select_one('.entity-result__title-text a, .actor-name, h3 a')
                headline_elem = card.select_one('.entity-result__primary-subtitle, .subline-level-1')
                location_elem = card.select_one('.entity-result__secondary-subtitle, .subline-level-2')
                
                name = name_elem.get_text(strip=True) if name_elem else ''
                if not name:
                    continue
                    
                profiles.append({
                    'name': name,
                    'headline': headline_elem.get_text(strip=True) if headline_elem else '',
                    'location': location_elem.get_text(strip=True) if location_elem else '',
                    'profile_url': name_elem.get('href', '') if name_elem else '',
                    'source': 'linkedin_browserless'
                })
            except Exception as e:
                continue
        
        print(f"  Found {len(profiles)} LinkedIn profiles")
        return profiles


class BrowserlessIndeedScraper:
    """Indeed job scraper using Browserless.io"""
    
    def __init__(self, browserless: BrowserlessClient):
        self.client = browserless
    
    def search_jobs(self, keywords: str, location: str = "", remote: bool = False) -> List[Dict]:
        """Search Indeed for jobs"""
        print(f"\n💼 Indeed Search: {keywords} in {location or 'all locations'}")
        
        from urllib.parse import quote
        search_url = f"https://www.indeed.com/jobs?q={quote(keywords)}&l={quote(location)}"
        if remote:
            search_url += "&remotejob=032b3046-06a3-4876-8dfd-474eb5e7ed11"
        
        html = self.client.get_content(search_url, wait_for='.jobsearch-ResultsList, .mosaic-provider-jobcards')
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []
        
        # Multiple selector patterns for Indeed's changing layout
        cards = soup.select('.job_seen_beacon, .resultContent, .jobCard_mainContent, [data-jk]')
        
        for card in cards[:25]:
            try:
                title_elem = card.select_one('.jobTitle a, h2.jobTitle span, [data-testid="job-title"]')
                company_elem = card.select_one('.companyName, [data-testid="company-name"], .company')
                location_elem = card.select_one('.companyLocation, [data-testid="text-location"], .location')
                snippet_elem = card.select_one('.job-snippet, .underShelfFooter, .jobCardShelfContainer')
                salary_elem = card.select_one('.salary-snippet, [data-testid="attribute_snippet_testid"]')
                
                title = title_elem.get_text(strip=True) if title_elem else ''
                if not title:
                    continue
                
                # Get job URL
                link = card.select_one('a[href*="/rc/clk"], a[data-jk], .jobTitle a')
                job_url = ''
                if link:
                    href = link.get('href', '')
                    if href.startswith('/'):
                        job_url = f"https://www.indeed.com{href}"
                    else:
                        job_url = href
                
                jobs.append({
                    'title': title,
                    'company': company_elem.get_text(strip=True) if company_elem else '',
                    'location': location_elem.get_text(strip=True) if location_elem else '',
                    'snippet': snippet_elem.get_text(strip=True)[:200] if snippet_elem else '',
                    'salary': salary_elem.get_text(strip=True) if salary_elem else '',
                    'url': job_url,
                    'source': 'indeed_browserless'
                })
            except Exception:
                continue
        
        print(f"  Found {len(jobs)} Indeed jobs")
        return jobs
    
    def search_resumes(self, keywords: str, location: str = "") -> List[Dict]:
        """Search Indeed resume database"""
        print(f"\n📝 Indeed Resume Search: {keywords}")
        
        from urllib.parse import quote
        search_url = f"https://www.indeed.com/resumes?q={quote(keywords)}&l={quote(location)}"
        
        html = self.client.get_content(search_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        resumes = []
        
        cards = soup.select('.resMosaic-card, .resume-card')
        
        for card in cards[:20]:
            try:
                name_elem = card.select_one('.resume-name, h2')
                title_elem = card.select_one('.resume-title, .headline')
                location_elem = card.select_one('.resume-location, .location')
                
                resumes.append({
                    'name': name_elem.get_text(strip=True) if name_elem else '',
                    'title': title_elem.get_text(strip=True) if title_elem else '',
                    'location': location_elem.get_text(strip=True) if location_elem else '',
                    'source': 'indeed_resumes_browserless'
                })
            except Exception:
                continue
        
        print(f"  Found {len(resumes)} Indeed resumes")
        return resumes


class BrowserlessSpokeoScraper:
    """Enhanced Spokeo scraper using Browserless.io for JavaScript rendering"""
    
    def __init__(self, browserless: BrowserlessClient, email: str = None, password: str = None):
        self.client = browserless
        self.email = email or os.environ.get('SPOKEO_EMAIL', '')
        self.password = password or os.environ.get('SPOKEO_PASSWORD', '')
    
    def search_address(self, address: str, city: str, state: str = "TX", zipcode: str = None) -> Dict:
        """Search property by address with JS rendering"""
        print(f"\n🏠 Spokeo Address Search: {address}, {city}")
        
        full_address = f"{address}, {city}, {state}"
        if zipcode:
            full_address += f" {zipcode}"
        
        from urllib.parse import quote
        search_url = f"https://www.spokeo.com/search?q={quote(full_address)}"
        
        html = self.client.get_content(search_url, wait_for='.search-results, .result-card', timeout=45000)
        if not html:
            return {'address': full_address, 'source': 'spokeo_browserless', 'error': 'No content'}
        
        soup = BeautifulSoup(html, 'html.parser')
        
        result = {
            'address': full_address,
            'owner_name': '',
            'phone': '',
            'email': '',
            'property_value': '',
            'source': 'spokeo_browserless'
        }
        
        # Extract data from rendered page
        owner_elem = soup.select_one('.owner-name, .resident-name, [class*="owner"], .name-link')
        if owner_elem:
            result['owner_name'] = owner_elem.get_text(strip=True)
        
        phone_elem = soup.select_one('.phone-number, [class*="phone"], a[href^="tel:"]')
        if phone_elem:
            phone_text = phone_elem.get_text(strip=True)
            # Extract phone pattern
            phone_match = re.search(r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})', phone_text)
            if phone_match:
                result['phone'] = phone_match.group(1)
        
        email_elem = soup.select_one('[class*="email"], a[href^="mailto:"]')
        if email_elem:
            email_text = email_elem.get('href', '').replace('mailto:', '') or email_elem.get_text(strip=True)
            if '@' in email_text:
                result['email'] = email_text
        
        value_elem = soup.select_one('[class*="value"], [class*="price"]')
        if value_elem:
            value_text = value_elem.get_text(strip=True)
            if '$' in value_text:
                result['property_value'] = value_text
        
        print(f"  Owner: {result['owner_name'] or 'Not found'}")
        return result
    
    def search_person(self, name: str, city: str = None, state: str = "TX") -> Dict:
        """Search for person by name"""
        print(f"\n👤 Spokeo Person Search: {name}")
        
        from urllib.parse import quote
        search_parts = [name]
        if city:
            search_parts.append(city)
        if state:
            search_parts.append(state)
        
        search_url = f"https://www.spokeo.com/search?q={quote(' '.join(search_parts))}"
        
        html = self.client.get_content(search_url, timeout=45000)
        if not html:
            return {'name': name, 'source': 'spokeo_browserless', 'error': 'No content'}
        
        soup = BeautifulSoup(html, 'html.parser')
        
        result = {
            'name': name,
            'addresses': [],
            'phones': [],
            'emails': [],
            'source': 'spokeo_browserless'
        }
        
        # Extract addresses
        for addr in soup.select('[class*="address"]')[:3]:
            addr_text = addr.get_text(strip=True)
            if len(addr_text) > 10:
                result['addresses'].append(addr_text)
        
        # Extract phones
        for phone in soup.select('[class*="phone"], a[href^="tel:"]')[:3]:
            phone_text = phone.get_text(strip=True)
            phone_match = re.search(r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})', phone_text)
            if phone_match:
                result['phones'].append(phone_match.group(1))
        
        return result


class BrowserlessInstagramScraper:
    """Instagram scraper using Browserless.io"""
    
    def __init__(self, browserless: BrowserlessClient):
        self.client = browserless
    
    def get_profile(self, username: str) -> Dict:
        """Get Instagram profile data"""
        print(f"\n📷 Instagram Profile: @{username}")
        
        username = username.replace('@', '').strip().lower()
        url = f"https://www.instagram.com/{username}/"
        
        html = self.client.get_content(url, timeout=30000)
        if not html:
            return {'username': username, 'source': 'instagram_browserless', 'error': 'No content'}
        
        soup = BeautifulSoup(html, 'html.parser')
        
        result = {
            'username': username,
            'full_name': '',
            'bio': '',
            'followers': 0,
            'following': 0,
            'posts': 0,
            'external_url': '',
            'is_verified': False,
            'is_private': False,
            'source': 'instagram_browserless'
        }
        
        # Try to extract JSON-LD data
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    result['full_name'] = data.get('name', '')
                    result['bio'] = data.get('description', '')
                    result['external_url'] = data.get('url', '')
            except:
                continue
        
        # Try meta tags
        og_title = soup.find('meta', property='og:title')
        if og_title:
            title_content = og_title.get('content', '')
            if '•' in title_content:
                parts = title_content.split('•')
                if len(parts) >= 1:
                    result['full_name'] = parts[0].strip().replace(f'@{username}', '').strip(' ()')
        
        og_desc = soup.find('meta', property='og:description')
        if og_desc:
            desc = og_desc.get('content', '')
            # Parse follower counts from description
            followers_match = re.search(r'([\d,.]+[KMB]?)\s*Followers', desc, re.I)
            if followers_match:
                result['followers'] = self._parse_count(followers_match.group(1))
            
            following_match = re.search(r'([\d,.]+[KMB]?)\s*Following', desc, re.I)
            if following_match:
                result['following'] = self._parse_count(following_match.group(1))
            
            posts_match = re.search(r'([\d,.]+[KMB]?)\s*Posts', desc, re.I)
            if posts_match:
                result['posts'] = self._parse_count(posts_match.group(1))
        
        print(f"  Name: {result['full_name'] or 'Not found'}")
        print(f"  Followers: {result['followers']:,}")
        return result
    
    def _parse_count(self, count_str: str) -> int:
        """Parse follower/following count string to int"""
        count_str = count_str.replace(',', '').strip().upper()
        multiplier = 1
        
        if 'K' in count_str:
            multiplier = 1000
            count_str = count_str.replace('K', '')
        elif 'M' in count_str:
            multiplier = 1000000
            count_str = count_str.replace('M', '')
        elif 'B' in count_str:
            multiplier = 1000000000
            count_str = count_str.replace('B', '')
        
        try:
            return int(float(count_str) * multiplier)
        except:
            return 0


class BrowserlessJobScraper:
    """Multi-platform job scraper using Browserless.io"""
    
    def __init__(self, browserless: BrowserlessClient):
        self.client = browserless
    
    def scrape_remote_co(self, category: str = "developer") -> List[Dict]:
        """Scrape Remote.co jobs"""
        print(f"\n🌐 Remote.co Search: {category}")
        
        url = f"https://remote.co/remote-jobs/{category}/"
        html = self.client.get_content(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []
        
        for listing in soup.select('.job_listing, .card')[:20]:
            title = listing.select_one('.position, .job-title, h3')
            company = listing.select_one('.company, .company-name')
            link = listing.select_one('a[href*="job"]')
            
            if not title:
                continue
            
            job_url = ''
            if link:
                href = link.get('href', '')
                if href.startswith('/'):
                    job_url = f"https://remote.co{href}"
                else:
                    job_url = href
            
            jobs.append({
                'title': title.get_text(strip=True),
                'company': company.get_text(strip=True) if company else '',
                'url': job_url,
                'source': 'remote_co'
            })
        
        print(f"  Found {len(jobs)} Remote.co jobs")
        return jobs
    
    def scrape_wellfound(self, role: str = "ai-automation") -> List[Dict]:
        """Scrape Wellfound (AngelList) jobs"""
        print(f"\n🚀 Wellfound Search: {role}")
        
        url = f"https://wellfound.com/role/l/{role}"
        html = self.client.get_content(url, wait_for='[class*="styles_component"], .job-card', timeout=45000)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []
        
        cards = soup.select('[class*="JobListingCard"], [class*="styles_component"], .job-card, [data-test="job-card"]')
        
        for card in cards[:20]:
            title = card.select_one('h2, [class*="title"], .job-title')
            company = card.select_one('[class*="company"], .startup-name, [class*="CompanyName"]')
            location = card.select_one('[class*="location"], .job-location')
            salary = card.select_one('[class*="salary"], [class*="compensation"]')
            link = card.select_one('a[href*="/jobs/"], a[href*="/company/"]')
            
            if not title:
                continue
            
            job_url = ''
            if link:
                href = link.get('href', '')
                if href.startswith('/'):
                    job_url = f"https://wellfound.com{href}"
                else:
                    job_url = href
            
            jobs.append({
                'title': title.get_text(strip=True),
                'company': company.get_text(strip=True) if company else '',
                'location': location.get_text(strip=True) if location else '',
                'salary': salary.get_text(strip=True) if salary else '',
                'url': job_url,
                'source': 'wellfound'
            })
        
        print(f"  Found {len(jobs)} Wellfound jobs")
        return jobs
    
    def scrape_flexjobs(self, keywords: str = "ai automation") -> List[Dict]:
        """Scrape FlexJobs listings"""
        print(f"\n💼 FlexJobs Search: {keywords}")
        
        from urllib.parse import quote
        url = f"https://www.flexjobs.com/search?search={quote(keywords)}"
        html = self.client.get_content(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        jobs = []
        
        for listing in soup.select('.job-item, .job-card, [class*="JobCard"]')[:20]:
            title = listing.select_one('.job-title, h2, h3')
            company = listing.select_one('.company-name, .employer')
            location = listing.select_one('.location, .job-location')
            link = listing.select_one('a[href*="/job/"]')
            
            if not title:
                continue
            
            jobs.append({
                'title': title.get_text(strip=True),
                'company': company.get_text(strip=True) if company else '',
                'location': location.get_text(strip=True) if location else '',
                'url': link.get('href', '') if link else '',
                'source': 'flexjobs'
            })
        
        print(f"  Found {len(jobs)} FlexJobs listings")
        return jobs


class BrowserlessStemCellScraper:
    """Scraper for stem cell/PRP centers using Browserless.io"""
    
    def __init__(self, browserless: BrowserlessClient):
        self.client = browserless
    
    def search_closed_clinics(self, city: str, state: str = "TX") -> List[Dict]:
        """Search for closed stem cell/PRP clinics"""
        print(f"\n🏥 Searching closed clinics in {city}, {state}")
        
        from urllib.parse import quote
        
        results = []
        
        # Search Google for closed clinics
        search_queries = [
            f"stem cell clinic closed {city} {state}",
            f"PRP center out of business {city} {state}",
            f"regenerative medicine clinic closed {city} Texas"
        ]
        
        for query in search_queries:
            url = f"https://www.google.com/search?q={quote(query)}"
            html = self.client.get_content(url)
            if not html:
                continue
            
            soup = BeautifulSoup(html, 'html.parser')
            
            for result in soup.select('.g, [data-header-feature]')[:5]:
                title = result.select_one('h3')
                snippet = result.select_one('.VwiC3b, .IsZvec')
                link = result.select_one('a')
                
                if title:
                    results.append({
                        'title': title.get_text(strip=True),
                        'snippet': snippet.get_text(strip=True)[:200] if snippet else '',
                        'url': link.get('href', '') if link else '',
                        'query': query,
                        'city': city,
                        'source': 'google_search'
                    })
            
            time.sleep(1)  # Rate limiting
        
        print(f"  Found {len(results)} potential results")
        return results


# ============================================
# UNIFIED SCRAPER SERVICE
# ============================================

class UnifiedScraperService:
    """
    Unified scraping service integrating all scrapers with Browserless.io
    Provides a single API for all scraping operations
    """
    
    def __init__(self, browserless_api_key: str = None):
        print("\n" + "=" * 50)
        print("INITIALIZING UNIFIED SCRAPER SERVICE")
        print("=" * 50)
        
        self.browserless = BrowserlessClient(browserless_api_key)
        
        # Initialize all scrapers
        self.linkedin = BrowserlessLinkedInScraper(self.browserless)
        self.indeed = BrowserlessIndeedScraper(self.browserless)
        self.spokeo = BrowserlessSpokeoScraper(self.browserless)
        self.instagram = BrowserlessInstagramScraper(self.browserless)
        self.jobs = BrowserlessJobScraper(self.browserless)
        self.stemcell = BrowserlessStemCellScraper(self.browserless)
        
        print("\n✓ All scrapers initialized")
        print("  - LinkedIn Scraper")
        print("  - Indeed Scraper")
        print("  - Spokeo Scraper")
        print("  - Instagram Scraper")
        print("  - Multi-Platform Job Scraper")
        print("  - Stem Cell Clinic Scraper")
    
    def scrape_jobs(self, keywords: str, location: str = "", 
                   sources: List[str] = None, remote_only: bool = False) -> Dict[str, List]:
        """
        Scrape jobs from multiple platforms
        
        Args:
            keywords: Job search keywords
            location: Location filter
            sources: List of sources ['indeed', 'remote_co', 'wellfound', 'linkedin', 'flexjobs']
            remote_only: Filter for remote jobs only
        
        Returns:
            Dict mapping source names to job lists
        """
        if sources is None:
            sources = ['indeed', 'wellfound']
        
        print(f"\n" + "=" * 50)
        print(f"JOB SEARCH: {keywords}")
        print(f"Location: {location or 'Any'}")
        print(f"Sources: {', '.join(sources)}")
        print("=" * 50)
        
        results = {}
        
        if 'indeed' in sources:
            results['indeed'] = self.indeed.search_jobs(keywords, location, remote=remote_only)
        
        if 'wellfound' in sources:
            role_slug = keywords.lower().replace(' ', '-')
            results['wellfound'] = self.jobs.scrape_wellfound(role_slug)
        
        if 'remote_co' in sources:
            category = keywords.lower().split()[0] if keywords else 'developer'
            results['remote_co'] = self.jobs.scrape_remote_co(category)
        
        if 'linkedin' in sources:
            results['linkedin'] = self.linkedin.search_profiles(keywords, location)
        
        if 'flexjobs' in sources:
            results['flexjobs'] = self.jobs.scrape_flexjobs(keywords)
        
        total = sum(len(v) for v in results.values())
        print(f"\n✓ Total jobs found: {total}")
        
        return results
    
    def scrape_property(self, address: str, city: str, state: str = "TX", 
                       zipcode: str = None, sources: List[str] = None) -> Dict:
        """
        Scrape property information from multiple sources
        """
        if sources is None:
            sources = ['spokeo']
        
        print(f"\n" + "=" * 50)
        print(f"PROPERTY SEARCH: {address}, {city}")
        print("=" * 50)
        
        results = {}
        
        if 'spokeo' in sources:
            results['spokeo'] = self.spokeo.search_address(address, city, state, zipcode)
        
        return results
    
    def scrape_person(self, name: str, city: str = None, state: str = "TX") -> Dict:
        """Scrape person information"""
        return self.spokeo.search_person(name, city, state)
    
    def scrape_instagram(self, username: str) -> Dict:
        """Scrape Instagram profile"""
        return self.instagram.get_profile(username)
    
    def scrape_closed_clinics(self, cities: List[str] = None, state: str = "TX") -> Dict[str, List]:
        """
        Scrape for closed stem cell/PRP clinics
        """
        if cities is None:
            cities = ['Austin', 'San Antonio', 'Houston']
        
        print(f"\n" + "=" * 50)
        print(f"CLOSED CLINIC SEARCH")
        print(f"Cities: {', '.join(cities)}")
        print("=" * 50)
        
        results = {}
        for city in cities:
            results[city] = self.stemcell.search_closed_clinics(city, state)
        
        return results
    
    def get_page_content(self, url: str, wait_for: str = None) -> Optional[str]:
        """Generic page content fetching with JS rendering"""
        return self.browserless.get_content(url, wait_for)
    
    def take_screenshot(self, url: str, full_page: bool = False) -> Optional[bytes]:
        """Take screenshot of any URL"""
        return self.browserless.get_screenshot(url, full_page)
    
    def generate_pdf(self, url: str) -> Optional[bytes]:
        """Generate PDF from URL"""
        return self.browserless.get_pdf(url)
    
    def export_results(self, results: Dict, filename: str = None) -> str:
        """Export results to CSV"""
        import pandas as pd
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"scraper_results_{timestamp}.csv"
        
        all_data = []
        for source, items in results.items():
            if isinstance(items, list):
                for item in items:
                    item['_source'] = source
                    all_data.append(item)
            elif isinstance(items, dict):
                items['_source'] = source
                all_data.append(items)
        
        if all_data:
            df = pd.DataFrame(all_data)
            df.to_csv(filename, index=False)
            print(f"\n✓ Results exported to: {filename}")
        
        return filename


# ============================================
# FACTORY FUNCTION
# ============================================

def get_scraper_service(api_key: str = None) -> UnifiedScraperService:
    """Factory function to get scraper service instance"""
    if api_key is None:
        api_key = os.environ.get('BROWSERLESS_API_KEY', '')
    return UnifiedScraperService(api_key)


# ============================================
# CLI / MAIN
# ============================================

def main():
    """Main execution for testing"""
    print("\n" + "=" * 70)
    print("STORMBUSTER BROWSERLESS.IO INTEGRATION TEST")
    print("=" * 70)
    
    # Check for API key
    api_key = os.environ.get('BROWSERLESS_API_KEY', '')
    
    if not api_key:
        print("\n⚠️  BROWSERLESS_API_KEY not found in environment!")
        print("\nTo set up:")
        print("1. Get API key from https://browserless.io")
        print("2. Set environment variable: BROWSERLESS_API_KEY=your_key")
        print("3. Or create .env file with: BROWSERLESS_API_KEY=your_key")
        print("\n" + "=" * 70)
        return
    
    # Initialize service
    service = get_scraper_service(api_key)
    
    # Test job search
    print("\n" + "=" * 50)
    print("TEST 1: Job Search")
    print("=" * 50)
    
    jobs = service.scrape_jobs(
        keywords="AI automation specialist",
        location="remote",
        sources=['indeed', 'wellfound']
    )
    
    for source, job_list in jobs.items():
        print(f"\n{source.upper()}: {len(job_list)} jobs")
        for job in job_list[:3]:
            print(f"  - {job.get('title', 'N/A')} at {job.get('company', 'N/A')}")
    
    # Export results
    if any(jobs.values()):
        service.export_results(jobs, 'D:\\job_search_results.csv')
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()

