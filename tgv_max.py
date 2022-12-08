from dotenv import load_dotenv, find_dotenv
from discord.ext import commands
from datetime import datetime, timedelta
import requests
import discord
import asyncio
import json
import os

async def search_train(data, channelId, taskId):
    nb_train = len(data)
    for i in range(0, nb_train):
        try:
            departureDateTime = data[i]["departureDateTime"].split("T")
            date = departureDateTime[0]
            hour = departureDateTime[1]
            origine = data[i]["originName"]
            destination = data[i]["destinationName"]
            f = open("sncf.txt", "a+")
            f.seek(0)
            if (data[i]["availableSeatsCount"] != 0 and json.dumps(data[i]) not in f.read()):
                print(f'{origine} vers {destination} : {date} à {hour}')
                f.write(json.dumps(data[i]) + "\n")
                channel = bot.get_channel(channelId)
                await channel.send(f'\U0001F684 \U0001F3E0 {origine} vers \U000027A1 {destination} : \U0001F4C5 {date} à {hour}')
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
    url = prepare_url(date, origine, destination, minHour, maxHour)
    response = requests.get(url)
    await search_train(response.json(), channelId, taskId)

def prepare_url(date, origine, destination, minHour, maxHour):
    url = f"https://sncf-simulateur-api-prod.azurewebsites.net/api/RailAvailability/Search"
    url += "/" + origine
    url += "/" + destination
    url += "/" + date + "T" + minHour + ":00"
    url += "/" + date + "T" + maxHour + ":00"
    return url

async def search_loop(day, origine, destination, minHour, maxHour, channelId, taskId):
    while True:
        current_date = datetime.now()
        for i in range(1,31):
            date = (current_date + timedelta(days=i)).strftime("%Y-%m-%d")
            if (datetime.strptime(date, '%Y-%m-%d').weekday() == day):
                if (origine == "REIMS"):
                    await get_train(date, "REIMS", destination, minHour, maxHour, channelId, taskId)
                elif (destination == "REIMS"):
                    await get_train(date, origine, "REIMS", minHour, maxHour, channelId, taskId)
                    await get_train(date, origine, "CHAMPAGNE-ARDENNE", minHour, maxHour, channelId, taskId)
                else:
                    await get_train(date, origine, destination, minHour, maxHour, channelId, taskId)
        await asyncio.sleep(120)

def main():
    load_dotenv(find_dotenv())
    global bot
    global current_tasks
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents)
    listDays = ["lundi", "mardi", "mercredi",
    "jeudi", "vendredi", "samedi", "dimanche"]
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
        day = listDays.index(args[0].lower())
        origine = "PARIS%20(intramuros)" if args[1] == "PARIS" else args[1]
        destination = "PARIS%20(intramuros)" if args[2] == "PARIS" else args[2]
        minHour = args[3]
        maxHour = args[4]

        try:
            taskId = len(current_tasks)
            task = bot.loop.create_task(search_loop(day, origine, destination, minHour, maxHour, channelId, taskId))
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
                    tasks += f'{index}: {listDays[int(task["day"])]} {task["origine"]} {task["destination"]} {task["minHour"]} {task["maxHour"]}\n'
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