from datetime import date
import traceback
from urllib.parse import urljoin
from travel_search import TravelScraper


class HotelScraper(TravelScraper):
    base_url = "http://booking.com"

    def get_search_url(self):
        city_str = self.city.replace(" ", "+")
        url = "{}/searchresults.en-us.html?&ss=".format(self.base_url)
        url += "{}&dest_type=city&checkin_year={}".format(city_str, self.checkin.year)
        url += "&checkin_month={}&checkin_monthday={}".format(self.checkin.month, self.checkin.day)
        url += "&checkout_year={}&checkout_month={}".format(self.checkout.year, self.checkout.month)
        url += "&checkout_monthday={}&group_adults=2".format(self.checkout.day)
        url += "&order=review_score_and_price&update_av=1&percent_htype_hotel=1&no_dorms=1&shw_aparth=0"
        # filters = price < 160 (this may vary), available props, hotels
        url += "&nflt=rpt%3D1%3Bpri%3D1%3Bpri%3D2%3Bpri%3D3%3Boos%3D1%3Bconcise_unit_type%3D0%3B"
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
                    value.append(tuple(map(float, coordinates['data-coords'].split(",")))[::-1])
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
    hs = HotelScraper("Chicago", "Canada", date1, date2)
    hs.get_prices(2)
    hs.sort_and_filter()
    hs.write_pricing_data()
