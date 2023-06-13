import requests
import unreal_engine as ue


def get_tag_name(tag_id):
    """
    Gets the tag name corresponding to a given tag id using the Unreal Engine API

    :param tag_id: str; The ID corresponding to the tag
    :return: str; The name of the tag, or None if the tag_id does not exist.
    """
    all_tags = ue.EditorAssetLibrary.get_all_tags()

    for tag in all_tags:
        if tag.tag_id == tag_id:
            return tag.tag_name

    return None


if __name__ == "__main__":
    tag_id = "22"  # Replace this with the tag id you want to find the name for
    tag_name = get_tag_name(tag_id)

    if tag_name:
        print(f"Tag ID: {tag_id} corresponds to Tag Name: {tag_name}")
