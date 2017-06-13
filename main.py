# jMath by Antonio "monk" Mancuso - Giugno 2017
# 
# versione: 0.6.0 - aggiunta di un suggerimento
# versione: 0.5.0 - salvataggio in locale dei punteggi per analisi successiva
#				  - rimozione valore palloncino uguale a risultato
#				  - uso di Animation in modo di rendere le animazioni uguali su tutti i device
# versione: 0.4.0 - rilascio iniziale

import random
from datetime import datetime
#import operator 
import kivy
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import ObjectProperty#,NumericProperty
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.utils import platform
from kivy.core.audio import SoundLoader#,Sound
from kivy.logger import Logger
#from kivy.uix.button import Button
from kivy.storage.jsonstore import JsonStore
from kivy.animation  import Animation

__version__ = '0.6.0'

class KivyLoggerWrapper:
	# Semplice wrapper del Logger di Kivy
    def __init__(self, title, debug_enabled):
    	# debug_enabled: a True visualizza i messaggi
        self.title = title
        self.debug_enabled = debug_enabled

    def info(self, message):
    	if self.debug_enabled:
    		Logger.info('%s: [%s]  %s' % (self.title, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), message))

class Pollice(Image):
	# placeholder per Pollice definito in kv
	# simbolo grafico che indica una risposta errata
	def __init__(self, w):
		super(Pollice, self).__init__()
		#Log.info(**kwargs)
		self.width = w * 0.7
		self.height = w * 0.7
	
class Cuoricino(Image):
	# placeholder per Cuoricino definito in kv
	# simbolo grafico che indica una risposta esatta
	# def __init__(self, **kwargs):
	def __init__(self, w):
		super(Cuoricino, self).__init__()
		#Log.info(**kwargs)
		self.width = w
		self.height = w
	

class Aeroplano(Image):
	# Visualizza dei semplici messaggi sullo schermo
	velocita = 3
	sound_motore   = SoundLoader.load('data/aeroplano.wav')

	def decolla(self, plane):
		# posiziona l'aeroplano ed inizia l'animazione del movimento
		# plane: nome del file grafico da usare. uno per ogni messaggio
		Log.info("Aereo inizia volo")		
		self.source = 'data/' + plane + '.png'
		self.sound_motore.volume = 0.5
		self.sound_motore.play()
		self.pos = (self.parent.width - 100, self.parent.height/4)
		self.height = '100dp' # visualizza l'aeroplano nascosto
		self.vola(None,None)

	def vola(self, animation, widget):
		Log.info("Animazione start {}".format(self.velocita))
		#self.top = 0
		anim = Animation(x=-self.width, d=self.velocita)
		anim.start(self)

class Palloncino(Widget):
	# Palloncino definito in kv con le possibili risposte
	value         = 0 # valore stampato sul palloncino
	velocita      = 8 # velocita' d'ascensione del palloncino (in secondi)
	sound_wrong   = SoundLoader.load('data/wrong.wav') # effetto sonoro in caso di risposta errata
	sound_correct = SoundLoader.load('data/correct.wav') # effetto sonoro in caso di risposta esatta
	passaggi      = 0 # conta il numero di passaggi del palloncino
	corretto      = False # indica se il palloncino contiene il valore corretto dell'operazione

	def muovi(self, animation, widget):
		Log.info("Animazione start {}".format(self.velocita))
		self.top = 0
		anim = Animation(y=self.parent.top, d=self.velocita)
		anim.bind(on_complete=self.muovi)
		anim.start(self)

	def on_touch_down(self, touch):
		# gestisce il touch/click sul palloncino		
		if self.collide_point(*touch.pos) and not self.disabled:
			Log.info("Giocatore ha selezionato palloncino con valore {}".format(self.value))
			if self.parent.updateTesto(self.value):
				Log.info("Risposta esatta")
				self.sound_correct.play() # True = risposta esatta
			else:
				Log.info("Risposta errata")
				self.sound_wrong.play() # True = risposta errata
			return True
	
	def oscura(self, dt):
		# spegne l'illuminazione del palloncino
		if self.corretto == True:
			self.ids.palloncino_label.text = "[color=ffffff]" + str(self.value) + "[/color]"

	def illumina(self):
		# se il palloncino contiene il valore corretto lo illumina con la luce viola
		if self.corretto == True:
			self.ids.palloncino_label.text = "[color=#e006e8]" + str(self.value) + "[/color]"
			Clock.schedule_once(self.oscura, 3)

	def on_pos(self,obj,position):
		if (int(position[1]) == self.parent.top):
			self.passaggi += 1 # conta il numero di volte che il palloncino raggiunge il top dello schermo
			Log.info(self.passaggi)
			if self.passaggi == 3: # ogni 3 passaggi illumona il palloncino
				Log.info("Suggerimento")
				self.illumina()
				self.passaggi = 0
		
	def stampa_valore(self):
		# visualizza il valore assegnato al palloncino sul palloncino
		self.ids.palloncino_label.text = str(self.value)


class jMathGame(FloatLayout):
	# classe principale del gioco. gestisce tutti gli aspetti del gioco e l'avanzamento tra i livelli
	# al giocatore vengono richieste delle semplici operazioni elemntari (10) per ogni livello
	# i possibili risultati sono stampati su tre palloncini che volano verso l'alto
	# un solo palloncino ha stampato il valore esatto dell'operazione
	# se il giocatore seleziona il palloncino con il risultato corretto viene aggiuntpo un cuoricino al punteggio
	# in caso contrario viene aggiunto un pollice verso al punteggio  e il risultato corretto viene visualizzato
	# in questo modo il giocatore in caso di errore puo' apprendere il risultato corretto e quindi avanzare successivamente ai livelli superiori
	# dopo aver risposto a 10 operazioni il livello finisce
	# se tutte le risposte sono corrette si avanza al livello successivo che implica un operatore diverso
	# in caso contrario il livello e l'operatore associato ricomincia dall'inizio
	# una volta terminato il 4 ed ultimo livello, il gioco riprende dal livello 1 ma la velocita' dei palloncini aumenta e di conseguenza la difficolta' del livello
	# il gioco non finisce mai. chiaramente ad un certo punto la velocita' dei palloncini sara' cosi' alta da rendere praticamente impossibile accedere al livello successivo
	img_bg      = ObjectProperty(None)
	palloncino1 = ObjectProperty(None)
	palloncino2 = ObjectProperty(None)
	palloncino3 = ObjectProperty(None)
	testo       = ObjectProperty(None)
	overlay     = ObjectProperty(None)
	aeroplano   = ObjectProperty(None)
	sound_track = SoundLoader.load('data/music.wav') # colonna sonora
	numero_sx   = 0 # primo valore dell'operazione
	numero_dx   = 0 # secondo valore dell'operazione
	risultato_palloncino = 0 # contiene il valore del palloncino selezionato dal giocatore
	punteggio   = 0 # punteggio per ogni livello
	operatore   = '+' # operatore da usare per un dato livello (+,-,x,: valori accettati)
	livello     = 1 # livello corrente del gioco
	numero_operazioni         = 0 # numero operazione eseguita. serve a contare lo stato di progresso in un livello
	numero_operazioni_livello = 10 # numero di operazioni da risolvere per ogni livello ed operatore
	risultato_operazione = 0 # risultato operazione corrente
	colore_risultato_corretto = "098e10" 
	colore_risultato_errato   = "ff0000"
	punteggio_icon_w = 0 # usato per adattare le dimensioni del cuoricino e del pollice in base allo schermo
	data_store = 0 # JSON datastore per memorizzare i punteggi per ogni giorno
	current_date = 0 # data corrente
			

	def __init__(self, **kwargs):
		super(jMathGame, self).__init__(**kwargs)
		# creo una lista di palloncini per comodita'
		self.palloncini  = [self.palloncino1, self.palloncino2, self.palloncino3]
		self.current_date = datetime.now().strftime('%Y-%m-%d')
		self.data_store = JsonStore('jmath_store.json')
		if self.current_date not in self.data_store:
			self.data_store[self.current_date] = {'+': {'cuoricino':0, 'pollice':0}, '-': {'cuoricino':0, 'pollice':0}, 'x': {'cuoricino':0, 'pollice':0}, ':': {'cuoricino':0, 'pollice':0}}
			
	def soundtrack_suona(self):
		# imposta la colonna sonora e la suona
		Log.info("Suona colonna sonora")
		self.sound_track.loop = True
		self.sound_track.volume = 0.1
		self.sound_track.play()

	def soundtrack_silenzio(self):
		# ferma la colonna sonora
		Log.info("Stop colonna sonora")
		self.sound_track.stop()

	def enable_palloncini(self, status):
		# abilita i palloncini in base al valore di status
		# status = True palloncini abilitati ed attivi
		Log.info("enable_palloncino = {}".format(status))
		for p in self.palloncini:
			p.disabled = not status

	def esegui_operazione(self):
		# esegue la specifica operazione su due valori in base all'operatore selezionato dal livello di gioco
		return {"+": (lambda x,y: x+y), "-": (lambda x,y: x-y), "x": (lambda x,y: x*y), ":": (lambda x,y: x//y)}[self.operatore](self.numero_sx, self.numero_dx) 
		
	def testo_operazione(self, stato, valore):
		# scrive il testo dell'operazione
		# stato = True il risultato viene scritto in verde altrimenti in rosso
		# valore: valore da visualizzare
		color = self.colore_risultato_corretto if stato else self.colore_risultato_errato
		return "[color=000000]" + str(self.numero_sx) + ' ' + self.operatore + ' ' + str(self.numero_dx) + ' = ' + "[/color]" + "[color=" + color + "]" + str(valore) + "[/color]"
	
	def update_punteggio(self, tipo, valore):
		# aggiorna la barra del punteggio
		# tipo = True visualizza un Cuoricino ed incrementa il punteggio
		# tipo = False visdualizza un pollice verso
		Log.info("Aggiornamento barra punteggio {} - {}".format(tipo, valore))
		punteggi = self.data_store[self.current_date] # preleva i punteggi della giornata
		if tipo:
			widget = Cuoricino(self.punteggio_icon_w)
			self.punteggio += 1
			punteggi[self.operatore]['cuoricino'] += 1 # memorizza il nuovo valore per l'operatore in corso
		else:
			widget = Pollice(self.punteggio_icon_w)
			punteggi[self.operatore]['pollice'] += 1

		self.data_store[self.current_date] = punteggi # salva il punteggio aggiornato
		self.testo.text = self.testo_operazione(tipo, valore)
		self.ids.barra_punteggio.add_widget(widget)

	def updateTesto(self, risultato_palloncino):
		Log.info("updateTesto - {}".format(risultato_palloncino))
		self.risultato_palloncino = risultato_palloncino # valore selezionato dal giocatore
		self.enable_palloncini(False) # disabilita i palloncini 

		#risultato_operazione = self.esegui_operazione() # esegue l'operazione richiesta al giocatore
		risultato_operazione = self.risultato_operazione # esegue l'operazione richiesta al giocatore
		if  risultato_operazione == risultato_palloncino:
			# risposta esatta
			self.update_punteggio(True, risultato_operazione)
			Clock.schedule_once(self.iniziaLivello, 3) # aspetta 3 secondi per ricominciare il livello
			return True
		else:
			# risposta errata
			self.update_punteggio(False, risultato_palloncino)
			Clock.schedule_once(self.showRightValue, 3) # aspetta 3 secondi per visualizzare il risultato corretto dell'operazione
			return False	
	
	def showRightValue(self, dt):
		# visualizza il risulatto corretot dell'operazione
		# permette al giocatore di apprendere come avanzare nei livelli
		Log.info("Visualizza valore corretto")
		#self.testo.text = self.testo_operazione(True, self.esegui_operazione())
		self.testo.text = self.testo_operazione(True, self.risultato_operazione)
		Clock.schedule_once(self.iniziaLivello, 3) # # aspetta 3 secondi per ricominciare il livello

	def estrai_valori(self, tipo):
		# semplice logica di estrazione dei valori per l'operazione e per i palloncini
		# tipo = True esegue estrazione per i valori dell'operazione
		# tipo = False esegue estrazione per i valori dei palloncini
		# restituisce una coppia di valori valore1, valore2		
		while True: # estrae finche' le condizioni non sono rispettate
			# seleziona 2 valori a casa tra 1 e 10
			valore1 = random.randint(1, 10)
			valore2 = random.randint(1, 10)
			Log.info("Estrazione valori {}-{}-{}".format(tipo,valore1, valore2))
			# se estrazione per palloncino i due valori devono essere diversi
			if not tipo:
				# if valore1 != valore2:
				if (valore1 != valore2) and (valore1 != self.risultato_operazione) and (valore2 != self.risultato_operazione):
					return valore1,valore2
			else:
				# estrazione per + e x non ci sono vincoli
				if self.operatore == '+' or self.operatore == 'x':
					return valore1,valore2
				# estrazione per '-' la sottrazione deve essere positiva
				elif self.operatore == '-':
					if valore1 >= valore2:
						return valore1,valore2
				# estrazione per ':' la divisione deve essere intera
				elif self.operatore == ':':
			 		if (divmod(valore1, valore2)[1] == 0):
			 			return valore1,valore2

	def pulisci_barra_punteggio(self):
		# pulisce la barra dei punteggi e resetta il punteggio ed il numero corrente di operazioni
		Log.info("Pulisci barra punteggio")
		widgets_punteggio = self.ids.barra_punteggio.children
		for i in range (0, len(widgets_punteggio)):
			self.ids.barra_punteggio.remove_widget(widgets_punteggio[0])
		self.numero_operazioni = 0
		self.punteggio = 0
		self.iniziaLivello(0)


	def decidi_operatore(self):
		# semplice mapping tra livello ed operatore
		if self.livello == 1:
			self.operatore = '+'
		elif self.livello == 2:
			self.operatore = '-'
		elif self.livello == 3:
			self.operatore = 'x'
		elif self.livello == 4:
			self.operatore = ':'
		Log.info("Operatore selezionato [{}]".format(self.operatore))

	def decidi_messaggio_aereo(self):
		# decide se visualizzare un messaggio aereo
		# se abbiamo effettuato la meta' delle operazioni ed il punteggio e' almeno la meta' + 1 
		# allora visualizza messaggio di apprezzamento
		# altrimenti visualizza messaggio di incoraggiamento
		Log.info("Decidi messaggio aereo")
		if self.numero_operazioni == (self.numero_operazioni_livello / 2):
				if self.punteggio >= (self.numero_operazioni_livello / 2) - 1:
					self.ids.aeroplano.decolla("plane1")
					Log.info("Aereo1 selezionato")
				else:
					self.ids.aeroplano.decolla("plane2")
					Log.info("Aereo2 selezionato")
		else:
			Log.info("Nessun aereo selezioanto")

		# se siamo all'ultima operazione ed ne abbiamo sbagliato solo 2
		# allora visualizza messaggio di apprezzamento
		# altrimenti visualizza messaggio di incoraggiamento
		if self.numero_operazioni == self.numero_operazioni_livello - 1:
			if self.punteggio >= (self.numero_operazioni_livello) - 2:
				self.ids.aeroplano.decolla("plane1")
				Log.info("Aereo1 selezionato")
			else:
				self.ids.aeroplano.decolla("plane2")
				Log.info("Aereo2 selezionato")
		else:
			Log.info("Nessun aereo selezioanto")

	def assegna_valore_palloncini(self):
		# estare a sorte quale palloncino contiene il valore corretto
		indice_palloncino_corretto = random.randint(0, 2)
		palloncino_corretto = self.palloncini[indice_palloncino_corretto]
		Log.info("Palloncino selezionato {}".format(indice_palloncino_corretto))

		# estra un valore a caso per i rimanenti palloncini
		valore_palloncini = self.estrai_valori(False)		
		Log.info("Valore palloncini estratti {}".format(valore_palloncini))	
			
		i=0
		# assegna il valore dell'operazione al palloncino estratto a sorte
		# palloncino_corretto.value = self.esegui_operazione()
		palloncino_corretto.value = self.risultato_operazione
		palloncino_corretto.corretto = True
		palloncino_corretto.passaggi = 0
		# assegna i valori estratti a sorte ai rimanenti pallonicni
		for palloncino in self.palloncini:
			if palloncino is not palloncino_corretto:
				palloncino.value = valore_palloncini[i]
				palloncino.corretto = False
				palloncino.passaggi = 0
				i += 1

	def stampa_valore_palloncini(self):
		# stampa il valore assegnato su ciascun palloncino
		Log.info("stampa_valore_palloncini")
		for palloncino in self.palloncini:
			palloncino.stampa_valore()

	def assegna_valori_operazione(self):
		# estrae a sorte i valori dell'operazioni
		self.numero_sx, self.numero_dx = self.estrai_valori(True)
		self.numero_operazioni += 1
		self.risultato_operazione = self.esegui_operazione()
		self.testo.text = self.testo_operazione(False, '?')
		Log.info("Valori operazione {}-{}".format(self.numero_sx, self.numero_dx))

	def iniziaLivello(self, dt):
		# gestione livelli gioco
		Log.info("-----------------")
		Log.info(self.size)
		Log.info(self.ids.testo.font_size)
		Log.info("livello = {}".format(self.livello))
		Log.info("punteggio = {}".format(self.punteggio))
		Log.info("numero_operazioni = {}".format(self.numero_operazioni))
		Log.info("numero_operazioni_livello = {}".format(self.numero_operazioni_livello))
		self.decidi_operatore() # assegna operatore in base al numero di livello
					
		# il giocatore non ha ancora completato il livello in corso
		if self.numero_operazioni < self.numero_operazioni_livello:
			self.decidi_messaggio_aereo()
			self.assegna_valori_operazione()
			self.assegna_valore_palloncini()
			self.stampa_valore_palloncini()
			self.enable_palloncini(True)
		else:
			# siamo alla fine del livello
			if self.punteggio == self.numero_operazioni_livello:
				self.livello += 1
				if self.livello == 5: 
					# ricomincia dal livello ed aumenta la difficolta'
					self.livello = 1
					self.aumenta_velocita_palloncini(0)
			self.pulisci_barra_punteggio()	

	def aumenta_velocita_palloncini(self, dt):
		# aumenta la velocita' di tutti i palloncini in modo uniforme
		Log.info("Aumenta velocita' palloncini")
		for palloncino in self.palloncini:
			palloncino.velocita -= 0.5

	def set_metrics(self, dt):
		w = self.size[0]
		h = self.size[1]
		Log.info("WIDTH={}".format(w))
		Log.info("HEIGHT={}".format(h))
		self.punteggio_icon_w  = w/10
		Log.info("VEL PALLONCINO={}".format(self.ids.palloncino1.velocita))
		self.iniziaLivello(0)

		for palloncino in self.palloncini:
			palloncino.muovi(None, None)
		
class jMathApp(App):
	def build(self):
		# metodo specifico di Kivy
		jMathG = jMathGame() # inizializzazione del core del gioco
		jMathG.soundtrack_suona() # fa' partire la colonna sonora di fondo		
		Clock.schedule_once(jMathG.set_metrics, 0) # uso questo trucchetto di chiamare il metodo tramite CLock per poter impostare le metrics
		return jMathG

if __name__ == '__main__':
	# inizializzazione del Log
	Log = KivyLoggerWrapper('jMath', True)
	Log.info("jMath {} starting on {}".format(__version__, platform))
	if platform == 'win':
		# su windows imposto la finestra ad una tipica risoluzione mobile
		Window.size = 540, 960
		#Window._set_top(50)
		Window.top = 50

	from kivy.metrics import Metrics 
	Log.info("DPI={}".format(Metrics.dpi))
	Log.info("DENSITY={}".format(Metrics.density))
	Log.info("FONT SCALE={}".format(Metrics.fontscale))
	Log.info("100 DP to PX={}".format(kivy.metrics.dp(100)))

	jMathApp().run()