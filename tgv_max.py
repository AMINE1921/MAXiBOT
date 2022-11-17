from dotenv import load_dotenv, find_dotenv
from discord.ext import commands
from datetime import datetime
import requests
import discord
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

async def search_loop(day, origine, destination, minHour, maxHour, channelId):
    while True:
        try:
            if (origine == "REIMS"):
                await get_train(day, "REIMS", destination, minHour, maxHour, channelId)
                await get_train(day, "CHAMPAGNE-ARDENNE", destination, minHour, maxHour, channelId)
            elif (destination == "REIMS"):
                await get_train(day, origine, "REIMS", minHour, maxHour, channelId)
                await get_train(day, origine, "CHAMPAGNE-ARDENNE", minHour, maxHour, channelId)
            else:
                await get_train(day, origine, destination, minHour, maxHour, channelId)
            await asyncio.sleep(120)
        except Exception as e:
            print(e)
            channel = bot.get_channel(channelId)
            await channel.send("f'Une erreur est survenue: {e}'")

def main():
    load_dotenv(find_dotenv())
    global bot
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents)
    current_tasks = []

    @bot.command()
    async def infos(ctx):
        embed = discord.Embed(title="Guide d'utilisation !",
                              description="Ce bot permet de rechercher des trains TGV Max", color=0x00ff00)
        embed.add_field(
            name="Format:", value="!maxi [le jour de la semaine] [la ville de départ] [la ville d'arrivé] [heure de départ minimum] [heure de départ maximum]", inline=False)
        embed.add_field(
            name="Exemple:", value="!maxi mardi REIMS PARIS 07:00 10:00")
        embed.set_footer(text="Veuillez respecter la forme du message pour activer le Bot !",
                         icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/4/46/Logo_SNCF_2011.svg/1024px-Logo_SNCF_2011.svg.png")
        await ctx.send(embed=embed)

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

        try:
            task = bot.loop.create_task(search_loop(day, origine, destination, minHour, maxHour, channelId))
            current_tasks.append({"task": task, "day": day, "origine": origine, "destination": destination, "minHour": minHour, "maxHour": maxHour})
        except Exception as e:
            print(e)
            await ctx.send("Une erreur est survenue")

    @bot.command()
    async def stop(ctx, *args):
        if len(args) == 0:
            if (len(current_tasks)>0):
                tasks = ""
                for index, task in enumerate(current_tasks):
                    tasks += f'{index}: {task["day"]} {task["origine"]} {task["destination"]} {task["minHour"]} {task["maxHour"]}\n'
            else:
                tasks = "Aucune recherche n'est lancée"
            embed = discord.Embed(title="Guide d'utilisation pour arrêter une recherche !",
                              description="Pour arrêter une recherche il faut suivre l'exemple ci-dessous", color=0x00ff00)
            embed.add_field(
                name="Tâches actuelles:", value=tasks, inline=False)
            embed.add_field(
            name="Exemple:", value="!stop 0")
            embed.set_footer(text="Veuillez respecter la forme du message pour activer le Bot !",
                            icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/4/46/Logo_SNCF_2011.svg/1024px-Logo_SNCF_2011.svg.png")
            await ctx.send(embed=embed)
        else:
            if (len(current_tasks)>0):
                try:
                    index = int(args[0])
                    current_tasks[index]["task"].cancel()
                    current_tasks.pop(index)
                    await ctx.send("La recherche a bien été arreté")
                except Exception as e:
                    print(e)
                    await ctx.send("Une erreur est survenue")
            else: 
                await ctx.send("Aucune recherche n'est lancée")

    bot.run(os.environ.get("BOT_KEY"))

if __name__ == '__main__':
    main()
