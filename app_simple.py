import os
import sys
import json

import requests
from flask import Flask, request
import datetime

import env

app = Flask(__name__)

@app.route('/webhook', methods=['GET'])
def verify():
    # Source: https://github.com/hartleybrody/fb-messenger-bot/blob/master/app.py
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == env.VERIFY_TOKEN:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


@app.route('/webhook', methods=['POST'])
def webhook():

    data = request.get_json()
    log(data)  # you may not want to log every incoming message in production, but it's good for testing

    if data["object"] == "page":

        for entry in data["entry"]:
            page_id = entry["id"]
            time_of_event = entry["time"]

            for messaging_event in entry["messaging"]:

                if messaging_event.get("message"):  # someone sent us a message
                    receive_message(messaging_event)

                    # sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    # recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    # message_text = messaging_event["message"]["text"]  # the message's text

                    # send_message(sender_id, "got it, thanks!")
                elif messaging_event.get("delivery"):  # delivery confirmation                
                    pass

                elif messaging_event.get("optin"):  # optin confirmation
                    pass

                elif messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    receive_postback(messaging_event)
                else:
                    log("Unknown event received: {event} ".format(event=messaging_event))

    # // Assume all went well.
    # //
    # // You must send back a 200, within 20 seconds, to let us know you've 
    # // successfully received the callback. Otherwise, the request will time out.                    
    return "ok", 200

def receive_message(event):
    # log('message event data: ', event)
    sender_id = event["sender"]["id"]        # the facebook ID of the person sending you the message
    recipient_id = event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID    
    time_of_message = event["timestamp"]
    time_converted = convert_timestame(time_of_message)
    message = event["message"]

    log("Received message for user {sender_id} and page {recipient_id} at {time} with message:".format(sender_id=sender_id, recipient_id=recipient_id, time=time_of_message))
    log(message)

    message_id = message["mid"]
    message_text = message["text"] if "text" in message else None
    message_attachments = message["attachments"] if "attachments" in message else None

    # If we receive a text message, check to see if it matches a keyword
    # and send back the example. Otherwise, just echo the text we received.
    if message_text:
        if message_text == 'generic':
            send_generic_message(sender_id)
        else:
            send_text_message(sender_id, message_text)
    elif message_attachments:
        send_text_message(sender_id, "Message with attachment received")        


def send_generic_message(recipient_id):
    message_data = json.dumps({
            "recipient": {
                "id": recipient_id
                },
            "message": {
              "attachment": {
                 "type": "template",
                 "payload": {
                    "template_type": "generic",
                    "elements": [
                       {
                          "title": "rift",
                          "subtitle": "Next-generation virtual reality",
                          "item_url": "https://www.oculus.com/en-us/rift/",
                          "image_url": "http://messengerdemo.parseapp.com/img/rift.png",
                          "buttons": [
                             {
                                "type": "web_url",
                                "url": "https://www.oculus.com/en-us/rift/",
                                "title": "Open Web URL"
                             },
                             {
                                "type": "postback",
                                "title": "Call Postback",
                                "payload": "Payload for first bubble"
                             }
                          ]
                       },
                       {
                          "title": "touch",
                          "subtitle": "Your Hands, Now in VR",
                          "item_url": "https://www.oculus.com/en-us/touch/",
                          "image_url": "http://messengerdemo.parseapp.com/img/touch.png",
                          "buttons": [
                             {
                                "type": "web_url",
                                "url": "https://www.oculus.com/en-us/touch/",
                                "title": "Open Web URL"
                             },
                             {
                                "type": "postback",
                                "title": "Call Postback",
                                "payload": "Payload for second bubble"
                             }
                          ]
                       }
                    ]
                 }
              }
           }
        })

    call_send_API(message_data)

def send_text_message(recipient_id, message_text):
    message_data = json.dumps({
            "recipient": {
                "id": recipient_id
                },
            "message": {
                "text": "P: " + message_text #add P: before the text
            }
        })

    call_send_API(message_data)

def receive_postback(event):
    sender_id = event["sender"]["id"]
    recipient_id = event["recipient"]["id"]
    time_of_postback = event["timestamp"]
    time_converted = convert_timestame(time_of_postback)

    payload = event["postback"]["payload"]

    log("Received postback for user {sender} and page {recipient} with payload {payload} at {time}".format(
            sender=sender_id,
            recipient=recipient_id,
            payload=payload,
            time=time_of_postback
        ))

    send_text_message(sender_id, "Postback called")

def call_send_API(message_data):
    params = {
        "access_token": env.PAGE_ACCESS_TOKEN,
        "date_format": "U"
    }
    headers = {
        "Content-Type": "application/json"
    }

    try:
        r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=message_data)
        if r.status_code != 200:
            log(r.status_code)
            log(r.text)

            return        
    except Exception as e:
        log("Unable to send message.")
        log(e)
        return

    response_body = r.json()
    log("response: {body}".format(body=response_body))
    message_id = response_body["message_id"]
    recipient_id = response_body["recipient_id"]

    log("Successfully sent generic message with id {message_id} to recipient {recipient_id}".format(message_id=message_id, recipient_id=recipient_id))



def send_message(recipient_id, message_text):

    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def log(message):  # simple wrapper for logging to stdout on heroku
    print str(message)
    sys.stdout.flush()

def convert_timestame(timestamp):
    return datetime.datetime.utcfromtimestamp(int(timestamp)/1000)


if __name__ == '__main__':
    app.run(debug=True)