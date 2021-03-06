import netvend.netvend as netvend
import util
import sqlite3

def commandAdd(self, command):
	"""
		Add a new agent
		display the address and balance
		add the agent to the profiles
	"""
	if len(command) < 2:
		self.writeConsole('You need to supply a seed value')
		return
	self.agentSeed = command[1]
	util.getAgent(self)
	util.getAddress(self)
	util.initialTip(self)
	util.getBalance(self)
	self.agentNick = util.getNick(self, self.agentAddress)
	conn = sqlite3.connect('coinflow.db')
	c = conn.cursor()
	c.execute('select id from profiles where seed=?;', (command[1],))
	id = c.fetchone()
	if id is None:
		c.execute('insert into profiles (nick, seed) values (?,?);', (str(self.agentNick), str(self.agentSeed)))
	else:
		c.execute('update profiles set nick=? where seed=?;', (str(self.agentNick), str(self.agentSeed)))
	conn.commit()
	conn.close()
	self.writeConsole('Agent created.\nAddress is ' + str(self.agentAddress) + '\nBalance is ' + str(self.agentBalance))
	#check for new nicknames
	if util.pollAllPosts(self):
		util.checkNewNicks(self) 
	#self.poll()
	return
			
def commandLogin(self, command):
	"""
		Login as an existing agent
		can login using nick, address or seed.
		display the nickname (if present), address and balance
		check profiles and update or insert
	"""
	if len(command) < 2:
		self.writeConsole('You need to supply some detail for the agent you want to login as.\nCould be the agents nickname, address or seed')
		return
	seed = util.getSeedFromNick(command[1])
	if seed is False:
		self.agentSeed = command[1]
	else:
		self.agentSeed = seed
	util.getAgent(self)
	util.getAddress(self)
	util.getBalance(self)
	self.agentNick = util.getNick(self, self.agentAddress)
	conn = sqlite3.connect('coinflow.db')
	c = conn.cursor()
	c.execute('select id from profiles where seed=?;', (str(self.agentSeed),))
	id = c.fetchone()
	if id is None:
		c.execute('insert into profiles (nick, seed) values (?,?);', (str(self.agentNick), str(self.agentSeed)))
	else:
		c.execute('update profiles set nick=? where seed=?;', (str(self.agentNick), str(self.agentSeed)))
	conn.commit()
	conn.close()
	self.writeConsole((('Logged in as ' + str(self.agentNick)) if len(self.agentNick) > 0 else ('Logged in'))  + '.\nAddress is ' + str(self.agentAddress) + '\nBalance is ' + str(self.agentBalance))
	#check for new nicknames
	if util.pollAllPosts(self):
		util.checkNewNicks(self)
	#check for new posts from follows
	if util.pollFollowsPosts(self):
		util.displayFollowsPosts(self)
	#self.poll()
	return
			
def commandTip(self, command):
	"""
		Tip a nickname, address or post_id
		nickname tipping still in progress
	"""
	if self.agent is None:
		self.writeConsole('You don\'t have an active agent.\n/add an agent or /login in order to tip.')
		return
	elif len(command) < 2:
		self.writeConsole('You need to supply the detail of the agent or post you wish to tip.')
		return
	#command[1] could be an address, a nickname or a post id
	#we can identify addresses so do that first
	if util.isAddress(command[1]):
		#we know it's an address
		tipAddress = command[1]
		postId = None
	#otherwise test for nickname
	elif util.getAddressFromNick(command[1]) is not False:
		tipAddress = util.getAddressFromNick(command[1])
		postId = None
	#all it can be after that is a post id
	else:
		tipAddress = util.getAddressFromPostID(self, command[1])
		if tipAddress is False:
			self.writeConsole('Tip Failed - ' + command[1] + ' was not a nickname, address or post id')
			return
		postId = command[1]
	try:
		response = self.agent.tip(tipAddress, int(self.tipAmount), postId)
		if response['success'] == 1:
			try:
				self.agentBalance = self.agent.fetch_balance()
			except netvend.NetvendResponseError as e:
				self.agentBalance = 0
			self.writeConsole('Tip successful.\nTip ID : ' + str(response['command_result']) + ' - New Balance : ' + str(self.agentBalance))
		else:
			self.writeConsole('Tip Failed')
			return
	except netvend.NetvendResponseError as e:
		self.writeConsole('Tip failed - ' + str(e))
	return
	
def commandGetTipAmount(self, command):
	"""
		display the current tip amount
	"""
	if self.agent is None:
		self.writeConsole('You don\'t have an active agent.\n/add an agent or /login in order to view tip information.')
		return
	self.writeConsole('Current Tip Amount is ' + str(self.tipAmount) + ' musat')
	return

def commandSetTipAmount(self, command):
	"""
		set the current tip amount
		only in musat for the moment
	"""
	if self.agent is None:
		self.writeConsole('You don\'t have an active agent.\n/add an agent or /login in order to set tip information.')
		return
	if len(command) < 2:
		self.writeConsole('You need to supply the new tip amount in musat.')
		return
	self.tipAmount = command[1]
	self.writeConsole('Tip amount has been set to ' + str(command[1]) + ' musat.')
	return
	
def commandBalance(self, command):
	"""
		display the balance of the currently logged in agent
	"""
	if self.agent is None:
		self.writeConsole('You don\'t have an active agent.\nYou need to be logged in to view your balance.') 
		return
	util.getBalance(self)
	self.writeConsole('Balance is ' + str(self.agentBalance))
	return
			
def commandPost(self, command):
	"""
		Post a message to netvend
	"""
	if self.agent is None:
		self.writeConsole('You don\'t have an active agent.\n/add an agent or /login in order to post.') 
		return
	if len(command) < 2:
		self.writeConsole('You need to supply the message to post.')
		return
	try:
		response = self.agent.post('post:' + command[1])
		if response['success'] == 1:
			self.writeConsole('(' + str(response['command_result']) + ') >> ' + str(command[1]))
		else:
			self.writeConsole('Post failed')
	except netvend.NetvendResponseError as e:
		self.writeConsole('Post failed - ' + str(e))
	return
		
def commandHistory(self, command):
	"""
		Display the last ten posts for the specified user
		the users current agents posts are shown if no address/nick is given
	"""
	if self.agent is None:
		self.writeConsole('You don\'t have an active agent.\n/add an agent or /login in order to view history.') 
		return
	if len(command) < 2:
		address = self.agentAddress
		nick = self.agentNick
	else:
		address = util.getAddressFromNick(command[1])
		if address is False:
			address = command[1]
			nick = command[1]
		else:
			address = address
			nick = command[1]
	self.writeConsole('\n== Last 10 Posts for ' + nick + ' ==\n')
	query = "select posts.post_id, posts.data, history.fee from posts inner join history on posts.history_id = history.history_id where posts.address = '" + str(address) + "' order by posts.ts asc limit 10"
	rows = util.putQuery(self, query)
	if rows is False:
		self.writeConsole('No posts to display')
		return
	for row in rows['rows']:
		if 'post:' in row[1]:
			post = row[1].split(':', 1)[1]
		else:
			post = row[1]
		self.writeConsole('Post ID: ' + str(row[0]) + ' Fee: ' + str(row[2]) + '\n>> ' + str(post) + '\n')
	return
			
def commandNick(self, command):
	"""
		set a nickname for the user
		nickname needs to be unique
		update profile
		update the list of nicks first
	"""
	if self.agent is None:
		self.writeConsole('You don\'t have an active agent.\n/add an agent or /login in order to set your nickname.') 
		return
	if len(command) < 2:
		self.writeConsole('You need to specify a nickname')
		return
	#update nicknames
	if util.pollAllPosts(self):
		util.checkNewNicks(self)
	util.getAllNicks(self)
	if command[1] in self.allNicks:
		self.writeConsole(command[1] + ' is already taken as a nickname.')
		return
	try:
		response = self.agent.post('nick:' + command[1])
		if response['success'] == 1:
			self.writeConsole('(' + str(response['command_result']) + ') >> Set nickname to ' + str(command[1]))
			self.agentNick = command[1]
			conn = sqlite3.connect('coinflow.db')
			c = conn.cursor()
			c.execute('select id from profiles where seed=?;', (str(self.agentSeed),))
			id = c.fetchone()
			if id is None:
				c.execute('insert into profiles (nick, seed) values (?,?);', (str(self.agentNick), str(self.agentSeed)))
			else:
				c.execute('update profiles set nick=? where seed=?;', (str(self.agentNick), str(self.agentSeed)))
			conn.commit()
			conn.close()
		else:
			self.writeConsole('Setting nick failed')
	except netvend.NetvendResponseError as e:
		self.writeConsole('Setting nick failed - ' + str(e))
	return

def commandListAgents(self, command):
	"""
		List all users in the system
		update the list of nicks first
	"""
	if self.agent is None:
		self.writeConsole('You don\'t have an active agent.\n/add an agent or /login in order to list agents.') 
		return
	#update nicknames
	if util.pollAllPosts(self):
		util.checkNewNicks(self)
	self.writeConsole('\n== Agents ==\n')
	util.getAllNicks(self)
	for nick in self.allNicks:
		self.writeConsole(nick)
	return
	
def commandFollow(self, command):
	"""
		Follow the specified agent
		can specify address or nick
		update the list of nicks first
	"""
	if self.agent is None:
		self.writeConsole('You don\'t have an active agent.\n/add an agent or /login in order to follow agents.') 
		return
	if len(command) < 2:
		self.writeConsole('You need to specify an agent to follow')
		return
	#update nicknames
	if util.pollAllPosts(self):
		util.checkNewNicks(self)
	conn = sqlite3.connect('coinflow.db')
	c = conn.cursor()
	if util.isAddress(command[1]):
		query = "select address from accounts where address = '" + command[1] + "';"
		rows = util.putQuery(self, query)
		if rows is False:
			self.writeConsole('Couldn\'t find agent ' + command[1])
			return
		address = command[1]
		nick = util.getNick(self, address)
	else:
		c.execute('select address from nicks where nick=?;', (command[1],))
		address = c.fetchone()
		if address is None:
			self.writeConsole('Couldn\'t find agent ' + command[1])
			return
		address = address[0]
		nick = command[1]
	c.execute("select id from follows where address = ?;", (str(address),))
	id = c.fetchone() 
	if id is None:
		c.execute("insert into follows (nick, address, account) values (?,?,?);", (str(nick), str(address), str(self.agentAddress)))
	else:
		c.execute("update follows set nick=? where address=? and account=?;", (str(nick), str(address), str(self.agentAddress)))
	conn.commit()
	conn.close()
	self.writeConsole('You are now following ' + nick)
	return
	
def commandListFollows(self, command):
	"""
		List all the agents you are following
		update the list of nicks first
	"""
	if self.agent is None:
		self.writeConsole('You don\'t have an active agent.\n/add an agent or /login in order to list the agents you follow.') 
		return
	follows = util.getfollows(self)
	if not follows:
		self.writeConsole('You don\'t follow anyone yet')
		return
	self.writeConsole('\n== Following ==\n')
	for follow in follows:
		self.writeConsole(follow[0])
	return

def commandListProfiles(self, command):
	"""
		list the profiles of the current user
		each profile has been logged into at least once
		you don't need to be logged in to view profiles 
	"""
	conn = sqlite3.connect('coinflow.db')
	c = conn.cursor()
	c.execute('select nick from profiles;')
	profiles = c.fetchall()
	conn.close()
	if not profiles:
		self.writeConsole('You don\'t have any profiles.\nAdd an agent to add a profile.')
		return
	self.writeConsole('\n== Profiles ==\n')
	for profile in profiles:
		self.writeConsole(profile[0])
	return
			
		
	
