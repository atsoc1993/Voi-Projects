import discord
from discord.ext import commands, tasks
from discord.utils import get
from algosdk.v2client import algod
import subprocess
import requests

'''
This is the indexer method alternative to the original main.py file. 
Instead of decoding, encoding, sequencing and formatting bytes in the 
smart contract marketplace application boxes we can directly query information
from all marketplace app ID's using the new indexer.

Uniquely, although there is an endpoint for retrieving sales information,
this bot only needs to monitor listing information to detect sales and 
any details related. This reduces unnecessary querying to the indexer
'''

intents = discord.Intents.default()
intents.message_content = True  

client = commands.Bot(command_prefix = '!', intents= intents)
client.remove_command('help')

algod_token = 'INSERT NODE TOKEN'
algod_port = 'INSERT NODE PORT'

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
    channel_id = 'REPLACE WITH CHANNEL ID'
    channel = client.get_channel(channel_id)
    await channel.send(embed=embed)


def initial_scan():
    global marketplace_dict
    algod_client = algod.AlgodClient(algod_token, algod_port)
    cursor_start = algod_client.status()['last-round']
    indexer_url = f'https://arc72-idx.voirewards.com/nft-indexer/v1/mp/listings?min-round={cursor_start}'

    r = requests.get(indexer_url, verify=False)
    r_data = r.json()
    for _ in r_data['listings']:
        if _['currency'] == 0:
            currency = "Voi"
        elif _['currency'] == 6779767:
            currency = "Via"
        else:
            currency = "Unknown"

        marketplace_dict[_['tokenId']] = {
            "collection": _['collectionId'],
            "address": _['seller'],
            "tokenid": _['tokenId'],
            "price": _['price'],
            "currency": currency
        }
        
    return marketplace_dict

@tasks.loop(seconds=30)      
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



def marketplace_circulating_scan():

    circulating_dict = {

    }
    
    algod_client = algod.AlgodClient(algod_token, algod_port)
    cursor_start = algod_client.status()['last-round']
    indexer_url = f'https://arc72-idx.voirewards.com/nft-indexer/v1/mp/listings?min-round={cursor_start}'
    
    r = requests.get(indexer_url, verify=False)
    r_data = r.json()
    for _ in r_data['listings']:
        if _['currency'] == 0:
            currency = "Voi"
        elif _['currency'] == 6779767:
            currency = "Via"
        else:
            currency = "Unknown"

        circulating_dict[_['tokenId']] = {
            "collection": _['collectionId'],
            "address": _['seller'],
            "tokenid": _['tokenId'],
            "price": _['price'],
            "currency": currency
        }
        
    return circulating_dict

initial_scan()

client.run('INSERT BOT TOKEN')


 
