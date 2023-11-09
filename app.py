import tornado.ioloop
import tornado.web
import near_api
import json
import requests

from chat import Chat

TX_RECIPIENT_ID = "dev-1699532201092-55717281948005"
PK = "6e7a1cdd29b0b78fd13af4c5598feff4ef2a97166e3ca6f2e4fbfccd80505bf1"


class BytesEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return obj.decode('utf-8')
        return json.JSONEncoder.default(self, obj)


class GetPkHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "GET, OPTIONS")

    async def get(self):
        self.write(json.dumps({"pk": PK}))


class GetArchiveHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "GET, OPTIONS")

    async def get(self):
        user = self.get_argument("user", default=None)
        if not user:
            return self.write("No user parameter provided in the request.")

        chat = Chat()
        response = chat.get_archive(user)
        self.write(json.dumps(response))


class MainHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "GET, OPTIONS")

    async def get(self):
        txhash = self.get_argument("txhash", default=None)
        if txhash:
            print(f"Received txhash: {txhash}")
        else:
            return self.write("No txhash parameter provided in the request.")

        pk = self.get_argument("pk", default=None)
        if pk:
            print(f"Received pk: {pk}")
        else:
            return self.write("No pk parameter provided in the request.")

        try:
        # Open and read the JSON configuration file
            with open('config.json', 'r') as config_file:
                config = json.load(config_file)
                account_id = config.get("account_id")
                private_key = config.get("private_key")
                contract_id = config.get("contract_id")

                if not (account_id and private_key and contract_id):
                    return self.write("Illegal config")

                print("Quex account_id: %s, contract_id: %s" % (account_id, contract_id))

                near_provider = near_api.providers.JsonProvider("https://rpc.testnet.near.org")

                tx = near_provider.get_tx(txhash, TX_RECIPIENT_ID)

                # tx_object=json.loads(tx)

                request = tx["receipts_outcome"][0]['outcome']['logs'][0]
                executor_id = tx["transaction_outcome"]["outcome"]["executor_id"]
                deposit = tx["transaction"]["actions"][0]["FunctionCall"]["deposit"]

                if deposit != '100000000000000000000000': # 0.1 NEAR
                    return self.write("Illegal deposit")

                print("request %s executor_id %s" % (request, executor_id))
                #print(tx)
                #return(0)

                url = 'http://148.113.16.225:3001/certify'

                # Data to be sent in the POST request
                data = {
                    'address': executor_id,  # You can replace this with the desired input method
                    'request': json.dumps({
                        "model": "gpt-4",
                        "messages": [
                            {
                                "role": "user",
                                "content": request
                            }
                        ],
                        "temperature": 0.7
                    })
                }

                # Send the POST request
                response = requests.post(url, json=data, headers={'Content-Type': 'application/json'})

                # Check for request errors
                if response.status_code != 200:
                    print(f'HTTP error: {response.status_code}')
                else:
                    # Print the response
                    print(response.text)

                    response_object = json.loads(response.text)
                    print("response_object", response_object)
                    print("response_object data", response_object["data"])
                    print("response_object signature", response_object["signature"])

                    key_pair = near_api.signer.KeyPair(private_key)
                    signer = near_api.signer.Signer(account_id, key_pair)
                    account = near_api.account.Account(near_provider, signer)

                    chat = Chat()
                    response_object = chat.message(
                        txhash=txhash,
                        user=executor_id,
                        message=request
                    )

                    response_data = response_object["data"]

                    print("response_object", response_object)
                    print("type", type(response_object))

                    print("response_data", response_data)
                    print("type", type(response_data))

                    message = json.dumps(response_data)
                    args = {"pk_string": pk, "message": message, "sig_string": response_object["signature"]}
                    print("args", args)

                    try:
                        out = account.function_call(contract_id, "addResponse1", args)
                    except:
                        print ("try again")
                        out = account.function_call(contract_id, "addResponse1", args)

                    parsed_response_data = response_data
                    print("jparsed_data", parsed_response_data)
                    print("type jparsed_data", type(parsed_response_data))
                    # inner_json_string = parsed_response_data["response"]
                    print("parsed_response_data resp", parsed_response_data["response"])


                    results = {
                        "id": out["transaction_outcome"]["id"],
                        "logs": out["receipts_outcome"][0]["outcome"]["logs"][0],
                        "content": parsed_response_data["response"]["choices"][0]["message"]["content"]
                    }


                    return self.write(json.dumps(results, cls=BytesEncoder))

        except FileNotFoundError:
            print(f"Error decoding JSON in '{config_file_path}'")

        # Access individual configuration settings





        #self.write(json.dumps({}, cls=BytesEncoder))

application = tornado.web.Application([
    (r'/', MainHandler),
    (r'/pk', GetPkHandler),
    (r'/archive', GetArchiveHandler),
])

if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.current().start()
