import json

src_filename = 'D:/Projets_Perso/03d_CodePython/UEVaultManager/testing/metadata_from_EGS_query (new format).json'
dest_filename = 'D:/Projets_Perso/03d_CodePython/UEVaultManager/testing/metadata_converted.json'


def json_data_mapping(data_from_egs_format: dict) -> dict:
    """
    Convert json data from EGS format (NEW) to UEVM format (OLD, i.e. legendary
    :param data_from_egs_format: json data from EGS format (NEW)
    :return: json data in UEVM format (OLD)
    """
    app_name = data_from_egs_format['releaseInfo'][-1]['appId']
    category = data_from_egs_format['categories'][0]['path']

    if category == 'assets/codeplugins':
        category = 'plugins/engine'
    category_1 = category.split('/')[0]
    categorie = [{'path': category}, {'path': category_1}]
    data_to_uevm_format = {
        'app_name': app_name,
        'app_title': data_from_egs_format['title'],
        'asset_infos': {
            'Windows': {
                'app_name': app_name,
                # 'asset_id': data_from_egs_format['id'], # no common value between EGS and UEVM
                # 'build_version': app_name,  # no common value between EGS and UEVM
                'catalog_item_id': data_from_egs_format['catalogItemId'],
                # 'label_name': 'Live-Windows',
                'metadata': {},
                'namespace': data_from_egs_format['namespace']
            }
        },
        'base_urls': [],
        'metadata': {
            'categories': categorie,
            'creationDate': data_from_egs_format['effectiveDate'],
            'description': data_from_egs_format['description'],
            'developer': data_from_egs_format['seller']['name'],
            'developerId': data_from_egs_format['seller']['id'],
            # 'endOfSupport': False,
            'entitlementName': data_from_egs_format['catalogItemId'],
            # 'entitlementType' : 'EXECUTABLE',
            # 'eulaIds': [],
            'id': data_from_egs_format['catalogItemId'],
            # 'itemType': 'DURABLE',
            'keyImages': data_from_egs_format['keyImages'],
            'lastModifiedDate': data_from_egs_format['effectiveDate'],
            'longDescription': data_from_egs_format['longDescription'],
            'namespace': data_from_egs_format['namespace'],
            'releaseInfo': data_from_egs_format['releaseInfo'],
            'status': data_from_egs_format['status'],
            'technicalDetails': data_from_egs_format['technicalDetails'],
            'title': data_from_egs_format['title'],
            # 'unsearchable': False
        }
    }
    return data_to_uevm_format


with open(src_filename, 'r', encoding='utf-8') as src_file:
    data_src = json.load(src_file)

data_dest = json_data_mapping(data_src)

with open(dest_filename, 'w', encoding='utf-8') as dest_file:
    json.dump(data_dest, dest_file, ensure_ascii=False, indent=4)

print(f'Conversion complete. The data was saved in {dest_filename}')
