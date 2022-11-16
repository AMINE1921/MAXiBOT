from dotenv import load_dotenv, find_dotenv
from datetime import datetime
import requests
import discord
from discord.ext import commands, tasks
import asyncio
import os


async def search_train(data, day, minHour, maxHour, channelId):
    nb_train = len(data["records"])
    for i in range(0, nb_train):
        hour = data["records"][i]["fields"]["heure_depart"]
        date = data["records"][i]["fields"]["date"]
        origine = data["records"][i]["fields"]["origine"]
        destination = data["records"][i]["fields"]["destination"]
        id = data["records"][i]["recordid"]
        f = open("sncf.txt", "a+")
        f.seek(0)
        if (minHour <= hour and hour <= maxHour and datetime.strptime(date, '%Y-%m-%d').weekday() == day and id not in f.read()):
            print(f'{origine} vers {destination} : {date} à {hour}')
            f.write(id + "\n")
            channel = bot.get_channel(channelId)
            await channel.send(f'\U0001F684 \U0001F3E0 {origine} vers \U000027A1 {destination} : \U0001F4C5 {date} à {hour}')
        f.close()


async def get_train(day, origine, destination, minHour, maxHour, channelId):
    url = prepare_url(origine, destination)
    response = requests.get(url)
    await search_train(response.json(), day, minHour, maxHour, channelId)


def prepare_url(origine, destination):
    url = f"https://ressources.data.sncf.com/api/records/1.0/search/?rows=2000&dataset=tgvmax&sort=-date&start=0&exclude.od_happy_card=NON"
    url += "&refine.origine=" + origine
    url += "&refine.destination=" + destination
    return url


def main():
    load_dotenv(find_dotenv())
    global bot
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents)

    @bot.command()
    async def maxi(ctx, *args, given_name=None):
        channelId = ctx.channel.id
        listDays = ["lundi", "mardi", "mercredi",
                    "jeudi", "vendredi", "samedi", "dimanche"]
        day = listDays.index(args[0].lower())
        origine = "PARIS+(intramuros)" if args[1] == "PARIS" else args[1]
        destination = "PARIS+(intramuros)" if args[2] == "PARIS" else args[2]
        minHour = args[3]
        maxHour = args[4]
        global search_loop

        @tasks.loop(seconds=120)
        async def search_loop():
            if (origine == "REIMS"):
                await get_train(day, "REIMS", destination, minHour, maxHour, channelId)
                await get_train(day, "CHAMPAGNE-ARDENNE", destination, minHour, maxHour, channelId)
            elif (destination == "REIMS"):
                await get_train(day, origine, "REIMS", minHour, maxHour, channelId)
                await get_train(day, origine, "CHAMPAGNE-ARDENNE", minHour, maxHour, channelId)
            else:
                await get_train(day, origine, destination, minHour, maxHour, channelId)
            await asyncio.sleep(120)

        search_loop.start()

    @bot.command()
    async def stop(ctx):
        search_loop.cancel()
        await ctx.send("Successfully deactivated SpamMode")

    bot.run(os.environ.get("BOT_KEY"))


if __name__ == '__main__':
    main()
