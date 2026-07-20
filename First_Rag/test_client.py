import json
import requests

url ="http://127.0.0.1:8000/api/chat/stream"
payload={"message":"What are the rules mentioned in the document?"}

print("Sending request to FastAPI backend...")

reponse=requests.post(url,json=payload,stream=True)

if(reponse.status_code==200):
    print("\n---Streaming Response Starts---")

    for line in reponse.iter_lines():
        if line:
            decoedLine=line.decode('utf-8')

            if(decoedLine.startswith("data: ")):
                dataContent=decoedLine[6:]

                if(dataContent=="[Done]"):
                    print("\n---Stream Complete---")
                    break

                try:
                    chunkJson=json.loads(dataContent)
                    token=chunkJson.get("token","")
                    print(token, end="",flush=True)
                except json.JSONDecodeError:
                    print(f"\nRam line error parsing: {decoedLine}")

else:
    print(f"Failed to connect. Status code: {reponse.status_code}")
    print(reponse.text)

