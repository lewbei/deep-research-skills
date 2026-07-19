import urllib.request
import urllib.parse
import re
import html
from typing import List, Dict

def web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Performs a web search using DuckDuckGo HTML interface and returns a list of dicts with keys 'title', 'link', and 'snippet'.
    """
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html_content = response.read().decode('utf-8', errors='ignore')
            
        # Parse results using regex
        # Look for result containers
        # Typical DDG HTML layout:
        # <div class="web-result...">
        #   <a class="result__snippet" href="link">title</a>
        #   <span class="result__snippet">snippet</span>
        # </div>
        
        # Match links and titles: <a class="result__snippet" href="(.*?)">(.*?)</a>
        # Match snippets: <a class="result__snippet" ...>(.*?)</a>
        # Let's use a simpler match: find divs of class result
        result_blocks = re.findall(r'<div class="result.*?">(.*?)</div>\s*</div>', html_content, re.DOTALL)
        
        results = []
        for block in result_blocks:
            # Extract link and title
            link_match = re.search(r'<a class="result__url" href="(.*?)".*?>(.*?)</a>', block, re.DOTALL)
            if not link_match:
                # Fallback to result__snippet link
                link_match = re.search(r'<a class="result__snippet" href="(.*?)".*?>(.*?)</a>', block, re.DOTALL)
                
            snippet_match = re.search(r'<a class="result__snippet".*?>(.*?)</a>', block, re.DOTALL)
            
            # Extract title and link
            if link_match:
                raw_link = link_match.group(1)
                # Unquote link if it goes through ddg redirect
                link = raw_link
                if "uddg=" in raw_link:
                    parsed_url = urllib.parse.urlparse(raw_link)
                    params = urllib.parse.parse_qs(parsed_url.query)
                    if "uddg" in params:
                        link = params["uddg"][0]
                
                title = re.sub(r'<[^>]*>', '', link_match.group(2)).strip()
                title = html.unescape(title)
            else:
                continue
                
            # Extract snippet
            snippet = ""
            if snippet_match:
                snippet = re.sub(r'<[^>]*>', '', snippet_match.group(1)).strip()
                snippet = html.unescape(snippet)
            else:
                # Try finding result__snippet class in span/div
                span_match = re.search(r'<span class="result__snippet".*?>(.*?)</span>', block, re.DOTALL)
                if span_match:
                    snippet = re.sub(r'<[^>]*>', '', span_match.group(1)).strip()
                    snippet = html.unescape(snippet)
                    
            results.append({
                'title': title,
                'link': link,
                'snippet': snippet
            })
            
            if len(results) >= max_results:
                break
                
        # If no result blocks found, let's try a fallback parser
        if not results:
            # Fallback regex matches
            links = re.findall(r'href="([^"]*?uddg=[^"]*?)"', html_content)
            titles = re.findall(r'class="result__snippet"[^>]*?>(.*?)</a>', html_content, re.DOTALL)
            for idx, raw_link in enumerate(links):
                if idx >= max_results:
                    break
                link = raw_link
                if "uddg=" in raw_link:
                    parsed_url = urllib.parse.urlparse(raw_link)
                    params = urllib.parse.parse_qs(parsed_url.query)
                    if "uddg" in params:
                        link = params["uddg"][0]
                title = re.sub(r'<[^>]*>', '', titles[idx]).strip() if idx < len(titles) else "No Title"
                results.append({
                    'title': html.unescape(title),
                    'link': link,
                    'snippet': ""
                })
                
        return results
    except Exception as e:
        print(f"Error fetching search results: {e}")
        return []
