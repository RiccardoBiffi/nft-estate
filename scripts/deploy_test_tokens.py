import time
from brownie import network, config
from brownie import MockDAI, MockWETH
from scripts.utilities import (
    get_account,
)


BRICK_TOTAL_SUPPLY = 1000000 * 10**18


def publish_source_policy():
    return config["networks"][network.show_active()].get("verify", False)


def deploy():
    account = get_account()

    dai_token = MockDAI.deploy(
        {"from": account},
        publish_source=publish_source_policy(),
    )

    weth_token = MockWETH.deploy(
        {"from": account},
        publish_source=publish_source_policy(),
    )

    print(f"Deployed mock DAI to {dai_token.address}")
    print(f"Deployed mock WETH to {weth_token.address}")


def main():
    deploy()

    time.sleep(1)


if __name__ == "__main__":
    main()
