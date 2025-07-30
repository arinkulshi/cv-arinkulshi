import json
import requests
import time
import zipfile
import io
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
import re

class CompleteSECCompanySearch:
    def __init__(self, user_agent: str = "MyCompany support@mycompany.com"):
        """
        Complete SEC company search including both public and private companies.
        """
        self.headers = {
            'User-Agent': user_agent
        }
        self.base_delay = 0.1
        self.bulk_submissions_cache = None  # Cache for bulk submissions data
        
        # Enhanced SIC code mapping
        self.sic_mapping = {
            "5812": "Eating Places/Restaurants",
            "7372": "Prepackaged Software", 
            "3571": "Electronic Computers",
            "7373": "Computer Integrated Systems Design",
            "3674": "Semiconductors & Related Devices",
            "6211": "Security Brokers & Dealers",
            "2834": "Pharmaceutical Preparations",
            "3711": "Motor Vehicles & Car Bodies",
            "4813": "Telephone Communications",
            "1311": "Crude Petroleum & Natural Gas",
            "2911": "Petroleum Refining",
            "5961": "Catalog & Mail-Order Houses",
            "7370": "Computer Programming & Data Processing",
            "8742": "Management Consulting Services",
            "2080": "Beverages",
            "3577": "Computer Peripheral Equipment",
            "6141": "Personal Credit Institutions",
            "4899": "Communications Services",
            "7371": "Computer Programming Services",
            "7389": "Business Services, NEC"
        }

        # Form D industry mapping (from SEC Form D categories)
        self.form_d_industries = {
            "Agriculture": "Agriculture",
            "Banking & Financial Services": "Financial Services", 
            "Business Services": "Business Services",
            "Energy": "Energy",
            "Health Care": "Healthcare",
            "Manufacturing": "Manufacturing",
            "Real Estate": "Real Estate",
            "Retailing": "Retail",
            "Restaurants": "Food & Restaurants",
            "Technology": "Technology",
            "Travel": "Travel & Tourism"
        }
    
    def _make_request(self, url: str) -> Optional[Dict]:
        """Make a request with proper rate limiting and error handling."""
        try:
            time.sleep(self.base_delay)
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Request error for {url}: {e}")
            return None

    def _fetch_bulk_submissions_sample(self) -> Optional[Dict]:
        """
        Fetch a sample of the bulk submissions data for searching private companies.
        Note: Full bulk data is 100MB+, so we'll use individual API calls instead.
        """
        try:
            print("Fetching bulk submissions data sample...")
            # For demo purposes, we'll just return None and use individual API calls
            # In production, you might want to download and cache the full bulk data
            return None
        except Exception as e:
            print(f"Error fetching bulk data: {e}")
            return None

    def search_public_companies(self, company_name: str) -> List[Dict]:
        """Search public companies using the tickers API."""
        url = "https://www.sec.gov/files/company_tickers.json"
        companies_data = self._make_request(url)
        
        if not companies_data:
            return []
        
        matches = []
        company_name_lower = company_name.lower()
        
        for key, company in companies_data.items():
            title_lower = company['title'].lower()
            ticker_lower = company.get('ticker', '').lower()
            
            if (company_name_lower in title_lower or 
                company_name_lower in ticker_lower or
                title_lower in company_name_lower):
                
                matches.append({
                    'cik': str(company['cik_str']).zfill(10),
                    'name': company['title'],
                    'ticker': company['ticker'],
                    'company_type': 'public'
                })
        
        return matches

    def search_by_cik_direct(self, cik: str) -> Optional[Dict]:
        """
        Search for a company by CIK directly using submissions API.
        This works for both public and private companies.
        """
        cik_formatted = str(cik).zfill(10)
        url = f"https://data.sec.gov/submissions/CIK{cik_formatted}.json"
        
        submissions_data = self._make_request(url)
        if submissions_data:
            return {
                'cik': cik_formatted,
                'name': submissions_data.get('name', 'Unknown'),
                'ticker': submissions_data.get('tickers', [''])[0] if submissions_data.get('tickers') else '',
                'company_type': 'public' if submissions_data.get('tickers') else 'private',
                'submissions_data': submissions_data
            }
        return None

    def search_edgar_full_text(self, company_name: str, max_results: int = 10) -> List[Dict]:
        """
        Alternative search method using EDGAR's search capabilities.
        Note: This is a conceptual method - actual implementation would require
        parsing EDGAR search results or using a third-party API.
        """
        # This is a placeholder for EDGAR full-text search
        # In practice, you'd need to either:
        # 1. Parse the HTML from sec.gov/edgar/search
        # 2. Use the bulk submissions.zip file
        # 3. Use a third-party SEC API service
        
        print(f"  Searching EDGAR full-text for '{company_name}'...")
        found_companies = []
        
        # For demonstration, let's try some common CIK patterns
        # In reality, you'd search the full EDGAR database
        test_ciks = []
        
        # Try searching recent filings or use other heuristics
        # This is where you'd implement full EDGAR search logic
        
        return found_companies

    def parse_form_d_filing(self, cik: str, accession_number: str) -> Dict:
        """
        Parse a Form D filing to extract industry information.
        """
        industry_info = {
            'industry_category': None,
            'business_description': None,
            'revenue_range': None,
            'offering_amount': None
        }
        
        try:
            # Construct Form D URL
            cik_no_zeros = str(int(cik))  # Remove leading zeros for URL
            acc_clean = accession_number.replace('-', '')
            
            # Try multiple possible URLs for Form D
            possible_urls = [
                f"https://www.sec.gov/Archives/edgar/data/{cik_no_zeros}/{accession_number}/xslFormDX01/primary_doc.xml",
                f"https://www.sec.gov/Archives/edgar/data/{cik_no_zeros}/{accession_number}/primary_doc.xml",
                f"https://www.sec.gov/Archives/edgar/data/{cik_no_zeros}/{accession_number}.txt"
            ]
            
            for url in possible_urls:
                try:
                    response = requests.get(url, headers=self.headers)
                    if response.status_code == 200:
                        if url.endswith('.xml'):
                            # Parse XML Form D
                            content = response.text
                            # Look for industry group information
                            if 'Technology' in content:
                                industry_info['industry_category'] = 'Technology'
                            elif 'Financial' in content or 'Banking' in content:
                                industry_info['industry_category'] = 'Financial Services'
                            elif 'Health' in content or 'Medical' in content:
                                industry_info['industry_category'] = 'Healthcare'
                            # Add more pattern matching as needed
                            
                            # Extract offering amount if available
                            amount_match = re.search(r'Total Offering Amount.*?\$([0-9,]+)', content)
                            if amount_match:
                                industry_info['offering_amount'] = amount_match.group(1)
                                
                        break
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"Error parsing Form D for CIK {cik}: {e}")
        
        return industry_info

    def get_enhanced_submissions_data(self, cik: str) -> Optional[Dict]:
        """Get enhanced submissions data with Form D parsing for private companies."""
        cik_formatted = str(cik).zfill(10)
        url = f"https://data.sec.gov/submissions/CIK{cik_formatted}.json"
        
        submissions_data = self._make_request(url)
        if not submissions_data:
            return None
        
        # Check if this is a private company with Form D filings
        if 'filings' in submissions_data and 'recent' in submissions_data['filings']:
            recent_filings = submissions_data['filings']['recent']
            
            # Look for Form D filings
            for i, form_type in enumerate(recent_filings.get('form', [])):
                if form_type == 'D':  # Form D filing
                    accession_number = recent_filings.get('accessionNumber', [None])[i]
                    if accession_number:
                        # Parse the Form D for industry information
                        form_d_info = self.parse_form_d_filing(cik, accession_number)
                        submissions_data['form_d_info'] = form_d_info
                        break
        
        return submissions_data

    def extract_comprehensive_industry_info(self, submissions_data: Dict, company_name: str) -> Dict:
        """Extract comprehensive industry information from submissions data."""
        industry_info = {
            'sic_code': None,
            'sic_description': None,
            'business_description': None,
            'industry_category': None,
            'company_type': None,
            'form_d_info': None,
            'source': 'submissions'
        }
        
        try:
            # Determine company type
            if submissions_data.get('tickers'):
                industry_info['company_type'] = 'public'
            else:
                industry_info['company_type'] = 'private'
            
            # Extract SIC information
            if 'sic' in submissions_data and submissions_data['sic']:
                industry_info['sic_code'] = submissions_data['sic']
                industry_info['sic_description'] = self.sic_mapping.get(
                    str(submissions_data['sic']), f"SIC {submissions_data['sic']}"
                )
            
            # Extract business description
            if 'businessDescription' in submissions_data:
                desc = submissions_data['businessDescription']
                if len(desc) > 300:
                    desc = desc[:300] + "..."
                industry_info['business_description'] = desc
            
            # Extract Form D information for private companies
            if 'form_d_info' in submissions_data:
                industry_info['form_d_info'] = submissions_data['form_d_info']
                if submissions_data['form_d_info'].get('industry_category'):
                    industry_info['industry_category'] = submissions_data['form_d_info']['industry_category']
            
            # Fallback to name-based classification if no other industry info
            if not any([industry_info['sic_code'], industry_info['industry_category'], industry_info['business_description']]):
                name_classification = self.classify_industry_from_name(company_name)
                industry_info.update(name_classification)
                industry_info['source'] = 'name_classification'
                
        except Exception as e:
            print(f"Error extracting comprehensive industry info: {e}")
        
        return industry_info

    def classify_industry_from_name(self, company_name: str) -> Dict:
        """Classify industry based on company name patterns."""
        name_lower = company_name.lower()
        
        # Enhanced keyword matching
        industry_keywords = {
            'Technology': ['software', 'tech', 'systems', 'data', 'cloud', 'cyber', 'digital', 
                          'computer', 'platform', 'analytics', 'ai', 'artificial intelligence',
                          'app', 'mobile', 'web', 'internet', 'online'],
            'Financial Services': ['bank', 'financial', 'capital', 'investment', 'fund', 'credit', 
                                 'loan', 'mortgage', 'insurance', 'securities', 'finance'],
            'Healthcare': ['pharma', 'medical', 'health', 'bio', 'therapeutic', 'clinical',
                          'hospital', 'drug', 'medicine', 'healthcare'],
            'Retail': ['retail', 'store', 'shop', 'market', 'grocery', 'consumer', 'commerce'],
            'Energy': ['energy', 'oil', 'gas', 'petroleum', 'solar', 'wind', 'utility',
                      'electric', 'power', 'renewable'],
            'Manufacturing': ['manufacturing', 'industrial', 'auto', 'motor', 'machinery',
                            'equipment', 'materials', 'production'],
            'Food & Beverage': ['food', 'restaurant', 'coffee', 'beverage', 'dining', 'kitchen',
                              'cafe', 'bar', 'brewery', 'wine'],
            'Real Estate': ['real estate', 'property', 'construction', 'building', 'development'],
            'Transportation': ['transport', 'logistics', 'shipping', 'delivery', 'freight'],
            'Media': ['media', 'entertainment', 'publishing', 'content', 'broadcast', 'film']
        }
        
        industry_info = {
            'industry_category': 'Unknown',
            'confidence': 'low'
        }
        
        for industry, keywords in industry_keywords.items():
            if any(keyword in name_lower for keyword in keywords):
                industry_info['industry_category'] = industry
                industry_info['confidence'] = 'medium'
                break
        
        return industry_info

    def comprehensive_company_search(self, company_name: str, include_cik: str = None) -> List[Dict]:
        """
        Comprehensive search including both public and private companies.
        """
        all_results = []
        
        # Method 1: Search public companies
        print(f"🔍 Searching public companies for '{company_name}'...")
        public_matches = self.search_public_companies(company_name)
        
        # Method 2: If CIK provided, search directly
        if include_cik:
            print(f"🎯 Searching by CIK: {include_cik}")
            cik_result = self.search_by_cik_direct(include_cik)
            if cik_result:
                public_matches.append(cik_result)
        
        # Method 3: Enhanced processing for all found companies
        for match in public_matches[:5]:  # Limit to avoid rate limiting
            print(f"📊 Processing: {match['name']} (CIK: {match['cik']})...")
            
            # Get enhanced submissions data
            enhanced_data = self.get_enhanced_submissions_data(match['cik'])
            if enhanced_data:
                # Extract comprehensive industry information
                industry_info = self.extract_comprehensive_industry_info(enhanced_data, match['name'])
                
                result = {
                    'cik': match['cik'],
                    'name': match['name'],
                    'ticker': match.get('ticker', ''),
                    'company_type': industry_info.get('company_type', match.get('company_type', 'unknown')),
                    'sic_code': industry_info.get('sic_code'),
                    'sic_description': industry_info.get('sic_description'),
                    'business_description': industry_info.get('business_description'),
                    'industry_category': industry_info.get('industry_category'),
                    'form_d_info': industry_info.get('form_d_info'),
                    'data_source': industry_info.get('source'),
                    'filing_count': len(enhanced_data.get('filings', {}).get('recent', {}).get('form', []))
                }
                
                all_results.append(result)
        
        return all_results


def main():
    # Initialize the comprehensive search
    searcher = CompleteSECCompanySearch("MyCompany support@mycompany.com")
    
    # Test cases including both public and private companies
    test_cases = [
        {"name": "Tesla", "cik": None}, 
        {"name": "Hexify", "cik": "1518449"},  # Private company from your example
    ]
    
    for test_case in test_cases:
        print(f"\n{'='*80}")
        print(f"🚀 SEARCHING: {test_case['name']}")
        if test_case['cik']:
            print(f"📋 Including CIK: {test_case['cik']}")
        print('='*80)
        
        results = searcher.comprehensive_company_search(
            test_case['name'], 
            test_case['cik']
        )
        
        if results:
            for company in results:
                print(f"\n📈 Company: {company['name']}")
                print(f"🎯 CIK: {company['cik']}")
                print(f"🏢 Type: {company['company_type'].upper()}")
                print(f"📊 Ticker: {company['ticker'] or 'N/A'}")
                print(f"🏷️  SIC Code: {company['sic_code'] or 'N/A'}")
                print(f"🏭 SIC Description: {company['sic_description'] or 'N/A'}")
                print(f"🎨 Industry Category: {company['industry_category'] or 'N/A'}")
                print(f"📝 Business Description: {company['business_description'] or 'N/A'}")
                print(f"📋 Filing Count: {company['filing_count']}")
                print(f"📡 Data Source: {company['data_source']}")
                
                if company['form_d_info']:
                    print(f"💼 Form D Info: {company['form_d_info']}")
                    
                print("-" * 60)
        else:
            print("❌ No results found")


if __name__ == "__main__":
    main()
