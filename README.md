# tradunio

Tradunio helps you to play <a href="http://www.comunio.es">Comunio</a> game and control your opponents and when it is a good deal to sell or to buy.

## Usage
Initializes the database and retrieves the first data to work.

`
./tradunio.py --init
`

Cron this on your server and you will receive an email all mornings with your updated team, players to sell and players to buy.

Updates the data of all the users and players and sends you an email.

`
./tradunio.py --update --mail
`

Updates best players to sell.

`
./tradunio.py --sell --mail


Updates best players to buy.

`
./tradunio.py --buy --mail
