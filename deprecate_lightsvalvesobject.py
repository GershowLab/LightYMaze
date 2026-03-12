import numpy as np
import random
import time
import RPi.GPIO as GPIO
from collections import Counter

class LightsValves:
	def __init__(self,red,ir,v1,v2,v3,v4,v5,v6):
		self.red = red
		self.ir = ir
		self.v1 = v1
		self.v2 = v2
		self.v3 = v3
		self.v4 = v4
		self.v5 = v5
		self.v6 = v6
		self.framecount = 0
		self.avoidtest = 0
		self.starttime = 0
		self.firstpass = 0
		self.vacpass = 0
		self.reciprocal_firstpass = 0
		self.rewardtime = 10.1
		self.avoidcode = 0
		self.choosecode = 1
		self.enter1code = 2
		self.enter2code = 3
		self.enter3code = 4
		self.leave1code = 5
		self.leave2code = 6
		self.leave3code = 7
                self.co2down1code = 8
                self.co2down2code = 9
                self.co2down3code = 10
                self.airdown1code = 11
                self.airdown2code = 12
                self.airdown3code = 13
                self.vacon1code = 14
                self.vacon2code = 15
                self.vacon3code = 16
                self.redoncode = 17
                self.backupcode = 18
                self.co2offallcode = 19
		self.leftcircle = 0
		self.backuptest = 0
		self.timestopped = 30 #seconds
		self.pttime = 15 #time for c02/air, so actual cycle = double this number
		self.waittime = 900 #15 minutes between spaced training

	def on(self, pin):
		GPIO.output(pin,GPIO.HIGH)
	def off(self, pin):
		GPIO.output(pin, GPIO.LOW)

	def training(self,ptnum,trainreps,rewardwhen):
		CO2 = [self.v1, self.v3, self.v5]
		vac = [self.v2, self.v4, self.v6]
		self.on(vac[1])
		for i in range(0,3):
			self.off(CO2[i])
                time.sleep(10)
		if rewardwhen == "A": #reward during all training cycles
			for j in range(0,ptnum):
				for i in range(1,3):
					self.on(CO2[i])
				self.on(self.red)
				time.sleep(self.pttime)
				self.off(self.red)
				for i in range(1,3):
					self.off(CO2[i])
				time.sleep(self.pttime)
		if rewardwhen == "F": #reward only during first X training cycles
			for j in range(0,trainreps):
				for i in range(1,3):
					self.on(CO2[i])
				self.on(self.red)
				time.sleep(self.pttime)
				self.off(self.red)
				for i in range(1,3):
					self.off(CO2[i])
				time.sleep(self.pttime)
			for j in range (0,ptnum-trainreps):
				for i in range(1,3):
					self.on(CO2[i])
				time.sleep(self.pttime)
				for i in range(1,3):
					self.off(CO2[i])
				time.sleep(self.pttime)
		if rewardwhen == "L": #reward only during last X training cycles
			for j in range(0,ptnum-trainreps):
				for i in range(1,3):
					self.on(CO2[i])
				time.sleep(self.pttime)
				for i in range(1,3):
					self.off(CO2[i])
				time.sleep(self.pttime)
			for j in range (0,trainreps):
				for i in range(1,3):
					self.on(CO2[i])
				self.on(self.red)
				time.sleep(self.pttime)
				self.off(self.red)
				for i in range(1,3):
					self.off(CO2[i])
				time.sleep(self.pttime)
		if rewardwhen == "B": #reward first X and last X cycles, with 18 extinction between
			for j in range(0,trainreps):
				for i in range(1,3):
					self.on(CO2[i])
				self.on(self.red)
				time.sleep(self.pttime)
				self.off(self.red)
				for i in range(1,3):
					self.off(CO2[i])
				time.sleep(self.pttime)
			for j in range (0,ptnum-trainreps):
				for i in range(1,3):
					self.on(CO2[i])
				time.sleep(self.pttime)
				for i in range(1,3):
					self.off(CO2[i])
				time.sleep(self.pttime)
			for j in range(0,trainreps):
				for i in range(1,3):
					self.on(CO2[i])
				self.on(self.red)
				time.sleep(self.pttime)
				self.off(self.red)
				for i in range(1,3):
					self.off(CO2[i])


	def spacedtraining(self,ptnum,spacedptnum,spacedtrainingreps):
		CO2 = [self.v1, self.v3, self.v5]
		vac = [self.v2, self.v4, self.v6]
		self.on(vac[1])
		for i in range(0,3):
			self.off(CO2[i])
                time.sleep(10)
		for j in range(0, spacedtrainingreps):
			print("block " + str(j))
			for k in range(0,spacedptnum):
				for i in range(1,3):
					self.on(CO2[i])
				self.on(self.red)
				time.sleep(self.pttime)
				self.off(self.red)
				for i in range(1,3):
					self.off(CO2[i])
				time.sleep(self.pttime)
			time.sleep(self.waittime)
			
	def co2offduringtraining(self,ptnum):
		CO2 = [self.v1, self.v3, self.v5]
		vac = [self.v2, self.v4, self.v6]
		for i in range(0,3):
			self.off(CO2[i])		
		self.on(vac[1])
		time.sleep(10)
		for i in range(0,ptnum):
			self.on(self.red)
			time.sleep(self.pttime)
			self.off(self.red)
			time.sleep(self.pttime)


	def phasetrain_co2first(self, ptnum):
		CO2 = [self.v1, self.v3, self.v5]
		vac = [self.v2, self.v4, self.v6]
		self.on(vac[1])
		for i in range(0,3):
			self.off(CO2[i])
		time.sleep(10)
		for j in range(0,ptnum):
			for i in range(1,3):
				self.on(CO2[i])
			time.sleep(7.5)
			self.on(self.red)
			time.sleep(7.5)
			for i in range(1,3):
				self.off(CO2[i])
			time.sleep(7.5)
			self.off(self.red)
			time.sleep(7.5)

	def phasetrain_airfirst(self, ptnum):
		CO2 = [self.v1, self.v3, self.v5]
		vac = [self.v2, self.v4, self.v6]
		self.on(vac[1])
		for i in range(0,3):
			self.off(CO2[i])
		time.sleep(10)
		self.on(self.red) #for the first cycle: reward starts 7.5s before co2 onset
		time.sleep(7.5)
		for j in range(1,ptnum):
			for i in range(1,3):
				self.on(CO2[i])
			time.sleep(7.5)
			self.off(self.red)
			time.sleep(7.5)
			for i in range(1,3):
				self.off(CO2[i])
			time.sleep(7.5)
			self.on(self.red)
			time.sleep(7.5)
		self.off(self.red)

	def longerairpaired(self, ptnum):
		CO2 = [self.v1, self.v3, self.v5]
		vac = [self.v2, self.v4, self.v6]
		self.on(vac[1])
		for i in range(0,3):
			self.off(CO2[i])
		time.sleep(10)
		for j in range(1,ptnum):
			for i in range(1,3):
				self.on(CO2[i])
			time.sleep(self.pttime)
			for i in range(1,3):
				self.off(CO2[i])
			self.on(self.red)
			time.sleep(self.pttime)
			self.off(self.red)
			time.sleep(45)

	def longerairunpaired(self, ptnum):
		CO2 = [self.v1, self.v3, self.v5]
		vac = [self.v2, self.v4, self.v6]
		self.on(vac[1])
		for i in range(0,3):
			self.off(CO2[i])
		time.sleep(10)
		for j in range(1,ptnum):
			for i in range(1,3):
				self.on(CO2[i])
			time.sleep(self.pttime)
			for i in range(1,3):
				self.off(CO2[i])
			time.sleep(45)
			self.on(self.red)
			time.sleep(self.pttime)
			self.off(self.red)


	def longerairtwoco2(self, ptnum):
		CO2 = [self.v1, self.v3, self.v5]
		vac = [self.v2, self.v4, self.v6]
		self.on(vac[1])
		for i in range(0,3):
			self.off(CO2[i])
		time.sleep(10)
		for j in range(1,ptnum):
			for i in range(1,3):
				self.on(CO2[i])
			time.sleep(self.pttime)
			for i in range(1,3):
				self.off(CO2[i])
			self.on(self.red)
			time.sleep(self.pttime)
			self.off(self.red)
			for i in range(1,3):
				self.on(CO2[i])
			time.sleep(self.pttime)
			for i in range(1,3):
				self.off(CO2[i])
			time.sleep(30)



        def reciprocal_pretrain(self,ptnum):
		CO2 = [self.v1, self.v3, self.v5]
		vac = [self.v2, self.v4, self.v6]
		self.on(vac[1])
		for i in range(0,3):
			self.off(CO2[i])		
		time.sleep(10)
		for j in range(0,ptnum):
			for i in range(0,3):
				self.on(CO2[i])
			time.sleep(self.pttime)
			for i in range(0,3):
				self.off(CO2[i])
			self.on(self.red)
			time.sleep(self.pttime)
			self.off(self.red)


	def run_test_noreward(self,prev_state, curr_state, nextclosest_state, decisionfile, decisionall,starttime,framecount,maggot,odorontime, valvelog):
		self.prev_state = prev_state
		self.curr_state = curr_state
		self.nextclosest_state = nextclosest_state
		self.decisionfile = decisionfile
		self.decisionall = decisionall
		self.starttime = starttime
		self.framecount = framecount
		self.maggot = maggot
		self.odorontime = odorontime
		self.valvelog = valvelog
		CO2 = [self.v1, self.v3, self.v5]
		vac = [self.v2, self.v4, self.v6]
		odorstate = []
		vacstate = []
		for i in range(0,3):
			b = GPIO.input(CO2[i])
			odorstate.append(b)
		for i in range(0,3):
			b = GPIO.input(vac[i])
			vacstate.append(b)
		if sum(vacstate) != 0:
                        vacon = vacstate.index(1) + 4
			vacchan = vacstate.index(1) + 1
		if sum(vacstate) == 0: 
			vacon = 0
		if self.prev_state - self.curr_state == -3 and self.curr_state != 3: #entering
			if sum(odorstate) == 1 and vacon != self.curr_state: #it's not reentering original channel, it's chosen a new channel
				self.vacpass = 0
				vartime = framecount
				timestamp = time.time() - starttime
                                timestring = str(vartime)
				print("Entering Circle "+ str(self.curr_state-3) + " " + timestring + ", time = " + str(timestamp))
				self.decisionall.append(["Entering Circle "+ str(self.curr_state-3),timestring,str(timestamp)])
				vac_on = self.curr_state - 4
				self.decisionall.append(["Vac On Channel "+ str(self.curr_state-3),timestring,str(timestamp)])
                                if sum(odorstate) != 0:
                                        co2channel = odorstate.index(1)+1
                                if sum(vacstate) != 0:
                                        prevvac = vacstate.index(1)+1
				for i in range(0,3):
					self.off(CO2[i])
					self.off(vac[i])
				self.on(vac[vac_on]) #Switch vacuum to the current state
				self.off(self.red)
				self.starttime = 0
				self.firstpass = 0
				self.avoidtest = 0
                                self.valvelog.append(["Vacuum Valve Closed - Channel "+ str(prevvac),timestring,str(timestamp)])
                                self.valvelog.append(["CO2 Valve Closed - Channel "+ str(co2channel),timestring,str(timestamp)])
                                self.valvelog.append(["Vacuum Valve Open - Channel "+ str(self.curr_state-3),timestring,str(timestamp)])
		if self.prev_state - self.curr_state == 3 and self.curr_state != 0: #leaving
			index = self.curr_state - 1 #python is zero indexed
			vac_state = self.curr_state
			choices = [1,2,3]
			del choices[index] #make sure CO2 choice isn't for the current channel
                        if vac[index] != 1 and self.vacpass == 0:
                        #if for some reason the wrong vacuum channel is on; like if the larva moved and it didn't record a decision, so still registering as being in another circle
                        #should not happen, but build in a failsafe just to make sure correct vac is always on!
                                self.vacpass = 1
                                vartime = framecount
                                timestring = str(vartime)
                                timestamp = time.time() - starttime
				if sum(vacstate) != 0:
                                        prevvac = vacstate.index(1)+1
					if prevvac != self.curr_state:
                               			self.valvelog.append(["Vacuum Valve Closed - Channel "+ str(prevvac),timestring,str(timestamp)])
                                for i in range(0,3):
                                        self.off(vac[i])
                                self.on(vac[index])
                                self.valvelog.append(["Vacuum Valve Open - Channel "+ str(self.curr_state),timestring,str(timestamp)])
			if sum(odorstate) == 0: #if CO2 is not on, pick one
                                vartime = framecount
                                timestring = str(vartime)
                                timestamp = time.time() - starttime
				print("Leaving Circle " + str(self.curr_state) + " " + timestring+ ", time = " + str(timestamp))
				odor_on = random.choice(choices) #randomly choose one channel to have co2
				print("CO2 + Air Down Channel " + str(odor_on) + " " + timestring + ", time = " + str(timestamp))
				self.on(CO2[odor_on-1])
				self.odorontime.append(timestamp)
				self.avoidtest = 0
				self.firstpass = 0
                                self.backuptest = 0 
				self.decisionall.append(["Leaving Circle " + str(self.curr_state),timestring, str(timestamp)])
				self.decisionall.append(["CO2 + Air Down Channel " + str(odor_on),timestring, str(timestamp)])
				self.valvelog.append(["CO2 Valve Open - Channel " + str(odor_on),timestring, str(timestamp)])
			if sum(odorstate) == 2: #both odorstate valves are on, bad! this shouldn't ever happen but built in a failsafe to reset system
				#shut off all CO2 valves
				for i in range(0,3):
					self.off(CO2[i])
				self.avoidtest = 0
				self.starttime = 0
				self.firstpass = 0
		if sum(odorstate) == 1: #If the odor is on, aka it's left a channel and might be making a decision
			correct = odorstate.index(1) + 1 #channel with co2
			vacchan = vacstate.index(1) + 1 #channel with vacuum aka the departure channel
			vaccircle = vacstate.index(1) + 4
			correctplus3 = correct + 3
			if correct == 1 and vacchan == 2:
				avoidchan = 3
			elif correct == 1 and vacchan == 3:
				avoidchan = 2
			elif correct == 2 and vacchan == 1:
				avoidchan = 3
			elif correct == 2 and vacchan == 3:
				avoidchan = 1
			elif correct == 3 and vacchan == 2:
				avoidchan = 1
			elif correct == 3 and vacchan == 1:
				avoidchan = 2
			else:
				avoidchan = 7
			if self.curr_state == correct and self.firstpass == 0: #if it's choosing co2 and computer hasn't yet marked it (make sure you don't double count)
                                vartime = framecount
                                timestamp = time.time() - starttime
				timestring = str(vartime)
				randomnum = random.random()
				print("Choose" + " " + timestring+ ", time = " + str(timestamp))
				self.decisionfile.append(1)
				self.decisionall.append((["Choose",timestring,str(timestamp)]))
				self.firstpass = 1
			if self.curr_state == avoidchan and self.avoidtest == 0: #if it's avoiding co2 and computer hasn't yet marked it (make sure you don't double count)
				vartime = framecount
				timestring = str(vartime)
				timestamp = time.time() - starttime
				print("Avoid" + " " + timestring+ ", time = " + str(timestamp))
				self.decisionfile.append(0)
				self.decisionall.append(["Avoid",timestring,str(timestamp)])
				self.avoidtest = 1
			if self.prev_state == 0 and self.curr_state == vacchan and self.backuptest == 0: #if it's backing up into original channel; don't count as a decision
                                #this doesn't affect any decision lists; just there for keeping track of location
				vartime = framecount
				timestring = str(vartime)
				timestamp = time.time() - starttime
				print("Back Up" + " " + timestring+ ", time = " + str(timestamp))
				self.decisionall.append(["Back Up",timestring,str(timestamp)])
				self.backuptest = 1
                        currenttime = time.time() - starttime
			odortime = self.odorontime[-1]
                        odorontotal = currenttime - odortime
			if odorontotal >= self.timestopped: #If CO2 has been on for longer than 30 seconds, turn off co2 and reset system
				vartime = framecount
				timestring = str(vartime)
				timestamp = time.time() - starttime
				if self.curr_state == 0:
				#only check where it's closest to if it's already in the center; this is to weed out when the larva is wandering in the circle
					if self.nextclosest_state == correct and self.firstpass == 0:
						print("Choose" + " " + timestring+ ", time = " + str(timestamp))
						self.decisionfile.append(1)
						self.decisionall.append((["Choose",timestring,str(timestamp)]))
						self.firstpass = 1
					if self.nextclosest_state == avoidchan and self.avoidtest == 0:
						print("Avoid" + " " + timestring+ ", time = " + str(timestamp))
						self.decisionfile.append(0)
						self.decisionall.append((["Avoid",timestring,str(timestamp)]))
						self.avoidtest = 1
					#if closest is the channel it came out of, then it hasn't chosen yet
					#do this because center of larva is being tracked; it's often in another channel but hasn't "clicked" in the code yet
					#states are sensitive in the middle of the maze, so will only select a decision if right on the cusp
				for i in range(0,3):
					self.off(CO2[i])
				print("Turn off CO2" + " " + timestring+ ", time = " + str(timestamp))
				self.decisionall.append((["Turn off CO2",timestring,str(timestamp)]))
				self.valvelog.append(["CO2 Valve Closed - Channel " + str(correct),timestring, str(timestamp)])
		if maggot == [-1, -1]: #If tracker has lost the larva, turn off any CO2
                        vartime = framecount
                        timestring = str(vartime)
                        timestamp = time.time() - starttime
                        if sum(odorstate) != 0:
                                for i in range(0,3):
                                        self.off(CO2[i])
                                print("Maggot Stop/NotFound - Turn off CO2" + " " + timestring+ ", time = " + str(timestamp))
                                self.decisionall.append((["Maggot Stop/NotFound - Turn off CO2",timestring,str(timestamp)]))
                                co2channel = odorstate.index(1)+1
                                self.valvelog.append(["CO2 Valve Closed - Channel " + str(co2channel),timestring, str(timestamp)])
		

	
	def offall(self):
		CO2 = [self.v1, self.v3, self.v5]
		vac = [self.v2, self.v4, self.v6]
		for i in range(0,3):
			self.off(CO2[i])
			self.off(vac[i])
		self.off(self.red)



