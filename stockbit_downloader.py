from selenium import webdriver
from time import sleep

class StockbitDownloader:
    def __init__(self):
        self.download_path = "./stockbit"
        self.driver = webdriver.Chrome("chromedriver")  # pastikan di PATH
        self.target_url = "https://stockbit.com/"

    def login(self, username, password):
        self.driver.get(self.target_url + "#/login")
        sleep(2)
        self.driver.find_element_by_id("username").send_keys(username)
        self.driver.find_element_by_id("password").send_keys(password)
        self.driver.find_element_by_id("loginbutton").click()

    def load_stock_financials(self, stock="asii"):
        self.driver.get(self.target_url + f"#/symbol/{stock}/financials")

    def save_html(self, stock_code):
        with open(f"{stock_code}.html", "w", encoding="utf-8") as f:
            f.write(self.driver.page_source)

if __name__ == "__main__":
    dl = StockbitDownloader()
    dl.login("Zhaaa5", "Prasetyadwi24")
    sleep(3)
    dl.load_stock_financials("asii")
    dl.save_html("ASII")
