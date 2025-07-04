#!/usr/bin/env python3
import os
import time
import re
import requests
import logging
import json
import pyjokes
import traceback
from .mispattruploader import misp_custom
import helper
import asyncio
import nest_asyncio
import slack
from logging.config import dictConfig

nest_asyncio.apply()

loop = asyncio.get_event_loop()
### Configuration loading and logging enabled.
dir_path = os.path.dirname(os.path.realpath(__file__))
config_file = dir_path + "/config.json"
# instantiate Slack client
output_error_file = ""
with open(config_file) as json_data_file:
    data = json.load(json_data_file)
token = data["slack"]["SLACK_BOT_TOKEN"]
if "logging" in data:
    if "output_file" in data["logging"]:
        output_all_file = data["logging"]["output_file"]
    else:
        exit("Please include output_file in config")
    if "output_error_file" in data["logging"]:
        output_error_file = data["logging"]["output_error_file"]
else:
    output_all_file = dir_path + "/sambot.log"


logging_config = dict(
    version=1,
    formatters={
        "f": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}
    },
    handlers={
        "Stream": {
            "class": "logging.StreamHandler",
            "formatter": "f",
            "level": "DEBUG",
        },
        "file_all": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "f",
            "filename": output_all_file,
            "mode": "a",
            "maxBytes": 10485760,
            "backupCount": 5,
        },
    },
    root={
        "handlers": ["Stream", "file_all"],
        "level": "DEBUG",
    },
)

if output_error_file != "":
    logging_config["handlers"]["file_error"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "level": "ERROR",
        "formatter": "f",
        "filename": output_error_file,
        "mode": "a",
        "maxBytes": 10485760,
        "backupCount": 5,
    }
    logging_config["root"]["handlers"].append("file_error")

dictConfig(logging_config)

logger = logging.getLogger("SAMbot")
try:
    slack_client = slack.WebClient(token=token, run_async=True)
    test = loop.run_until_complete(slack_client.api_call("auth.test"))
    logger.info("Slack client created")
    logger.info("Connecting to misp server")
    misp = misp_custom(data["misp"]["url"], data["misp"]["key"], data["misp"]["ssl"])
    logger.info("Connected to misp server successfully")
    helperFunc = helper.TonyTheHelper(slack_client)
    # starterbot's user ID in Slack: value is assigned after the bot starts up
    starterbot_id = None
    slack_test = slack.RTMClient(token=token)
except Exception:
    logger.error("Exception Caught! FIX YOUR CONFIG %s")
    error = traceback.format_exc()
    logger.error(error)
    exit()
# constants
RTM_READ_DELAY = 1  # 1 second delay between reading from RTM
EXAMPLE_COMMAND = "Tell a joke"
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"


def get_username(slack_event, channel):
    slack_temp = slack.WebClient(token=token, run_async=False)
    logger.info(channel)
    members = slack_temp.conversations_members(channel=channel)
    logger.info(members.data)
    print(dir(members))
    if "user" in slack_event:
        logger.info(slack_event["user"])
        for member in members.data["members"]:
            logger.info("member: %s" % member)
            if member == slack_event["user"]:
                member_profile = slack_temp.users_info(user=member)
                if member_profile["ok"]:
                    name = member_profile["user"]["profile"]["display_name_normalized"]
                    logger.info(name)
                    return name
                else:
                    return "Unknown"
    else:
        return "Unknown"


def parse_bot_commands(event):
    """
    Parses a list of events coming from the Slack RTM API to find bot commands.
    If a bot command is found, this function returns a tuple of command and channel.
    If its not found, then this function returns None, None.
    """
    logger.info(event)

    # try:
    # logger.debug(event)
    if "files" in event:
        for file in event["files"]:
            if file["mode"] == "snippet":
                url = file["url_private_download"]
                title = file["title"]
                if title == "Untitled":
                    strTitle = "#Warroom"
                else:
                    strTitle = "#Warroom " + title
                headers = {"Authorization": "Bearer " + token}
                r = requests.get(url, headers=headers)
                content = r.content.decode("utf-8")
                logger.error(r.content)
                e_time = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(float(event["event_ts"]))
                )
                e_title = e_time + " - " + strTitle
                username = get_username(event, event["channel"])
                # await username
                logger.info(username)
                misp_response = misp.misp_send(0, content, e_title, username)
                return misp_response, None, event["channel"], event["user"]
    # except:
    # error = traceback.format_exc()
    # helperFunc.respond_channel(error, event["channel"])


# def respond(command, channel, user):
# 	# This is where you start to implement more commands!
# 	# Sends the response back to the channel
# 	slack_client.api_call(
# 		"chat.postEphemeral",
# 		channel=channel,
# 		text=command,
# 		user=user
# 	)

# def helperFunc.respond_channel(command, channel):
# 	slack_client.api_call(
# 		"chat.postMessage",
# 		channel=channel,
# 		text=command
# 	)


def parse_direct_mention(message_text):
    """
    Finds a direct mention (a mention that is at the beginning) in message text
    and returns the user ID which was mentioned. If there is no direct mention, returns None
    """
    matches = re.search(MENTION_REGEX, message_text)
    # the first group contains the username, the second group contains the remaining message
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)


def tell_a_joke(command, channel, user):
    """
    Executes bot command if the command is known
    """
    # Default response is help text for the user
    default_response = "Not sure what you mean. Try *{}*.".format(EXAMPLE_COMMAND)
    help_command = "Help"
    # Finds and executes the given command, filling in response
    response = None
    # This is where you start to implement more commands!
    if command.lower().startswith(EXAMPLE_COMMAND.lower()):
        response = (
            pyjokes.get_joke(category="all")
            + " This joke has been Brought to you by pyjokes."
        )
    elif command.lower().startswith(help_command.lower()):
        response = helperFunc.print_help()
    # Sends the response back to the channel
    helperFunc.respond_channel(response or default_response, channel)


@slack.RTMClient.run_on(event="message")
def main(**payload):
    data = payload["data"]
    # web_client = payload["web_client"]
    # rtm_client = payload["rtm_client"]
    logger.info(payload)
    try:
        if data is not None:
            misp_response, smartass, channel, user = parse_bot_commands(data)
            if misp_response:
                helperFunc.respond(misp_response, channel, user)
            elif smartass:
                print(smartass)
                tell_a_joke(smartass, channel, user)
            time.sleep(RTM_READ_DELAY)
    except KeyboardInterrupt:
        logger.error("Bot was manually stopped with ctrl+c")
    except Exception:
        error = traceback.format_exc()
        logger.error(error)
        helperFunc.respond_channel(
            "The bot has caught a fatal error. Please review the error log. Exiting now.",
            "#Warroom",
        )
        exit()


if __name__ == "__main__":
    if slack_client.rtm_connect(with_team_state=False, auto_reconnect=True):
        logger.info("SAMbot connected and running!")
        # # Read bot's user ID by calling Web API method `auth.test`
        # starterbot_id = slack_client.api_call("auth.test")["user_id"]
        # online = True

        try:
            slack_test.start()
            loop.run_forever()
        except KeyboardInterrupt:
            logger.error("Bot was manually stopped with ctrl+c")
        except Exception:
            error = traceback.format_exc()
            logger.error(error)
            helperFunc.respond_channel(
                "The bot has caught a fatal error. Please review the error log. Exiting now.",
                "#Warroom",
            )
            online = False

    else:
        logger.info("Connection failed. Exception traceback printed above.")
