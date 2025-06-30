# coding=utf-8
import nodriver as uc
import json

async def main():
    # Start the headless browser
    browser = await uc.start(
    browser_executable_path="C:/Program Files/Chromium/Application/chrome.exe",
        headless=True
    )

    # Navigate to the Amazon product page
    page = await browser.get(
        "https://www.amazon.in/Meta-Quest-Console-Virtual-Reality/dp/B0CB3WXL12"
    )

    # Extracting product title
    title_element = await page.select("#productTitle")
    title = title_element.text.strip() if title_element else None

    # Extracting product price
    price_element = await page.select("span.a-offscreen")
    price = price_element.text if price_element else None

    # Extracting product rating
    rating_element = await page.select("#acrPopover")
    rating_text = rating_element.attrs.get("title") if rating_element else None
    rating = rating_text.replace("out of 5 stars", "") if rating_text else None

    # Extracting product image URL
    image_element = await page.select("#landingImage")
    image_url = image_element.attrs.get("src") if image_element else None

    # Extracting product description
    description_element = await page.select("productDescription")
    description = description_element.text.strip() if description_element else None

    # Extracting number of reviews
    reviews_element = await page.select("#acrCustomerReviewText")
    reviews = reviews_element.text.strip() if reviews_element else None

    # Storing extracted data in a dictionary
    product_data = {
        "Title": title,
        "Price": price,
        "Description": description,
        "Image Link": image_url,
        "Rating": rating,
        "Number of Reviews": reviews,
    }

    # Saving data to a JSON file
    with open("product_data.json", "w", encoding="utf-8") as json_file:
        json.dump(product_data, json_file, ensure_ascii=False)
    print("Data has been saved to product_data.json")

    # Stopping the headless browser
    browser.stop()

if __name__ == "__main__":
    # Running the main function
    uc.loop().run_until_complete(main())