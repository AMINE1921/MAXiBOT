from dotenv import load_dotenv, find_dotenv
from discord.ext import commands
from datetime import datetime, timedelta
import aiohttp
import discord
import asyncio
import json
import os


class Bot(commands.Bot):
    async def async_cleanup(self):
        channel = bot.get_channel(1042387439706185828)
        await channel.send(f':anger: Bot is offline :face_with_spiral_eyes:')

    async def close(self):
        await self.async_cleanup()
        await super().close()


async def search_train(data, minHour, maxHour, channelId, taskId):
    nb_train = len(data["proposals"])
    for i in range(0, nb_train):
        try:
            departureDateTime = data["proposals"][i]["departureDate"].split(
                "T")
            date = departureDateTime[0]
            hour = departureDateTime[1]
            origine = data["proposals"][i]["origin"]["label"]
            destination = data["proposals"][i]["destination"]["label"]
            f = open("sncf.txt", "a+")
            f.seek(0)
            if (minHour <= hour and hour <= maxHour and json.dumps(data["proposals"][i]) not in f.read()):
                print(f'{origine} vers {destination} : {date} à {hour}')
                f.write(json.dumps(data["proposals"][i]) + "\n")
                channel = bot.get_channel(channelId)
                await channel.send(f':bullettrain_side: :house: {origine} vers :arrow_right: {destination} : :date: {date} à {hour}')
            f.close()
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
                    await channel.send(f':x: Aucune station trouvée')
                if response["stations"]:
                    listStations = ""
                    for index, station in enumerate(response["stations"][:10]):
                        listStations += f'**{station["station"]}**: {station["codeStation"]}\n'
                    embed = discord.Embed(title="Liste de gares",
                                          description=f'Voici la liste des gars contenant "{name.replace("+", " ")}"', color=0x00ff00)
                    embed.add_field(
                        name="Liste: ", value=listStations, inline=False)
                    embed.set_footer(text="MAXiBOT",
                                     icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/4/46/Logo_SNCF_2011.svg/1024px-Logo_SNCF_2011.svg.png")
                    await channel.send(embed=embed)


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
    async def maxiDev(ctx, *args, given_name=None):
        command = args[0]

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
                                              "destination": destination, "minHour": minHour, "maxHour": maxHour})
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
                embed.set_footer(text="Veuillez respecter la forme du message pour activer le Bot !",
                                 icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/4/46/Logo_SNCF_2011.svg/1024px-Logo_SNCF_2011.svg.png")
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
                    if (len(current_tasks) > 0):
                        tasks = ""
                        with open('stationsList.json', 'r') as f:
                            dataStations = json.load(f)
                        for index, task in enumerate(current_tasks):
                            stationOrigine = next(
                                (item for item in dataStations["stations"] if item["codeStation"] == task["origine"]), None)
                            stationDestination = next(
                                (item for item in dataStations["stations"] if item["codeStation"] == task["destination"]), None)
                            tasks += f'{index}: {listDays[int(task["day"])]} {stationOrigine["station"]} {stationDestination["station"]} {task["minHour"]} {task["maxHour"]}\n'
                    else:
                        tasks = "Aucune recherche n'est lancée"
                    embed = discord.Embed(title="Guide d'utilisation pour arrêter une recherche !",
                                          description="Pour arrêter une recherche il faut suivre l'exemple ci-dessous", color=0x00ff00)
                    embed.add_field(
                        name="Tâches actuelles:", value=tasks, inline=False)
                    embed.add_field(
                        name="Exemple:", value="!maxi stop 0")
                    embed.set_footer(text="Veuillez respecter la forme du message pour activer le Bot !",
                                     icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/4/46/Logo_SNCF_2011.svg/1024px-Logo_SNCF_2011.svg.png")
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

    bot.run(os.environ.get("BOT_KEY"))


if __name__ == '__main__':
    main()
