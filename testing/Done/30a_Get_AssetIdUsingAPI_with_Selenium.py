# coding=utf-8
import requests
import json
from bs4 import BeautifulSoup
from selenium import webdriver


def selenium_setup():
    """
    Set up a Selenium WebDriver for Chrome with specific options.
    :return:  A configured Selenium WebDriver instance for Chrome.
    """
    window_width = 1024
    window_height = 768
    window_left = 2680  # moved to the 3rd screen
    window_top = 0

    options = webdriver.ChromeOptions()
    options.binary_location = r'C:\Program Files\Chromium\Application\chrome.exe'
    options.add_argument(f'--window-size={window_width},{window_height}')  # set the initial size of the window
    options.add_argument(f'--window-position={window_left},{window_top}')  # set the initial position of the window
    options.add_argument('--window-name="UndetectedChrome"')
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')  # Disable the default browser check, do not prompt to set it as such
    options.add_argument('--no-experiments')
    options.add_argument('--enable-gpu')
    options.add_argument('--disable-sync')
    options.add_argument('--disable-extensions')  # Disable all chrome extensions
    options.add_argument('--enable-automation')
    options.add_argument('--disable-client-side-phishing-detection')  # Disables client-side phishing detection
    options.add_argument('--disable-component-extensions-with-background-pages')  # Disable some built-in extensions that aren't affected
    options.add_argument('--disable-default-apps')  # Disable installation of default apps
    options.add_argument('--disable-features=InterestFeedContentSuggestions')  # Disables the Discover feed on NTP
    options.add_argument('--disable-features=Translate')  # Disables Chrome translation,
    options.add_argument('--hide-scrollbars')  # Hide scrollbars from screenshots.
    options.add_argument('--mute-audio')  # Mute any audio
    options.add_argument('--no-first-run')  # Skip first run wizards
    options.add_argument('--ash-no-nudges')  # Avoids blue bubble "user education" nudges (e.g. "… give your browser a new look", Memory Saver)
    options.add_argument('--disable-search-engine-choice-screen')  # Disable the 2023+ search engine choice screen
    options.add_argument('--propagate-iph-for-testing')
    options.add_argument('--disable-features=MediaRouter')

    return webdriver.Chrome(options)


def find_asset_id_via_api(name_or_slug_or_url: str, driver) -> (str, str):
    """
    Find the asset_id and fab_id of an asset on the Unreal Engine Marketplace using its name, slug, or URL.
    :param name_or_slug_or_url:  The name, slug, or URL of the asset to search for.
    :return: A dictionary containing the asset_id and fab_id of the asset if found, otherwise empty strings.
    """
    """
      url de recherche d'assets sur le marketplace Unreal Engine :
      https://www.unrealengine.com/marketplace/api/assets? :
    
      selon copilot:
      
      le simple GET sur https://www.unrealengine.com/marketplace/api/assets
      ne renvoie en fait qu’une petite partie des assets (typiquement les produits payants « en vitrine », un sous-ensemble trié par défaut), et n’inclut pas :
          • les packs “starter” ou freebies
          • les assets non-premium ou hors « vitrine »
          • certaines catégories (ex. les contenus editor-only)
          
      En gros, ce point d’entrée REST est un endpoint non-documenté et statique, à usage “cache”/vitrine, pas un moteur de recherche exhaustif.
    
      Principaux paramètres
      
      OK keywords : terme(s) de recherche
      HS free : true/false (ne garder que les assets gratuits ou payants)
      ? sortBy : relevancy, publishedDate, price, popularity, sales, etc.
      ? sortDir : asc / desc
      ? limit : nombre de résultats par page (ex. 10, 20, 50, 100)
      ? offset : pour paginer (ex. 0, 20, 40…)
      ? locale : en-US, fr-FR, de-DE…
    
      selon gemini 2.5 pro
      Paramètres Possibles:
      
      ? search: Pour rechercher des assets par mot-clé.
          Exemple: https://www.unrealengine.com/marketplace/api/assets?search=environment
      ? category: Pour filtrer les assets par catégorie.
          Exemple: https://www.unrealengine.com/marketplace/api/assets?category=environments/urban
      ? sortBy et sortDir: Pour trier les résultats.
          sortBy peut probablement prendre des valeurs comme relevancy, updated, price, etc.
          sortDir serait ASC (ascendant) ou DESC (descendant).
          Exemple: https://www.unrealengine.com/marketplace/api/assets?sortBy=updated&sortDir=DESC
      ? start et count: Pour la pagination des résultats.
          start serait l'index de départ.
          count serait le nombre de résultats par page.
          Exemple: https://www.unrealengine.com/marketplace/api/assets?start=20&count=20
    
    """
    asset_id = ''
    fab_id = ''
    result = {'asset_id': asset_id, 'fab_id': fab_id}
    # if the input is a URL, extract the slug from it
    if 'https://' in name_or_slug_or_url:
        name_or_slug_or_url = name_or_slug_or_url.split('/')[-1]
    name_encoded = requests.utils.quote(name_or_slug_or_url)
    url = f"https://www.unrealengine.com/marketplace/api/assets?keywords={name_encoded}&sortBy=relevancy&limit=20"
    driver.get(url)
    content = str(driver.page_source)
    soup = BeautifulSoup(content, "html.parser")
    # extraire la balise <pre> contenant le JSON
    pre_tag = soup.find("pre")
    if not pre_tag:
        print("<pre> introuvable dans la page HTML")
        return result
    # convertir le contenu en JSON
    try:
        data = json.loads(pre_tag.string)
    except json.JSONDecodeError as e:
        print(f"Erreur lors de la conversion du contenu en JSON : {e!r}")
        return result

    found = False
    item = {}
    try:
        # The answer contains a 'data' or 'elements' table according to the version of the API
        data_inner = data.get("data", [])
        items = data_inner.get("elements", [])
        for item in items:
            if item.get("title", "").lower() == name_or_slug_or_url.lower() or item.get("urlSlug", "").lower() == name_or_slug_or_url.lower():
                found = True
                break
            release_infos = item.get("releaseInfo", {})
            for release in release_infos:
                if release.get("versionTitle", "").lower() == name_or_slug_or_url.lower() or release.get("appId",
                                                                                                         "").lower() == name_or_slug_or_url.lower():
                    found = True
                    break

        if found:
            asset_id = item.get('id', '')
            fab_id = item.get('customAttributes', {}).get('FabListingId', {}).get('value', '')
    except (Exception, ) as e:
        print(f"Erreur lors de l'extraction des données : {e!r}")
    return {'asset_id': asset_id, 'fab_id': fab_id}


if __name__ == "__main__":
    driver = selenium_setup()
    # try to get the asset_id and the fab_id of an asset using its name or urlslug
    # need a selenium browser to bypass the captcha
    # NOTE: "animation-starter-pack", "AnimStarterPack" are not found even if they exist on the marketplace ! (why ?)

    names_or_slugs = ["unrealJs", "volcrate", "animation-starter-pack", "AnimStarterPack"]
    for name_or_slug in names_or_slugs:
        ids = find_asset_id_via_api(name_or_slug, driver)
        m_asset_id = ids.get('asset_id', None)
        m_fab_id = ids.get('fab_id', None)
        if m_asset_id:
            print(f"Asset_id for '{name_or_slug}': {m_asset_id}")
            print(f"fab_id for '{name_or_slug}': {m_fab_id}")
        else:
            print(f"Asset '{name_or_slug}' not found via API.")
