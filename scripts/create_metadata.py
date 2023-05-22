import json
from pathlib import Path
from urllib.parse import urlparse
from brownie import config
from scripts.utilities import get_breed, is_local_blockchain
from scripts.upload_to_ipfs import (
    upload_with_local_IPFS_node,
    upload_with_pinata,
    UploadType,
)
from brownie import CoincreteAsset, network
from metadata.metadata_template import metadata_template

# todo clean up

DESC_EXCLAMATIONS = [
    "Such a good boy!",
    "Much wow!",
    "Goood boy!",
    "Squirrel?",
    "Wooof!",
    "Uh a mailman!",
    "Back to my tail...",
    "Bau bau!",
    "Wof woooof!",
    "Any treat for me?",
]

BASE_ATTRIBUTE = [
    "Smart",
    "Playful",
    "Fast",
    "Fabulous",
    "Funny",
    "Adorable",
    "Strong",
    "Sneaky",
    "Hungry",
    "Sweet",
]


def create_metadata():
    ac = CoincreteAsset[-1]
    n_token = ac.tokenCounter()
    print(f"You have created {n_token} NFT on contract {ac.address}\n")

    NFTs_metadata_URI = {}
    URI_file_name = f"./metadata/{network.show_active()}/URIs.json"

    for token_id in range(n_token):
        breed = get_breed(ac.tokenId_Dog(token_id)[0])
        md_file_name = f"./metadata/{network.show_active()}/{token_id}-{breed}.json"

        if config["ipfs"]["overwrite_metadata"] or not Path(md_file_name).exists():
            uri = create_NFT_metadata(md_file_name, ac.tokenId_Dog(token_id))
            NFTs_metadata_URI[str(token_id)] = uri

        else:
            print(f"File {md_file_name} already exists. Delete it to overwrite it")
            print("Check brownie-config > ipfs > overwrite_metadata\n")

    if NFTs_metadata_URI is not {}:
        if config["ipfs"]["overwrite_metadata"]:
            # save URI on file
            with open(URI_file_name, "w") as fp:
                json.dump(NFTs_metadata_URI, fp)
        else:
            with open(f"./metadata/{network.show_active()}/URIs.json", "a+") as fp:
                try:
                    fp.seek(0)
                    previous_NFTs_URI = json.load(fp)
                except:
                    print("Exception opening file")
                    previous_NFTs_URI = {}

            print(previous_NFTs_URI)
            print(NFTs_metadata_URI)

            updated_NFTs_URI = previous_NFTs_URI | NFTs_metadata_URI
            with open(f"./metadata/{network.show_active()}/URIs.json", "w") as fp:
                json.dump(updated_NFTs_URI, fp)


def get_image_from(breed):
    return "./img/" + breed.lower().replace("_", "-") + ".png"


def create_NFT_metadata(md_file_name, data):
    print(f"Creating {md_file_name}")

    NFT_metadata = metadata_template

    NFT_metadata["name"] = get_breed(data[0]).replace("_", " ").capitalize()
    NFT_metadata["description"] = (
        f"A beautiful {NFT_metadata['name']} pup. " + DESC_EXCLAMATIONS[data[2]]
    )

    NFT_metadata["attributes"][0]["value"] = BASE_ATTRIBUTE[data[1]]
    NFT_metadata["attributes"][1]["value"] = data[3]
    NFT_metadata["attributes"][2]["value"] = data[4]
    image_path = get_image_from(get_breed(data[0]))
    image_uri = (
        upload_with_pinata(image_path)
        if config["ipfs"]["upload_type"] == UploadType.PINATA.value
        else upload_with_local_IPFS_node(image_path)
    )
    NFT_metadata["image"] = image_uri

    # save metadata on file
    with open(md_file_name, "w") as fp:
        json.dump(NFT_metadata, fp)

    if config["ipfs"]["upload_type"] == UploadType.PINATA.value:
        metadata_URI = upload_with_pinata(md_file_name)
    else:
        metadata_URI = upload_with_local_IPFS_node(md_file_name)

    return metadata_URI


def get_hash(file_URI):
    return urlparse(file_URI).path.split("/")[-1]


def main():
    if is_local_blockchain():
        print("\n!!!Run me on the rinkeby network!!!\n")
        return
    create_metadata()
