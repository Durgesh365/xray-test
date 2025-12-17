
What is wiki_space_key?
Yes, it's necessary! In Confluence, every page belongs to a "Space". Think of it like this:

Space = Top-level container (like a separate wiki site)
Pages = Content within that space, organized in a hierarchy

For example, "STI-Standard Tools and Infrastructure" is likely your Space key (probably something like "STI" or "STITOOLS").
Updated Solution
Since you have different folder paths for each app, we need to:

Store the complete parent page path in config
Navigate through the hierarchy to find the correct parent page

1. Update config.yaml
yamlMITO:
  fix_version: "v1.2.3"
  wiki_space_key: "STI"  # or whatever your space key is
  wiki_parent_path: "STI-Standard Tools and Infrastructure/MITO/MITO FY-25/MITO Release"
  # other existing keys...

Omniview:
  fix_version: "v2.0.1"
  wiki_space_key: "STI"
  wiki_parent_path: "STI-Standard Tools and Infrastructure/STI/Omniview/Omniview Release"
  # other existing keys...
2. Update config.py
python@dataclass
class Appconfig:
    jira_url: str
    fix_version: str
    wiki_space_key: str
    wiki_parent_path: str
    # ... other existing fields

def get_app_config(app_name: str) -> Appconfig:
    app = config_data.get(app_name)
    if not app:
        raise ValueError(f"App {app_name} not found in config")
    
    return Appconfig(
        jira_url=os.getenv("jiraUrl"),
        fix_version=app.get("fix_version"),
        wiki_space_key=app.get("wiki_space_key", "STI"),
        wiki_parent_path=app.get("wiki_parent_path"),
        # ... other fields
    )
3. Updated wiki_utils.py
pythonimport os
import json
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def find_page_by_path(space_key: str, page_path: str, headers: dict) -> Optional[str]:
    """
    Navigate through wiki hierarchy to find the parent page ID.
    
    Args:
        space_key: Confluence space key
        page_path: Path like "Parent1/Parent2/Parent3"
        headers: Request headers with authentication
    
    Returns:
        Page ID of the final page in the path, or None if not found
    """
    api_endpoint = "https://wiki.siemens-energy.com/rest/api/content"
    
    pages = page_path.split("/")
    current_parent_id = None
    
    for i, page_title in enumerate(pages):
        page_title = page_title.strip()
        logger.info(f"Searching for page: '{page_title}' (level {i+1}/{len(pages)})")
        
        # Build search URL
        if current_parent_id:
            # Search within the parent page
            search_url = f"{api_endpoint}/{current_parent_id}/child/page?title={page_title}"
        else:
            # Search at space root level
            search_url = f"{api_endpoint}?title={page_title}&spaceKey={space_key}&expand=ancestors"
        
        try:
            response = requests.get(search_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                if results:
                    current_parent_id = results[0]['id']
                    logger.info(f"Found page '{page_title}' with ID: {current_parent_id}")
                else:
                    logger.error(f"Page '{page_title}' not found in the hierarchy")
                    return None
            else:
                logger.error(f"Error searching for '{page_title}': {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Exception while searching for '{page_title}': {str(e)}")
            return None
    
    return current_parent_id


def create_wiki_page(html_content: str, page_title: str, space_key: str, parent_path: str) -> str:
    """
    Create a wiki page with the given HTML content under a specific parent path.
    
    Args:
        html_content: HTML content to publish
        page_title: Page title (typically the fix_version)
        space_key: Confluence space key
        parent_path: Full path to parent page (e.g., "Parent1/Parent2/Parent3")
    
    Returns:
        URL of created page or error message
    """
    api_endpoint = "https://wiki.siemens-energy.com/rest/api/content"
    session_cookie = os.getenv("WIKI_SESSION_COOKIE")
    
    if not session_cookie:
        logger.error("WIKI_SESSION_COOKIE environment variable not set")
        return "Error: Wiki session cookie not configured"
    
    headers = {
        "Cookie": session_cookie,
        "Content-Type": "application/json",
        "X-Atlassian-Token": "no-check"
    }
    
    # Find the parent page ID by navigating the path
    logger.info(f"Finding parent page in path: '{parent_path}'")
    parent_id = find_page_by_path(space_key, parent_path, headers)
    
    if not parent_id:
        logger.error(f"Could not find parent page at path: '{parent_path}'")
        return "Error: Parent page not found in wiki hierarchy"
    
    logger.info(f"Will create page '{page_title}' under parent ID: {parent_id}")
    
    # Prepare page data
    page_data = {
        "type": "page",
        "title": page_title,
        "space": {
            "key": space_key
        },
        "ancestors": [{"id": parent_id}],
        "body": {
            "storage": {
                "value": html_content,
                "representation": "storage"
            }
        }
    }
    
    # Create wiki page
    logger.info(f"Creating wiki page: '{page_title}'")
    try:
        response = requests.post(
            api_endpoint,
            headers=headers,
            data=json.dumps(page_data)
        )
        
        if response.status_code == 200:
            result = response.json()
            page_url = f"https://wiki.siemens-energy.com{result['_links']['webui']}"
            logger.info(f"Wiki page created successfully: {page_url}")
            return page_url
        else:
            logger.error(f"Failed to create page: {response.status_code} - {response.text}")
            return f"Error: Failed to create page - {response.status_code}"
    except Exception as e:
        logger.error(f"Exception while creating wiki page: {str(e)}")
        return f"Error: {str(e)}"
4. Update email_run.py
pythonfrom .wiki_utils import create_wiki_page

def run():
    try:
        html = read_report_html(html_path)
        
        # Send email
        try:
            send_email_html(
                # ...,
                subject=subject,
                html_body=html,
                # ...
            )
            logger.info("Email sent successfully")
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
        
        # Create wiki page with fix_version as the page title
        try:
            wiki_url = create_wiki_page(
                html_content=html,
                page_title=cfg.fix_version,  # Using fix_version as page name
                space_key=cfg.wiki_space_key,
                parent_path=cfg.wiki_parent_path
            )
            
            if wiki_url.startswith("http"):
                logger.info(f"Wiki page published: {wiki_url}")
            else:
                logger.error(f"Wiki page creation failed: {wiki_url}")
        except Exception as e:
            logger.error(f"Exception during wiki page creation: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error in run: {str(e)}")
