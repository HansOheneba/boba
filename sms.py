import http.client
import json

conn = http.client.HTTPSConnection("pevqze.api.infobip.com")
payload = json.dumps(
    {
        "messages": [
            {
                "from": "447860099299",
                "to": "233592076527",
                "messageId": "077786b2-a5fc-4824-ae73-d4f2b2f9542b",
                "content": {
                    "templateName": "test_whatsapp_template_en",
                    "templateData": {"body": {"placeholders": ["Hans"]}},
                    "language": "en",
                },
            }
        ]
    }
)
headers = {
    "Authorization": "App 3a5cd51f66a33fb80abeb67052fc8363-81da1149-8980-4714-9ede-b659dd34bc30",
    "Content-Type": "application/json",
    "Accept": "application/json",
}
conn.request("POST", "/whatsapp/1/message/template", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
