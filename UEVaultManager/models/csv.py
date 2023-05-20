"""
Implementation for:
- CSV_headings: contains the title of each column and a boolean value to know if its contents must be preserved if it already exists in the output file (To Avoid overwriting data changed by the user in the file)
"""
CSV_headings = {
    'Asset_id': False,  # ! important: Do not Rename => this field is used as main key for each asset
    'App name': False,
    'App title': False,
    'Category': False,
    'UE Version': False,
    'Review': False,
    'Developer': False,
    'Description': False,
    'Status': False,
    'Discount Price': False,
    'On sale': False,
    'Purchased': False,
    'Obsolete': False,
    'Supported Versions': False,
    'Grab result': False,
    'Price': False,  # ! important: Rename Wisely => this field is searched by text in the next lines
    'Old Price': False,  # ! important: always place it after the Price field in the list
    # User Fields
    'Comment': True,
    'Stars': True,
    'Must Buy': True,
    'Test result': True,
    'Installed Folder': True,
    'Alternative': True,
    'Asset Folder': True,
    # less important fields
    'Page title': False,
    'Image': False,
    'Url': True,  # could be kept if a better url that can be used to download the asset is found
    'Compatible Versions': False,
    'Date Added': True,
    'Creation Date': False,
    'Update Date': False,
    'Uid': False
}
