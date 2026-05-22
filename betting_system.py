import random
import matplotlib.pyplot as plt
import csv
import math
import requests
import smtplib
from email.mime.text import MIMEText
import socket
import urllib3.util.connection as urllib3_cn

def allowed_gai_family():
    return socket.AF_INET

urllib3_cn.allowed_gai_family = allowed_gai_family

session = requests.Session()

session.proxies = {}
from bs4 import BeautifulSoup

API_TOKEN = "c8c576df251c4d5ba18f239d4f7d8c24"

ODDS_API_KEY = "73b0ebb65843161696a41f39505423af"

TELEGRAM_TOKEN = "8963703387:AAGea27irfAvPkfk3Ufoxp0ornWav2P1z8"

CHAT_ID = "1643795522"

EMAIL_SENDER = "clreder@gmail.com"
EMAIL_PASSWORD = "xgjbsweeoqojkwwn"
EMAIL_RECEIVER = "clr_eder18@hotmail.com"

total_apostado = 0
total_ganado = 0
wins = 0
losses = 0
historial_bankroll = []

alerted_bets = set()

all_value_bets = []

bankroll = 1000

max_bankroll = bankroll
max_drawdown = 0
archivo_csv = open("apuestas.csv", "w", newline="")

writer = csv.writer(archivo_csv)

writer.writerow([
    "Equipo",
    "Probabilidad",
    "Cuota",
    "Stake",
    "Resultado",
    "Bankroll"
])

def get_real_odds():

    url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds"

    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu",
        "markets": "h2h,totals,btts",
        "oddsFormat": "decimal"
    }

    response = requests.get(url, params=params)

    return response.json()

def poisson(goles_esperados, goles):

    probabilidad = (
        (goles_esperados ** goles)
        * math.exp(-goles_esperados)
    ) / math.factorial(goles)

    return probabilidad


def probabilidad_over(linea, lambda_total):

    limite = int(linea)

    suma = 0

    for goles in range(limite + 1):

        suma += poisson(lambda_total, goles)

    over = 1 - suma

    return over

def over_25_probability(expected_goals):

    prob = 1 - (
        poisson( expected_goals , 0 )
        + poisson( expected_goals , 1 )
        + poisson( expected_goals , 2 )
    )

    return prob

def btts_probability(xg_home, xg_away):

    home_scored = 1 - poisson(xg_home, 0)

    away_scored = 1 - poisson(xg_away, 0)

    return home_scored * away_scored

def expected_corners_calc(home_corners, away_corners):

    return home_corners + away_corners

def corners_over_probability(linea, expected_corners):

    return probabilidad_over(linea, expected_corners)

def cuota_justa(probabilidad):

    if probabilidad <= 0:
        return 0

    cuota = 1 / probabilidad
    
    return cuota

def btts_prob(
    goles_local,
    goles_visitante
):

    local_marca = (
        1 - poisson(goles_local, 0)
    )

    visitante_marca = (
        1 - poisson(goles_visitante, 0)
    )

    btts = (
        local_marca * visitante_marca
    )

    return btts
    return cuota

def expected_corners(
    ataque_local,
    defensa_visitante,
    ataque_visitante,
    defensa_local
):

    corners_local = (
        ataque_local + defensa_visitante
    ) / 2

    corners_visitante = (
        ataque_visitante + defensa_local
    ) / 2

    total = (
        corners_local + corners_visitante
    )

    return total
def expected_shots(
    ataque_local,
    defensa_visitante,
    ataque_visitante,
    defensa_local
):

    shots_local = (
        ataque_local + defensa_visitante
    ) / 2

    shots_visitante = (
        ataque_visitante + defensa_local
    ) / 2

    total = (
        shots_local + shots_visitante
    )

    return total

def expected_shots_on_target(
    ataque_local,
    defensa_visitante,
    ataque_visitante,
    defensa_local
):

    sot_local = (
        ataque_local + defensa_visitante
    ) / 2

    sot_visitante = (
        ataque_visitante + defensa_local
    ) / 2

    total = (
        sot_local + sot_visitante
    )

    return total

def expected_player_shots(
    jugador_media,
    rival_concede
):

    expected = (
        jugador_media + rival_concede
    ) / 2

    return expected


def get_understat_page(url):

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(
        url,
        headers=headers
    )

    return response.text

def send_telegram(message):

    with open("value_bets.txt", "a", encoding="utf-8") as f:
        f.write(message)
        f.write("\n\n")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:

        

        response = requests.post(
            url,
            data=payload,
            timeout=30,
            
        )

        if response.status_code == 200:
            print("Telegram alert sent")

        else:
            print("Telegram status:", response.status_code)

    except requests.exceptions.RequestException as e:

        print("Telegram connection failed")
       
        print(e)

    except Exception as e:

        print("TELEGRAM ERROR:")
        print(e)

def send_email_alert(message):

    try:
        msg = MIMEText(message)

        msg["Subject"] = "VALUE BET DETECTED"
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER

        server = smtplib.SMTP("smtp.office365.com", 587)
        server.starttls()

        server.login(EMAIL_SENDER, EMAIL_PASSWORD)

        server.sendmail(
            EMAIL_SENDER,
            EMAIL_RECEIVER,
            msg.as_string()
        )

        server.quit()

        print("EMAIL SENT")

    except Exception as e:
        print("EMAIL ERROR")
        print(e)

def normalize_team(name):

    name = name.lower()

    replacements = [
        "fc",
        "cf",
        "ac",
        "sc",
        "club",
        "deportivo",
        "balompie",
        ".",
        "-",
    ]

    for word in replacements:
        name = name.replace(word, "")

    name = " ".join(name.split())

    return name

def get_bet365_odds():

    url = "https://api.the-odds-api.com/v4/sports/soccer/odds/"

    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "eu",
        "markets": "h2h,totals",
        "bookmakers": "pinnacle",
        "oddsFormat": "decimal"
    }

    response = requests.get(url, params=params)

    return response.json()

def get_matches():

    headers = {
        "X-Auth-Token": API_TOKEN
    }

    response = requests.get(
        "https://api.football-data.org/v4/matches",
        headers=headers
    )

    data = response.json()

    for match in data["matches"]:

        home = match["homeTeam"]["name"]
        away = match["awayTeam"]["name"]

        fecha = match["utcDate"]

        estado = match["status"]

        print()
        print(home, "vs", away)
        print("Fecha:", fecha)
        print("Estado:", estado)

    return data
    
def analizar_partido(equipo, probabilidad, cuota, apuesta):

    global bankroll, total_apostado, total_ganado, wins, losses
    global max_bankroll, max_drawdown

    

    value = probabilidad * cuota

    ganancia = apuesta * cuota

    edge = (value - 1) * 100   

    b = cuota - 1

    p = probabilidad

    q = 1 - p

    kelly = ((b * p) - q) / b



    
    stake = bankroll * kelly * 0.25

    max_stake = bankroll * cap
    

    if stake > max_stake:
        stake = max_stake


    if stake < 0:
        stake = 0 

    total_apostado = total_apostado + stake    

    numero_random = random.random()

    if numero_random < probabilidad:
        resultado = "win"
    else:
        resultado = "lose"      

   #print("")

   #print("Equipo:", equipo)

   #print("Value:", round(value, 2))

   #print("Edge:", round(edge, 2), "%")

   #print("Ganancia posible:", round(ganancia, 2))

   #print("Stake recomendado:", round(stake, 2))

    if resultado == "win":
       #print("Resultado: WIN")
        bankroll = bankroll + ganancia
        total_ganado = total_ganado + ganancia   
        wins = wins + 1  

    else:
       #print("Resultado: LOSE")
        bankroll = bankroll - stake  
        losses = losses + 1

   #print("Nuevo bankroll:", round(bankroll, 2))
    historial_bankroll.append(bankroll)
    

    if bankroll > max_bankroll:
        max_bankroll = bankroll

    drawdown = ((max_bankroll - bankroll) / max_bankroll) * 100

    if drawdown > max_drawdown:
        max_drawdown = drawdown
    writer.writerow([
    equipo,
    probabilidad,
    cuota,
    round(stake, 2),
    resultado,
    round(bankroll, 2)
])
    if total_apostado > 0:
        roi = (total_ganado - total_apostado) / total_apostado * 100
    else:
        roi = 0

   #print("ROI:", round(roi, 2), "%")

    




  

bankroll = 1000

wins = 0
losses = 0    



 #  for partido in partidos:
 #      analizar_partido(partido[0], partido[1], partido[2], partido[3])

resultados_finales = []

caps = [0.01, 0.02, 0.05, 0.10]

tabla_resultados = []

for cap in caps:

    resultados_finales = []

    for simulacion in range(100):

        bankroll = 1000

        total_apostado = 0
        total_ganado = 0

        wins = 0

        losses = 0

        historial_bankroll = []

        max_bankroll = bankroll

        max_drawdown = 0

        partidos = []

        for i in range(4000):
        
            equipo = "Equipo_" + str(i)

            probabilidad = random.uniform(0.30, 0.70)

            cuota = random.uniform(1.50, 3.50)

            apuesta = random.randint(20, 100)

            partidos.append([
                equipo,
                probabilidad,
                cuota,
                apuesta
            ])

        for partido in partidos:
            

            analizar_partido(
                partido[0],
                partido[1],
                partido[2],
                partido[3]
            )

        resultados_finales.append(bankroll)
    print("")
    print("RESUMEN FINAL")
    print("Wins:", wins)
    print("Losses:", losses) 
   




    total_bets = wins + losses

    if total_bets > 0:
        winrate = (wins / total_bets) * 100
    else:
        winrate = 0

    print("Winrate:", round(winrate, 2), "%")

    print("Bankroll final:", round(bankroll, 2))

    print("Total apostado:", round(total_apostado, 2))

    print("Total ganado:", round(total_ganado, 2))

    roi_final = ((bankroll - 1000) / 1000) * 100

    print("ROI final:", round(roi_final, 2), "%")

    print("Max Drawdown:", round(max_drawdown, 2), "%")

    plt.plot(historial_bankroll)

    plt.title("Evolucion del Bankroll")

    plt.xlabel("Apuestas")

    plt.ylabel("Bankroll")

    plt.savefig("bankroll.png")

    plt.figure()

    plt.hist(resultados_finales, bins=20)

    plt.title("Distribucion Monte Carlo")

    plt.xlabel("Bankroll Final")

    plt.ylabel("Frecuencia")

    plt.savefig("montecarlo.png")

    promedio = sum(resultados_finales) / len(resultados_finales)

    mejor = max(resultados_finales)

    peor = min(resultados_finales)

    print("")
    print("CAP:", int(cap * 100), "%")

    print("")
    print("MONTE CARLO")
    print("Promedio final:", round(promedio, 2))
    print("Mejor resultado:", round(mejor, 2))
    print("Peor resultado:", round(peor, 2))
    ruina = 0

    for resultado in resultados_finales:
        if resultado < 500:
            ruina = ruina + 1

    riesgo_ruina = (ruina / len(resultados_finales)) * 100

    print("Risk of Ruin:", round(riesgo_ruina, 2), "%")

    tabla_resultados.append([
        int(cap * 100),
        round(roi_final, 2),
        round(max_drawdown, 2),
        round(promedio, 2),
        round(mejor, 2),
        round(peor, 2),
        round(riesgo_ruina, 2)
   ])

print("")
print("TABLA FINAL")
print("CAP | ROI | DD | PROM | BEST | WORST | RISK")
for fila in tabla_resultados:
    print(fila)

print("")
print("POISSON TEST")

print(poisson(2.5, 0))
print(poisson(2.5, 1))
print(poisson(2.5, 2))
print(poisson(2.5, 3))
print("")
print("OVER 2.5 TEST")

print(probabilidad_over(2.5, 2.5))

print("")
print("CUOTA JUSTA TEST")

prob_over = probabilidad_over(2.5, 2.5)

cuota = cuota_justa(prob_over)

print("Probabilidad:", prob_over)

print("Cuota justa:", round(cuota, 2))

print("")
print("VALUE BET TEST")

cuota_bookmaker = 2.40

if cuota_bookmaker > cuota:

    print("VALUE BET DETECTED")

else:

    print("NO VALUE")

print("")
print("CORNERS TEST")

corners_prob = probabilidad_over(9.5, 10.2)

print("Probabilidad:", corners_prob)

corners_cuota = cuota_justa(corners_prob)

print("Cuota justa:", round(corners_cuota, 2))    

print("")
print("EXPECTED CORNERS TEST")

lambda_corners = expected_corners(
    7.0,
    5.0,
    4.8,
    5.5
)

print("Expected corners:", round(lambda_corners, 2))

print("")
print("BTTS TEST")

btts = btts_prob(
    1.7,
    1.2
)

print("BTTS Probabilidad:", round(btts, 4))

btts_cuota = cuota_justa(btts)

print("BTTS Cuota justa:", round(btts_cuota, 2))    

print("")
print("SHOTS TEST")

lambda_shots = expected_shots(
    15.2,
    13.1,
    11.8,
    12.4
)

print("Expected shots:", round(lambda_shots, 2))

shots_prob = probabilidad_over(
    24.5,
    lambda_shots
)

print("Over 24.5 shots:", round(shots_prob, 4))

shots_cuota = cuota_justa(shots_prob)

print("Shots cuota justa:", round(shots_cuota, 2))

print("")
print("SHOTS ON TARGET TEST")

lambda_sot = expected_shots_on_target(
    5.8,
    4.9,
    4.7,
    5.1
)

print("Expected SOT:", round(lambda_sot, 2))

sot_prob = probabilidad_over(
    8.5,
    lambda_sot
)

print("Over 8.5 SOT:", round(sot_prob, 4))

sot_cuota = cuota_justa(sot_prob)

print("SOT cuota justa:", round(sot_cuota, 2))

print("")
print("PLAYER SHOTS TEST")

player_lambda = expected_player_shots(
    4.2,
    3.8
)

print("Expected player shots:", round(player_lambda, 2))

player_prob = probabilidad_over(
    3.5,
    player_lambda
)

print("Over 3.5 player shots:", round(player_prob, 4))

player_cuota = cuota_justa(player_prob)

print("Player cuota justa:", round(player_cuota, 2))

print("")
print("UNDERSTAT TEST")

#html = get_understat_page(
#    "https://fbref.com/en/comps/9/Premier-League-Stats"
#)

# print("HTML descargado:", len(html))

print("")
print("LIVE MATCHES TEST")

matches = get_matches()

for match in matches["matches"]:

    home = match["homeTeam"]["name"]

    away = match["awayTeam"]["name"]

    status = match["status"]

    date = match["utcDate"]

    print("")
    print(home, "vs", away)
    print("Fecha:", date)
    print("Estado:", status)

print()
print("LIVE MATCHES TEST")

get_matches()

def analizar_partido_completo(
    home_team,
    away_team,
    xg_home,
    xg_away,
    corners_home,
    corners_away
):

    print("\n====================")
    print(home_team, "vs", away_team)
    print("====================")

    # GOLES ESPERADOS
    expected_goals = xg_home + xg_away

    print("\nGOALS")
    print("Expected goals:", round(expected_goals, 2))

    # OVER 2.5
    prob_over25 = over_25_probability(expected_goals)

    cuota_over25 = cuota_justa(prob_over25)

    print("\nOVER 2.5")
    print("Probability:", round(prob_over25, 4))
    print("Fair odds:", round(cuota_over25, 2))

    prob_over15 = 1 - (
        poisson(expected_goals, 0)
        + poisson(expected_goals, 1)
    )

    fair_over15 = cuota_justa(prob_over15)

    market_odds_over15 = random.uniform(1.20, 1.60)

    ev_over15 = (prob_over15 * market_odds_over15) - 1

    markets.append({
        "name": "OVER 1.5",
        "probability": prob_over15,
        "fair_odds": fair_over15,
        "market_odds": market_odds_over15,
        "ev": ev_over15
    })

    prob_under35 = (
        poisson(expected_goals, 0)
        + poisson(expected_goals, 1)
        + poisson(expected_goals, 2)
        + poisson(expected_goals, 3)
    )

    prob_over35 = 1 - prob_under35

    fair_over35 = cuota_justa(prob_over35)

    market_odds_over35 = random.uniform(2.20, 4.00)

    ev_over35 = (prob_over35 * market_odds_over35) - 1

    markets.append({
        "name": "OVER 3.5",
        "probability": prob_over35,
        "fair_odds": fair_over35,
        "market_odds": market_odds_over35,
        "ev": ev_over35
    })

    # BTTS
    btts = btts_probability(xg_home, xg_away)

    print("\nBTTS")
    print("Probability:", round(btts, 4))
    print("Fair odds:", round(cuota_justa(btts), 2))

    # CORNERS
    expected_corners = expected_corners_calc(
        corners_home,
        corners_away
    )

    corners_prob = corners_over_probability(
        expected_corners,
        10.5
    )

    print("\nCORNERS")
    print("Expected:", round(expected_corners, 2))
    print("Probability:", round(corners_prob, 4))
    print("Fair odds:", round(cuota_justa(corners_prob), 2))

print("\ncAUTO SCANNER\n")

send_telegram("TEST TELEGRAM OK")

send_email_alert("TEST EMAIL OK")


data = get_matches()

matches = data["matches"]

for match in matches:

    competition = match["competition"]["name"]

    allowed_leagues = [
        "Premier League",
        "Primera Division",
        "Serie A",
        "Bundesliga",
        "Ligue 1",
        "LaLiga Hypermotion",
        "Primeira Liga",
        "Veikkausliiga",
        "Eredivisie",
        "Chinese Super League",
        "Superliga",
        "Eliteserien",
        "Saudi Pro League",
        "MLS",
        "Allsvenskan",
        "J1 League",
        "Super Lig",
        "Serie A - Brazil",
        "Primera Division - Argentina",
    ]

    if competition not in allowed_leagues:
        continue     


    home_team = match["homeTeam"]["name"]

    away_team = match["awayTeam"]["name"]

    print("\n====================")
    print(home_team, "vs", away_team)
    print("====================")

    xg_home = random.uniform(1.0, 2.2)

    xg_away = random.uniform(0.8, 2.0)

    expected_goals = xg_home + xg_away

    prob_over25 = probabilidad_over(2.5, expected_goals)

    fair = cuota_justa(prob_over25)

    market_odds = 0

    odds_data = get_bet365_odds()

    for game in odds_data:

        if not isinstance(game, dict):
            print("IGNORADO:", game)
            continue


        api_home = game["home_team"]
        api_away = game["away_team"]

        api_home = normalize_team(api_home)
        api_away = normalize_team(api_away)

        home_team_normalized = normalize_team(home_team)
        away_team_normalized = normalize_team(away_team)

        if (
            home_team_normalized in api_home
            or api_home in home_team_normalized
        ):

            if (
                away_team_normalized in api_away
                or api_away in away_team_normalized
            ):

                if game["bookmakers"]:

                    bookmaker = game["bookmakers"][0]

                    for market_data in bookmaker["markets"]:

                        if market_data["key"] == "totals":

                            outcomes = market_data["outcomes"]
 
                            for outcome in outcomes:

                                if outcome["name"] == "Over" and outcome["point"] == 2.5:

                                    market_odds = outcome["price"]

                                    if market_odds <= 1:
                                        continue

    ev = (prob_over25 * market_odds) - 1

    b = market_odds - 1
    p = prob_over25
    q = 1 - p

    kelly = ((b * p) - q) / b

    if kelly < 0:
        kelly = 0

    

    markets = []

    markets.append({
        "name": "OVER 2.5",
        "probability": prob_over25,
        "fair_odds": fair,
        "market_odds": market_odds,
        "ev": ev,
        "kelly": kelly,

    })

    prob_under25 = 1 - prob_over25

    under25_fair = cuota_justa(prob_under25)

    under25_market_odds = random.uniform(1.70, 2.30)

    under25_ev = (prob_under25 * under25_market_odds) - 1

    b = under25_market_odds - 1
    p = prob_under25
    q = 1 - p

    kelly = ((b * p) - q) / b

    if kelly < 0:
        kelly = 0

    markets.append({
        "name": "UNDER 2.5",
        "probability": prob_under25,
        "fair_odds": under25_fair,
        "market_odds": under25_market_odds,
        "ev": under25_ev,
        "kelly": kelly,

    })

    draw_prob = max(0.15, 0.35 - (expected_goals - 2.0) * 0.1)

    draw_fair = cuota_justa(draw_prob)

    draw_market_odds = random.uniform(2.80, 4.20)

    draw_ev = (draw_prob * draw_market_odds) - 1

    b = draw_market_odds - 1
    p = draw_prob
    q = 1 - p

    kelly = ((b * p) - q) / b

    if kelly < 0:
        kelly = 0

    markets.append({
        "name": "DRAW",
        "probability": draw_prob,
        "fair_odds": draw_fair,
        "market_odds": draw_market_odds,
        "ev": draw_ev,
        "kelly": kelly,
    })

    btts = btts_probability(xg_home, xg_away)

    btts_fair = cuota_justa(btts)

    btts_market_odds = random.uniform(1.70, 2.20)

    btts_ev = (btts * btts_market_odds) - 1

    markets.append({
        "name": "BTTS",
        "probability": btts,
        "fair_odds": btts_fair,
        "market_odds": btts_market_odds,
        "ev": btts_ev,
        "kelly": kelly,
    })

    for market in markets:

        print()
        print("MARKET:", market["name"])

        print("Probability:", round(market["probability"], 4))

        print("Fair odds:", round(market["fair_odds"], 2))

        print("Market odds:", round(market["market_odds"], 2))

        print("EV:", round(market["ev"], 4))

        print("Kelly:", round(market["kelly"] * 100, 2), "%")

        if market["ev"] > 0.03:

            all_value_bets.append({
                "match": f"{home_team} vs {away_team}",
                "market": market["name"],
                "probability": market["probability"],
                "fair_odds": market["fair_odds"],
                "market_odds": market["market_odds"],
                "ev": market["ev"]
            })

            bet_id = f"{home_team}_{away_team}_{market['name']}"

            if bet_id in alerted_bets:
                continue

            alerted_bets.add(bet_id)

            print(">>> VALUE BET DETECTED <<<")

            alert = f"""

                VALUE BET DETECTED

                {home_team} vs {away_team}

                Market: {market["name"]}

                Probability: {round(market["probability"],4)}

                Fair Odds: {round(market["fair_odds"],2)}

                Market Odds: {round(market["market_odds"],2)}

                EV: {round(market["ev"],4)}

                """
            send_telegram(alert)
            send_email_alert(alert)



print("\nTOP VALUE BETS")

sorted_bets = sorted(
    all_value_bets,
    key=lambda x: x["ev"],
    reverse=True
)

for bet in sorted_bets[:10]:

    print("\n====================")
    print(bet["match"])
    print("Market:", bet["market"])
    print("EV:", round(bet["ev"], 4))
    print("Odds:", bet["market_odds"])
        
from flask import Flask
import threading
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Scanner Bets Running"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web).start()

from flask import Flask
import threading
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "scanner running"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask).start()
