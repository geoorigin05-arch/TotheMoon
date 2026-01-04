from bs4 import BeautifulSoup
import re

def parse_fundamental_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ")

    def extract(label):
        m = re.search(label + r".*?([0-9.,]+)", text, re.IGNORECASE)
        if m:
            return float(m.group(1).replace(",", ""))
        return None

    return {
        "ROE": extract("ROE"),
        "EPS": extract("EPS"),
        "PER": extract("PER"),
        "PBV": extract("PBV")
    }
