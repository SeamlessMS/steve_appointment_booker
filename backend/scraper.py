import asyncio
import subprocess
import json
import os
import tempfile
from config import get_config
import logging
import random

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_mcp_config(api_token, web_unlocker_zone=None, browser_auth=None):
    """Create a temporary MCP configuration file with Bright Data settings"""
    config = {
        "mcpServers": {
            "Bright Data": {
                "command": "npx",
                "args": ["@brightdata/mcp"],
                "env": {
                    "API_TOKEN": api_token
                }
            }
        }
    }
    
    if web_unlocker_zone:
        config["mcpServers"]["Bright Data"]["env"]["WEB_UNLOCKER_ZONE"] = web_unlocker_zone
    
    if browser_auth:
        config["mcpServers"]["Bright Data"]["env"]["BROWSER_AUTH"] = browser_auth
    
    temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(config, temp_config)
    temp_config.close()
    
    return temp_config.name

def run_mcp_scraper(prompt, config_path):
    """Run a Bright Data MCP scraping task using the MCP client"""
    try:
        cmd = ["npx", "@brightdata/mcp-client", "--config", config_path, "--prompt", prompt]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"MCP client error: {result.stderr}")
            return []
        
        # Parse the output to extract structured data
        try:
            # The output might contain logs and other information before the JSON
            # Look for a valid JSON object in the output
            output_lines = result.stdout.strip().split('\n')
            json_data = None
            
            for line in output_lines:
                line = line.strip()
                if line.startswith('{') and line.endswith('}'):
                    try:
                        json_data = json.loads(line)
                        break
                    except json.JSONDecodeError:
                        continue
            
            if json_data and 'businesses' in json_data:
                return json_data['businesses']
            elif json_data:
                return [json_data]
            else:
                logger.warning("No valid JSON data found in MCP output")
                return []
                
        except json.JSONDecodeError:
            logger.error(f"Failed to parse MCP output: {result.stdout}")
            return []
            
    except Exception as e:
        logger.error(f"Error running MCP client: {str(e)}")
        return []
    finally:
        # Clean up the temporary config file
        if os.path.exists(config_path):
            os.unlink(config_path)

def scrape_businesses(location="Denver, CO", industry="Plumbing", limit=30):
    """Scrape businesses from Google Maps or business directories using Bright Data MCP"""
    config = get_config()
    api_token = config['BRIGHTDATA_API_TOKEN']
    web_unlocker_zone = config['BRIGHTDATA_WEB_UNLOCKER_ZONE']
    browser_auth = config.get('BRIGHTDATA_BROWSER_AUTH', '')
    
    if not api_token:
        logger.warning("No Bright Data API token provided. Using dummy data.")
        return generate_dummy_businesses(location, industry, limit)
    
    # Create MCP config file
    config_path = create_mcp_config(api_token, web_unlocker_zone, browser_auth)
    
    # Craft the prompt for business extraction
    prompt = f"Extract data for {limit} {industry} companies in {location} from Google Maps or business directories. For each business, get their name, phone number, address, website if available, and estimate the number of employees if shown. Return as structured JSON."
    
    # Run the MCP scraper
    businesses = run_mcp_scraper(prompt, config_path)
    
    # Process and format the results
    formatted_businesses = []
    for business in businesses[:limit]:
        city, state = extract_city_state(business.get('address', location))
        formatted_businesses.append({
            'name': business.get('name', f'Unknown {industry} Business'),
            'phone': business.get('phone', 'N/A'),
            'category': industry,
            'address': business.get('address', location),
            'website': business.get('website', ''),
            'employee_count': business.get('employee_count', 0),
            'city': city,
            'state': state,
            'industry': industry
        })
    
    return formatted_businesses

def scrape_yelp_businesses(location="Denver, CO", industry="Plumbing", limit=30):
    """Scrape businesses from Yelp using Bright Data MCP"""
    config = get_config()
    api_token = config['BRIGHTDATA_API_TOKEN']
    web_unlocker_zone = config['BRIGHTDATA_WEB_UNLOCKER_ZONE']
    browser_auth = config.get('BRIGHTDATA_BROWSER_AUTH', '')
    
    if not api_token:
        logger.warning("No Bright Data API token provided. Using dummy data.")
        return generate_dummy_businesses(location, industry, limit)
    
    # Create MCP config file
    config_path = create_mcp_config(api_token, web_unlocker_zone, browser_auth)
    
    # Craft the prompt for business extraction
    prompt = f"Extract data for {limit} {industry} businesses in {location} from Yelp.com. For each business, get their name, phone number, address, website if available, and any info about business size or number of employees. Return as structured JSON."
    
    # Run the MCP scraper
    businesses = run_mcp_scraper(prompt, config_path)
    
    # Process and format the results
    formatted_businesses = []
    for business in businesses[:limit]:
        city, state = extract_city_state(business.get('address', location))
        formatted_businesses.append({
            'name': business.get('name', f'Unknown {industry} Business'),
            'phone': business.get('phone', 'N/A'),
            'category': industry,
            'address': business.get('address', location),
            'website': business.get('website', ''),
            'employee_count': estimate_employee_count(business),
            'city': city,
            'state': state,
            'industry': industry
        })
    
    return formatted_businesses

def estimate_employee_count(business):
    """Estimate employee count based on business data"""
    # Try to use explicit employee count if available
    if 'employee_count' in business and business['employee_count']:
        try:
            return int(business['employee_count'])
        except (ValueError, TypeError):
            pass
    
    # Try to extract from description if available
    if 'description' in business:
        desc = business['description'].lower()
        if 'team of ' in desc:
            try:
                idx = desc.index('team of ') + 8
                end_idx = idx
                while end_idx < len(desc) and (desc[end_idx].isdigit() or desc[end_idx] == ' '):
                    end_idx += 1
                num = ''.join(c for c in desc[idx:end_idx] if c.isdigit())
                if num:
                    return int(num)
            except:
                pass
    
    # Use number of reviews as a rough proxy for size if available
    if 'review_count' in business and business['review_count']:
        try:
            reviews = int(business['review_count'])
            if reviews > 50:
                return 15
            elif reviews > 20:
                return 10
            else:
                return 5
        except:
            pass
    
    # Default estimate based on business category
    return 10  # Default: assume 10 employees

def extract_city_state(address):
    """Extract city and state from an address string"""
    if not address:
        return "Unknown", "Unknown"
    
    # Simple implementation - would need to be more robust in production
    parts = address.split(',')
    if len(parts) >= 2:
        city = parts[-2].strip()
        state_zip = parts[-1].strip().split()
        state = state_zip[0] if state_zip else "Unknown"
        return city, state
    
    return "Unknown", "Unknown"

def generate_dummy_businesses(location="Denver, CO", industry="Plumbing", limit=30):
    """Generate dummy business data for testing"""
    cities = ["Denver", "Colorado Springs"]
    industries = ["Plumbing", "Electrical", "Construction", "HVAC", "Landscaping"]
    
    if location.startswith("Denver"):
        city = "Denver"
        state = "CO"
    elif location.startswith("Colorado Springs"):
        city = "Colorado Springs"
        state = "CO"
    else:
        city = cities[0]
        state = "CO"
    
    if industry not in industries:
        industry = random.choice(industries)
    
    businesses = []
    for i in range(limit):
        business_name = f"{industry} Pro {i+1}"
        employee_count = random.randint(5, 50)
        
        businesses.append({
            'name': business_name,
            'phone': f"720-555-{1000+i:04d}",
            'category': industry,
            'address': f"{100+i} Main St, {city}, {state} 80{200+i}",
            'website': f"https://www.{business_name.lower().replace(' ', '')}.com",
            'employee_count': employee_count,
            'city': city,
            'state': state,
            'industry': industry
        })
    
    return businesses

def scrape_business_leads(location="Denver, CO", industry="Plumbing", limit=30):
    """Scrape business leads from various sources"""
    if ',' not in location:
        location = f"{location}, CO"
    
    config = get_config()
    
    # If Bright Data API token is available, use the real scrapers
    if config['BRIGHTDATA_API_TOKEN']:
        # Scrape from multiple sources and combine results
        businesses = []
        
        # Try to get half from Google Maps/Directories and half from Yelp
        half_limit = limit // 2
        businesses.extend(scrape_businesses(location, industry, half_limit))
        businesses.extend(scrape_yelp_businesses(location, industry, half_limit))
        
        # If we didn't get enough, try to fill in
        if len(businesses) < limit:
            # Try to get more from the first source
            more_businesses = scrape_businesses(location, industry, limit - len(businesses))
            businesses.extend(more_businesses)
        
        # Limit to the requested number
        return businesses[:limit]
    else:
        # Use dummy data if no Bright Data API token
        return generate_dummy_businesses(location, industry, limit)
