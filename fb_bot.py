import pyowm
import apiai
import requests
import simplejson as json
from flask import Flask, request

from decouple import config

app = Flask(__name__)

OWM_API = config('OWM_API')

CLIENT_ACCESS_TOKEN = config('CLIENT_ACCESS_TOKEN')
VERIFY_TOKEN = config('VERIFY_TOKEN')
PAGE_ACCESS_TOKEN = config("PAGE_ACCESS_TOKEN")

ai = apiai.ApiAI(CLIENT_ACCESS_TOKEN)

@app.route("/", methods=['GET', 'POST'])
def recieve_message():
	'''
	Handle messages sent by facebook messenger to the applicaiton
	'''
	if request.method == "GET":
		token_sent = request.args.get('hub.verify_token')
		return verify_fb_token(token_sent)

	else:
		output = request.get_json()
		if output['object'] == 'page':
			for event in output['entry']:
				for message in event['messaging']:
					if message.get("message"):

						sender_id = message['sender']['id']
						recipient_id = message['recipient']['id']
						message_text = message['message'].get("text")
						message_to_send = parse_user_text(message_text)
						send_message_response(sender_id, message_to_send)

	return "Message process"


def verify_fb_token(token_sent):
	#verify if user has correct verifying token from facebook
	if token_sent == VERIFY_TOKEN:
		return request.args.get("hub.challenge")
	return "Invalid Verification"


def parse_user_text(message_text):
	'''
	Send the message to API AI which invokes an intent
	and sends the response accordingly
	The bot response is appened with weaher data fetched from
	open weather map client
	'''

	request = ai.text_request()
	request.query = message_text

	r = request.getresponse()
	response = json.loads(r.read().decode('utf-8'))
	response_status = response['status']['code']
	if response_status == 200:
		print('Bot response ', response['result']['fulfillment']['speech'])

		weather_report = ''

		input_city = response['result']['parameters']['geo-city']

		owm = pyowm.OWM(CLIENT_ACCESS_TOKEN)

		observation = owm.weather_at_place(input_city)
		w = observation.get_weather()
		print(w)
		print(w.get_humidity())
		print(w.get_wind())
		max_temp = str(w.get_temperature('celsius')['temp_max'])
		min_temp = str(w.get_temperature('celsius')['temp_min'])
		current_temp = str(w.get_temperature('celsius')['temp'])
		wind_speed = str(w.get_wind()['speed'])
		humidity = str(w.get_humidity())
		weather_report = ' max_temp : ' + max_temp + ' min_temp : ' + min_temp + ' current_temp : ' + current_temp + ' wind speed : ' + wind_speed + ' humidity : ' + humidity + '% '
		print("Weather Report ", weather_report)
		return (response['result']['fulfillment']['speech'] + weather_report)

	else:
		print('Please try again')

	return "Parse Happened"

def send_message(sender_id, message_text):
	'''
	Sending response back to the user using facebook graph API
	'''
	r = requests.post("https://graph.facebook.com/v2.6/me/messages",
		params={'access_token' : PAGE_ACCESS_TOKEN},
		headers={'Content-Type' : 'application/json'},
		data=json.dumps({"recipient" : {'id' : sender_id}, "message" : {'text' : message_text}}))


def send_message_response(sender_id, message_text):
	delimiter = '. '
	messages = message_text.split(delimiter)

	for message in messages:
		send_message(sender_id, message)

	return 'Message send'


if __name__ == '__main__':
	app.run()