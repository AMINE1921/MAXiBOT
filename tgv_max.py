from dotenv import load_dotenv, find_dotenv
from discord.ext import commands
from datetime import datetime, timedelta
import aiohttp
import discord
import patreon
import asyncio
import json
import os


class Bot(commands.Bot):
    async def async_cleanup(self):
        channel = bot.get_channel(1056632494411231272)
        await channel.send(":anger: Le bot est hors ligne :face_with_spiral_eyes:")

    async def close(self):
        await self.async_cleanup()
        await super().close()

    async def on_ready(self):
        channel = bot.get_channel(1056632494411231272)
        await channel.send(":anger: Le bot est maintenant prêt à être utilisé :fire:")


async def search_train(data, minHour, maxHour, channelId, taskId):
    if 'proposals' in data:
        for i in range(len(data['proposals'])):
            try:
                departureDateTime = data['proposals'][i]['departureDate'].split(
                    'T')
                date = departureDateTime[0]
                hour = departureDateTime[1]
                origine = data['proposals'][i]['origin']['label']
                destination = data['proposals'][i]['destination']['label']
                route = {
                    'date': date,
                    'hour': hour,
                    'origine': origine,
                    'destination': destination,
                    "channelId": channelId,
                }
                if (os.path.exists("logs.json") == False):
                    with open('logs.json', 'x') as f:
                        json.dump([], f)
                with open('logs.json', 'r') as f:
                    logsData = json.load(f)
                if minHour <= hour <= maxHour and route not in logsData:
                    print(
                        f'{origine} vers {destination} : {date} à {hour}')
                    logsData.append(route)
                    with open('logs.json', 'w') as f:
                        json.dump(logsData, f)
                    channel = bot.get_channel(channelId)
                    await channel.send(f':bullettrain_side: :house: {origine} :arrow_right: {destination} : :date: {date} à {hour}')
            except Exception as e:
                print(e)
                channel = bot.get_channel(channelId)
                await channel.send(f'Une erreur est survenue: {e}')
                index = int(taskId)
                current_tasks[index]["task"].cancel()
                current_tasks.pop(index)
                break


async def get_train(date, origine, destination, minHour, maxHour, channelId, taskId):
    data = {'departureDateTime': date + "T00:00:00",
            'destination': destination, 'origin': origine}
    url = "https://www.maxjeune-tgvinoui.sncf/api/public/refdata/search-freeplaces-proposals"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as r:
            if r.status == 200:
                js = await r.json()
                await search_train(js, minHour, maxHour, channelId, taskId)


async def search_loop(day, origine, destination, minHour, maxHour, channelId, taskId):
    while True:
        current_date = datetime.now()
        for i in range(1, 31):
            date = (current_date + timedelta(days=i)).strftime("%Y-%m-%d")
            if (datetime.strptime(date, '%Y-%m-%d').weekday() == day):
                if (destination == "FRRHE"):
                    await get_train(date, origine, "FRRHE", minHour, maxHour, channelId, taskId)
                    await get_train(date, origine, "FREAH", minHour, maxHour, channelId, taskId)
                else:
                    await get_train(date, origine, destination, minHour, maxHour, channelId, taskId)
        await asyncio.sleep(120)


async def serach_station(name, channelId):
    channel = bot.get_channel(channelId)
    url = "https://www.maxjeune-tgvinoui.sncf/api/public/refdata/freeplaces-stations"
    params = {'label': name}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as r:
            if r.status == 200:
                response = await r.json()
                if not response["stations"]:
                    await channel.send(":x: Aucune station trouvée")
                if response["stations"]:
                    listStations = ""
                    for index, station in enumerate(response["stations"][:10]):
                        listStations += f'**{station["station"]}**: {station["codeStation"]}\n'
                    embed = discord.Embed(title="Liste de gares",
                                          description=f'Voici la liste des gars contenant "{name.replace("+", " ")}"', color=0x00ff00)
                    embed.add_field(
                        name="Liste: ", value=listStations, inline=False)
                    embed.set_footer(text="MAXiBOT",
                                     icon_url="https://i.imgur.com/hnjxCJ1.png")
                    await channel.send(embed=embed)


async def is_premium(userId):
    access_token = os.environ.get("CREATOR_ACCESS_TOKEN")
    api_client = patreon.API(access_token)
    campaign_response = api_client.fetch_campaign()
    campaign_id = campaign_response.data()[0].id()
    jsonapi_doc = api_client.fetch_page_of_pledges(campaign_id, 100)
    discord_ids = []
    while True:
        json_data = jsonapi_doc.json_data
        users = [entity for entity in json_data['included']
                 if 'type' in entity
                 and entity['type'] == 'user']
        discord_ids = [user['attributes']['social_connections']['discord']['user_id'] for user in users
                       if user['attributes']['social_connections']['discord'] is not None]
        json_data = jsonapi_doc.json_data
        if 'next' in json_data['links']:
            jsonapi_doc.links.next = jsonapi_doc.links.next.encode(
                'ascii', 'ignore')
            cursor = api_client.extract_cursor(jsonapi_doc)
            jsonapi_doc = api_client.fetch_page_of_pledges(
                campaign_id, 100, cursor).json_data
        else:
            break
    return str(userId) in discord_ids


def user_id_exists_in_current_tasks(user_id):
    for task in current_tasks:
        if task['userId'] == user_id:
            return True
    return False


def main():
    load_dotenv(find_dotenv())
    global bot
    global current_tasks
    intents = discord.Intents.default()
    intents.message_content = True
    bot = Bot(command_prefix='!', intents=intents)
    listDays = ["lundi", "mardi", "mercredi",
                "jeudi", "vendredi", "samedi", "dimanche"]
    current_tasks = []

    @bot.command()
    async def maxi(ctx, *args, given_name=None):
        command = args[0]
        userId = ctx.message.author.id

        if userId == 493410965644247055 or userId == 494033803463884802 or await is_premium(userId):
            match command:
                case "start":
                    try:
                        with open('stationsList.json', 'r') as f:
                            dataStations = json.load(f)
                        allCodesStations = list(
                            set(station['codeStation'] for station in dataStations['stations']))
                        channelId = ctx.channel.id
                        day = listDays.index(args[1].lower())
                        origine = args[2]
                        destination = args[3]
                        minHour = args[4]
                        maxHour = args[5]
                        taskId = len(current_tasks)
                        if origine in allCodesStations and destination in allCodesStations:
                            task = bot.loop.create_task(search_loop(
                                day, origine, destination, minHour, maxHour, channelId, taskId))
                            current_tasks.append({"task": task, "day": day, "origine": origine,
                                                  "destination": destination, "minHour": minHour, "maxHour": maxHour, "userId": userId})
                        else:
                            await ctx.send("Les codes stations ne sont pas corrects !")
                    except Exception as e:
                        print(e)
                        await ctx.send("Une erreur est survenue")
                case "info":
                    embed = discord.Embed(title="Guide d'utilisation !",
                                          description="Ce bot permet de rechercher des trains TGV Max", color=0x00ff00)
                    embed.add_field(
                        name="Format:", value="!maxi start [le jour de la semaine] [le code de la station de la ville de départ] [le code de la station de la ville d'arrivé] [heure de départ minimum] [heure de départ maximum]", inline=False)
                    embed.add_field(
                        name="Exemple:", value="!maxi start mardi FRPST FRRHE 07:00 10:00")
                    embed.add_field(
                        name="Autres commandes:", value="!maxi station [nom de la station]\n !maxi stop", inline=False)
                    embed.set_footer(text="Veuillez respecter la forme du message pour activer le Bot !",
                                     icon_url="https://i.imgur.com/hnjxCJ1.png")
                    await ctx.send(embed=embed)
                case "station":
                    try:
                        channelId = ctx.channel.id
                        arg = args[1: len(args)]
                        name = " ".join(arg)
                        if len(name) == 0:
                            await ctx.send("Veuillez renseigner un nom de station")
                        elif len(name) < 3:
                            await ctx.send("Veuillez renseigner un nom de station plus long")
                        else:
                            await serach_station(name, channelId)
                    except Exception as e:
                        print(e)
                        await ctx.send("Une erreur est survenue")
                case "stop":
                    if len(args) == 1:
                        if (len(current_tasks) > 0 and user_id_exists_in_current_tasks(userId)):
                            tasks = ""
                            with open('stationsList.json', 'r') as f:
                                dataStations = json.load(f)
                            for index, task in enumerate(current_tasks):
                                stationOrigine = next(
                                    (item for item in dataStations["stations"] if item["codeStation"] == task["origine"]), None)
                                stationDestination = next(
                                    (item for item in dataStations["stations"] if item["codeStation"] == task["destination"]), None)
                                if userId == task["userId"]:
                                    tasks += f'{index}: :date: {listDays[int(task["day"])]} :house: {stationOrigine["station"]} :arrow_right: {stationDestination["station"]} :timer: {task["minHour"]} {task["maxHour"]}\n'
                        else:
                            tasks = "Aucune recherche n'est lancée"
                        embed = discord.Embed(title="Guide d'utilisation pour arrêter une recherche !",
                                              description="Pour arrêter une recherche il faut suivre l'exemple ci-dessous", color=0x00ff00)
                        embed.add_field(
                            name="Tâches actuelles:", value=tasks, inline=False)
                        embed.add_field(
                            name="Exemple:", value="!maxi stop 0")
                        embed.set_footer(text="Veuillez respecter la forme du message pour activer le Bot !",
                                         icon_url="https://i.imgur.com/hnjxCJ1.png")
                        await ctx.send(embed=embed)
                    else:
                        if (len(current_tasks) > 0):
                            try:
                                index = int(args[1])
                                current_tasks[index]["task"].cancel()
                                current_tasks.pop(index)
                                await ctx.send("La recherche a bien été arreté")
                            except Exception as e:
                                print(e)
                                await ctx.send("Une erreur est survenue")
                        else:
                            await ctx.send("Aucune recherche n'est lancée")
                case _:
                    await ctx.send("Cette commande n'existe pas !")
        else:
            await ctx.send("Vous n'êtes pas membre dans notre patreon ! \n https://www.patreon.com/maxibot")

    bot.run(os.environ.get("BOT_KEY"))


if __name__ == '__main__':
    main()
