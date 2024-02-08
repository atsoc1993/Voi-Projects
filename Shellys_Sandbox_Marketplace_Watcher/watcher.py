import discord
from discord.ext import commands, tasks
from discord.utils import get
import time
from algosdk.v2client import algod
import base64
from algosdk import encoding
import time
import subprocess
import requests

intents = discord.Intents.default()
intents.message_content = True  

client = commands.Bot(command_prefix = '!', intents= intents)
client.remove_command('help')

algod_token = '8f374572eb63d1fb2718055b65396cb9a6a3c50fc71492bcbf215f23c3cc1bae'
algod_port = 'http://5.161.112.231:32953'


marketplace_dict = {

}


@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    marketplace_watcher.start()  
    
def get_token_uri(collection_id, asset_id):
    result = subprocess.run(["node", "obtainTokenURI.js", str(collection_id), str(asset_id)], capture_output=True, text=True)
    output = result.stdout.strip()
    return output[15:]
    
def fetch_metadata(token_uri):
    response = requests.get(token_uri)
    if response.status_code == 200:
        metadata = response.json()
        return metadata
    else:
        print("Failed, Status code:", response.status_code)

def confirm_buyer(collection_id, asset_id):
    result = subprocess.run(["node", "getNewHolder.js", str(collection_id), str(asset_id)], capture_output=True, text=True)
    output = result.stdout.strip()
    return output[12:]
    
async def market_activity(title_message, asset_id, listing_info):

    embed = discord.Embed(
        title=title_message,
        description="Shellaby's Market Activity!",
        color=discord.Color.blue()
    )
    if title_message == "Marketplace Sale!":
        address_type = "Buyer"
        buyer = confirm_buyer(listing_info['collection'], listing_info['tokenid'])
        if buyer == listing_info['address']:
            print(f"Marketplace Seller {buyer} de-listed or purchased their own ARC72: {listing_info['tokenid']}")
            return
        else:
            address = buyer
            print(f'Sale Completed by {listing_info['address']} to {address} for {listing_info['tokenid']}')
    elif title_message == "Marketplace Listing!":
        address_type = "Seller"
        address = listing_info['address']
        print(f"New Marketplace Listing by {address} for {listing_info['tokenid']}")

   
    token_uri = get_token_uri(listing_info['collection'], asset_id)
    metadata = fetch_metadata(token_uri)

    embed.add_field(name="Collection ID", value=str(listing_info['collection']), inline=False)
    embed.add_field(name="Asset ID", value=str(asset_id), inline=False)
    embed.add_field(name=address_type, value=address, inline=False)
    embed.add_field(name="Price", value=f"{listing_info['price']:,} {listing_info['currency']}", inline=False)
    embed.add_field(name="Name", value=metadata['name'], inline=False)
    embed.add_field(name="Description", value=metadata['description'], inline=False)
    if 'properties' in metadata:
        for prop, val in metadata['properties'].items():
            embed.add_field(name=prop, value=val, inline=True)
    embed.set_image(url=metadata.get('image', 'Default_image_URL'))
    embed.set_footer(text="Market activity provided by Foodie")
    channel_id = 1199022961542303776
    channel = client.get_channel(channel_id)
    await channel.send(embed=embed)


def get_box_info_decoded(app_id, box):
    algod_client = algod.AlgodClient(algod_token, algod_port)
    box_bytes_name = base64.b64decode(box['name'])
    box_info = algod_client.application_box_by_name(app_id, box_bytes_name)
    asset_info = box_info['value']
    bytes_info = base64.b64decode(asset_info)
    if bytes_info[72] == 1:
        collection_id = int.from_bytes(bytes_info[0:8], byteorder='big') 
        token_id = int.from_bytes(bytes_info[8:40], byteorder='big') 
        address = bytes_info[40:72] 
        price = int.from_bytes(bytes_info[82:114], byteorder='big')
        price = (price + price * 0.05) // 100_000
        address_encoded = encoding.encode_address(address)
        currency = "Via"
        return collection_id, address_encoded, token_id, price, currency

    else:
        collection_id = int.from_bytes(bytes_info[0:8], byteorder='big') 
        token_id = int.from_bytes(bytes_info[8:40], byteorder='big') 
        address = bytes_info[40:72] 
        price = int.from_bytes(bytes_info[73:81], byteorder='big') // 1_000_000
        price = price + price * 0.05
        address_encoded = encoding.encode_address(address)
        currency = "Voi"
        return collection_id, address_encoded, token_id, price, currency
    
def initial_scan(last_round):
    global marketplace_dict
    algod_client = algod.AlgodClient(algod_token, algod_port)
    status = algod_client.status()
    current_round = status['last-round']

    if current_round > last_round:
        last_round = current_round
        app_ids = [26944604, 28368532, 28378489]
        for app_id in app_ids:
            marketplace_arc = algod_client.application_boxes(app_id)
            boxes = marketplace_arc['boxes']
            try:
                for box in boxes:
                    collection_id, address_encoded, token_id, price, currency = get_box_info_decoded(app_id, box)
                    marketplace_dict[token_id] = {
                        "collection": collection_id,
                        "address": address_encoded,
                        "tokenid": token_id,
                        "price": price,
                        "currency": currency
                    }

            except Exception as e:
                print(f'Error: {e}')
                
    return marketplace_dict

@tasks.loop(seconds=2.4)      
async def marketplace_watcher():
    circulating_dict = marketplace_circulating_scan(last_round)
    initial_market_assets = [assets for assets in marketplace_dict]
    circulating_assets = [assets for assets in circulating_dict]


    for circulating_asset in circulating_assets:
        if circulating_asset not in initial_market_assets:
            marketplace_dict[circulating_asset] = circulating_dict[circulating_asset]
            title_message = "Marketplace Listing!"
            await market_activity(title_message, circulating_asset, circulating_dict[circulating_asset])
            
    for initial_asset in initial_market_assets:
        if initial_asset not in circulating_assets:
            title_message = "Marketplace Sale!"
            await market_activity(title_message, initial_asset, marketplace_dict[initial_asset])
            del marketplace_dict[initial_asset]



     

def marketplace_circulating_scan(last_round):
    circulating_dict = {

    }
    algod_client = algod.AlgodClient(algod_token, algod_port)
    status = algod_client.status()
    current_round = status['last-round']
    if current_round > last_round:
        last_round = current_round
        app_ids = [26944604, 28368532, 28378489]
        for app_id in app_ids:
            marketplace_arc = algod_client.application_boxes(app_id)
            boxes = marketplace_arc['boxes']
        for app_id in app_ids:
            marketplace_arc = algod_client.application_boxes(app_id)
            boxes = marketplace_arc['boxes']
            try:
                for box in boxes:
                    collection_id, address_encoded, token_id, price, currency = get_box_info_decoded(app_id, box)
                    circulating_dict[token_id] = {
                        "collection": collection_id,
                        "address": address_encoded,
                        "tokenid": token_id,
                        "price": price,
                        "currency": currency
                    }

            except Exception as e:
                print(f'Error: {e}')
                
    return circulating_dict

last_round = 0

initial_scan(last_round)



client.run('MTE5OTAyMzEyNjM0OTA5NDkxMg.GqoubM.u5sBxz6Uknrjd2u4XIjPmZlHfsu1iMPEWoOibU')


 
