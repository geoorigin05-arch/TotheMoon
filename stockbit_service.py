from stockbit_downloader import StockbitDownloader
from stockbit_parser import parse_fundamental_from_html

_downloader = None

def get_stockbit_fundamental(stock_code):
    global _downloader

    if _downloader is None:
        _downloader = Stockbit_Downloader()
        _downloader.login()  # sekali saja

    _downloader.load_stock_financials(stock_code.replace(".JK", "").lower())
    html = _downloader.driver.page_source

    return parse_fundamental_from_html(html)
