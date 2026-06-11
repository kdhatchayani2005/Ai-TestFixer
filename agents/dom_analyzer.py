import difflib
from bs4 import BeautifulSoup

class DOMAnalyzer:
    def __init__(self):
        pass
        
    def run(self, driver, failed_locator):
        """
        Extracts page source, parses it using BeautifulSoup4, and searches
        all tags for 'id', 'name', and 'class' attributes that are similar
        to the failed_locator. Returns candidates with similarity >= 0.4.
        """
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        
        candidates = []
        
        # We walk through all elements in the document
        for tag in soup.find_all(True):
            # Check ID
            if tag.has_attr("id"):
                val = tag["id"]
                score = difflib.SequenceMatcher(None, str(failed_locator), str(val)).ratio()
                if score >= 0.4:
                    candidates.append({
                        "tag": tag.name,
                        "attribute_type": "id",
                        "value": str(val),
                        "similarity_score": round(score, 4)
                    })
                    
            # Check Name
            if tag.has_attr("name"):
                val = tag["name"]
                score = difflib.SequenceMatcher(None, str(failed_locator), str(val)).ratio()
                if score >= 0.4:
                    candidates.append({
                        "tag": tag.name,
                        "attribute_type": "name",
                        "value": str(val),
                        "similarity_score": round(score, 4)
                    })
                    
            # Check Class
            if tag.has_attr("class"):
                # BS4 parsed class is a list of strings
                class_list = tag["class"]
                if isinstance(class_list, list):
                    val = " ".join(class_list)
                else:
                    val = str(class_list)
                    
                score = difflib.SequenceMatcher(None, str(failed_locator), val).ratio()
                if score >= 0.4:
                    candidates.append({
                        "tag": tag.name,
                        "attribute_type": "class",
                        "value": val,
                        "similarity_score": round(score, 4)
                    })
                    
        # Sort by similarity score descending
        candidates = sorted(candidates, key=lambda x: x["similarity_score"], reverse=True)
        
        # De-duplicate identical candidate listings to keep results clean
        seen = set()
        deduped_candidates = []
        for c in candidates:
            key = (c["tag"], c["attribute_type"], c["value"])
            if key not in seen:
                seen.add(key)
                deduped_candidates.append(c)
                
        return deduped_candidates
