""""Simple Python class to obtain pricing data for various travel searches."""

import time
import traceback
from datetime import date, timedelta
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import pandas as pd

UA = UserAgent()
DEBUG = True


class TravelScraper:
    """Generic travel scraping class."""
    base_url = None
    header = {'User-Agent': str(UA.chrome)}

    def __init__(self, city, country='USA', checkin=date.today(),
                 checkout=date.today() + timedelta(days=1)):
        self.city = city
        self.country = country
        self.checkin = checkin
        self.checkout = checkout
        self.pricing_data = None

    def get_prices(self, num_results=5):
        """Scrape prices from the specified number of pages and put results in pandas dataframe."""

        url = self.get_search_url()
        response = requests.get(url, headers=self.header)
        if response.ok:
            soup = BeautifulSoup(response.text, "lxml")
            links = self.get_page_links(soup)
            data = None
            for link in links[:num_results]:
                time.sleep(0.5)
                response = requests.get(link, headers=self.header)
                if not response.ok:
                    continue
                soup = BeautifulSoup(response.text, "lxml")
                data = self.process_results(soup, data)
            self.pricing_data = pd.DataFrame.from_dict(data)
            if DEBUG:
                with open(self.pricing_file(), 'w') as f:
                    self.pricing_data.to_csv(f, index=False)

    def get_search_url(self):
        """Overload this method to return search url."""
        pass

    def get_page_links(self, base_page):
        """Overload this method to return all the pages to search."""
        pass

    def process_results(self, page, page_data=None):
        """Method to process each result page and return the data."""
        return {}

    def sort_and_filter(self):
        """TODO:  Add sorting and filtering to the results"""
        pass

    def pricing_file(self):
        """Write out a csv of the pricing data."""
        return self.base_url.split("//")[-1].split(".")[0] + ".csv"


class HotelScraper(TravelScraper):
    base_url = "http://booking.com"

    def get_search_url(self):
        url = "{}/searchresults.en-us.html?&ss=".format(self.base_url)
        url += "{}&dest_type=city&checkin_year={}".format(self.city, self.checkin.year)
        url += "&checkin_month={}&checkin_monthday={}".format(self.checkin.month, self.checkin.day)
        url += "&checkout_year={}&checkout_month={}".format(self.checkout.year, self.checkout.month)
        url += "&checkout_monthday={}&group_adults=2".format(self.checkout.day)
        url += "&order=review_score_and_price&update_av=1&percent_htype_hotel=1"
        return url

    def get_page_links(self, base_page):
        return [urljoin(self.base_url, link['href']) for link in
                base_page.find_all("a", {"class": "bui-pagination__link"})]

    def process_results(self, html, page_data=None):
        keys = ["name", "score", "location", "price", "url"]
        if page_data is None:
            page_data = {key: [] for key in keys}
        divs = html.find_all("div", {"class": "sr_property_block"})
        for div in divs:
            try:
                if 'soldout_property' in div['class']:
                    continue
                value = list()
                value.append(div.find("span", {"class": "sr-hotel__name"}).text.strip())
                value.append(float(div['data-score']))
                coordinates = div.find("a", {"class": "bui-link"})
                if not coordinates:
                    coordinates = div.find("a", {"class": "map_address_pin"})
                if coordinates:
                    value.append(tuple(map(float, coordinates['data-coords'].split(","))))
                else:
                    value.append((0, 0))
                hotel_price = "".join([c for c in div.find("strong", {"class": "price"}).text.strip() if c.isdigit()])
                value.append(float(hotel_price))
                value.append(urljoin(self.base_url, div.find("a", {"class": "sr_item_photo_link"})['href'].split("?")[0]))
            except:
                traceback.print_exc()
            else:
                for i, key in enumerate(keys):
                    page_data[key].append(value[i])
        return page_data


if __name__ == '__main__':
    date1 = date(2019, 5, 28)
    date2 = date(2019, 5, 30)
    hs = HotelScraper("Atlanta", "Canada", date1, date2)
    hs.get_prices(2)
