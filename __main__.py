from argparse import ArgumentParser
from binascii import unhexlify
from base64 import b64encode
import os, requests, json


def process_cookie(cookie_path):
    with open(cookie_path) as f:
        cookie_data = f.read().split(":")
        return (cookie_data[0], cookie_data[1])


def rpc_request(method, params=[]):
    payload = json.dumps({"jsonrpc": "2.0", "id": "1e8", "method": method, "params": [p for p in params]})
    req = requests.post(hostport, auth=credentials, data=payload)

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


def find_ordinals(block_height):
    found = []

    #block_count = rpc_request("getblockcount")

    block = get_block(block_height)
    print(f"processing block #{block_height} with {len(block['tx'])} transactions")

    for tx_hash in block["tx"]:
        tx = get_tx(tx_hash)

        for vin in tx["vin"]:
            # ONLY READ SEGWIT TX
            if not "txinwitness" in vin:
                continue

            vin_pos = 0
            for witness in vin["txinwitness"]:
                bin_witness = unhexlify(witness)

                # IGNORE WITNESS WITHOUT 'ord' or '/'
                if not b"ord" in bin_witness or not b"/" in bin_witness:
                    continue
                
                # POINTER 
                p = 0
                metadata = b""

                len_program, c = parse_varint(bin_witness)
                p += c
                program = bin_witness[p : p + len_program]
                p += len_program + 9

                len_mimetype, c = parse_varint(bin_witness[p:])
                p += c
                mimetype = bin_witness[p : p + len_mimetype]
                p += len_mimetype

                # IGNORE WEIRD MIMETYPE
                if not b"/" in mimetype:
                    continue

                # IGNORE CURSED ORDINALS
                if bin_witness[p] != 0x00:
                    continue

                # OP_0
                p += 1
                
                while (p + 1) < len(bin_witness):

                    # PUSHDATA (0x01 to 0x4b)
                    if bin_witness[p] <= 0x4b:
                        len_chunk = bin_witness[p]
                        p += 1

                    # OP_PUSHDATA1
                    elif bin_witness[p] == 0x4c:
                        len_chunk = bin_witness[p+1]
                        p += 2

                    # OP_PUSHDATA2
                    elif bin_witness[p] == 0x4d:
                        len_chunk = int.from_bytes(bin_witness[p + 1 : p + 3], "little")
                        p += 3

                    # OP_PUSHDATA4
                    elif bin_witness[p] == 0x4e:
                        len_chunk = int.from_bytes(bin_witness[p + 1 : p + 5], "little")
                        p += 5
    
                    else:
                        p += 1
                        print(f"FATAL ERROR, INVALID OPCODE {bin_witness[p]} BLOCK {block_height} TX {tx_hash}")
                        exit()
                        
                    
                    metadata += bin_witness[p : p + len_chunk]
                    p += len_chunk

                if not p + 1 == len(bin_witness):
                    print(f"FATAL ERROR BLOCK {block_height} TX {tx_hash}")
                    exit()

                mimetype = mimetype.decode("utf-8")
                b64_metadata = b64encode(metadata).decode("utf-8")

                final_inscription = f"data:{mimetype};base64,{b64_metadata}"
                found.append(final_inscription)

                print(f"{tx_hash}:{vin_pos}")
                print(final_inscription)
                vin_pos += 1



def main(args):
    global credentials
    global hostport

    credentials = process_cookie(args.c)
    hostport = "http://127.0.0.1:8332"

    start = 767430 if (args.s is None) or (args.s < 767430) else args.s
    end = rpc_request("getblockcount") if args.f is None else args.f

    for block in range(start, end):
        find_ordinals(block)


if __name__ == "__main__":
    parser = ArgumentParser(description="Find the rarity of your satoshis")
    parser.add_argument("-c", help="Bitcoind RPC cookie", required=True)
    parser.add_argument("-s", type=int, help="start block height")
    parser.add_argument("-f", type=int, help="end block height")
    args = parser.parse_args()

    main(args)
