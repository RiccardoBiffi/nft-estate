from pathlib import Path
import requests
from brownie import config
from enum import Enum


class UploadType(Enum):
    IPFS = "ipfs"
    PINATA = "pinata"


def upload_with_local_IPFS_node(filepath):
    """
    Needs to run the local IPFS node with command
    > ipfs daemon
    """
    with Path(filepath).open("rb") as fp:  # open file in read mode as bytes
        file_bin = fp.read()

        # info from https://docs.ipfs.io/reference/http/api/#api-v0-add
        ipfs_url = "http://127.0.0.1:5001"  # info from command > ipfs daemon
        endpoint = "/api/v0/add"

        response = requests.post(ipfs_url + endpoint, files={"file": file_bin})

        ipfs_hash = response.json()["Hash"]
        filename = filepath.split("/")[-1]
        file_uri = f"https://ipfs.io/ipfs/{ipfs_hash}?filename={filename}"

        print(f"{filename}: {file_uri}")
        return file_uri


def upload_with_pinata(filepath):
    with Path(filepath).open("rb") as fp:  # open file in read mode as bytes
        file_bin = fp.read()

        # info from https://docs.pinata.cloud/pinata-api/pinning/pin-file-or-directory
        pinata_url = "https://api.pinata.cloud"
        endpoint = "/pinning/pinFileToIPFS"
        filename = filepath.split("/")[-1]
        header = {"Authorization": config["ipfs"]["pinata_jwm"]}

        response = requests.post(
            pinata_url + endpoint,
            headers=header,
            files={"file": (filename, file_bin)},
        )

        ipfs_hash = response.json()["IpfsHash"]
        file_uri = f"https://ipfs.io/ipfs/{ipfs_hash}?filename={filename}"

        print(f"{filename}: {file_uri}")
        return file_uri
