import json

import requests
from bs4 import BeautifulSoup


def get_asset_data_from_marketplace(url: str) -> dict:
    """
    Function to scrape scripts from a given url using BeautifulSoup.
    :param url: The url to scrape.
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Finding all script tags in the HTML
    # scripts = soup.find_all('script')

    # Finding all script tags with the type 'application/ld+json' in the HTML
    scripts = soup.find_all('script', {'type': 'application/ld+json'})

    # for index, script in enumerate(scripts):
    #     print(f"Script {index+1}:\n{script}\n")

    json_data = {}
    for index, script in enumerate(scripts):
        # Remove script tags
        json_text = script.string

        # Convert to Python dictionary
        json_dict = json.loads(json_text)

        # {'@context'   : 'https://schema.org', '@type': 'Product', 'sku': 'd27cf128fdc24e328cf950b019563bc5',
        #  'productID'  : 'd27cf128fdc24e328cf950b019563bc5', 'name': 'Volcrate', 'category': 'Characters',
        #  'image'      : ['https://cdn1.epicgames.com/ue/item/Volcrate_FeaturedNew-894x488-ad93ea4be7589802d9dc289a4af3a751.png'],
        #  'description': 'Here is a Volcrate, this race is a crossing between a bird and a human. They mostly behave as barbarians with their impressive musculature, performing powerful devastating attacks.',
        #  'releaseDate': '2016-12-21T00:00:00.000Z', 'brand': {'@type': 'Brand', 'name': 'Unreal Engine', 'logo': {'@type': 'ImageObject',
        #                                                                                                           'url'  : 'https://cdn2.unrealengine.com/Unreal+Engine%2Flogos%2FUnreal_Engine_Black-1125x1280-cfa228c80703d4ffbd1cc05eabd5ed380818da45.png'}},
        #  'offers'     : {'@type': 'Offer', 'price': '29.99', 'availability': 'http://schema.org/InStock', 'priceCurrency': 'USD',
        #                  'url'  : 'https://www.unrealengine.com/marketplace/en-US/product/volcrate'}
        # }

        # print(f"Script {index + 1}:\n{json_dict}\n")

        # check if the script describes a product
        if json_dict['@type'] == 'Product':
            try:
                json_data['id'] = json_dict['productID']
                json_data['name'] = json_dict['name']
                json_data['category'] = json_dict['category']
                json_data['description'] = json_dict['description']
                json_data['image'] = json_dict['image']
                json_data['release_date'] = json_dict['releaseDate']
                json_data['url'] = json_dict['offers']['url']  # must be the same as url
                json_data['price'] = json_dict['offers']['price']
                json_data['price_currency'] = json_dict['offers']['priceCurrency']
            except KeyError as error:
                print(f"A key is missing in Script {index + 1}: {error!r}")
                continue
    if json_data['url'].lower().replace('www.', '') != url.lower().replace('www.', ''):
        print(f"URLs do not match: {json_data['url']} != {url}")
    return json_data


if __name__ == "__main__":
    asset = get_asset_data_from_marketplace('https://www.unrealengine.com/marketplace/en-US/product/volcrate')
    print(asset)
