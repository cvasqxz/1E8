from argparse import ArgumentParser
from binascii import a2b_hex
from base64 import b64encode
import os, requests, json, subprocess


def process_cookie(cookie_path):
    cookie_data = ""

    if not os.path.isfile(cookie_path):
        return None, None

    with open(cookie_path) as f:
        cookie_data = f.read()

    if len(cookie_data) == 0:
        return None, None

    cookie_data = cookie_data.split(":")

    if len(cookie_data) != 2:
        return None, None

    return (cookie_data[0], cookie_data[1])


def rpc_request(method, params=[]):
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": "1e8",
            "method": method,
            "params": [p for p in params]
        }
    )

    req = requests.post(hostport, auth=credentials, data=payload)

    if req.status_code != 200:
        return None

    return req.json()["result"]


def get_tx(txid):
    raw_tx = rpc_request("getrawtransaction", [txid])
    return rpc_request("decoderawtransaction", [raw_tx])


def get_block(height):
    block_hash = rpc_request("getblockhash", [height])
    return rpc_request("getblock", [block_hash])


def parse_varint(s):
    if s[0] < 0xFD:
        return s[0], 1

    if s[0] == 0xFD:
        return int.from_bytes(s[1:4], "little"), 3

    if s[0] == 0xFE:
        return int.from_bytes(s[1:5], "little"), 5

    if s[0] == 0xFF:
        return int.from_bytes(s[1:9], "little"), 9


def find_ordinals(blocks_to_search):
    blockcount = rpc_request("getblockcount")

    for block_height in range(blockcount - blocks_to_search, blockcount + 1):
        block = get_block(block_height)
        print(f"processing block #{block_height} with {len(block['tx'])} transactions")

        for tx_hash in block["tx"]:
            tx = get_tx(tx_hash)

            for vout in tx['vout']:
                if vout['scriptPubKey']['asm'].startswith("OP_RETURN 13"):
                    print(tx['txid'])
                    print(vout['scriptPubKey'])


def main(args):
    global credentials
    global hostport

    credentials = process_cookie(args.c)

    if credentials == (None, None):
        exit()

    if args.n == "mainnet":
        hostport = "http://127.0.0.1:8332"

    if args.n == "testnet":
        hostport = "http://127.0.0.1:18332"

    find_ordinals(args.b)


if __name__ == "__main__":
    parser = ArgumentParser(description="Find the rarity of your satoshis")
    parser.add_argument("-c", help="Bitcoind RPC cookie", required=True)
    parser.add_argument("-n", help="mainnet/testnet", required=True)
    parser.add_argument("-b", type=int, help="how many blocks to process", required=True)
    args = parser.parse_args()

    main(args)
