from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.clock import Clock, mainthread
import TradingParameters
import threading
import requests
from TradingBot import TradingBot


class TradingWindow(Screen):
    """Trading Window screen. Created in 'TradingWindow.kv'. This screen outputs the actions of the bot and also
    outputs the bot's current watchlist."""

    # def populate(self):
    #     self.ids.rv2.data = [{'value': ''.join(sample(ascii_lowercase, 25)) * 10}
    #                          for x in range(50)]

    def clear(self):
        self.ids.rv.data = []

    def insert(self, value):
        self.ids.rv.data.insert(0, {'value': value or 'default value'})

    def update(self, value):
        if self.ids.rv.data:
            self.rv.data[0]['value'] = value or 'default new value'
            self.rv.refresh_from_data()

    def remove(self):
        if self.rv.data:
            self.rv.data.pop(0)

    def switchThread(self):
        App.bot.allowStartTrade()
        App.bot.trade(self.ids.botActions.data, self.ids.actionCountProgress, self.ids.coinBalance, self.ids.watchList,
                      self.ids.boughtItemCount)

    def switch(self):
        if self.ids.tradeSwitch.active:
            threading.Thread(target=self.switchThread).start()
        else:
            App.bot.stopTrade()


class TradingParameters(Screen):
    """Trading Parameter screen. Created in 'TradingParameters.kv'. This screen allows one to configure
    the bot's actions"""
    def search(self, name, lyst):
        matches = []
        for item in lyst:
            try:
                if name in item['c']:
                    matches.append(item)
            except KeyError:
                if name in item['l']:
                    matches.append(item)
        return matches

    def searchForPlayer(self, name, lyst):
        """Searches for the player in the fut database"""
        r = requests.get(
            "https://www.easports.com/fifa/ultimate-team/web-app/content/B1BA185F-AD7C-4128-8A64-746DE4EC5A82/2018/fut/items/web/players.json")
        players = r.json()
        self.results = []
        for playerType in players:
            self.results += self.search(name, players[playerType])

        for player in self.results:
            try:
                lyst.insert(0, {'text': player['c'] + " " + str(player['r'])})
            except KeyError:
                lyst.insert(0, {'text': player['f'] + " " + player['l'] + " " + str(player['r'])})
        self.results.reverse()
        for player in self.results:
            print(player)

    def addPlayerToBidList(self, lyst, rv, maxPriceTuple):
        """Adds the selected player and price to the bots bid list"""
        selectedNodes = self.ids.checked.selected_nodes
        playersToAdd = []
        index = 0
        for item in selectedNodes:
            try:
                string = "Player: " + self.results[item]['c'] + " Rating: " + str(self.results[item]['r']) + \
                         " Max Price: " + str(maxPriceTuple[index])

                lyst.insert(0, {'value': string})
                playersToAdd.append(tuple([self.results[item], maxPriceTuple[index]]))
            except KeyError:
                string = "Player: " + self.results[item]['f'] + " " + self.results[item]['l'] + " Rating: " + \
                         str(self.results[item]['r']) + " Max Price: " + str(maxPriceTuple[index])

                lyst.insert(0, {'value': string})
                playersToAdd.append(tuple([self.results[item], maxPriceTuple[index]]))
            index += 1
            rv.data.clear()
            rv.refresh_from_data()
            selectedNodes.clear()
        return playersToAdd


class History(Screen):
    """History screen. Created in 'History.kv'. This screen outputs the players bought and sold by the bot."""
    pass


class PriceAutoUpdater(Screen):
    """Price Auto-updater screen. Created in 'PriceAutoUpdater.kv'. This screen allows one to configure the
    price aut0-updater of the bot."""
    pass


class SettingsScreen(Screen):  # Name contains screen to avoid overriding KIVY Settings module.
    """Settings screen. Created in 'Settings.kv'. Allows one to fine tune certain aspects of the bot."""
    def getCurrentCoinLimit(self):
        """Gets the current coin limit and displays it in the settings page"""
        try:
            return App.bot.getCoinLimit()
        except AttributeError:
            return 0


class ScreenManagement(ScreenManager):
    """Controls the various screens of the program. Created in 'futautotrader.kv'."""
    def logout(self):
        """Ends Fut session and change screens"""
        self.current = 'LoginScreen'
        App.bot.logout()


class LoginScreen(Screen):
    """Login screen. Created in 'Login.kv'. Input fut login information here to access the app."""
    class InvalidLogin(Popup):
        """Popup class that triggers when user enters incorrect login info.
        Created in 'Login.kv'"""
        pass

    class FutGif(Image):
        """Image class that displays when loading the Fut session"""
        pass


    @mainthread
    def updateScreen(self):
        """Removes the futgif and changes screen to trading window"""
        self.remove_widget(self.loadingGif)
        self.parent.current = 'TradingWindow'

    def startLoginThread(self, username, password, secretAnswer):
        """Allows Fut session to be loaded in a second thread which stops
        program from hanging."""
        self.loadingGif = LoginScreen.FutGif()
        self.add_widget(self.loadingGif)
        threading.Thread(target = self.loginThread, args= (username, password, secretAnswer)).start()

    def loginThread(self, username, password, secretAnswer):
        """Takes the users username password and secretAnswer and attempts to login.
        Will request ea code if needed."""
        try:
            App.bot = TradingBot(username, password, secretAnswer)
            self.updateScreen()
        except:
            self.remove_widget(self.loadingGif)
            popup = LoginScreen.InvalidLogin(size_hint = (.4,.4))
            popup.open()


class FutAutoTrader(App):
    def build(self):
        return ScreenManagement()


def main():
    FutAutoTrader().run()


if __name__ == '__main__':
    main()


