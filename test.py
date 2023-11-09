from chat import Chat


chat = Chat()
pk = "user11"

response_object = chat.message(
    txhash="3",
    user=pk,
    message="It's controlling the funds using trusted hardware"
)
