""""Simple Python class to obtain pricing data for various travel searches."""

import time
from enum import Enum
from datetime import date, timedelta
import requests
from geopy import Nominatim
from geopy.distance import great_circle
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import pandas as pd

UA = UserAgent()
DEBUG = True


def get_geolocation(location):
    geo_location = Nominatim().geocode(location)
    return geo_location


class OutputType(Enum):
    Html = 'html'
    Csv = 'csv'
    Json = 'json'


class TravelScraper:
    """Generic travel scraping class."""
    base_url = None
    header = {'User-Agent': str(UA.chrome)}

    def __init__(self, city, country='USA', checkin=date.today(),
                 checkout=date.today() + timedelta(days=1)):
        # inputs
        self.city = city
        self.country = country
        self.checkin = checkin
        self.checkout = checkout
        self.raw_pricing_data = None
        self.filtered_data = None
        self.base_loc = get_geolocation(city)
        self.output_type = OutputType.Html
        # filters
        self._max_price = 1000
        self._min_score = 7.0
        self._max_dist = 5.0
        self._sort_by = ("price", False)

    # properties

    @property
    def max_price(self):
        return self._max_price

    @max_price.setter
    def max_price(self, price):
        if price > 25:
            self._max_price = price
        else:
            raise ValueError("Max Price: {} too Low!".format(price))

    @property
    def min_score(self):
        return self._min_score

    @min_score.setter
    def min_score(self, score):
        if score < 1.0 or score > 9.0:
            self._min_score = score
        else:
            raise ValueError("Min Score: {} invalid!".format(score))

    @property
    def max_dist(self):
        return self._max_dist

    @max_dist.setter
    def max_dist(self, dist):
        if dist > 0.0:
            self._max_dist = dist
        else:
            raise ValueError("Max Distance {} must be positive!".format(price))

    @property
    def sort_by(self):
        return self._sort_by

    @max_dist.setter
    def max_dist(self, sort_col, ascending=True):
        if sort_col in self.raw_pricing_data:
            self._sort_by = (sort_col, ascending)
        else:
            raise ValueError("Column {} does not exist!".format(sort_col))

    def get_prices(self, num_results=5):
        """Scrape prices from the specified number of pages and put results in pandas dataframe."""

        url = self.get_search_url()
        response = requests.get(url, headers=self.header)
        if response.ok:
            soup = BeautifulSoup(response.text, "lxml")
            data = self.process_results(soup)
            links = self.get_page_links(soup)
            for link in links[:num_results]:
                time.sleep(0.5)
                response = requests.get(link, headers=self.header)
                if not response.ok:
                    continue
                soup = BeautifulSoup(response.text, "lxml")
                data = self.process_results(soup, data)
            self.raw_pricing_data = pd.DataFrame.from_dict(data)
            # calc distances
            self.raw_pricing_data['distance'] = self.raw_pricing_data.location.apply(self.calc_distance)

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
        """Filter the results based on user-entered parameters."""
        df = self.raw_pricing_data
        self.filtered_data = df[(df['price'] < self.max_price) & (df['score'] > self.min_score)
                                & (df['distance'] < self.max_dist)]
        sort_by, ascending = self.sort_by
        self.filtered_data.sort_values(sort_by, ascending=ascending)
        self.custom_sort_and_filter()

    def custom_sort_and_filter(self):
        """Allows subclasses to apply unique sort/filter."""
        pass

    def write_pricing_data(self):
        ext = "." + str(self.output_type.value)
        with open(self.pricing_file() + ext, 'w') as f:
            if self.output_type == OutputType.Html:
                self.filtered_data.to_html(f)
            elif self.output_type == OutputType.Json:
                self.filtered_data.to_json(f)
            elif self.output_type == OutputType.Csv:
                self.filtered_data.to_csv(f)
            else:
                raise NotImplementedError

    def pricing_file(self):
        """Write out a csv of the pricing data."""
        return self.base_url.split("//")[-1].split(".")[0]

    def calc_distance(self, location):
        target = (self.base_loc.latitude, self.base_loc.longitude)
        return great_circle(location, target).miles

