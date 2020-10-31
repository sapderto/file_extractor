#File extractor

This bot can download all files from Telegram messages. By default bot download **application/pdf** mime type, if you need another just redact this condition 
````python
if "media" in message_dict and message_dict["media"] and "document" in message_dict["media"] and \
                "application" in message_dict["media"]["document"]["mime_type"]
````
Number of messages, requested in one query need to be redacted, remember that about 30 instant queries provokes 429 HTTP
````python
limit_msg = 30
````
Links on groups TG depends of this list, example:
````python
 urls = ["BookJava", "BookPython"]
````
Bot checks size of files to be sure, that download was successful. After every group chanel configuration file will be dropped, this file contains last processed id of message, so if you need to recheck all downloads just remove it. File *.session need your confirmation in TG.
## Config file

```
[Telegram]
api_id = 1234567 #your api id (7 digits)
api_hash = abcdef1234567890abcdef1234567890 #your api hash (32 hex symbols)
username = Name #your name in TG
directory = D:\Downloaded #directory where files will be saved (windows style)
```