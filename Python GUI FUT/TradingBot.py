import fut
import time
import random
import requests
from prettytable import PrettyTable


class TradingBot():
    """Class that represents the trading bot. Keeps track of player bought and sold among many other things."""
    def __init__(self, username, password, secretAnswer, coinLimit = 0):
        self.session = fut.Core(username, password, secretAnswer)
        self.boughtPlayers = []
        self.soldPlayers = []
        self.coins = self.session.keepalive()
        self.actionCount = 0  # necessary to make sure market is not pinged more that 500 times in one hour
        self.playersToTrade = {}
        self.coinLimit = coinLimit
        self.tradeStartTime = 0
        self.allowTrade = True

    def addPlayerToBidList(self, lyst):
        """Updates the players that the bot is currently trading"""
        print("Spooling up")
        for player in lyst:
            self.playersToTrade[player[0]['id']] = player[1]
            print("..")

    def logout(self):
        """Logs the bot out."""
        self.session.logout()

    def getCoinLimit(self):
        """Returns the current coin limit"""
        return self.coinLimit

    def getActionCount(self):
        """Returns the bot's action count"""
        return self.actionCount

    def updateActionCount(self, integer, progressBar):
        self.actionCount += integer
        print("Updating action count: " + str(self.getActionCount()))
        progressBar.value = self.getActionCount()

    def updateCoinLimit(self, newLimit):
        """The bot will not allow coins to drop below the specified level"""
        self.coinLimit = newLimit

    def stopTrade(self):
        """This stops the bot from being able to trade"""
        self.allowTrade = False

    def allowStartTrade(self):
        """This allows the bot to start trading"""
        self.allowTrade = True

    def outputWatchlist(self, watchList, watchListView):
        """This outputs a nicely formatted string to watch list recycle view"""
        watchListOutput = PrettyTable()
        watchListOutput.field_names = ["Player Names", "Price", "Time"]
        watchListView.data = []
        for player in watchList:
            watchListOutput.add_row([self.getPlayerName(player), self.getCurrentPlayerPrice(player), player['expires']])
        print(watchListOutput)
        for player in watchList:
            # TODO: Properly format the Watch List Status Window
            #print("%-15s %-3d %6d" % (self.getPlayerName(player), self.getCurrentPlayerPrice(player), player['expires']))
            watchListView.data.insert(len(watchListView.data),
                            {'value': str(self.getPlayerName(player) + " " + str(self.getCurrentPlayerPrice(player)) + " " + str(player['expires']))})

    def getWatchList(self):
        """Get the watchlist. Handles HTML timeouts"""
        try:
            watchList = self.session.watchlist()
            return watchList
        except:
            print("HTML TIMEOUT. TRYING AGAIN")
            time.sleep(15)
            self.getWatchList()
    # TODO: Fix error that occurs when player added to list while program is running
    
    def trade(self, dictionary, progressBar, currentCoin, watchListView, boughtItemCount):
        """The trading loop for the bot"""
        print("Warming up...")
        self.addPlayersToWatchList(dictionary, progressBar)
        print("Done adding players to bid list...")
        coinBalance = self.session.keepalive()
        currentCoin.text = "Current Balance: " + str(coinBalance)
        self.tradeStartTime = time.monotonic()
        self.session.relist()

        while coinBalance > self.coinLimit and self.allowTrade:
            if self.actionCount >= 500:
                print("Time to sleep: " + str(3600 - (time.monotonic() - self.tradeStartTime)))
                time.sleep(3600 - (time.monotonic() - self.tradeStartTime))
                # TODO: Need to fix timeout issue here
                self.tradeStartTime = 0
                self.updateActionCount(-500, progressBar)

            # Update GUI information
            coinBalance = self.session.keepalive()
            currentCoin.text = "Current Balance: " + str(coinBalance)
            boughtItemCount.text = "Bought Items: " + str(len(self.boughtPlayers))

            # Reset action count and relist trade piles every hour
            if time.monotonic() - self.tradeStartTime > 3600:
                self.actionCount = 0
                self.tradeStartTime = 0
                print("Relisting...")
                self.session.relist()

            self.updateActionCount(2, progressBar)
            watchList = self.getWatchList()

            print(str(len(watchList)) + str(watchList))
            self.outputWatchlist(watchList, watchListView)

            if len(watchList) > 0:
                nextWatchListExpire = watchList[0]['expires']
            else:
                nextWatchListExpire = 1000 # Go into normal loop
            print(nextWatchListExpire)

            # Choose which loop to enter
            if nextWatchListExpire < 120:
                self.getAggressive(dictionary, watchList, progressBar)
            elif nextWatchListExpire < 3000 and self.actionCount < 300:
                self.buyNowMode(nextWatchListExpire, watchList, progressBar)
            else:
                self.watchListLoop(dictionary, watchList, progressBar)

            time.sleep(random.randrange(1, 3))

    def getMaxBidPrice(self, bidPlayer):
        """Gets price to pay on players"""
        return self.playersToTrade.get(bidPlayer['assetId'], 0)

    def getNextBidPrice(self, bidPlayer):
        """Gets the next lowest bid price for player depending on their current price"""
        maxPrice = self.getMaxBidPrice(bidPlayer)
        currentPrice = self.getCurrentPlayerPrice(bidPlayer)
        if bidPlayer['currentBid'] == 0:
            return currentPrice

        if currentPrice < 1000:
            nextBidPrice = currentPrice + 50
        elif 1000 <= currentPrice < 10000:
            nextBidPrice = currentPrice + 100
        elif 10000 <= currentPrice < 50000:
            nextBidPrice = currentPrice + 250
        elif 50000 <= currentPrice < 100000:
            nextBidPrice = currentPrice + 500
        elif currentPrice >= 100000:
            nextBidPrice = currentPrice + 1000
        if nextBidPrice > maxPrice:
            nextBidPrice = None
        #print(nextBidPrice)
        return nextBidPrice

    @staticmethod
    def getPlayerName(bidPlayer):
        """Returns the player name given the assetID"""
        r = requests.get(
            "https://www.easports.com/fifa/ultimate-team/web-app/content/B1BA185F-AD7C-4128-8A64-746DE4EC5A82/2018/fut/items/web/players.json")
        players = r.json()
        name = ''
        for playerType in players:
            for player in players[playerType]:
                if player['id'] == bidPlayer['assetId']:
                    try:
                        name = player['c']
                    except:
                        name = player['f'] + " " + player['l']
                    return name

    @staticmethod
    def getCurrentPlayerPrice(x):
        """Returns the player's current price"""
        price = x['startingBid']
        if not x['currentBid'] == 0:
            price = x['currentBid']
        return price

    def addPlayersToWatchList(self, dictionary, progressBar):
        """Begins the trading loop for the bot. Adds all players to search for in the bot"""
        for player in self.playersToTrade:
            startPage = 1
            while True:
                auctionPlayers = self.session.search(ctype='player', start=startPage, assetId=player, max_price=self.playersToTrade[player])
                self.updateActionCount(1, progressBar)

                # Go through each player and bid
                for x in auctionPlayers:
                    print(self.getPlayerName(x))
                    # Get the price of the current player
                    price = self.getNextBidPrice(x)

                    # Bid given the right scenario
                    print(x)
                    dictionary.insert(len(dictionary), {'value': str(time.strftime("%I:%M:%S") +
                                                                     ": Attempting to bid on " + self.getPlayerName(x) +
                                                                     " for " + str(price))})

                    if x['expires'] < 3600 and not x['tradeState'] == 'closed' and not x['bidState'] == 'highest' and not price is None:
                        if self.session.bid(x['tradeId'], price):
                            dictionary.insert(len(dictionary),
                                              {'value': str(time.strftime("%I:%M:%S") + ": Bid Successful")})
                            print("Bid Successful")
                        self.updateActionCount(1, progressBar)
                    else:
                        dictionary.insert(len(dictionary), {'value':
                                                                str(time.strftime("%I:%M:%S") +
                                                                    ": Bid Failed. Expires in " + str(x['expires']))})
                        if x['expires'] > 3600:
                            break
                        # TODO Provide more reasoning for why bid failed. EX: "Not enough money"

                    time.sleep(random.randrange(2, 4))
                    # Finished bidding on this page

                # Begin loop on the next page
                startPage += 16

                # Break if on the last page or more than an hour out
                if len(auctionPlayers) < 16 or auctionPlayers[-1]['expires'] > 3600 and not self.allowTrade:
                    break

            print("Done with current player ...")
            time.sleep(random.randrange(6, 12))

    def watchListLoop(self, dictionary, watchList, progressBar, aggressive = False):
        """Runs the each player and the watchlist and performs the appropriate action."""
        dictionary.insert(len(dictionary),
                          {'value': str(time.strftime("%I:%M:%S") + ": Searching watch list for actions...")})

        for x in watchList:
            # Get the price of the current player
            price = self.getNextBidPrice(x)

            if price is None:
                if x['bidState'] == 'outbid':
                    dictionary.insert(len(dictionary),
                                      {'value': str(
                                          time.strftime("%I:%M:%S") + ": Player is to expensive.")})
                    dictionary.insert(len(dictionary),
                                      {'value': str(time.strftime("%I:%M:%S") + ": " + self.getPlayerName(x) +
                                                    " deleted from watch list.")})
                    self.session.watchlistDelete(x['tradeId'])

                elif x['bidState'] == 'highest' and x['tradeState'] == 'closed':
                    dictionary.insert(len(dictionary),
                                      {'value': str(
                                          time.strftime("%I:%M:%S") + ": Won auction!")})
                    dictionary.insert(len(dictionary),
                                      {'value': str(time.strftime("%I:%M:%S") + ": " + self.getPlayerName(x) +
                                                    " sent to trade pile")})
                    self.boughtPlayers.append(x)
                    self.session.sendToTradepile(x['id'])

            elif x['tradeState'] == 'closed':
                # Lost auction. Delete from watch list.
                if not x['bidState'] == 'highest':
                    dictionary.insert(len(dictionary),
                                      {'value': str(
                                          time.strftime("%I:%M:%S") + ": Lost auction.")})
                    dictionary.insert(len(dictionary), {'value': str(time.strftime("%I:%M:%S") + ": Removing " +
                                                                     self.getPlayerName(x) + " from watch list...")})
                    self.session.watchlistDelete(x['tradeId'])

                # Won auction. Send to the trade pile.
                else:
                    dictionary.insert(len(dictionary),
                                      {'value': str(
                                          time.strftime("%I:%M:%S") + ": Won Auction.")})
                    dictionary.insert(len(dictionary),
                                      {'value': str(time.strftime("%I:%M:%S") + ": Sending " + self.getPlayerName(x) +
                                                    " to trade pile...")})
                    print("Sending player to trade pile ..." + str(x))

                    self.boughtPlayers.append(x)
                    self.session.sendToTradepile(x['id'])

            elif x['expires'] < 3600 and not x['tradeState'] == 'closed' and not x['bidState'] == 'highest':
                dictionary.insert(len(dictionary), {'value': str(time.strftime("%I:%M:%S") +
                                                                 ": Attempting to bid on " + self.getPlayerName(x) +
                                                                " for " + str(price))})
                try:

                    if self.session.bid(x['tradeId'], price):
                        dictionary.insert(len(dictionary),
                                          {'value': str(time.strftime("%I:%M:%S") + ": Bid Successful")})
                        print("Bid Successful: " + str(x))
                    else:
                        dictionary.insert(len(dictionary), {'value': str(time.strftime("%I:%M:%S") + ": Bid Failed")})
                    self.updateActionCount(1, progressBar)
                    time.sleep(random.randrange(1, 4))
                except Exception:
                    print(Exception)  # This might cause problems

            # Aggressive is True when using getAggressive().
            if aggressive is True:
                if x['expires'] > 60:
                    print("Breaking due to expiration time")
                    break

        if aggressive is False:
            dictionary.insert(len(dictionary),
                              {'value': str(time.strftime("%I:%M:%S") + ": Waiting...")})
            time.sleep(random.randrange(20, 40))

    def getAggressive(self, dictionary, watchList, progressBar):
        """Allows one to win more bid wars by waiting less and only bidding on watch list players
        if they expire in less than a minute"""
        print("GOING AGGRESSIVE")
        self.watchListLoop(dictionary, watchList, progressBar, aggressive = True)

    def buyNowMode(self, nextWatchListExpire, watchList, progressBar):
        """Buy now mode. Will go through and attempt to buy players at the users defined max price"""
        if len(self.playersToTrade) == 0: return
        startTime = time.monotonic()
        searches = 0
        playerId = random.choice(list(self.playersToTrade.keys()))
        print(self.session.cardInfo(playerId))

        while self.allowTrade and self.getActionCount() < 500:
            if time.monotonic() - startTime > nextWatchListExpire - 50:
                break

            if time.monotonic() - startTime > 100:
                break

            print("checking for bin")
            binSearch = self.session.search(ctype='player', assetId=playerId,
                                                 max_buy=self.playersToTrade.get(playerId))
            print(binSearch)
            for player in binSearch:
                print("Found ITEM>>>>>")
                if self.session.bid(player["tradeId"], player['buyNowPrice']):
                    print("YESSSSSSSS")
                    self.boughtPlayers.append(player)
            time.sleep(random.randrange(1,2))
            self.updateActionCount(1, progressBar)
            searches += 1
            if searches == 15:
                time.sleep(10)
                searches = 0


# TODO: Bought players history list
# TODO: AUTO relist players
