import algosdk from "algosdk";
import { arc72 } from "ulujs";

const zeroAddress = "27BKAFASJE7KTHG427WDKYIKV5CPGNIKXS2A2IEXZVIJCQBUZLYQIX6LA4";

const ALGO_SERVER = "https://testnet-api.voi.nodly.io";
const ALGO_INDEXER_SERVER = "https://testnet-idx.voi.nodly.io";

const algodClient = new algosdk.Algodv2("", ALGO_SERVER, "");
const indexerClient = new algosdk.Indexer("", ALGO_INDEXER_SERVER, "");

async function getTokenUri(collectionId, tokenId) {
  const ci = new arc72(collectionId, algodClient, indexerClient, {
    acc: { addr: zeroAddress },
    formatBytes: true,
  });

  const tokenUri = await ci.arc72_tokenURI(tokenId);
  console.log("arc72_tokenURI", tokenUri.returnValue);
}

const collectionId = parseInt(process.argv[2]);
const tokenId = parseInt(process.argv[3]);

getTokenUri(collectionId, tokenId).catch(console.error);
