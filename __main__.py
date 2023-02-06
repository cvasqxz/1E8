from argparse import ArgumentParser
import os, requests, json

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
	payload = json.dumps({
		"jsonrpc": "2.0",
		"id": "1e8",
		"method": method,
		"params": [p for p in params]
	})

	req = requests.post(hostport, auth=credentials, data=payload)

	if req.status_code != 200:
		return None

	return req.json()["result"]


def get_tx(txid):
	raw_tx = rpc_request("getrawtransaction", [txid])
	json_tx = rpc_request("decoderawtransaction", [raw_tx])

	return json_tx


def get_ancestor(txid, address=None, vout_target=None):
	json_tx = get_tx(txid)

	if address is not None and vout_target is None:
		vout_buffer = 0
		vout_target = (0, 0)

		for vout in json_tx["vout"]:
			vout_address = vout["scriptPubKey"]["address"]
			vout_value = int(round(vout["value"]*1e8, 0))

			if address == vout_address:
				start_point = vout_buffer + 1 if vout_buffer > 0 else 0
				vout_target = (start_point, vout_buffer + vout_value)
				break

			vout_buffer += vout_value

	vin_buffer = 0
	vin_ranges = []

	for vin in json_tx["vin"]:
		if "coinbase" in vin:
			print("GENESIS FOUND:", txid)
			return []

		input_tx = get_tx(vin["txid"])
		input_value = input_tx["vout"][vin["vout"]]["value"]
		input_value = int(round(input_value*1e8, 0))

		if len(json_tx["vin"]) == 1:
			vin_ranges.append({"txid": vin["txid"], "range": vout_target})
			break

		vin_range = range(vin_buffer, vin_buffer + input_value)

		if vout_target[0] in vin_range or vout_target[1] in vin_range:

			start_point = vin_buffer + 1 if vin_buffer > 0 else 0
			end_point = vin_buffer + input_value

			if start_point < vout_target[0]:
				start_point = vout_target[0]

			if end_point > vout_target[1]:
				end_point = vout_target[1]
			
			vin_ranges.append({"txid": vin["txid"], "range": (start_point, end_point)})

		vin_buffer += input_value

	return vin_ranges


def main(args):
	global credentials
	global hostport

	credentials = process_cookie(args.cookie)

	if credentials == (None, None):
		exit()

	if args.network == "mainnet":
		hostport = "http://127.0.0.1:8332"

	if args.network == "testnet":
		hostport = "http://127.0.0.1:18332"

	received_by_address = rpc_request("listreceivedbyaddress")

	ancestors_array = []

	for addr in received_by_address:
		print(f"Address {addr['address']} found with {addr['amount']} BTC ({ len(addr['txids']) } Transaction IDs)")
		
		for txid in addr["txids"]:
			print("analyzing", txid)
			ancestors = get_ancestor(txid, address=addr["address"])
			
			while len(ancestors) > 0:
				ancestor = ancestors.pop()
				#print(ancestor, len(ancestors_array))
				new_ancestors = get_ancestor(ancestor["txid"], vout_target=ancestor["range"])
				ancestors += new_ancestors

if __name__ == "__main__":
	parser = ArgumentParser(description="Find the rarity of your satoshis")
	parser.add_argument("--cookie", default="Bitcoind RPC cookie")
	parser.add_argument("--network", default="mainnet/testnet/regtest")
	args = parser.parse_args()

	main(args)